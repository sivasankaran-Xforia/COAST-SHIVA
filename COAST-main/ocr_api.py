#!/usr/bin/env python3
"""
FastAPI: Engineering Drawing OCR (pdf2image + Tesseract) with robust Title/Length/BOM

Install (once):
  pip install fastapi uvicorn pdf2image pytesseract pillow

Also install Poppler (for pdf2image) and Tesseract OCR:
  macOS:   brew install poppler tesseract
  Ubuntu:  sudo apt-get install -y poppler-utils tesseract-ocr
  Windows: install Poppler for Windows + Tesseract; then set paths below or via env vars.

Run:
  uvicorn ocr_api_pdf2image:app --reload
Open Swagger UI:
  http://127.0.0.1:8000/docs
"""

import os
import re
from typing import Any, Dict, List, Tuple

from fastapi import FastAPI, UploadFile, File, Query, HTTPException
from fastapi.responses import JSONResponse

from pdf2image import convert_from_bytes
import pytesseract
from pytesseract import Output
from PIL import Image, ImageOps, ImageEnhance, ImageFilter

# ---------- Optional Windows paths ----------
# pytesseract.pytesseract.tesseract_cmd = r"C:\Program Files\Tesseract-OCR\tesseract.exe"
# POPPLER_PATH = r"C:\path\to\poppler-xx\Library\bin"  # folder containing pdftoppm.exe
POPPLER_PATH = os.environ.get("POPPLER_PATH")  # or set env var before running



# ========================== Image preprocessing ==========================
def preprocess(img: Image.Image, enhance: bool = True) -> Image.Image:
    g = img.convert("L")
    if not enhance:
        return g
    g = ImageOps.autocontrast(g, cutoff=1)
    g = ImageEnhance.Contrast(g).enhance(1.4)
    g = ImageEnhance.Sharpness(g).enhance(1.2)
    g = g.filter(ImageFilter.MedianFilter(size=3))
    return g

# ============================== OCR helpers ==============================
def ocr_page_text(img: Image.Image, psm: int) -> str:
    return pytesseract.image_to_string(img, lang="eng", config=f"--psm {psm}")

def ocr_page_data(img: Image.Image, psm: int) -> Dict[str, List[Any]]:
    return pytesseract.image_to_data(img, lang="eng", config=f"--psm {psm}", output_type=Output.DICT)

# ============================== Title logic ==============================
TITLE_KEYWORDS = r'(assembly|coupling|gear|shaft|housing|bracket|plate|adapter|flange|spacer|frame|mount)'
NEG_TITLE_WORDS = r'(torque|n-?m|rpm|speed|weight|mass|power|hp|kw|tolerance|scale|sheet|rev(?:ision)?|note|material|finish|coating|treat)'

def build_lines_from_data(data: Dict[str, List[Any]]) -> List[Dict[str, Any]]:
    n = len(data["text"])
    lines: Dict[Tuple[int, int, int], Dict[str, Any]] = {}
    for i in range(n):
        if int(str(data["conf"][i] or "-1")) < 0:
            continue
        t = (data["text"][i] or "").strip()
        if not t:
            continue
        key = (data["block_num"][i], data["par_num"][i], data["line_num"][i])
        left, top = int(data["left"][i]), int(data["top"][i])
        width, height = int(data["width"][i]), int(data["height"][i])
        right, bottom = left + width, top + height
        if key not in lines:
            lines[key] = dict(words=[], left=left, top=top, right=right, bottom=bottom, max_h=height)
        else:
            L = lines[key]
            L["left"] = min(L["left"], left)
            L["top"] = min(L["top"], top)
            L["right"] = max(L["right"], right)
            L["bottom"] = max(L["bottom"], bottom)
            L["max_h"] = max(L["max_h"], height)
        lines[key]["words"].append(t)
    out = []
    for L in lines.values():
        out.append({
            "text": " ".join(L["words"]).strip(),
            "left": L["left"], "top": L["top"], "right": L["right"], "bottom": L["bottom"],
            "max_h": L["max_h"]
        })
    return out

def pick_title_from_lines(lines: List[Dict[str, Any]], page_w: int, page_h: int) -> str | None:
    best, best_score = None, -1e9
    for L in lines:
        t = L["text"]
        if not (6 <= len(t) <= 80):
            continue
        # exclude non-titles
        if re.search(r'\b(BILL OF MATERIALS|BOM|SCALE|SHEET|REV(?:ISION)?)\b', t, re.I):
            continue
        if re.search(r'\b(PART\s*NO(?:\.|:)?|P/?N)\b', t, re.I):
            continue
        if not re.search(TITLE_KEYWORDS, t, re.I):
            continue
        penalty = -2.0 if re.search(NEG_TITLE_WORDS, t, re.I) else 0.0
        if ":" in t:
            penalty -= 0.6
        cx = (L["left"] + L["right"]) / 2
        cy = (L["top"] + L["bottom"]) / 2
        dx = abs(cx - page_w/2) / (page_w/2 + 1e-6)
        dy = abs(cy - page_h/2) / (page_h/2 + 1e-6)
        dist = (dx**2 + dy**2) ** 0.5
        center_score = 1.2 - dist
        height_score = L["max_h"] / 40.0
        score = center_score + height_score + penalty
        if score > best_score:
            best_score, best = score, t
    return best

def clean_title(title: str | None) -> str | None:
    if not title:
        return title
    title = re.sub(r'\b(?:PART\s*(?:NO\.?|NUMBER)|P/?N)\s*[:#-]?\s*[A-Z0-9.\-_/]+', '', title, flags=re.I)
    title = re.sub(r'\bBOM\b.*$', '', title, flags=re.I)
    title = re.sub(r'[\s\-\|:]+$', '', title).strip()
    title = re.sub(r'\s{2,}', ' ', title)
    return title or None

def fallback_title_from_text(full_text: str) -> str | None:
    lines = [ln.strip() for ln in full_text.splitlines() if ln.strip()]
    cands = []
    for ln in lines:
        if not (6 <= len(ln) <= 80):
            continue
        if not re.search(TITLE_KEYWORDS, ln, re.I):
            continue
        if re.search(NEG_TITLE_WORDS, ln, re.I):
            continue
        if re.search(r'\b(BOM|SHEET|SCALE|PART\s*NO|P/?N)\b', ln, re.I):
            continue
        cands.append(ln)
    if not cands:
        return None
    # prefer more uppercase (common on titles) and earlier appearance
    cands.sort(key=lambda s: (-(sum(ch.isupper() for ch in s) / max(1, len(s))), len(s)))
    return clean_title(cands[0])

# ============================ Field extraction ============================
def clean_person_name(s: str | None) -> str | None:
    if not s:
        return s
    s = s.replace("\n", " ")
    s = re.sub(r'[^A-Z.\s-]', ' ', s, flags=re.I)
    s = re.sub(r'\b(LINKED|BOM|CAD|ENG|QA|APPROVAL|APPROVED)\b', '', s, flags=re.I)
    s = re.sub(r'\s{2,}', ' ', s).strip(" .-")
    return s or None

def find_first(patterns: List[str], text: str) -> str | None:
    for pat in patterns:
        m = re.search(pat, text, re.IGNORECASE)
        if m:
            return m.group(m.lastindex or 0) if m.lastindex else m.group(0)
    return None

def extract_length(text: str) -> str | None:
    # direct forms
    m = find_first([
        r'\bOverall\s*Length\s*[:=\-]?\s*(\d+(?:\.\d+)?)\s*(mm|cm|in|")\b',
        r'\bLength\s*[:=\-]?\s*(\d+(?:\.\d+)?)\s*(mm|cm|in|")\b',
        r'\bL\s*[:=\-]?\s*(\d+(?:\.\d+)?)\s*(mm|cm|in|")\b',
        r'\bL\s*=\s*(\d+(?:\.\d+)?)\s*(mm|cm|in|")\b',
        r'\bL\.\s*(\d+(?:\.\d+)?)\s*(mm|cm|in|")\b'
    ], text)
    if m:
        return m
    # avoid spec-like units
    bad_ctx = re.compile(r'(?:N-?m|Nm|deg|°|kgf|MPa|bar)', re.I)
    meas = []
    for val, unit in re.findall(r'(\d+(?:\.\d+)?)\s*(mm|cm|in|")\b', text, re.I):
        snip_idx = text.find(f"{val} {unit}")
        ctx = text[max(0, snip_idx-10):snip_idx+10]
        if bad_ctx.search(ctx):
            continue
        meas.append((float(val), unit))
    if meas:
        def to_mm(v, u):
            u = u.lower()
            if u == 'mm': return v
            if u == 'cm': return v * 10
            if u in ('in', '"'): return v * 25.4
            return v
        meas.sort(key=lambda x: to_mm(*x), reverse=True)
        v, u = meas[0]
        return f"{v:g} {u}"
    # unitless L numbers
    m2 = re.search(r'(?:^|\b)L\s*[:=\-]?\s*(\d+(?:\.\d+)?)\b', text, re.I | re.M)
    if m2:
        return m2.group(1)
    return None

# ============================== BOM parsing ==============================
def group_by_line(data: Dict[str, List[Any]], y_tol: int = 6) -> List[List[Dict[str, Any]]]:
    words = []
    for i, t in enumerate(data["text"]):
        t = (t or "").strip()
        if not t:
            continue
        words.append({
            "text": t,
            "left": int(data["left"][i]),
            "top": int(data["top"][i]),
            "right": int(data["left"][i]) + int(data["width"][i]),
            "bottom": int(data["top"][i]) + int(data["height"][i]),
        })
    words.sort(key=lambda w: (w["top"], w["left"]))
    lines: List[List[Dict[str, Any]]] = []
    for w in words:
        if not lines:
            lines.append([w]); continue
        last = lines[-1][0]
        if abs(w["top"] - last["top"]) <= y_tol:
            lines[-1].append(w)
        else:
            lines.append([w])
    for ln in lines:
        ln.sort(key=lambda w: w["left"])
    return lines

def parse_bom_from_data(data: Dict[str, List[Any]]) -> List[Dict[str, str]]:
    lines = group_by_line(data)
    hdr_idx = None
    for i, ln in enumerate(lines):
        row_text = " ".join(w["text"] for w in ln)
        if re.search(r'\bITEM\b', row_text, re.I) and re.search(r'\bQTY\b', row_text, re.I):
            hdr_idx = i; break
    if hdr_idx is None:
        for i, ln in enumerate(lines):
            if re.search(r'BILL\s*OF\s*MATERIALS|^\s*BOM\s*$', " ".join(w["text"] for w in ln), re.I):
                hdr_idx = i + 1; break
    if hdr_idx is None:
        return []
    items: List[Dict[str, str]] = []
    for ln in lines[hdr_idx+1:]:
        row = [w["text"] for w in ln]
        row_text = " ".join(row)
        if re.search(r'\b(NOTES?|REV(?:ISION)?S?)\b', row_text, re.I):
            break
        if len(row) >= 4 and re.match(r'^\d{1,3}$', row[0]) and re.match(r'^\d{1,4}$', row[1]):
            items.append({"Item": row[0], "Qty": row[1], "Part No": row[2], "Description": " ".join(row[3:])})
        elif len(row) >= 3 and re.match(r'^\d{1,3}$', row[0]) and re.match(r'^\d{1,4}$', row[1]):
            items.append({"Item": row[0], "Qty": row[1], "Part No": "", "Description": " ".join(row[2:])})
    # de-dup
    seen, uniq = set(), []
    for r in items:
        key = (r["Item"], r["Qty"], r["Part No"], r["Description"])
        if key not in seen:
            seen.add(key); uniq.append(r)
    return uniq

def parse_bom_from_text(full_text: str) -> List[Dict[str, str]]:
    lines = [ln.strip() for ln in full_text.splitlines() if ln.strip()]
    start = None
    for i, ln in enumerate(lines):
        if re.search(r'\b(BOM|Bill of Materials?|BILL\s*OF\s*MATERIALS?)\b', ln, re.I):
            start = i; break
    if start is None:
        for i, ln in enumerate(lines):
            if re.search(r'\bITEM\b', ln, re.I) and re.search(r'\bQTY\b', ln, re.I):
                start = i; break
    if start is None:
        return []
    items: List[Dict[str, str]] = []
    for ln in lines[start+1:start+200]:
        if re.search(r'\b(NOTES?|REV(?:ISION)?S?)\b', ln, re.I):
            break
        parts = re.split(r'\s{2,}', ln)
        if len(parts) >= 4 and re.match(r'^\d{1,3}$', parts[0]) and re.match(r'^\d{1,4}$', parts[1]):
            items.append({"Item": parts[0], "Qty": parts[1], "Part No": parts[2], "Description": " ".join(parts[3:])})
        elif len(parts) >= 3 and re.match(r'^\d{1,3}$', parts[0]) and re.match(r'^\d{1,4}$', parts[1]):
            items.append({"Item": parts[0], "Qty": parts[1], "Part No": "", "Description": parts[2]})
    # de-dup
    seen, uniq = set(), []
    for r in items:
        key = (r["Item"], r["Qty"], r["Part No"], r["Description"])
        if key not in seen:
            seen.add(key); uniq.append(r)
    return uniq

# ============================= Core pipeline =============================
def process_pdf_bytes(filename: str, data: bytes, dpi: int = 300, max_pages: int | None = None,
                      enhance: bool = True, psm_primary: int = 6) -> Dict[str, Any]:
    images = convert_from_bytes(data, dpi=dpi, poppler_path=POPPLER_PATH)
    if max_pages:
        images = images[:max_pages]
    if not images:
        raise ValueError("No pages found in PDF")

    # 1) Build overall text with a primary PSM
    page_texts = [ocr_page_text(preprocess(im, enhance=enhance), psm=psm_primary) for im in images]
    full_text = "\n".join(page_texts)

    # 2) Title from page 1 using multiple PSM fallbacks
    title = None
    psm_candidates = [psm_primary, 4, 11]
    for psm in psm_candidates:
        data1 = ocr_page_data(preprocess(images[0], enhance=enhance), psm=psm)
        lines1 = build_lines_from_data(data1)
        w, h = images[0].size
        title = pick_title_from_lines(lines1, w, h)
        title = clean_title(title)
        if title:
            break
    if not title:
        title = fallback_title_from_text(full_text)

    # 3) Fields (Part No / Material / Date / DWG / CHK)
    material_line = find_first([
        r'\bMaterial\s*[:\-]?\s*([A-Za-z0-9\s\-/.,]+)',
        r'\bMATERIAL\s*[:\-]?\s*([A-Za-z0-9\s\-/.,]+)'
    ], full_text)
    material = re.sub(r'\bREV\b.*$', '', material_line, flags=re.I).strip(" :-") if material_line else None

    part_no = find_first([
        r'(?:Part\s*(?:No\.?|Number)|P/?N)\s*[:\-]?\s*([A-Z0-9\-_.]+)',
        r'^\s*P/N\s*[:\-]?\s*([A-Z0-9\-_.]+)'
    ], full_text)

    date = find_first([
        r'\bDate\s*[:\-]?\s*([0-3]?\d[./\-][0-1]?\d[./\-](?:\d{2}|\d{4}))',
        r'\bDATE\s*[:\-]?\s*([0-3]?\d[./\-][0-1]?\d[./\-](?:\d{2}|\d{4}))'
    ], full_text)

    drawn_by = find_first([
        r'\b(?:DWG\s*BY|DRAWN\s*BY|DRN)\s*[:\-]?\s*([A-Z.\s-]+)',
        r'\bDRAWN\s*[:\-]?\s*([A-Z.\s-]+)'
    ], full_text)
    drawn_by = clean_person_name(drawn_by)

    checked_by = find_first([
        r'\b(?:CHK\s*BY|CHECKED\s*BY|CHK\'?D\s*BY)\s*[:\-]?\s*([A-Z.\s-]+)',
        r'\bCHECKED\s*[:\-]?\s*([A-Z.\s-]+)'
    ], full_text)
    checked_by = clean_person_name(checked_by)

    # 4) Length
    length = extract_length(full_text)

    # 5) BOM from OCR geometry across pages; fallback to text if empty
    bom_all: List[Dict[str, str]] = []
    for im in images:
        d = ocr_page_data(preprocess(im, enhance=enhance), psm=psm_primary)
        bom_all.extend(parse_bom_from_data(d))
    if not bom_all:
        bom_all = parse_bom_from_text(full_text)

    fields = {
        "Part No": part_no,
        "Material": material,
        "Date": date,
        "DWG By / Drawn By": drawn_by,
        "CHK By / Checked By": checked_by,
        "Title / Part Name": title,
        "Length (heuristic)": length,
        "BOM": bom_all,
    }
    return {"fields": fields, "bom": bom_all}


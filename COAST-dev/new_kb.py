



import re, sys, pathlib, logging, logging.handlers
from typing import Any, Dict
import pandas as pd

COL_NUM = ["part number","part_number","partnumber","part id","part_id","partid","id","sg id","sgid","pn","code"]
COL_NAME = ["part name","part_name","partname","name","item","description","title"]
COL_DIM = ["dimension","dimensions","size","sizes","dim","dims"]

def _setup_logger(log_file=None, log_level="INFO"):
    lvl = getattr(logging, str(log_level).upper(), logging.INFO)
    logger = logging.getLogger("kb")
    if getattr(logger, "_is_setup", False):
        return logger
    logger.setLevel(lvl)
    fmt = logging.Formatter("%(asctime)s | %(levelname)s | %(message)s", "%Y-%m-%d %H:%M:%S")
    ch = logging.StreamHandler(sys.stdout)
    ch.setLevel(lvl); ch.setFormatter(fmt); logger.addHandler(ch)
    if log_file:
        fh = logging.handlers.RotatingFileHandler(log_file, maxBytes=2_000_000, backupCount=3, encoding="utf-8")
        fh.setLevel(lvl); fh.setFormatter(fmt); logger.addHandler(fh)
    logger._is_setup = True
    return logger

def _norm(s):
    return re.sub(r"\s+", " ", str(s).strip()).lower()

def _read_descriptor(text):
    fields = {}
    for line in text.splitlines():
        if ":" in line:
            k,v = line.split(":",1)
            fields[_norm(k)] = v.strip()
    pn = nm = dm = None
    for k in list(fields.keys()):
        if "part number" in k or k.strip() in {"number","id","code"}: pn = fields[k]
        if "part name" in k or k.strip()=="name": nm = fields[k]
        if "dimension" in k or k.strip() in {"size","sizes"}: dm = fields[k]
    return pn, nm, dm, text.strip()

_X_RE = re.compile(r"[x×X]")
_SEP_SPLIT_RE = re.compile(r"[\n;,/|]+")
_NUM_TOKEN_RE = re.compile(r"([0-9]+(?:\.[0-9]+)?)")

def _clean_unit_trailers(s):
    s = s.replace("mm","").replace("MM","")
    s = s.replace("inches","").replace("inch","").replace("in","")
    s = s.replace('"',"").replace("’","").replace("′","")
    return s

def _to_dim_canonical(s):
    if not s or _norm(s) in {"n/a","na","-","none"}: return ""
    s = s.replace(",", " ")
    s = _clean_unit_trailers(s)
    s = _X_RE.sub("x", s)
    s = re.sub(r"\b[mM]\s*", "", s)
    nums = _NUM_TOKEN_RE.findall(s)
    if not nums: return ""
    canon = [str(int(float(n))) if n.replace(".","",1).isdigit() else n for n in nums]
    return "x".join(canon)

def _explode_dim_cell(cell):
    if cell is None: return []
    raw = str(cell)
    chunks = []
    for part in _SEP_SPLIT_RE.split(raw):
        part = part.strip()
        if not part: continue
        subparts = re.split(r"\s{2,}|\t+", part) or [part]
        for sp in subparts:
            sp = sp.strip()
            if not sp: continue
            canon = _to_dim_canonical(sp)
            if canon: chunks.append(canon)
    if not chunks:
        canon = _to_dim_canonical(raw)
        if canon: chunks.append(canon)
    return chunks

def _safe_read_text(path, log):
    p = pathlib.Path(path)
    try:
        txt = p.read_text(encoding="utf-8")
    except UnicodeDecodeError:
        txt = p.read_text(encoding="utf-8-sig")
    log.info(f"Loaded descriptor from {path}")
    return txt

def _load_csv(path, log):
    try:
        df = pd.read_csv(path, dtype=str, keep_default_na=False)
    except UnicodeDecodeError:
        df = pd.read_csv(path, dtype=str, keep_default_na=False, encoding="utf-8-sig", engine="python")
    log.info(f"Loaded CSV: {path} with {len(df)} rows, {len(df.columns)} cols")
    return df

def _pick_cols(df, candidates):
    cols = [c for c in df.columns if _norm(c) in candidates]
    if cols: return cols
    return [c for c in df.columns if any(key in _norm(c) for key in candidates)]

def _match_df(df, part_number, part_name, dim_canon):
    num_cols = _pick_cols(df, set(COL_NUM))
    name_cols = _pick_cols(df, set(COL_NAME))
    dim_cols = _pick_cols(df, set(COL_DIM))
    masks = []
    if part_number and num_cols:
        v = _norm(part_number); m = False
        for c in num_cols: m = m | (df[c].astype(str).map(_norm)==v)
        masks.append(m)
    if part_name and name_cols:
        v = _norm(part_name); m = False
        for c in name_cols: m = m | (df[c].astype(str).map(_norm)==v)
        masks.append(m)
    if dim_canon and dim_cols:
        m = False
        for c in dim_cols:
            colmatch = df[c].astype(str).map(lambda x: dim_canon in _explode_dim_cell(x))
            m = m | colmatch
        masks.append(m)
    if not masks: return df.iloc[0:0]
    mask = masks[0]
    for m in masks[1:]: mask = mask | m
    return df[mask]

def _row_to_text(row):
    return "\n".join(f"{k.strip()}: {str(v).strip()}" for k,v in row.items())

def _any_exact_in_cols(df, value, coltype):
    if not value: return 0
    if coltype=="num":
        cols = _pick_cols(df, set(COL_NUM)); 
        if not cols: return 0
        v = _norm(value)
        return sum((df[c].astype(str).map(_norm)==v).sum() for c in cols)
    if coltype=="name":
        cols = _pick_cols(df, set(COL_NAME)); 
        if not cols: return 0
        v = _norm(value)
        return sum((df[c].astype(str).map(_norm)==v).sum() for c in cols)
    cols = _pick_cols(df, set(COL_DIM))
    if not cols: return 0
    v = _to_dim_canonical(value)
    if not v: return 0
    return sum(df[c].astype(str).map(lambda x: v in _explode_dim_cell(x)).sum() for c in cols)

def _read_descriptor_from_dict(data: Dict[str, Any]):
    pn = data.get("Part No", data.get("part no"))
    nm = data.get("Title / Part Name", data.get("part name"))
    dm = data.get("Length (heuristic)", data.get("dimensions"))
    original_text = "\n".join(f"{k}: {v}" for k, v in data.items())
    return pn, nm, dm, original_text

def generate_report(
    descriptor_dict: Dict[str, Any],
    bom_csv=None,
    po_csv=None,
    vendor_csv=None,
    out_path=None,
    log_file=None,
    log_level="INFO"
):
    """
    Generates a comprehensive report by matching a descriptor dictionary (from a PDF)
    against three CSV files: BOM, purchase orders, and vendor data.
    
    The report consolidates relevant information for a part, which can then be
    used to provide context for an LLM-powered chatbot.
    
    Args:
        descriptor_dict (dict): A dictionary containing the part's descriptor (from PDF).
        bom_csv (str): Path to the Bill of Materials CSV.
        po_csv (str): Path to the Purchase Orders CSV.
        vendor_csv (str): Path to the Vendor Database CSV.
        out_path (str, optional): Path to save the generated report.
        log_file (str, optional): Path for the log file.
        log_level (str, optional): Logging level.
    
    Returns:
        str: The generated report as a text string.
    """
    log = _setup_logger(log_file, log_level)
    
    # Read descriptor from dictionary
    pn, nm, dm, original = _read_descriptor_from_dict(descriptor_dict)
    log.info("Using descriptor from dictionary")

    if not (bom_csv and po_csv and vendor_csv):
        raise ValueError("bom_csv, po_csv, vendor_csv are required")

    bom_df = _load_csv(bom_csv, log)
    po_df = _load_csv(po_csv, log)
    vendor_df = _load_csv(vendor_csv, log)
    sources = [("BOM", bom_df), ("PURCHASE_ORDERS", po_df), ("VENDOR_DATABASE", vendor_df)]

    dim_canon = _to_dim_canonical(dm) if dm else ""

    pn_hits_total = sum(_any_exact_in_cols(df, pn, "num") for _, df in sources)
    nm_hits_total = sum(_any_exact_in_cols(df, nm, "name") for _, df in sources)
    dm_hits_total = sum(_any_exact_in_cols(df, dm, "dim") for _, df in sources)

    if not pn and not nm and not dim_canon:
        log.error("Error in input file: Missing Part Number, Part Name, and Dimensions.")
    else:
        if pn and pn_hits_total == 0: log.error(f"Error in input file: Part Number not found → '{pn}'")
        if nm and nm_hits_total == 0: log.error(f"Error in input file: Part Name not found → '{nm}'")
        if dm and not dim_canon: log.error(f"Error in input file: Dimensions not parseable → '{dm}'")
        if dim_canon and dm_hits_total == 0: log.error(f"Error in input file: Dimensions not found → '{dim_canon}'")
        if ((pn and pn_hits_total>0) or (nm and nm_hits_total>0) or (dim_canon and dm_hits_total>0)):
            log.info("At least one valid field matched in the sources.")

    out = []
    out.append("===== INPUT DESCRIPTOR =====")
    out.append(original if original else "(empty)")
    out.append("")
    out.append(f"Resolved Part Number: {pn if pn else '(not provided)'}")
    out.append(f"Resolved Part Name  : {nm if nm else '(not provided)'}")
    out.append(f"Resolved Dimensions : {dim_canon if dim_canon else '(not provided)'}")
    out.append("")
    for label, df in sources:
        matches = _match_df(df, pn, nm, dim_canon)
        out.append(f"===== MATCHES IN {label} =====")
        if matches.empty:
            out.append("No matches.")
        else:
            for i,(_, r) in enumerate(matches.iterrows(), start=1):
                out.append(f"-- Match #{i}")
                out.append(_row_to_text(r))
                out.append("")
    report = "\n".join(out).rstrip()+"\n"
    if out_path:
        pathlib.Path(out_path).write_text(report, encoding="utf-8")
        log.info(f"Wrote report to {out_path}")
    return report
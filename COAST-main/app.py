import datetime
import json
import traceback
from typing import Dict, List
from urllib import request
from fastapi import FastAPI, HTTPException, UploadFile, File, Form
from fastapi.middleware.cors import CORSMiddleware
from starlette.middleware.wsgi import WSGIMiddleware
from pydantic import BaseModel
from fastapi.responses import HTMLResponse, PlainTextResponse
from plotly.utils import PlotlyJSONEncoder
from fastapi.responses import JSONResponse
from chatbot import process_chat_query
from pathlib import Path
import shutil
import pandas as pd
import numpy as np
import os

from dashboard import get_individual_chart_data
from chatbot_manufacturing import process_manufacturing_chat
from ocr_api import process_pdf_bytes
from new_kb import generate_report
# from db import run_dash
from db import app_d

app = FastAPI()
app.mount("/xforia-coast/dashboard", WSGIMiddleware(app_d.server))
origins = [ 
    "http://localhost",
    "http://localhost:8080",
    "http://127.0.0.1",
    "http://127.0.0.1:8000",
    "https://www.xforiacoast.com"
]

# Allow requests from your Git Pages frontend
app.add_middleware(
    CORSMiddleware,
    allow_origins= origins,  
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

UPLOAD_FOLDER = Path("./uploads")
UPLOAD_FOLDER.mkdir(exist_ok=True)
file_path = ""
 
LATEST_RESPONSE = {"response": ""}
MANUFACTURING_CONTEXT_FILE = None

# run_dash(debug=True,port=8051)

@app.post("/upload_excel/")
async def upload_excel(
    file: UploadFile = File(...), 
    organization_name: str = Form(...),
    owner_name: str = Form(...)
    ):
    file_path = UPLOAD_FOLDER / file.filename
    with open(file_path, "wb") as f:
        shutil.copyfileobj(file.file, f)

    global EXCEL_FILE 
    EXCEL_FILE = file_path

    # Convert Excel -> CSV (for chatbot) 
    df = pd.read_excel(file_path)
    csv_path = file_path.with_suffix(".csv")
    df.to_csv(csv_path, index=False)
    return {"status": "success", "file_path": str(file_path)}

class ChatRequest(BaseModel):
    query: str
    # conversation_history will be a list of dictionaries,
    # e.g., [{"role": "user", "content": "Hi"}, {"role": "assistant", "content": "Hello!"}]
    conversation_history: List[Dict[str, str]] = [] # Default to empty list if not provided


@app.post("/chat/demo")
async def chat(request:ChatRequest):
    global LATEST_RESPONSE

    # Load the most recent uploaded CSV
    files = [f for f in os.listdir(UPLOAD_FOLDER) if f.endswith(".csv")]
    if not files:
        return {"error": "No patient data uploaded yet."}
    #file_path = os.path.join(UPLOAD_FOLDER, files[-1])

    current_conversation_history = list(request.conversation_history) 
    current_conversation_history.append({"role": "user", "content": request.query})
    print(EXCEL_FILE)
    # Get chatbot response, passing the full conversation history from the request
    response = process_chat_query(request.query, EXCEL_FILE, current_conversation_history)

    #LATEST_RESPONSE["response"] = response 
    current_conversation_history.append({"role": "assistant", "content": response})
    LATEST_RESPONSE["response"] = response
    
    return LATEST_RESPONSE


@app.get("/chat")
async def get_chat():
    return LATEST_RESPONSE

def make_json_safe(obj):
    if isinstance(obj, np.ndarray):
        return obj.tolist()
    if isinstance(obj, dict):
        return {k: make_json_safe(v) for k, v in obj.items()}
    if isinstance(obj, list):
        return [make_json_safe(v) for v in obj]
    return obj

@app.get("/api/dashboard/", response_class=JSONResponse)
async def get_dashboard_charts():
    full_path = "/Users/harishreekarthik/Downloads/Xforia_COAST/demo/uploads/Xforia_Coast_Demo_15.xlsx"
    
    try:
        if not os.path.exists(full_path):
            return JSONResponse(content={"error": "File not found."}, status_code=404)
        
        charts_data = get_individual_chart_data(full_path)
        return JSONResponse(content={"charts": charts_data})
        
    except Exception as e:
        traceback.print_exc()
        return JSONResponse(content={"error": "An internal error occurred."}, status_code=500)
    

##### MANUFACTURING DEMO 


@app.post("/upload_cad_pdf/")
async def upload_cad_pdf(
    file: UploadFile = File(...)
):
    # Ensure the file has a .pdf extension
    if not file.filename.endswith('.pdf'):
        return {"status": "error", "message": "Invalid file type. Please upload a .pdf file."}

    # Save the uploaded file to disk
    file_path = UPLOAD_FOLDER / file.filename
    with open(file_path, "wb") as f:
        shutil.copyfileobj(file.file, f)
        
    # Read the file's content into memory from the saved path
    file_bytes = file_path.read_bytes()

    # Process the PDF file and extract information
    try:
        pdf_data_dict = process_pdf_bytes(file.filename, file_bytes)
        # Try to get Part No from the extracted data
        part_no = pdf_data_dict['fields'].get('Part No', '')
        
        # Generate a unique filename for the report, using Part No if available
        if part_no:
            llm_context_file = os.path.join(UPLOAD_FOLDER, f"llm_context_part_{part_no}.txt")
        else:
            timestamp = datetime.datetime.now().strftime("%Y%m%d%H%M%S")
            llm_context_file = os.path.join(UPLOAD_FOLDER, f"llm_context_{timestamp}.txt")
        
        # Generate the report for the LLM
        report_text = generate_report(
            descriptor_dict=pdf_data_dict['fields'],
            bom_csv=os.path.join(UPLOAD_FOLDER, "CAD_Parts_BOM_complete.csv"),
            po_csv=os.path.join(UPLOAD_FOLDER, "CAD_Parts_purchase_orders.csv"),
            vendor_csv=os.path.join(UPLOAD_FOLDER, "CAD_Parts_vendor_database.csv"),
            out_path=llm_context_file
        )
        
        global MANUFACTURING_CONTEXT_FILE
        MANUFACTURING_CONTEXT_FILE = llm_context_file

        return {"status": "success", "filename": file.filename, "extracted_data": pdf_data_dict}
    except Exception as e:
        return {"status": "error", "message": f"Error processing PDF: {e}"}


@app.post("/chat/manufacturing")
async def chat_manufacturing(request: ChatRequest):
    """Handles chatbot queries for the manufacturing project"""
    global LATEST_RESPONSE

    try:
        if not MANUFACTURING_CONTEXT_FILE or not os.path.exists(MANUFACTURING_CONTEXT_FILE):
            raise HTTPException(status_code=404, detail="No manufacturing data has been processed yet. Please upload a file first.")
        
        # Pass both the query and the conversation history to the LLM function
        response_text = process_manufacturing_chat(request.query, MANUFACTURING_CONTEXT_FILE, request.conversation_history)

        # Update conversation history with the new user and assistant messages
        request.conversation_history.append({"role": "user", "content": request.query})
        request.conversation_history.append({"role": "assistant", "content": response_text})

        # Store the updated history and response
        LATEST_RESPONSE["response"] = response_text
        LATEST_RESPONSE["conversation_history"] = request.conversation_history
        return LATEST_RESPONSE
    except Exception as e:
        traceback.print_exc()
        return JSONResponse(status_code=500, content={"status": "error", "message": f"Error during manufacturing chat: {e}"})

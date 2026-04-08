from fastapi import FastAPI, UploadFile, File, BackgroundTasks, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
import os
import uuid
from typing import Dict
from pipeline.graph import etl_app

app = FastAPI(title="Data Pipeline API")

# Setup CORS for Frontend
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"], 
    allow_methods=["*"],
    allow_headers=["*"],
)

# For serving the frontend index.html
@app.get("/")
async def serve_frontend():
    return FileResponse("index.html")

job_store: Dict[str, dict] = {}

def execute_pipeline(job_id: str, file_path: str, ext: str):
    initial_state = {
        "job_id": job_id,
        "file_path": file_path,
        "file_type": ext,
        "status": "initialized",
        "errors": None
    }
    job_store[job_id] = initial_state
    
    try:
        final_state = etl_app.invoke(initial_state)
        job_store[job_id] = final_state
    except Exception as e:
        job_store[job_id]["status"] = "failed"
        job_store[job_id]["errors"] = str(e)

@app.post("/api/v1/upload")
async def trigger_pipeline(background_tasks: BackgroundTasks, file: UploadFile = File(...)):
    if not file.filename.endswith(('.csv', '.json')):
        raise HTTPException(status_code=400, detail="Only CSV/JSON files are supported.")
    
    job_id = str(uuid.uuid4())
    ext = file.filename.split('.')[-1]
    
    save_path = f"data/raw/{job_id}.{ext}"
    os.makedirs(os.path.dirname(save_path), exist_ok=True)
    with open(save_path, "wb") as buffer:
        buffer.write(await file.read())
        
    background_tasks.add_task(execute_pipeline, job_id, save_path, ext)
    
    return {"message": "Pipeline tracking initialized", "job_id": job_id}

@app.get("/api/v1/status/{job_id}")
async def inspect_pipeline_status(job_id: str):
    if job_id not in job_store:
        raise HTTPException(status_code=404, detail="Job footprint not found")
    
    state = job_store[job_id]
    return {
        "job_id": job_id,
        "status": state.get("status"),
        "errors": state.get("errors")
    }

@app.get("/api/v1/results/{job_id}")
async def fetch_results(job_id: str):
    if job_id not in job_store or job_store[job_id].get("status") != "completed":
        raise HTTPException(status_code=400, detail="Job pending/failed or invalid")
    
    return {"message": "ETL Completed successfully", "db_table": f"dataset_{job_id.replace('-', '_')}"}

import os
import logging
import pandas as pd
from typing import TypedDict, Optional, Dict, Any
from langgraph.graph import StateGraph, END

# Configure Logging
logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s")
logger = logging.getLogger("etl_pipeline")

# 1. Define the Context/State
class PipelineState(TypedDict):
    job_id: str
    file_path: str
    file_type: str
    raw_preview: Optional[Dict[str, Any]]
    cleaned_data_path: Optional[str]
    status: str
    errors: Optional[str]

# 2. Extract Node Definition
def extract_data(state: PipelineState) -> dict:
    logger.info(f"[Job: {state['job_id']}] Starting Extract phase...")
    try:
        if state["file_type"] == "csv":
            df = pd.read_csv(state["file_path"], nrows=5) 
        elif state["file_type"] == "json":
            df = pd.read_json(state["file_path"], lines=True, nrows=5)
        else:
            raise ValueError(f"Unsupported file type: {state['file_type']}")
        
        return {"status": "extracted", "raw_preview": df.to_dict(orient="records")}
    except Exception as e:
        logger.error(f"[Job: {state['job_id']}] Extraction failed: {e}")
        return {"status": "failed", "errors": str(e)}

# 3. Transform Node Definition
def transform_data(state: PipelineState) -> dict:
    logger.info(f"[Job: {state['job_id']}] Starting Transform phase...")
    try:
        if state["file_type"] == "csv":
            df = pd.read_csv(state["file_path"])
        else:
            df = pd.read_json(state["file_path"], lines=True)

        df.columns = df.columns.str.lower().str.replace(" ", "_")
        df.dropna(how="all", inplace=True)
        df.fillna("UNKNOWN", inplace=True)
        
        df_obj = df.select_dtypes(['object'])
        df[df_obj.columns] = df_obj.apply(lambda x: x.str.strip())

        transformed_path = f"data/temp/{state['job_id']}_transformed.parquet"
        os.makedirs(os.path.dirname(transformed_path), exist_ok=True)
        df.to_parquet(transformed_path, index=False)

        return {"status": "transformed", "cleaned_data_path": transformed_path}
    except Exception as e:
        logger.error(f"[Job: {state['job_id']}] Transformation failed: {e}")
        return {"status": "failed", "errors": str(e)}

# 4. Load Node Definition
def load_data(state: PipelineState) -> dict:
    logger.info(f"[Job: {state['job_id']}] Starting Load phase...")
    try:
        df = pd.read_parquet(state["cleaned_data_path"])
        
        import sqlite3
        os.makedirs("data/processed", exist_ok=True)
        conn = sqlite3.connect("data/processed/clean_data.db")
        table_name = f"dataset_{state['job_id'].replace('-', '_')}"
        
        df.to_sql(table_name, conn, if_exists="replace", index=False)
        conn.close()
        
        if os.path.exists(state["cleaned_data_path"]):
            os.remove(state["cleaned_data_path"])
            
        return {"status": "completed"}
    except Exception as e:
        logger.error(f"[Job: {state['job_id']}] Loading failed: {e}")
        return {"status": "failed", "errors": str(e)}

# Compile LangGraph State Machine
workflow = StateGraph(PipelineState)

workflow.add_node("extract", extract_data)
workflow.add_node("transform", transform_data)
workflow.add_node("load", load_data)

workflow.set_entry_point("extract")

workflow.add_conditional_edges(
    "extract", 
    lambda s: "end" if s["status"] == "failed" else "transform", 
    {"transform": "transform", "end": END}
)
workflow.add_conditional_edges(
    "transform", 
    lambda s: "end" if s["status"] == "failed" else "load", 
    {"load": "load", "end": END}
)
workflow.add_edge("load", END)

etl_app = workflow.compile()

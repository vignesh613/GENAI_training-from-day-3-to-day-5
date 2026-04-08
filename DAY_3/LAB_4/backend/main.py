import uuid
import os
from typing import Dict
from contextlib import asynccontextmanager

from fastapi import FastAPI, HTTPException, BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware
from dotenv import load_dotenv

from models.schemas import ReportRequest, ReportResponse, ReportStatus
from workflow.graph import run_report_workflow
from utils.logger import get_logger

load_dotenv(override=True)

logger = get_logger(__name__)

if not os.getenv("OPENAI_API_KEY"):
    logger.warning("⚠  OPENAI_API_KEY is not set — requests will fail until it is configured.")

# In-memory report store (swap for Redis / DB in production)
reports_store: Dict[str, dict] = {}


@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("🚀 Multi-Agent Report Generator API starting…")
    from db.chroma_client import get_collection
    get_collection()  # warm-up ChromaDB
    yield
    logger.info("Shutting down.")


app = FastAPI(
    title="Multi-Agent Report Generator",
    description="3-agent AI pipeline (Researcher → Writer → Editor) powered by LangGraph + OpenAI + ChromaDB",
    version="1.0.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ── Endpoints ──────────────────────────────────────────────────────────────────

@app.post("/generate-report", response_model=ReportResponse, summary="Start report generation")
async def generate_report(request: ReportRequest, background_tasks: BackgroundTasks):
    if not request.topic.strip():
        raise HTTPException(status_code=400, detail="Topic cannot be empty")
    if not os.getenv("OPENAI_API_KEY"):
        raise HTTPException(
            status_code=503,
            detail="OPENAI_API_KEY is not configured on the server. Add it to backend/.env",
        )

    report_id = str(uuid.uuid4())
    reports_store[report_id] = {
        "id": report_id,
        "topic": request.topic,
        "status": "processing",
        "final_report": None,
        "research_notes": None,
        "revision_count": 0,
        "error": None,
    }

    background_tasks.add_task(_run_pipeline, report_id, request.topic)

    logger.info(f"Report {report_id[:8]}… queued — topic: '{request.topic}'")
    return ReportResponse(
        report_id=report_id,
        status="processing",
        message=f"Report generation started for: {request.topic}",
    )


async def _run_pipeline(report_id: str, topic: str):
    try:
        result = await run_report_workflow(topic, report_id)
        reports_store[report_id].update(
            {
                "status": "completed",
                "final_report": result.get("final_report"),
                "research_notes": result.get("research_notes"),
                "revision_count": result.get("revision_count", 0),
            }
        )
        logger.info(f"Report {report_id[:8]}… completed ✓")
    except Exception as e:
        logger.error(f"Pipeline failed for {report_id[:8]}…: {e}", exc_info=True)
        reports_store[report_id].update({"status": "failed", "error": str(e)})


@app.get("/report/{report_id}", response_model=ReportStatus, summary="Get report status & content")
async def get_report(report_id: str):
    if report_id not in reports_store:
        raise HTTPException(status_code=404, detail="Report not found")
    return ReportStatus(**reports_store[report_id])


@app.get("/reports", summary="List all reports")
async def list_reports():
    return [
        {"id": r["id"], "topic": r["topic"], "status": r["status"]}
        for r in reports_store.values()
    ]


@app.get("/health", summary="Health check")
async def health():
    return {
        "status": "ok",
        "openai_configured": bool(os.getenv("OPENAI_API_KEY")),
        "active_reports": sum(1 for r in reports_store.values() if r["status"] == "processing"),
        "total_reports": len(reports_store),
    }

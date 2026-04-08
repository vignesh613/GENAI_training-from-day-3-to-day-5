from fastapi import FastAPI, HTTPException
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from pydantic import BaseModel
import uuid
import os

from models import ContentItem, SubmitRequest, ApprovalRequest, ModerationStatus
import database
from graph import app_graph, ModerationState

app = FastAPI(title="Content Moderation API")

# Ensure static directory exists
os.makedirs("static", exist_ok=True)

app.mount("/static", StaticFiles(directory="static"), name="static")

@app.get("/")
def serve_frontend():
    if os.path.exists("static/index.html"):
        return FileResponse("static/index.html")
    return {"message": "Frontend not found"}

@app.post("/submit")
def submit_content(request: SubmitRequest):
    content_id = str(uuid.uuid4())
    item = ContentItem(id=content_id, text=request.text)
    database.save_content(item)
    
    # Start the langgraph workflow
    config = {"configurable": {"thread_id": content_id}}
    state = ModerationState(
        content_id=content_id,
        text=request.text,
        status=ModerationStatus.PENDING.value,
        moderation_reason=""
    )
    
    for event in app_graph.stream(state, config):
        pass # iterate till it pauses or ends
        
    final_item = database.get_content(content_id)
    return {"id": final_item.id, "status": final_item.status, "reason": final_item.moderation_reason}

@app.get("/moderation-queue")
def get_queue():
    items = database.get_review_queue()
    return items

@app.post("/approve/{content_id}")
def approve_content(content_id: str, req: ApprovalRequest):
    item = database.get_content(content_id)
    if not item:
        raise HTTPException(status_code=404, detail="Content not found")
        
    if item.status != ModerationStatus.HUMAN_REVIEW:
        raise HTTPException(status_code=400, detail="Content is not in review state")
        
    config = {"configurable": {"thread_id": content_id}}
    
    # Update langgraph state
    app_graph.update_state(config, {"status": ModerationStatus.APPROVED.value, "moderation_reason": "Approved by human: " + (req.note or "")})
    
    item.status = ModerationStatus.APPROVED
    item.moderation_reason = "Approved by human: " + (req.note or "")
    database.save_content(item)
    
    # Resume the workflow
    for event in app_graph.stream(None, config):
        pass
        
    return {"status": "success"}

@app.post("/reject/{content_id}")
def reject_content(content_id: str, req: ApprovalRequest):
    item = database.get_content(content_id)
    if not item:
        raise HTTPException(status_code=404, detail="Content not found")
        
    if item.status != ModerationStatus.HUMAN_REVIEW:
        raise HTTPException(status_code=400, detail="Content is not in review state")
        
    config = {"configurable": {"thread_id": content_id}}
    
    app_graph.update_state(config, {"status": ModerationStatus.REJECTED.value, "moderation_reason": "Rejected by human: " + (req.note or "")})
    
    item.status = ModerationStatus.REJECTED
    item.moderation_reason = "Rejected by human: " + (req.note or "")
    database.save_content(item)
    
    for event in app_graph.stream(None, config):
        pass
        
    return {"status": "success"}
    
@app.get("/all")
def get_all():
    return database.get_all_content()

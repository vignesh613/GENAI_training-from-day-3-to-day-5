import logging
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from fastapi.staticfiles import StaticFiles
from app.workflow import app_workflow

# Configure robust logging for all branches
logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s")

app = FastAPI(title="Intelligent Router API")

class QueryRequest(BaseModel):
    query: str

class QueryResponse(BaseModel):
    query: str
    sentiment: str
    reply: str
    route: str

@app.post("/api/route", response_model=QueryResponse)
async def process_query(request: QueryRequest):
    try:
        # Initialize LangGraph state
        initial_state = {
            "query": request.query, 
            "sentiment": "", 
            "response": "", 
            "route_taken": ""
        }
        # Run workflow
        result = app_workflow.invoke(initial_state)
        
        return QueryResponse(
            query=result["query"],
            sentiment=result["sentiment"],
            reply=result["response"],
            route=result["route_taken"]
        )
    except Exception as e:
        logging.error(f"Critical error processing query: {str(e)}")
        raise HTTPException(status_code=500, detail="Internal Server Error due to workflow failure")

# Mount frontend interface natively
app.mount("/", StaticFiles(directory="static", html=True), name="static")

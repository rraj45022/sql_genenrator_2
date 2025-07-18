from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from .agent import process_query
from pydantic import BaseModel

app = FastAPI()

# Enable CORS for frontend-backend communication
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173"],  # Update if needed
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
class QueryRequest(BaseModel):
    query: str

from fastapi.responses import JSONResponse

@app.post("/ask")
async def ask_agent(request: QueryRequest):
    try:
        sql_query = process_query(request.query)
        return {"sql_query": sql_query}
    except Exception as e:
        return JSONResponse(status_code=500, content={"error": str(e)})


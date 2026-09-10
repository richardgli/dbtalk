import os
from dotenv import load_dotenv

from pydantic import BaseModel

from starlette.middleware.sessions import SessionMiddleware
from starlette.requests import Request
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from eval.eval_harness import get_agent_response
from utils.response_parser import parse_agent_response

load_dotenv()

class QueryRequest(BaseModel):
    question: str
    session_id: str

class QueryResponse(BaseModel):
    answer: str
    sql: str
    results: list[dict]

app = FastAPI()
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        os.getenv("FRONTEND_URL")
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
app.add_middleware(SessionMiddleware, secret_key=os.getenv("SECRET_KEY"))

@app.post('/api/query', response_model=QueryResponse)
async def ask(request: QueryRequest):
    response = get_agent_response(request.question, request.session_id)
    return parse_agent_response(response)
import os
import sys
from dotenv import load_dotenv

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from pydantic import BaseModel

from starlette.middleware.sessions import SessionMiddleware
from starlette.requests import Request
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from eval.eval_harness import get_agent_response
from utils.response_parser import parse_agent_response
from utils.conversation_manager import save_message, load_conversation, list_conversations, update_conversation_title

from data.db_init import init_tables
init_tables()
load_dotenv()

class QueryRequest(BaseModel):
    question: str
    session_id: str

class QueryResponse(BaseModel):
    answer: str
    sql: str
    results: list[dict]

class ConversationResponse(BaseModel):
    id: str
    created_at: str
    updated_at: str
    title: str | None

class MessageResponse(BaseModel):
    role: str
    text: str
    sql: str | None
    rows: list[dict] | None

class TitleRequest(BaseModel):
    title: str

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
    import time
    start = time.time()

    save_message(request.session_id, "user", request.question)

    response = get_agent_response(request.question, request.session_id)
    parsed = parse_agent_response(response)

    save_message(request.session_id, "assistant", parsed["answer"], parsed["sql"], parsed["results"])

    print(f"Total: {time.time() - start:.2f}s")
    return parsed


@app.get('/api/conversations', response_model=list[ConversationResponse])
async def get_conversations():
    """List all conversations."""
    return list_conversations()


@app.get('/api/conversations/{conversation_id}/messages', response_model=list[MessageResponse])
async def get_messages(conversation_id: str):
    """Load all messages for a conversation."""
    return load_conversation(conversation_id)


@app.put('/api/conversations/{conversation_id}/title')
async def set_title(conversation_id: str, request: TitleRequest):
    """Update the title of a conversation."""
    update_conversation_title(conversation_id, request.title)
    return {"status": "ok"}
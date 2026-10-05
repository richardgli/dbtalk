import os
import sys
from datetime import datetime
from sqlalchemy.orm import Session

# Add project root to path to import data schema (this file is in backend/utils/)
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from data.schema.base import engine
from data.schema.conversation import Conversation
from data.schema.message import Message


def save_message(conversation_id: str, role: str, content: str, sql: str = None, results = None):
    """Save a message to the database."""
    import json
    with Session(engine) as session:
        # Ensure conversation exists
        conversation = session.get(Conversation, conversation_id)
        if not conversation:
            conversation = Conversation(
                id=conversation_id,
                created_at=datetime.utcnow(),
                updated_at=datetime.utcnow()
            )
            session.add(conversation)
            session.commit()
            session.refresh(conversation)

        # Create message
        message = Message(
            conversation_id=conversation_id,
            role=role,
            content=content,
            sql=sql,
            results=json.dumps(results) if results else None,
            created_at=datetime.utcnow()
        )
        session.add(message)

        # Update conversation timestamp
        conversation.updated_at = datetime.utcnow()

        session.commit()


def load_conversation(conversation_id: str):
    """Load all messages for a conversation."""
    import json
    with Session(engine) as session:
        messages = session.query(Message).filter(
            Message.conversation_id == conversation_id
        ).order_by(Message.created_at).all()

        return [
            {
                "role": msg.role,
                "text": msg.content,
                "sql": msg.sql,
                "rows": json.loads(msg.results) if msg.results else None
            }
            for msg in messages
        ]


def list_conversations():
    """List all conversations with their metadata."""
    with Session(engine) as session:
        conversations = session.query(Conversation).order_by(
            Conversation.updated_at.desc()
        ).all()

        return [
            {
                "id": conv.id,
                "created_at": conv.created_at.isoformat(),
                "updated_at": conv.updated_at.isoformat(),
                "title": conv.title
            }
            for conv in conversations
        ]


def update_conversation_title(conversation_id: str, title: str):
    """Update the title of a conversation."""
    with Session(engine) as session:
        conversation = session.get(Conversation, conversation_id)
        if conversation:
            conversation.title = title
            session.commit()

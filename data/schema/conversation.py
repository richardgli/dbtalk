from datetime import datetime
from sqlalchemy.orm import Mapped, mapped_column
from data.schema.base import Base

class Conversation(Base):
    __tablename__ = "conversations"

    id: Mapped[str] = mapped_column(primary_key=True)
    created_at: Mapped[datetime] = mapped_column(nullable=False, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(nullable=False, default=datetime.utcnow, onupdate=datetime.utcnow)
    title: Mapped[str] = mapped_column(nullable=True)

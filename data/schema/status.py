from datetime import datetime
from sqlalchemy import ForeignKey, DateTime, Index
from sqlalchemy.orm import Mapped, mapped_column
from data.schema.base import Base

class Status(Base):
    __tablename__ = "device_status"

    device_id: Mapped[int] = mapped_column(
        ForeignKey("devices.id", ondelete="CASCADE"),
        primary_key=True,
    )
    time: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        primary_key=True,
    )
    online: Mapped[bool] = mapped_column(nullable=False)

    __table_args__ = (
        Index("ix_status_by_time", "time", "device_id"),
    )

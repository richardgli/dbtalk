from datetime import datetime
from sqlalchemy import ForeignKey, Index, DateTime
from sqlalchemy.orm import Mapped, mapped_column
from data.schema.base import Base

class Reading(Base):
    __tablename__ = "sensor_readings"

    time: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        primary_key=True,
    )
    device_id: Mapped[int] = mapped_column(
        ForeignKey("devices.id", ondelete="CASCADE"),
        primary_key=True
    )
    temperature: Mapped[float]

    __table_args__ = (
        Index("ix_readings_by_time", "time", "device_id"),
    )
    
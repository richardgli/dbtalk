from sqlalchemy.orm import Mapped, mapped_column
from data.schema.base import Base

class Device(Base):
    __tablename__ = "devices"

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(nullable=False)
    latitude: Mapped[float] = mapped_column(nullable=False)
    longitude: Mapped[float] = mapped_column(nullable=False)

    # Timezone formatted in IANA
    timezone: Mapped[str] = mapped_column(nullable=False)

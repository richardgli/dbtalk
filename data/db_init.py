from sqlalchemy import text
from data.schema.base import Base, engine

def init():
    Base.metadata.create_all(engine)

    with engine.connect() as conn:
        conn.execute(text(
            "SELECT create_hypertable('sensor_readings', 'time', if_not_exists => TRUE)"
        ))
        conn.execute(text(
            "SELECT create_hypertable('device_status', 'time', if_not_exists => TRUE)"
        ))
        conn.commit()
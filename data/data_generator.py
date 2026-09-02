import numpy as np
import pandas as pd
from zoneinfo import ZoneInfo
from typing import List

from sqlalchemy import Session
from data.schema.base import engine
from data.schema import Device, Reading
from data.db_init import init

devices = [
    Device(id=1, name="d_seattle", latitude=47.6062, longitude=-122.3321, timezone="America/Los_Angeles"),
    Device(id=2, name="d_dallas", latitude=32.7767, longitude=-96.7970, timezone="America/Chicago"),
    Device(id=3, name="d_toronto", latitude=43.6532, longitude=-79.3832, timezone="America/Toronto"),
    Device(id=4, name="d_london", latitude=51.5074, longitude=-0.1278, timezone="Europe/London"),
    Device(id=5, name="d_paris", latitude=48.8566, longitude=2.3522, timezone="Europe/Paris"),
    Device(id=6, name="d_victoria", latitude=48.4284, longitude=-123.3656, timezone="America/Vancouver"),
]

def generate_data():
    init()

    readings: List[Reading] = []
    date_range = pd.date_range(start="2026-08-01", end="2026-09-01", freq="10min", tz="UTC")

    for device in devices:
        outages = generate_outages()

        for utc_timestamp in date_range:
            # continue if utc_timestamp falls within an outage
            temperature = generate_temperature()

            readings.append(Reading(time=utc_timestamp, device_id=device.id, temperature=temperature))


    with Session(engine) as session:
        session.add_all(devices)
        session.add_all(readings)
        session.commit()
    
def generate_outages() -> List[pd.datetime]:
    pass

def generate_temperature() -> float:
    return 0

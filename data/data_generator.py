import numpy as np
import pandas as pd
import math
from zoneinfo import ZoneInfo
from typing import List

from sqlalchemy import Session
from data.schema.base import engine
from data.schema import Device, Reading
from data.db_init import init

devices = [
    Device(id=1, name="d_seattle", latitude=47.6062, longitude=-122.3321, timezone="America/Los_Angeles"),
    Device(id=2, name="d_saopaulo", latitude=-23.5505, longitude=-46.6333, timezone="America/Sao_Paulo"),
    Device(id=3, name="d_sydney", latitude=-33.8688, longitude=151.2093, timezone="Australia/Sydney"),
    Device(id=4, name="d_london", latitude=51.5074, longitude=-0.1278, timezone="Europe/London"),
    Device(id=5, name="d_paris", latitude=48.8566, longitude=2.3522, timezone="Europe/Paris"),
    Device(id=6, name="d_victoria", latitude=48.4284, longitude=-123.3656, timezone="America/Vancouver"),
]


def generate_outages() -> List[pd.datetime]:
    pass

def generate_temperature(utc_hour: float, day_of_year: int, latitude: float, longitude: float) -> float:
    """Using the dynamic temperature formula to approximate a temperature reading."""
    latitude_rad = math.radians(latitude)
    base_temp = 30 - 40 * math.pow(math.sin(latitude_rad), 2)
    seasonal_amplitude = 20 * math.sin(abs(latitude_rad))
    seasonal_shift = 172 if latitude_rad > 0 else 355
    daily_amplitude = 7 * math.cos(latitude_rad)
    local_solar_time = (utc_hour + (longitude / 15)) % 24

    seasonal_product = seasonal_amplitude * math.cos(2 * math.pi * (day_of_year - seasonal_shift) / 365)
    daily_product = daily_amplitude * math.cos(2 * math.pi * (local_solar_time - 14) / 24)
    temp = base_temp + seasonal_product + daily_product
    return temp

def generate_data() -> None:
    init()

    readings: List[Reading] = []
    date_range = pd.date_range(start="2026-08-01", end="2026-09-01", freq="10min", tz="UTC")

    for device in devices:
        outages = generate_outages()

        for utc_timestamp in date_range:
            # continue if utc_timestamp falls within an outage
            utc_hour = utc_timestamp.hour + utc_timestamp.minute / 60
            day_of_year = utc_timestamp.timetuple().tm_yday
            temperature = generate_temperature(utc_hour, day_of_year, device.latitude, device.longitude)

            readings.append(Reading(time=utc_timestamp, device_id=device.id, temperature=temperature))


    with Session(engine) as session:
        session.add_all(devices)
        session.add_all(readings)
        session.commit()

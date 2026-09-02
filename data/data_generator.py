from datetime import timedelta
import numpy as np
import pandas as pd
import math
from typing import List, Tuple

from sqlalchemy import Session
from data.schema.base import engine
from data.schema import Device, Reading
from data.db_init import init_tables

devices = [
    Device(id=1, name="d_seattle", latitude=47.6062, longitude=-122.3321, timezone="America/Los_Angeles"),
    Device(id=2, name="d_saopaulo", latitude=-23.5505, longitude=-46.6333, timezone="America/Sao_Paulo"),
    Device(id=3, name="d_sydney", latitude=-33.8688, longitude=151.2093, timezone="Australia/Sydney"),
    Device(id=4, name="d_london", latitude=51.5074, longitude=-0.1278, timezone="Europe/London"),
    Device(id=5, name="d_paris", latitude=48.8566, longitude=2.3522, timezone="Europe/Paris"),
    Device(id=6, name="d_victoria", latitude=48.4284, longitude=-123.3656, timezone="America/Vancouver"),
]


def generate_outages(rng, start_time: pd.datetime, end_time: pd.datetime) -> List[pd.datetime]:
    """Generates outage events (2-5 events) within a given date range."""
    total_minutes = (end_time - start_time).total_seconds() / 60
    num_outages = rng.integers(2, 5)
    outages: List[Tuple[int, int]] = []

    # Creating outage events by generating random start and end times
    for _ in range(num_outages):
        outage_start_time = rng.integers(0, total_minutes)
        outage_end_time = rng.integers(outage_start_time + 10, total_minutes)

        # Floor to nearest multiple of 10
        outage_start_time = outage_start_time - outage_start_time % 10
        outage_end_time = outage_end_time - outage_end_time % 10

        outages.append((outage_start_time, outage_end_time))

    # Merging overlapping outage events
    outages = outages.sort(key=lambda x: x[0])
    merged_outages: List[Tuple[int, int]] = []
    for start, end in outages:
        if merged_outages and start <= merged_outages[-1][1]:
            merged_outages[-1] = (merged_outages[-1][0], max(merged_outages[-1][1], end))
        else:
            merged_outages.append((start, end))

    return merged_outages


def generate_temperature(utc_hour: float, day_of_year: int, latitude: float, longitude: float) -> float:
    """Uses the dynamic temperature formula to approximate a temperature reading."""
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
    init_tables()

    readings: List[Reading] = []
    date_range = pd.date_range(start="2026-08-01 00:00:00", end="2026-09-01 00:00:00", freq="10min", tz="UTC")
    rng = np.random.default_rng(seed=8)

    for device in devices:
        outages = generate_outages(rng, date_range[0], date_range[-1])

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

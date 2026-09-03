import os
from dotenv import load_dotenv
from datetime import timedelta

import numpy as np
import pandas as pd
import pytest

from sqlalchemy import create_engine
from sqlalchemy.orm import Session, make_transient

import data.schema.base as base_module
import data.data_generator as gen_module

from data.schema import Device, Reading
from data.schema.base import test_engine
from data.db_init import init_dev_tables
from data.data_generator import generate_temperature, generate_outages, generate_data, devices

load_dotenv()

TEST_DATABASE_URL = os.getenv("DEV_DATABASE_URL")
RANGE_START = pd.Timestamp("2026-08-01 00:00:00", tz="UTC")
RANGE_END = pd.Timestamp("2026-09-01 00:00:00", tz="UTC")


# ---------------------------------------------------------------------------
# Generates dataset once to be reused across tests
# ---------------------------------------------------------------------------

@pytest.fixture(scope="session")
def db_engine():
    engine = test_engine
    yield engine
    engine.dispose()


@pytest.fixture(scope="session")
def generated_data(db_engine):
    mp = pytest.MonkeyPatch()
    mp.setattr(base_module, "engine", db_engine)
    mp.setattr(gen_module, "engine", db_engine)

    captured_outages = []
    original_generate_outages = gen_module.generate_outages

    def spy(rng, start, end):
        result = original_generate_outages(rng, start, end)
        captured_outages.append(result)
        return result

    mp.setattr(gen_module, "generate_outages", spy)

    base_module.Base.metadata.drop_all(db_engine)
    init_dev_tables()

    device_ids = [device.id for device in devices]

    generate_data()

    outages_by_device = dict(zip(device_ids, captured_outages))

    yield {"engine": db_engine, "outages_by_device": outages_by_device}

    mp.undo()
    for device in devices:
        make_transient(device)
    base_module.Base.metadata.drop_all(db_engine)


# ---------------------------------------------------------------------------
# generate_temperature tests
# ---------------------------------------------------------------------------

class TestGenerateTemperature:
    def test_returns_a_float(self):
        temp = generate_temperature(utc_hour=12, day_of_year=180, latitude=45, longitude=0)
        assert isinstance(temp, float)

    def test_equator_has_no_seasonal_variation(self):
        t_jan = generate_temperature(utc_hour=6, day_of_year=1, latitude=0, longitude=0)
        t_jul = generate_temperature(utc_hour=6, day_of_year=182, latitude=0, longitude=0)
        assert t_jan == pytest.approx(t_jul)

    def test_poles_are_colder_than_equator_on_average(self):
        equator = generate_temperature(utc_hour=12, day_of_year=172, latitude=0, longitude=0)
        pole = generate_temperature(utc_hour=12, day_of_year=172, latitude=90, longitude=0)
        assert equator > pole

    def test_daily_peak_near_2pm_local_solar_time(self):
        lat, lon, day = 40, 0, 172
        t_2pm = generate_temperature(utc_hour=14, day_of_year=day, latitude=lat, longitude=lon)
        t_2am = generate_temperature(utc_hour=2, day_of_year=day, latitude=lat, longitude=lon)
        t_8pm = generate_temperature(utc_hour=20, day_of_year=day, latitude=lat, longitude=lon)
        assert t_2pm > t_2am
        assert t_2pm > t_8pm

    def test_longitude_shifts_local_solar_time(self):
        lat, day = 40, 172
        t_at_lon_0 = generate_temperature(utc_hour=14, day_of_year=day, latitude=lat, longitude=0)
        t_at_lon_neg180_hour2 = generate_temperature(utc_hour=2, day_of_year=day, latitude=lat, longitude=180)
        assert t_at_lon_0 == pytest.approx(t_at_lon_neg180_hour2, abs=1e-6)

    def test_handles_negative_latitude(self):
        temp = generate_temperature(utc_hour=12, day_of_year=172, latitude=-33.87, longitude=151.2)
        assert -60 < temp < 60

    @pytest.mark.parametrize("day_of_year", [1, 90, 172, 265, 355, 365])
    def test_no_exceptions_across_year(self, day_of_year):
        generate_temperature(utc_hour=10, day_of_year=day_of_year, latitude=48.86, longitude=2.35)


# ---------------------------------------------------------------------------
# generate_outages tests
# ---------------------------------------------------------------------------

class TestGenerateOutages:
    def test_same_seed_is_deterministic(self):
        outages_a = generate_outages(np.random.default_rng(seed=8), RANGE_START, RANGE_END)
        outages_b = generate_outages(np.random.default_rng(seed=8), RANGE_START, RANGE_END)
        assert outages_a == outages_b

    def test_outage_count_within_expected_bounds(self):
        outages = generate_outages(np.random.default_rng(seed=1), RANGE_START, RANGE_END)
        assert 1 <= len(outages) <= 4

    def test_each_outage_starts_before_it_ends(self):
        outages = generate_outages(np.random.default_rng(seed=2), RANGE_START, RANGE_END)
        for outage_start, outage_end in outages:
            assert outage_start < outage_end

    def test_outages_are_sorted_and_non_overlapping(self):
        outages = generate_outages(np.random.default_rng(seed=3), RANGE_START, RANGE_END)
        for (_, prev_end), (cur_start, _) in zip(outages, outages[1:]):
            assert prev_end < cur_start  # strictly separated, in order

    def test_outages_fall_within_the_requested_range(self):
        outages = generate_outages(np.random.default_rng(seed=4), RANGE_START, RANGE_END)
        for outage_start, outage_end in outages:
            assert RANGE_START <= outage_start <= RANGE_END
            assert RANGE_START <= outage_end <= RANGE_END

    def test_outage_boundaries_are_multiples_of_ten_minutes(self):
        outages = generate_outages(np.random.default_rng(seed=5), RANGE_START, RANGE_END)
        for outage_start, outage_end in outages:
            assert (outage_start - RANGE_START).total_seconds() % 600 == 0
            assert (outage_end - RANGE_START).total_seconds() % 600 == 0


# ---------------------------------------------------------------------------
# generate_data tests
# ---------------------------------------------------------------------------

class TestGenerateDataReadings:
    def test_creates_readings_for_every_device(self, generated_data):
        with Session(generated_data["engine"]) as session:
            assert session.query(Device).count() == 6
            assert session.query(Reading).count() > 0

    def test_no_readings_fall_inside_an_outage(self, generated_data):
        with Session(generated_data["engine"]) as session:
            for device in session.query(Device).all():
                outages = generated_data["outages_by_device"][device.id]
                times = [
                    pd.Timestamp(r.time).tz_convert("UTC")
                    for r in session.query(Reading).filter(Reading.device_id == device.id).all()
                ]
                for start, end in outages:
                    assert not any(start <= t <= end for t in times)

    def test_reading_timestamps_are_within_generation_range(self, generated_data):
        with Session(generated_data["engine"]) as session:
            times = [pd.Timestamp(r.time).tz_convert("UTC") for r in session.query(Reading).all()]
        assert all(RANGE_START <= t <= RANGE_END for t in times)

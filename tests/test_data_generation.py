import math
from datetime import timedelta

import numpy as np
import pandas as pd
import pytest

from data.data_generator import generate_temperature, generate_outages, generate_data


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
    @pytest.fixture
    def time_range(self):
        start = pd.Timestamp("2026-08-01 00:00:00", tz="UTC")
        end = pd.Timestamp("2026-09-01 00:00:00", tz="UTC")
        return start, end

    def test_same_seed_is_deterministic(self, time_range):
        start, end = time_range
        outages_a = generate_outages(np.random.default_rng(seed=8), start, end)
        outages_b = generate_outages(np.random.default_rng(seed=8), start, end)
        assert outages_a == outages_b

    def test_outage_count_within_expected_bounds(self, time_range):
        start, end = time_range
        outages = generate_outages(np.random.default_rng(seed=1), start, end)
        assert 1 <= len(outages) <= 4

    def test_each_outage_starts_before_it_ends(self, time_range):
        start, end = time_range
        outages = generate_outages(np.random.default_rng(seed=2), start, end)
        for outage_start, outage_end in outages:
            assert outage_start < outage_end

    def test_outages_are_sorted_and_non_overlapping(self, time_range):
        start, end = time_range
        outages = generate_outages(np.random.default_rng(seed=3), start, end)
        for (prev_start, prev_end), (cur_start, cur_end) in zip(outages, outages[1:]):
            assert prev_end < cur_start  # strictly separated, in order

    def test_outages_fall_within_the_requested_range(self, time_range):
        start, end = time_range
        outages = generate_outages(np.random.default_rng(seed=4), start, end)
        for outage_start, outage_end in outages:
            assert start <= outage_start <= end
            assert start <= outage_end <= end

    def test_outage_boundaries_are_multiples_of_ten_minutes(self, time_range):
        start, end = time_range
        outages = generate_outages(np.random.default_rng(seed=5), start, end)
        for outage_start, outage_end in outages:
            assert (outage_start - start).total_seconds() % 600 == 0
            assert (outage_end - start).total_seconds() % 600 == 0

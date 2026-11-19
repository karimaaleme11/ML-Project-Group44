"""Download daily historical weather for 6 cities from the Open-Meteo archive API.

One request per city (2016-01-01 .. 2025-12-31). Each raw response is saved as
data/raw/<city>.json. Cities that were already downloaded are skipped, so the
script can be re-run safely.
"""

import json
import time
from collections import deque
from pathlib import Path

import requests

ENDPOINT = "https://archive-api.open-meteo.com/v1/archive"
HOURLY_LIMIT = 5_000
DAILY_LIMIT = 10_000
MAX_ATTEMPTS = 5
RETRY_CODES = (429, 500, 502, 503, 504)

START_DATE = "2016-01-01"
END_DATE = "2025-12-31"

LOCATIONS = {
    "london": (51.5074, -0.1278),
    "berlin": (52.5200, 13.4050),
    "new_york": (40.7128, -74.0060),
    "tokyo": (35.6762, 139.6503),
    "sydney": (-33.8688, 151.2093),
    "vancouver": (49.2827, -123.1207),
}

DAILY_VARIABLES = [
    "weather_code",
    "temperature_2m_max",
    "temperature_2m_min",
    "temperature_2m_mean",
    "apparent_temperature_mean",
    "precipitation_sum",
    "rain_sum",
    "precipitation_hours",
    "wind_speed_10m_max",
    "wind_direction_10m_dominant",
]


def wait_for_rate_limits(hourly_times: deque, daily_times: deque) -> None:
    """Sleep if one more request would break the hourly or daily limit."""
    while True:
        now = time.time()
        while hourly_times and now - hourly_times[0] >= 3600:
            hourly_times.popleft()
        while daily_times and now - daily_times[0] >= 86400:
            daily_times.popleft()

        waits = []
        if len(hourly_times) >= HOURLY_LIMIT:
            waits.append(3600 - (now - hourly_times[0]))
        if len(daily_times) >= DAILY_LIMIT:
            waits.append(86400 - (now - daily_times[0]))
        if not waits:
            return
        time.sleep(max(waits) + 1)


def download_location(session, location, latitude, longitude,
                      hourly_times, daily_times) -> dict:
    """Request one city. Retries on 429/5xx and on network errors."""
    params = {
        "latitude": latitude,
        "longitude": longitude,
        "start_date": START_DATE,
        "end_date": END_DATE,
        "daily": ",".join(DAILY_VARIABLES),
        "timezone": "auto",
    }

    for attempt in range(MAX_ATTEMPTS):
        wait_for_rate_limits(hourly_times, daily_times)

        try:
            response = session.get(ENDPOINT, params=params, timeout=60)
        except requests.exceptions.RequestException as err:
            print(f"{location}: network error ({err}), retrying")
            time.sleep(2 ** attempt)
            continue

        # every request that reached the server counts towards the limits
        now = time.time()
        hourly_times.append(now)
        daily_times.append(now)

        if response.status_code == 200:
            payload = response.json()
            if payload.get("error") is True or "daily" not in payload:
                raise RuntimeError(f"Invalid response for {location}: {payload}")
            return payload

        if response.status_code in RETRY_CODES:
            print(f"{location}: HTTP {response.status_code}, retrying")
            time.sleep(2 ** attempt)
            continue

        # e.g. 400 -> the request itself is wrong, retrying will not help
        raise RuntimeError(
            f"{location}: HTTP {response.status_code} - {response.text}"
        )

    raise RuntimeError(f"Could not download {location} after {MAX_ATTEMPTS} attempts")


def collect() -> None:
    output_dir = Path("data/raw")
    output_dir.mkdir(parents=True, exist_ok=True)

    hourly_times: deque[float] = deque()
    daily_times: deque[float] = deque()

    with requests.Session() as session:
        for location, (latitude, longitude) in LOCATIONS.items():
            output = output_dir / f"{location}.json"
            if output.exists():
                print(f"Skipping {location}, already downloaded.")
                continue

            payload = download_location(
                session, location, latitude, longitude, hourly_times, daily_times
            )

            # write to a temp file first so a crash never leaves a half-written json
            tmp = output.with_suffix(".tmp")
            tmp.write_text(
                json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8"
            )
            tmp.replace(output)
            print(f"Saved {location} to {output}")
            time.sleep(0.25)


if __name__ == "__main__":
    collect()

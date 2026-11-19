import json
from pathlib import Path

import pandas as pd

RAIN_THRESHOLD_MM = 1.0


def run_sensing() -> None:
    raw_dir = Path("data/raw")
    processed_dir = Path("data/processed")
    processed_dir.mkdir(parents=True, exist_ok=True)

    json_files = sorted(raw_dir.glob("*.json"))
    if not json_files:
        raise FileNotFoundError("No json files in data/raw - run data_collection.py first")

    frames = []
    for json_file in json_files:
        payload = json.loads(json_file.read_text(encoding="utf-8"))
        daily = pd.DataFrame(payload["daily"]).rename(columns={"time": "date"})
        daily["location"] = json_file.stem
        frames.append(daily)

    sensed = pd.concat(frames, ignore_index=True)
    sensed["date"] = pd.to_datetime(sensed["date"])

    # remove duplicates by location + date, then sort
    before = len(sensed)
    sensed = sensed.drop_duplicates(subset=["location", "date"])
    print(f"Removed {before - len(sensed)} duplicate rows")
    sensed = sensed.sort_values(["location", "date"]).reset_index(drop=True)

    # shift(-1) is only correct if every day follows the previous one
    gaps = sensed.groupby("location")["date"].diff().dropna()
    if not (gaps == pd.Timedelta(days=1)).all():
        raise ValueError("Found missing days inside a location - the target would be wrong")

    # put location first, then date, then the weather variables
    columns = ["location", "date"] + [
        c for c in sensed.columns if c not in ("location", "date")
    ]
    sensed = sensed[columns]
    sensed.to_csv(raw_dir / "sensed_data.csv", index=False)
    print(f"Saved sensed_data.csv with shape {sensed.shape}")

    # target: did it rain >= 1 mm on the NEXT day (same location)
    next_day_precip = sensed.groupby("location")["precipitation_sum"].shift(-1)
    target = sensed.copy()
    target["RainTomorrow"] = (next_day_precip >= RAIN_THRESHOLD_MM).astype(int)

    # the last day of each location has no "tomorrow", so it is dropped
    target = target[next_day_precip.notna()].reset_index(drop=True)

    target.to_csv(processed_dir / "dataset_with_target.csv", index=False)
    print(f"Saved dataset_with_target.csv with shape {target.shape}")


if __name__ == "__main__":
    run_sensing()

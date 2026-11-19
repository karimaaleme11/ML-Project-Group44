Group: 44

# ML Project - Part A: rain prediction (RainTomorrow)

Binary classification: will it rain at least 1.0 mm tomorrow? Data: daily historical weather from the Open-Meteo Historical Weather API for London, Berlin, New York, Tokyo, Sydney and Vancouver (2016-01-01 to 2025-12-31).

## Project structure

- `data_collection.py` - downloads the raw data from the API (rate-limit handling, retries, skips cities that were already downloaded) into `data/raw/<city>.json`.
- `sensing.py` - reads the local json files only (no API calls), merges them, adds `location` and `date`, removes duplicates by location + date, and saves `data/raw/sensed_data.csv`. It also creates `RainTomorrow` from the next day's `precipitation_sum` (>= 1.0 mm -> 1), removes the last day of each location, and saves `data/processed/dataset_with_target.csv`.
- `dataset_creation.ipynb` - data understanding (priors, relationships, data quality), feature preparation, and creation of `data/processed/final_dataset.csv`.
- `data/raw/` - raw json files exactly as received from the API, and `sensed_data.csv`.
- `data/processed/` - `dataset_with_target.csv` (intermediate) and `final_dataset.csv`.
- `requirements.txt` - packages and versions.

## How to run

Developed with Python 3.14.

```bash
python -m venv .venv
source .venv/bin/activate          # Windows: .venv\Scripts\activate
pip install -r requirements.txt

python data_collection.py          # needs internet, skipped for files that already exist
python sensing.py
# then run dataset_creation.ipynb from top to bottom (Run All)
```

The raw json files are included in the submission, so `data_collection.py` can be skipped.

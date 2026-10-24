import json
from pathlib import Path
from datetime import datetime, timezone

DATA_FILE = Path("data/fx_history.json")


def main():
    if not DATA_FILE.exists():
        raise FileNotFoundError(
            f"Data file not found: {DATA_FILE}"
        )

    with DATA_FILE.open("r", encoding="utf-8") as file:
        data = json.load(file)

    records = data.get("records", [])

    if not records:
        raise ValueError("No exchange rate records found.")

    records.sort(key=lambda record: record["date"])

    latest = records[-1]

    print("Egypt USD/EGP Data Check")
    print("------------------------")
    print("Check time:", datetime.now(timezone.utc).isoformat())
    print("Total records:", len(records))
    print("Latest date:", latest["date"])
    print("Latest USD/EGP rate:", latest["usd_egp_weighted_avg"])

    print("Data validation completed successfully.")


if __name__ == "__main__":
    main()

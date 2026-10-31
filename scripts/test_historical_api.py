
import json
import urllib.request

BASE = "https://foudalens.com/api/market/trading-summary?date="

for date in ["2026-10-28", "2026-10-27", "2026-10-26"]:
    print(f"\n=== Testing {date} ===")

    req = urllib.request.Request(
        BASE + date,
        headers={
            "User-Agent": "Mozilla/5.0",
            "Accept": "application/json"
        }
    )

    try:
        with urllib.request.urlopen(req, timeout=30) as response:
            payload = json.load(response)

        print("Success:", payload.get("success"))
        print("Returned date:", payload.get("date"))

        if payload.get("success") is not True:
            print("API did not confirm success")
            continue

        if payload.get("date") != date:
            print("WARNING: Date mismatch — skipped")
            continue

        data = payload.get("data") or {}

        for instrument in ["bills", "bonds"]:
            print(f"\n{instrument.upper()}")

            for row in data.get(instrument, []):
                name = row.get("name")
                if name not in ("Arab", "Non-Arab Foreigners"):
                    continue

                buy = row.get("buyValue")
                sell = row.get("sellValue")
                net = row.get("netValue")

                print(
                    name,
                    "| Buy:", buy,
                    "| Sell:", sell,
                    "| Net:", net
                )

    except Exception as error:
        print("ERROR:", type(error).__name__, str(error))

print("\nTEST FINISHED — no files modified.")

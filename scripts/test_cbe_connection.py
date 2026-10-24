import urllib.request
import urllib.error
import sys
from datetime import datetime, timezone

CBE_URL = (
    "https://www.cbe.org.eg/en/markets/"
    "foreign-exchange/foreign-exchange-historical-data"
)

def main():
    print("=" * 55)
    print("CENTRAL BANK OF EGYPT - CONNECTION TEST")
    print("=" * 55)

    print("Test time:", datetime.now(timezone.utc).isoformat())
    print("Target:", CBE_URL)

    request = urllib.request.Request(
        CBE_URL,
        headers={
            "User-Agent": "Mozilla/5.0",
            "Accept": "text/html"
        }
    )

    try:
        with urllib.request.urlopen(request, timeout=30) as response:

            status = response.status
            content = response.read()

            print("HTTP Status:", status)
            print("Response size:", len(content), "bytes")

            if status == 200 and len(content) > 0:
                print("SUCCESS: CBE website is reachable.")
                print("Connection test completed successfully.")
                return 0

            print("FAILED: Unexpected response.")
            return 1

    except urllib.error.HTTPError as error:
        print("HTTP ERROR:", error.code)
        return 1

    except urllib.error.URLError as error:
        print("CONNECTION ERROR:", error.reason)
        return 1

    except Exception as error:
        print("UNEXPECTED ERROR:", str(error))
        return 1


if __name__ == "__main__":
    sys.exit(main())

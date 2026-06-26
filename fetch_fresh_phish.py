import json
import re
import urllib.request
from datetime import datetime, timezone
from pathlib import Path

OUTPUT_DIR = Path("docs/fresh-phish")
OUTPUT_FILE = OUTPUT_DIR / "phishing.json"

BASE_URL = "https://raw.githubusercontent.com/Phishing-Database/Phishing.Database/master"

FEEDS = {
    "domains": [
        f"{BASE_URL}/phishing-domains-ACTIVE.txt",
        f"{BASE_URL}/phishing-domains-NEW-today.txt",
        f"{BASE_URL}/phishing-domains-NEW-last-hour.txt",
    ],
    "urls": [
        f"{BASE_URL}/phishing-links-ACTIVE.txt",
        f"{BASE_URL}/phishing-links-NEW-today.txt",
        f"{BASE_URL}/phishing-links-NEW-last-hour.txt",
    ],
    "ips": [
        f"{BASE_URL}/phishing-IPs-ACTIVE.txt",
        f"{BASE_URL}/phishing-ips-NEW-today.txt",
        f"{BASE_URL}/phishing-ips-NEW-last-hour.txt",
    ],
}

LIMIT_PER_TYPE = 500


def fetch_lines(url):
    try:
        with urllib.request.urlopen(url, timeout=60) as response:
            text = response.read().decode("utf-8", errors="ignore")
    except Exception as error:
        print(f"[ERROR] Failed to fetch {url}: {error}")
        return []

    lines = []

    for line in text.splitlines():
        line = line.strip()

        if not line:
            continue

        if line.startswith("#"):
            continue

        lines.append(line)

    return lines


def clean_indicator(value):
    value = value.strip()
    value = re.sub(r"\s+", "", value)
    return value


def unique_keep_order(values):
    seen = set()
    result = []

    for value in values:
        value = clean_indicator(value)

        if not value:
            continue

        if value in seen:
            continue

        seen.add(value)
        result.append(value)

    return result


def main():
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    data = {
        "generated_at": datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S UTC"),
        "source": {
            "name": "Phishing.Database",
            "url": "https://github.com/Phishing-Database/Phishing.Database",
            "license": "MIT",
            "license_url": "https://github.com/Phishing-Database/Phishing.Database/blob/master/LICENSE",
            "authors": [
                "Mitchell Krog",
                "Nissar Chababy",
                "Phishing.Database Contributors"
            ]
        },
        "domains": [],
        "urls": [],
        "ips": [],
        "stats": {}
    }

    for feed_type, urls in FEEDS.items():
        collected = []

        for url in urls:
            print(f"[INFO] Fetching {feed_type}: {url}")
            collected.extend(fetch_lines(url))

        cleaned = unique_keep_order(collected)

        data[feed_type] = cleaned[:LIMIT_PER_TYPE]
        data["stats"][feed_type] = {
            "displayed": len(data[feed_type]),
            "collected_before_limit": len(cleaned),
            "limit": LIMIT_PER_TYPE
        }

        print(f"[INFO] {feed_type}: collected {len(cleaned)}, displayed {len(data[feed_type])}")

    with OUTPUT_FILE.open("w", encoding="utf-8") as file:
        json.dump(data, file, indent=2, ensure_ascii=False)

    print(f"[OK] Generated {OUTPUT_FILE}")


if __name__ == "__main__":
    main()

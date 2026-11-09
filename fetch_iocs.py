import os
import requests
import json
import re
import csv
import io
import ipaddress
from html import escape
from datetime import datetime

# =========================================================
# DATUM I DIREKTORIJI
# =========================================================
today = datetime.now().strftime("%Y-%m-%d")

base_folder = "docs/daily-ioc"
folder = os.path.join(base_folder, f"ioc-{today}")
output_file = os.path.join(folder, "index.html")

# =========================================================
# API KLJUČEVI
# =========================================================
ABUSEIPDB_API_KEY = os.getenv("ABUSEIPDBKEY", "").strip()
MALWAREBAZAAR_AUTH_KEY = os.getenv(
    "MALWAREBAZAAR_AUTH_KEY", ""
).strip()

# =========================================================
# FEODO
# =========================================================
def fetch_feodo_ips():
    url = "https://feodotracker.abuse.ch/downloads/ipblocklist.csv"

    try:
        r = requests.get(url, timeout=30)
    except requests.RequestException:
        print("[!] Feodo: mrežna greška pri preuzimanju.")
        return []

    if r.status_code != 200:
        print(f"[!] Feodo: HTTP {r.status_code}.")
        return []

    ips = set()

    # CSV može sadržavati datum prije IP adrese.
    # Provjeravamo polja umjesto pretpostavke da je IP prvi.
    for row in csv.reader(io.StringIO(r.text), skipinitialspace=True):
        if not row or row[0].lstrip().startswith("#"):
            continue

        for value in row:
            try:
                ip = ipaddress.ip_address(value.strip())
            except ValueError:
                continue

            ips.add(str(ip).replace(".", "[.]"))
            break

    print(f"[+] Feodo: preuzeto {len(ips)} IP adresa.")
    return sorted(ips)


# =========================================================
# ABUSEIPDB
# =========================================================
def fetch_abuseipdb_ips():
    if not ABUSEIPDB_API_KEY:
        print("[!] AbuseIPDB: nedostaje ABUSEIPDBKEY.")
        return []

    headers = {
        "Key": ABUSEIPDB_API_KEY,
        "Accept": "application/json",
    }

    try:
        r = requests.get(
            "https://api.abuseipdb.com/api/v2/blacklist",
            headers=headers,
            params={
                "confidenceMinimum": 75,
                "limit": 10000,
            },
            timeout=30,
        )
    except requests.RequestException:
        print("[!] AbuseIPDB: mrežna greška pri preuzimanju.")
        return []

    if r.status_code != 200:
        print(f"[!] AbuseIPDB: HTTP {r.status_code}.")
        return []

    try:
        payload = r.json()
    except ValueError:
        print("[!] AbuseIPDB: odgovor nije valjan JSON.")
        return []

    if not isinstance(payload, dict):
        print("[!] AbuseIPDB: neočekivan format odgovora.")
        return []

    data = payload.get("data")

    if not isinstance(data, list):
        print("[!] AbuseIPDB: nedostaje lista podataka.")
        return []

    ips = set()

    for item in data:
        if not isinstance(item, dict):
            continue

        value = item.get("ipAddress")

        if not isinstance(value, str):
            continue

        try:
            ip = ipaddress.ip_address(value.strip())
        except ValueError:
            continue

        ips.add(str(ip).replace(".", "[.]"))

    print(f"[+] AbuseIPDB: preuzeto {len(ips)} IP adresa.")
    return sorted(ips)


# =========================================================
# MALWAREBAZAAR
# =========================================================
def fetch_malware_hashes():
    if not MALWAREBAZAAR_AUTH_KEY:
        raise RuntimeError(
            "MalwareBazaar: nedostaje MALWAREBAZAAR_AUTH_KEY."
        )

    url = (
        "https://mb-api.abuse.ch/v2/files/exports/"
        f"{MALWAREBAZAAR_AUTH_KEY}/recent.csv"
    )

    try:
        r = requests.get(url, timeout=60)
    except requests.RequestException:
        # Ne ispisujemo URL ni iznimku jer mogu sadržavati ključ.
        raise RuntimeError(
            "MalwareBazaar: mrežna greška pri preuzimanju."
        ) from None

    if r.status_code != 200:
        raise RuntimeError(
            f"MalwareBazaar: HTTP {r.status_code}."
        )

    hashes = set()

    for row in csv.reader(io.StringIO(r.text), skipinitialspace=True):
        if not row or row[0].lstrip().startswith("#"):
            continue

        # Tražimo polje koje sadrži SHA256 hash.
        for value in row:
            value = value.strip()

            if re.fullmatch(r"[0-9a-fA-F]{64}", value):
                hashes.add(value.lower())
                break

    if not hashes:
        raise RuntimeError(
            "MalwareBazaar: odgovor ne sadrži valjane SHA256 hashove."
        )

    print(f"[+] MalwareBazaar: preuzeto {len(hashes)} hashova.")
    return sorted(hashes)


# =========================================================
# HTML TEMPLATE
# =========================================================
def init_html(path):
    with open(path, "w", encoding="utf-8") as f:
        f.write(f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>Daily IOC – {today}</title>
<link rel="stylesheet" href="/assets/style.css">
</head>

<body>
<div class="container">

<h1>IOC Report</h1>

<a href="/daily-ioc/">← Back to IOC archive</a>

<p>Date: {today}</p>

<!-- CONTENT -->

<a href="/daily-ioc/">← Back to IOC archive</a>

</div>
</body>
</html>
""")


# =========================================================
# UPDATE SECTION
# =========================================================
def update_section(title, items, path):
    items = sorted(set(items))
    safe_title = escape(title)

    items_html = "\n".join(
        f"<li>{escape(item)}</li>" for item in items
    )

    section_html = f"""
<section class="ioc-section">
<h2>{safe_title}</h2>
<ul>
{items_html}
</ul>
</section>
"""

    if not os.path.exists(path):
        init_html(path)

    with open(path, "r", encoding="utf-8") as f:
        content = f.read()

    # Prepoznaje i <section> i <section class="ioc-section">.
    pattern = re.compile(
        rf"<section\b[^>]*>\s*"
        rf"<h2>{re.escape(safe_title)}</h2>.*?</section>",
        re.S,
    )

    # Uklanja i eventualne stare duplikate iste sekcije.
    content = pattern.sub("", content)

    content = content.replace(
        "<!-- CONTENT -->",
        f"{section_html}\n<!-- CONTENT -->",
        1,
    )

    with open(path, "w", encoding="utf-8") as f:
        f.write(content)


# =========================================================
# ARCHIVE INDEX + JSON EXPORT
# =========================================================
def update_archive():
    entries = sorted(
        [
            name
            for name in os.listdir(base_folder)
            if re.fullmatch(r"ioc-\d{4}-\d{2}-\d{2}", name)
            and os.path.isfile(
                os.path.join(base_folder, name, "index.html")
            )
        ],
        reverse=True,
    )

    index_path = os.path.join(base_folder, "index.html")

    with open(index_path, "w", encoding="utf-8") as f:
        f.write("""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>IOC Archive</title>
<link rel="stylesheet" href="/assets/style.css">
</head>

<body>
<div class="container">

<a class="back-link" href="/">← Back to homepage</a>

<h1>IOC Archive</h1>

<ul>
""")

        for entry in entries:
            date = entry.removeprefix("ioc-")
            f.write(
                f'<li><a href="/daily-ioc/{entry}/">'
                f"{date}</a></li>\n"
            )

        f.write("""
</ul>

</div>
</body>
</html>
""")

    latest_json_path = os.path.join(base_folder, "iocs.json")

    entries_json = [
        {
            "date": entry.removeprefix("ioc-"),
            "folder": entry,
        }
        for entry in entries[:3]
    ]

    with open(latest_json_path, "w", encoding="utf-8") as f:
        json.dump(
            {"items": entries_json},
            f,
            indent=2,
            ensure_ascii=False,
        )


# =========================================================
# PIPELINE
# =========================================================
def main():
    # Prvo dohvaćamo hashove. Ako dohvat ne uspije,
    # prekidamo izvođenje prije izmjene izvještaja.
    hashes = fetch_malware_hashes()

    feodo = fetch_feodo_ips()
    abuse = fetch_abuseipdb_ips()
    ips = sorted(set(feodo + abuse))

    os.makedirs(folder, exist_ok=True)

    update_section("Malicious IPs", ips, output_file)
    update_section("File Hashes", hashes, output_file)

    update_archive()

    print("[+] IOC generated:", output_file)
    print(f"[+] Ukupno: {len(ips)} IP adresa i {len(hashes)} hashova.")


if __name__ == "__main__":
    try:
        main()
    except RuntimeError as error:
        print(f"[!] {error}")
        raise SystemExit(1)

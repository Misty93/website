import os
import requests
import json
from datetime import datetime, timedelta

# =========================
# CONFIG
# =========================

today = datetime.now().strftime("%Y-%m-%d")

base_folder = "docs/daily-ioc"
folder = f"{base_folder}/ioc-{today}"
output_file = os.path.join(folder, "index.html")

os.makedirs(folder, exist_ok=True)

URLSCAN_API_KEY = "YOUR_URLSCAN_API_KEY"

urlscan_headers = {
    "Content-Type": "application/json",
    "API-Key": URLSCAN_API_KEY
}

# =========================
# FEEDS
# =========================

def fetch_feodo_ips():
    url = "https://feodotracker.abuse.ch/downloads/ipblocklist.csv"
    try:
        r = requests.get(url, timeout=10)
        ips = []

        for line in r.text.splitlines():
            if line.startswith("#") or not line.strip():
                continue
            ip = line.split(",")[0]
            if "." in ip:
                ips.append(ip.replace(".", "[.]"))

        return ips

    except Exception as e:
        print(f"[Feodo error] {e}")
        return []


def fetch_abuseipdb_ips():
    headers = {
        "Key": "YOUR_ABUSEIPDB_KEY",
        "Accept": "application/json"
    }

    try:
        r = requests.get(
            "https://api.abuseipdb.com/api/v2/blacklist?confidenceMinimum=90",
            headers=headers,
            timeout=10
        )

        data = r.json().get("data", [])
        return [x["ipAddress"].replace(".", "[.]") for x in data]

    except Exception as e:
        print(f"[AbuseIPDB error] {e}")
        return []


def fetch_malware_hashes():
    url = "https://bazaar.abuse.ch/export/txt/sha256/recent/"
    try:
        r = requests.get(url, timeout=10)
        return [l for l in r.text.splitlines() if l and not l.startswith("#")]
    except Exception as e:
        print(f"[MalwareBazaar error] {e}")
        return []


def fetch_threatfox_domains():
    url = "https://threatfox.abuse.ch/api/v1/"
    try:
        r = requests.post(url, data={"query": "recent", "limit": 100}, timeout=10)
        data = r.json().get("data", [])

        domains = []
        for item in data:
            d = item.get("ioc_value", "")
            if "." in d and not d.startswith("http"):
                domains.append(d.replace(".", "[.]"))

        return domains

    except Exception as e:
        print(f"[ThreatFox error] {e}")
        return []


def fetch_urlscan_domains():
    url = "https://urlscan.io/api/v1/search/?q=visibility:public"

    try:
        r = requests.get(url, headers=urlscan_headers, timeout=10)
        data = r.json().get("results", [])

        domains = []
        for item in data:
            d = item.get("page", {}).get("domain")
            if d and "." in d:
                domains.append(d.replace(".", "[.]"))

        return domains

    except Exception as e:
        print(f"[URLScan error] {e}")
        return []


# =========================
# HTML BUILDER (FULL REBUILD)
# =========================

def render_html(ips, hashes, domains, emails):
    return f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8" />
<meta name="viewport" content="width=device-width, initial-scale=1.0" />
<title>Daily IOC – {today}</title>

<style>

* {{
    box-sizing: border-box;
}}

html, body {{
    margin: 0;
    padding: 0;
    background: #121212;
    color: #fff;
    font-family: 'Segoe UI', sans-serif;
    overflow-x: hidden;
    width: 100%;
}}

.container {{
    max-width: 900px;
    margin: 0 auto;
    padding: 2rem;
}}

h1, h2 {{
    color: #ff4500;
}}

a {{
    color: #ff4500;
    text-decoration: none;
    word-break: break-word;
}}

a:hover {{
    text-decoration: underline;
}}

.section {{
    margin-top: 2rem;
}}

.box {{
    background: #1a1a1a;
    border: 1px solid #2a2a2a;
    border-radius: 10px;
    overflow-x: auto;
}}

ul {{
    list-style: none;
    margin: 0;
    padding: 0;
}}

li {{
    padding: 0.6rem 1rem;
    border-bottom: 1px solid #2a2a2a;

    font-family: monospace;

    word-break: break-all;
    overflow-wrap: anywhere;
}}

li:last-child {{
    border-bottom: none;
}}

@media (max-width: 768px) {{
    .container {{
        padding: 1rem;
    }}

    li {{
        font-size: 0.82rem;
    }}
}}

</style>
</head>

<body>

<div class="container">

<h1>IOC Report</h1>
<p>Date: {today}</p>

<div class="section">
<h2>Malicious IPs</h2>
<div class="box"><ul>
{''.join(f"<li>{i}</li>" for i in sorted(set(ips)))}
</ul></div>
</div>

<div class="section">
<h2>File Hashes</h2>
<div class="box"><ul>
{''.join(f"<li>{h}</li>" for h in sorted(set(hashes)))}
</ul></div>
</div>

<div class="section">
<h2>Domains</h2>
<div class="box"><ul>
{''.join(f"<li>{d}</li>" for d in sorted(set(domains)))}
</ul></div>
</div>

<div class="section">
<h2>Emails</h2>
<div class="box"><ul>
{''.join(f"<li>{e}</li>" for e in sorted(set(emails)))}
</ul></div>
</div>

</div>

</body>
</html>
"""


# =========================
# MAIN PIPELINE
# =========================

ips = fetch_feodo_ips() + fetch_abuseipdb_ips()
hashes = fetch_malware_hashes()
domains = fetch_threatfox_domains() + fetch_urlscan_domains()
emails = []

html = render_html(ips, hashes, domains, emails)

with open(output_file, "w", encoding="utf-8") as f:
    f.write(html)

# =========================
# JSON EXPORT
# =========================

with open(os.path.join(folder, "index.json"), "w", encoding="utf-8") as f:
    json.dump({
        "date": today,
        "ips": ips,
        "hashes": hashes,
        "domains": domains,
        "emails": emails
    }, f, indent=2)


# =========================
# ARCHIVE INDEX
# =========================

index_path = f"{base_folder}/index.html"

entries = sorted([
    d.replace("ioc-", "")
    for d in os.listdir(base_folder)
    if d.startswith("ioc-") and os.path.isdir(os.path.join(base_folder, d))
], reverse=True)

archive_html = f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8" />
<meta name="viewport" content="width=device-width, initial-scale=1.0" />
<title>IOC Archive</title>

<style>
body {{
    background:#121212;
    color:#fff;
    font-family:sans-serif;
    margin:0;
    padding:2rem;
}}
a {{
    color:#ff4500;
}}
</style>
</head>

<body>

<h1>IOC Archive</h1>
<a href="/">← Back</a>

<ul>
{''.join(f'<li><a href="/daily-ioc/ioc-{e}/">{e}</a></li>' for e in entries)}
</ul>

</body>
</html>
"""

with open(index_path, "w", encoding="utf-8") as f:
    f.write(archive_html)


# =========================
# LAST 3 DAYS JSON
# =========================

today_date = datetime.now().date()

valid_dates = {
    (today_date - timedelta(days=i)).strftime("%Y-%m-%d")
    for i in range(3)
}

items = [
    {"date": d, "folder": f"ioc-{d}"}
    for d in sorted(valid_dates, reverse=True)
]

with open(f"{base_folder}/iocs.json", "w", encoding="utf-8") as f:
    json.dump({"items": items}, f, indent=2)


print(f"[+] IOC generated: {output_file}")

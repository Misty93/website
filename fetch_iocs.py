import os
import requests
import json
import re
from datetime import datetime, timedelta

# === Datum i direktoriji ===
today = datetime.now().strftime("%Y-%m-%d")

folder = f"docs/daily-ioc/ioc-{today}"
os.makedirs(folder, exist_ok=True)

output_file = os.path.join(folder, "index.html")

# === API ključevi (NE DIRANO) ===
URLSCAN_API_KEY = "019e684b-7f1c-7081-ae66-a0599e161f03"
ABUSEIPDB_API_KEY = "9d65c5d41328705852b276fded1d7c15e23adf4e415752dcc0f895171e34e4d0a84c1"
URLHAUS_API_KEY = "9855c372bef1a34518253ab2036a90a764a95f2bd5fcf01b"

urlscan_headers = {
    "Content-Type": "application/json",
    "API-Key": URLSCAN_API_KEY
}

# =========================================================
# FEODO
# =========================================================
def fetch_feodo_ips():
    url = "https://feodotracker.abuse.ch/downloads/ipblocklist.csv"

    try:
        r = requests.get(url, timeout=20)
        if r.status_code != 200:
            return []

        ips = []

        for line in r.text.splitlines():
            if line.startswith("#") or not line.strip():
                continue

            ip = line.split(",")[0].strip()

            if re.match(r"^\d{1,3}(\.\d{1,3}){3}$", ip):
                ips.append(ip.replace(".", "[.]"))

        return ips

    except:
        return []


# =========================================================
# ABUSEIPDB (FIXED)
# =========================================================
def fetch_abuseipdb_ips():

    headers = {
        "Key": ABUSEIPDB_API_KEY.strip(),
        "Accept": "application/json"
    }

    try:
        r = requests.get(
            "https://api.abuseipdb.com/api/v2/blacklist",
            headers=headers,
            params={
                "confidenceMinimum": 90,
                "limit": 10000
            },
            timeout=20
        )

        if r.status_code != 200:
            print(r.text)
            return []

        data = r.json().get("data", [])

        return [x.get("ipAddress", "").replace(".", "[.]") for x in data if x.get("ipAddress")]

    except:
        return []


# =========================================================
# MALWAREBAZAAR
# =========================================================
def fetch_malware_hashes():

    url = "https://bazaar.abuse.ch/export/txt/sha256/recent/"

    try:
        r = requests.get(url, timeout=20)
        if r.status_code != 200:
            return []

        return [
            line.strip()
            for line in r.text.splitlines()
            if line and not line.startswith("#")
        ]

    except:
        return []


# =========================================================
# THREATFOX
# =========================================================
def fetch_threatfox_domains():

    url = "https://threatfox.abuse.ch/api/v1/"

    try:
        r = requests.post(
            url,
            json={"query": "get_iocs", "days": 1},
            timeout=20
        )

        if r.status_code != 200:
            return []

        data = r.json().get("data", [])

        out = []

        for item in data:
            ioc = item.get("ioc", "")
            if "." not in ioc:
                continue
            if ioc.startswith("http"):
                continue
            if re.match(r"^\d{1,3}(\.\d{1,3}){3}$", ioc):
                continue

            out.append(ioc.replace(".", "[.]"))

        return out

    except:
        return []


# =========================================================
# URLSCAN
# =========================================================
def fetch_urlscan_domains():

    url = "https://urlscan.io/api/v1/search/?q=visibility:public"

    try:
        r = requests.get(url, headers=urlscan_headers, timeout=20)

        if r.status_code != 200:
            return []

        data = r.json().get("results", [])

        return [
            x.get("page", {}).get("domain", "").replace(".", "[.]")
            for x in data
            if x.get("page", {}).get("domain")
        ]

    except:
        return []


# =========================================================
# URLHAUS (FIXED + ADDED)
# =========================================================
def fetch_urlhaus():

    url = "https://urlhaus-api.abuse.ch/v1/urls/recent/"

    try:
        r = requests.get(url, timeout=20)

        if r.status_code != 200:
            return [], []

        data = r.json().get("urls", [])

        ips = []
        domains = []

        for item in data:
            u = item.get("url", "")
            if "://" in u:
                dom = u.split("/")[2]
                domains.append(dom.replace(".", "[.]"))

        return ips, domains

    except:
        return [], []


# =========================================================
# EMAILS
# =========================================================
def extract_emails(domains):

    out = []

    for d in domains:
        d = d.replace("[.]", "")
        if d.startswith("www."):
            d = d[4:]
        out.append(f"abuse@{d}")

    return sorted(set(out))


# =========================================================
# HTML (UNCHANGED DESIGN)
# =========================================================
def init_html(path):

    with open(path, "w", encoding="utf-8") as f:
        f.write(f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8" />
<meta name="viewport" content="width=device-width, initial-scale=1.0" />
<title>Daily IOC – {today}</title>

<style>

* {{
    box-sizing: border-box;
}}

html {{
    overflow-x: hidden;
}}

body {{
    background-color: #121212;
    color: #ffffff;
    font-family: 'Segoe UI', sans-serif;
    margin: 0;
    padding: 2rem;
    overflow-x: hidden;
    line-height: 1.6;
}}

.container {{
    width: 100%;
    max-width: 900px;
    margin: 0 auto;
}}

h1, h2 {{
    color: #ff4500;
}}

.ioc-box {{
    background: #1a1a1a;
    border: 1px solid #2a2a2a;
    border-radius: 10px;
}}

li {{
    padding: 0.7rem 1rem;
    border-bottom: 1px solid #2a2a2a;
    font-family: monospace;
    word-break: break-word;
}}

a {{
    color: #ff4500;
}}

</style>

</head>

<body>
<div class="container">

<h1>IOC Report</h1>

<a href="/daily-ioc/">← Back to IOC archive</a>

<p>Date: {today}</p>

<!-- CONTENT -->

</div>
</body>
</html>
""")


# =========================================================
# SECTION UPDATE
# =========================================================
def update_section(title, items, path):

    items = sorted(set(items))

    html = f"""
<section>
<h2>{title}</h2>
<div class="ioc-box">
<ul>
{''.join(f"<li>{i}</li>" for i in items)}
</ul>
</div>
</section>
"""

    if not os.path.exists(path):
        init_html(path)

    with open(path, "r", encoding="utf-8") as f:
        content = f.read()

    pattern = re.compile(rf"<section>\s*<h2>{re.escape(title)}</h2>.*?</section>", re.S)

    if pattern.search(content):
        content = pattern.sub(html, content)
    else:
        content = content.replace("<!-- CONTENT -->", f"<!-- CONTENT -->\n{html}")

    with open(path, "w", encoding="utf-8") as f:
        f.write(content)


# =========================================================
# PIPELINE
# =========================================================
feodo = fetch_feodo_ips()
abuse = fetch_abuseipdb_ips()

urlhaus_ips, urlhaus_domains = fetch_urlhaus()

ips = sorted(set(feodo + abuse + urlhaus_ips))

hashes = fetch_malware_hashes()

domains = sorted(set(
    fetch_threatfox_domains()
    + fetch_urlscan_domains()
    + urlhaus_domains
))

emails = extract_emails(domains)

# =========================================================
# OUTPUT
# =========================================================
update_section("Malicious IPs", ips, output_file)
update_section("File Hashes", hashes, output_file)
update_section("Domains", domains, output_file)
update_section("Emails", emails, output_file)

with open(os.path.join(folder, "index.json"), "w") as f:
    json.dump({
        "date": today,
        "ips": ips,
        "hashes": hashes,
        "domains": domains,
        "emails": emails
    }, f, indent=2)

print("[+] IOC generated:", output_file)

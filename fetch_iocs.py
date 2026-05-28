import os
import requests
import json
import re
from datetime import datetime

# === Datum i direktoriji ===
today = datetime.now().strftime("%Y-%m-%d")

base_folder = "docs/daily-ioc"
folder = f"{base_folder}/ioc-{today}"
os.makedirs(folder, exist_ok=True)

output_file = os.path.join(folder, "index.html")

# === API ključevi iz GitHub Secrets ===
ABUSEIPDB_API_KEY = os.getenv("ABUSEIPDBKEY")
URLSCAN_API_KEY = os.getenv("URLSCANIO")
URLHAUS_API_KEY = os.getenv("URLHAUS")

urlscan_headers = {
    "Content-Type": "application/json",
    "API-Key": (URLSCAN_API_KEY or "").strip()
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
# ABUSEIPDB
# =========================================================
def fetch_abuseipdb_ips():

    if not ABUSEIPDB_API_KEY:
        return []

    headers = {
        "Key": ABUSEIPDB_API_KEY.strip(),
        "Accept": "application/json"
    }

    try:
        r = requests.get(
            "https://api.abuseipdb.com/api/v2/blacklist",
            headers=headers,
            params={
                "confidenceMinimum": 75,
                "limit": 10000
            },
            timeout=20
        )

        if r.status_code != 200:
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

        return [line.strip() for line in r.text.splitlines() if line and not line.startswith("#")]

    except:
        return []

# =========================================================
# THREATFOX
# =========================================================
def fetch_threatfox_domains():
    url = "https://threatfox.abuse.ch/api/v1/"

    try:
        r = requests.post(url, json={"query": "get_iocs", "days": 1}, timeout=20)

        if r.status_code != 200:
            return []

        data = r.json().get("data", [])

        out = []
        for item in data:
            ioc = item.get("ioc", "")
            if "." in ioc and not ioc.startswith("http"):
                out.append(ioc.replace(".", "[.]"))

        return out

    except:
        return []

# =========================================================
# URLSCAN
# =========================================================
def fetch_urlscan_domains():

    if not URLSCAN_API_KEY:
        return []

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
# URLHAUS
# =========================================================
def fetch_urlhaus():
    url = "https://urlhaus-api.abuse.ch/v1/urls/recent/"

    try:
        r = requests.get(url, timeout=20)

        if r.status_code != 200:
            return [], []

        data = r.json().get("urls", [])

        domains = []
        for item in data:
            u = item.get("url", "")
            if "://" in u:
                dom = u.split("/")[2]
                domains.append(dom.replace(".", "[.]"))

        return [], domains

    except:
        return [], []

# =========================================================
# EMAILS
# =========================================================
def extract_emails(domains):
    out = []
    for d in domains:
        d = d.replace("[.]", ".")
        if d.startswith("www."):
            d = d[4:]
        out.append(f"abuse@{d}")
    return sorted(set(out))

# =========================================================
# HTML TEMPLATE
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
* {{ box-sizing: border-box; }}

body {{
    background-color: #121212;
    color: #ffffff;
    font-family: 'Segoe UI', sans-serif;
    margin: 0;
    padding: 2rem;
}}

.container {{
    max-width: 900px;
    margin: 0 auto;
}}

h1, h2 {{ color: #ff4500; }}

.ioc-box {{
    background: #1a1a1a;
    border: 1px solid #2a2a2a;
    border-radius: 10px;
}}

li {{
    padding: 0.7rem 1rem;
    border-bottom: 1px solid #2a2a2a;
    font-family: monospace;
}}

a {{ color: #ff4500; }}
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
domains = sorted(set(fetch_threatfox_domains() + fetch_urlscan_domains() + urlhaus_domains))
emails = extract_emails(domains)

update_section("Malicious IPs", ips, output_file)
update_section("File Hashes", hashes, output_file)
update_section("Domains", domains, output_file)
update_section("Emails", emails, output_file)

# =========================================================
# ARCHIVE (FIX: always rebuilt AFTER all writes)
# =========================================================
index_path = os.path.join(base_folder, "index.html")

entries = []
for name in os.listdir(base_folder):
    path = os.path.join(base_folder, name)
    if os.path.isdir(path) and name.startswith("ioc-"):
        entries.append(name.replace("ioc-", ""))

entries.sort(reverse=True)

with open(index_path, "w", encoding="utf-8") as f:
    f.write("""<!DOCTYPE html>
<html lang='en'>
<head>
<meta charset='UTF-8' />
<title>IOC Archive</title>
<style>
body { background:#121212; color:#fff; font-family:sans-serif; padding:2rem; }
h1 { color:#ff4500; }
a { color:#ff4500; }
</style>
</head>
<body>
<h1>IOC Archive</h1>
<ul>
""")

    for d in entries:
        f.write(f"<li><a href='/daily-ioc/ioc-{d}/'>{d}</a></li>\n")

    f.write("""
</ul>
</body>
</html>
""")

# =========================================================
# JSON EXPORT
# =========================================================
with open(os.path.join(base_folder, "iocs.json"), "w", encoding="utf-8") as f:
    json.dump({
        "date": today,
        "ips": ips,
        "hashes": hashes,
        "domains": domains,
        "emails": emails
    }, f, indent=2)

print("[+] IOC generated:", output_file)

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

# === URLScan API Key ===
URLSCAN_API_KEY = "01970bef-509f-76fe-9361-b08d21433140"
urlscan_headers = {
    "Content-Type": "application/json",
    "API-Key": URLSCAN_API_KEY
}

# === Threat feed: Feodo Tracker ===
def fetch_feodo_ips():
    url = "https://feodotracker.abuse.ch/downloads/ipblocklist.csv"
    try:
        r = requests.get(url, timeout=10)
        lines = r.text.splitlines()
        ips = []
        for line in lines:
            if line.startswith("#") or not line.strip():
                continue
            ip = line.split(",")[0]
            if "." in ip:
                ips.append(ip.replace(".", "[.]"))
        return ips
    except Exception as e:
        print(f"[!] Error fetching Feodo IPs: {e}")
        return []

# === Threat feed: AbuseIPDB ===
def fetch_abuseipdb_ips():
    headers = {
        "Key": "9d65c5d41328705852b276fded1d7c15e23adf4e415752dcc0f895171e34e4c40e93554e4d0a84c1",
        "Accept": "application/json"
    }
    try:
        r = requests.get(
            "https://api.abuseipdb.com/api/v2/blacklist?confidenceMinimum=90",
            headers=headers,
            timeout=10
        )
        data = r.json().get("data", [])
        return [entry["ipAddress"].replace(".", "[.]") for entry in data]
    except Exception as e:
        print(f"[!] Error fetching AbuseIPDB IPs: {e}")
        return []

# === Threat feed: MalwareBazaar ===
def fetch_malware_hashes():
    url = "https://bazaar.abuse.ch/export/txt/sha256/recent/"
    try:
        r = requests.get(url, timeout=10)
        lines = r.text.splitlines()
        return [line for line in lines if line and not line.startswith("#")]
    except Exception as e:
        print(f"[!] Error fetching MalwareBazaar hashes: {e}")
        return []

# === Threat feed: ThreatFox domains ===
def fetch_threatfox_domains():
    url = "https://threatfox.abuse.ch/api/v1/"
    try:
        r = requests.post(url, data={"query": "recent", "limit": 100}, timeout=10)
        results = r.json().get("data", [])
        domains = []
        for item in results:
            domain = item.get("ioc_value", "")
            if "." in domain and not domain.startswith("http"):
                domains.append(domain.replace(".", "[.]"))
        return domains
    except Exception as e:
        print(f"[!] Error fetching ThreatFox domains: {e}")
        return []

# === URLScan: Fetch suspicious domains ===
def fetch_urlscan_domains():
    search_url = "https://urlscan.io/api/v1/search/?q=visibility:public"
    try:
        r = requests.get(search_url, headers=urlscan_headers, timeout=10)
        data = r.json().get("results", [])
        domains = []
        for item in data:
            domain = item.get("page", {}).get("domain")
            if domain and "." in domain:
                domains.append(domain.replace(".", "[.]"))
        return domains
    except Exception as e:
        print(f"[!] Error fetching URLScan domains: {e}")
        return []

# === HTML template init ===
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

    body {{
      background-color: #121212;
      color: #ffffff;
      font-family: 'Segoe UI', sans-serif;
      margin: 0;
      padding: 2rem;
      overflow-x: hidden;
    }}

    h1, h2 {{
      color: #ff4500;
    }}

    .container {{
      max-width: 900px;
      margin: 0 auto;
    }}

    .ioc-section {{
      margin-bottom: 2rem;
    }}

    .ioc-box {{
      background: #1a1a1a;
      border: 1px solid #2a2a2a;
      border-radius: 10px;
      max-width: 100%;
      overflow-x: auto;
    }}

    ul {{
      list-style: none;
      padding: 0;
      margin: 0;
    }}

    li {{
      padding: 0.6rem 1rem;
      border-bottom: 1px solid #2a2a2a;
      font-family: monospace;
      word-break: break-word;
      overflow-wrap: anywhere;
    }}

    li:last-child {{
      border-bottom: none;
    }}

    a {{
      color: #ff4500;
      text-decoration: none;
    }}

    a:hover {{
      text-decoration: underline;
    }}

    .back-link {{
      display: inline-block;
      margin-bottom: 1rem;
    }}
  </style>
</head>

<body>
  <div class="container">

    <h1>IOC Report</h1>
    <a class="back-link" href="/daily-ioc/">← Back to IOC archive</a>
    <p>Date: {today}</p>

    <!-- CONTENT -->

  </div>
</body>
</html>
""")

# === HTML section update ===
def update_section(section_title, new_items, html_path):
    deduped_items = sorted(set(new_items))

    section_html = f"""
    <section class="ioc-section">
      <h2>{section_title}</h2>
      <div class="ioc-box">
        <ul>
          {''.join(f"<li>{item}</li>" for item in deduped_items)}
        </ul>
      </div>
    </section>
    """

    if not os.path.exists(html_path):
        init_html(html_path)

    with open(html_path, "r", encoding="utf-8") as f:
        content = f.read()

    pattern = re.compile(
        rf"<section class=\"ioc-section\">\s*<h2>{re.escape(section_title)}</h2>.*?</section>",
        re.DOTALL
    )

    if pattern.search(content):
        content = pattern.sub(section_html, content)
    else:
        content = content.replace("<!-- CONTENT -->", f"<!-- CONTENT -->\n{section_html}")

    with open(html_path, "w", encoding="utf-8") as f:
        f.write(content)

# === Fetch IOC data ===
ips = list(set(fetch_feodo_ips() + fetch_abuseipdb_ips()))
hashes = fetch_malware_hashes()
domains = list(set(fetch_threatfox_domains() + fetch_urlscan_domains()))
emails = []

# === Write IOC sections ===
update_section("Malicious IPs", ips, output_file)
update_section("File Hashes", hashes, output_file)
update_section("Domains", domains, output_file)
update_section("Emails", emails, output_file)

# === Save JSON ===
with open(os.path.join(folder, "index.json"), "w", encoding="utf-8") as f:
    json.dump({
        "date": today,
        "ips": ips,
        "hashes": hashes,
        "domains": domains,
        "emails": emails
    }, f, indent=2)

# === Archive index ===
index_path = "docs/daily-ioc/index.html"
base_folder = "docs/daily-ioc"

entries = [
    name.replace("ioc-", "")
    for name in os.listdir(base_folder)
    if name.startswith("ioc-") and os.path.isdir(os.path.join(base_folder, name))
]
entries.sort(reverse=True)

with open(index_path, "w", encoding="utf-8") as f:
    f.write("""<!DOCTYPE html>
<html lang='en'>
<head>
  <meta charset='UTF-8' />
  <title>IOC Archive</title>
  <meta name='viewport' content='width=device-width, initial-scale=1.0' />
  <style>
    body { background-color: #121212; color: #fff; font-family: sans-serif; padding: 2rem; }
    h1 { color: #ff4500; }
    ul { list-style: none; padding: 0; }
    li { margin: 0.3rem 0; }
    a { color: #ff4500; text-decoration: none; }
    a:hover { text-decoration: underline; }
  </style>
</head>
<body>
  <h1>IOC Archive</h1>
  <p><a href='/'>← Back to homepage</a></p>
  <ul>
""")
    for date in entries:
        f.write(f"    <li><a href='/daily-ioc/ioc-{date}/'>{date}</a></li>\n")
    f.write("""  </ul>
</body>
</html>""")

# === Last 3 days JSON ===
latest_json_path = "docs/daily-ioc/iocs.json"

today_date = datetime.now().date()
valid_dates = {
    (today_date - timedelta(days=i)).strftime("%Y-%m-%d")
    for i in range(3)
}

items = []
for name in os.listdir(base_folder):
    if name.startswith("ioc-") and os.path.isdir(os.path.join(base_folder, name)):
        date_str = name.replace("ioc-", "")
        if date_str in valid_dates:
            items.append({
                "date": date_str,
                "folder": name
            })

items.sort(key=lambda x: x["date"], reverse=True)

with open(latest_json_path, "w", encoding="utf-8") as f:
    json.dump({"items": items}, f, indent=2)

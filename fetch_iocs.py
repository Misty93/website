import os
import requests
import json
import re
from datetime import datetime

# === Datum i direktoriji ===
today = datetime.now().strftime("%Y-%m-%d")
folder = f"docs/daily-ioc/ioc-{today}"
os.makedirs(folder, exist_ok=True)
output_file = os.path.join(folder, "index.html")

# === Threat feed: Feodo Tracker ===
def fetch_feodo_ips():
    url = "https://feodotracker.abuse.ch/downloads/ipblocklist.csv"
    try:
        r = requests.get(url)
        lines = r.text.splitlines()
        ips = []
        for line in lines:
            if line.startswith("#") or not line.strip():
                continue
            ip = line.split(",")[0]
            if "." in ip:
                ips.append(ip.replace(".", "[.]"))
        return ips
    except:
        return []

# === Threat feed: AbuseIPDB (API key) ===
def fetch_abuseipdb_ips():
    headers = {
        "Key": "9d65c5d41328705852b276fded1d7c15e23adf4e415752dcc0f895171e34e4c40e93554e4d0a84c1",
        "Accept": "application/json"
    }
    try:
        r = requests.get("https://api.abuseipdb.com/api/v2/blacklist?confidenceMinimum=90", headers=headers)
        data = r.json().get("data", [])
        return [entry["ipAddress"].replace(".", "[.]") for entry in data]
    except:
        return []

# === Threat feed: MalwareBazaar ===
def fetch_malware_hashes():
    url = "https://bazaar.abuse.ch/export/txt/sha256/recent/"
    try:
        r = requests.get(url)
        lines = r.text.splitlines()
        return [line for line in lines if line and not line.startswith("#")]
    except:
        return []

# === Threat feed: ThreatFox domains ===
def fetch_threatfox_domains():
    url = "https://threatfox.abuse.ch/api/v1/"
    try:
        r = requests.post(url, data={"query": "recent", "limit": 100})
        domains = []
        results = r.json().get("data", [])
        for item in results:
            domain = item.get("ioc_value", "")
            if "." in domain and not domain.startswith("http"):
                domains.append(domain.replace(".", "[.]"))
        return domains
    except:
        return []

# === HTML template i sekcijski update ===
def update_section(section_title, new_items, html_path):
    deduped_items = sorted(set(new_items))
    section_html = f"<h2>{section_title}</h2>\n<ul>\n" + "\n".join(f"<li>{item}</li>" for item in deduped_items) + "\n</ul>"

    if not os.path.exists(html_path):
        with open(html_path, "w", encoding="utf-8") as f:
            f.write(f"""<!DOCTYPE html>
<html><head><meta charset='UTF-8'><title>IOC {today}</title>
<style>body{{background:#121212;color:#fff;font-family:sans-serif;padding:2rem;}}
h1,h2,h3{{color:#ff4500}}ul{{list-style:none;padding:0}}li{{padding:0.2rem 0}}
a{{color:#ff4500;text-decoration:none}}a:hover{{text-decoration:underline}}</style>
</head><body>
<h1>Daily IOC Report – {today}</h1>
<p><a href="/daily-ioc/">← Back to archive</a></p>
</body></html>""")

    with open(html_path, "r", encoding="utf-8") as f:
        content = f.read()

    pattern = re.compile(rf"<h2>{re.escape(section_title)}</h2>\s*<ul>.*?</ul>", re.DOTALL)
    if pattern.search(content):
        content = pattern.sub(section_html, content)
    else:
        content = content.replace("</body>", section_html + "\n</body>")

    with open(html_path, "w", encoding="utf-8") as f:
        f.write(content)

# === Fetch IOC podaci ===
ips = fetch_feodo_ips() + fetch_abuseipdb_ips()
hashes = fetch_malware_hashes()
domains = fetch_threatfox_domains()
emails = []  # za kasnije

# === Piši IOC u HTML ===
update_section("🔴 Malicious IPs", ips, output_file)
update_section("🧬 File Hashes", hashes, output_file)
update_section("🌐 Domains", domains, output_file)
update_section("✉️ Emails", emails, output_file)

# === Snimi IOC i kao JSON ===
with open(os.path.join(folder, "index.json"), "w", encoding="utf-8") as f:
    json.dump({
        "date": today,
        "ips": ips,
        "hashes": hashes,
        "domains": domains,
        "emails": emails
    }, f, indent=2)

# === Obnovi index.html ===
index_path = "docs/daily-ioc/index.html"
base_folder = "docs/daily-ioc"
entries = []

for name in os.listdir(base_folder):
    if name.startswith("ioc-") and os.path.isdir(os.path.join(base_folder, name)):
        date = name.replace("ioc-", "")
        entries.append(date)

entries.sort(reverse=True)

with open(index_path, "w", encoding="utf-8") as f:
    f.write("""<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8" />
  <title>IOC Archive</title>
  <meta name="viewport" content="width=device-width, initial-scale=1.0" />
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
  <ul>
""")
    for date in entries:
        f.write(f'    <li><a href="/daily-ioc/ioc-{date}/">{date}</a></li>\n')
    f.write("""  </ul>
</body>
</html>""")

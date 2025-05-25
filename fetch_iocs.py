import os
import requests
from datetime import datetime

# === Fetch IPs from Feodo Tracker ===
def fetch_feodo_ips():
    url = "https://feodotracker.abuse.ch/downloads/ipblocklist.csv"
    r = requests.get(url)
    lines = r.text.splitlines()
    ips = []
    for line in lines:
        if line.startswith("#") or not line.strip():
            continue
        ip = line.split(",")[0]
        ips.append(ip.replace(".", "[.]"))
    return ips

# === Fetch hashes from MalwareBazaar ===
def fetch_malware_hashes():
    url = "https://bazaar.abuse.ch/export/txt/sha256/recent/"
    r = requests.get(url)
    lines = r.text.splitlines()
    return [line for line in lines if line and not line.startswith("#")]

# === Fetch domains from ThreatFox ===
def fetch_threatfox_domains():
    url = "https://threatfox.abuse.ch/api/v1/"
    r = requests.post(url, data={"query": "recent", "limit": 100})
    domains = []
    try:
        results = r.json().get("data", [])
        for item in results:
            domain = item.get("ioc_value", "")
            if "." in domain and not domain.startswith("http"):
                domains.append(domain.replace(".", "[.]"))
    except Exception as e:
        print("Error parsing ThreatFox:", e)
    return domains

# === HTML helper ===
def html_list(title, items):
    if not items:
        return ""
    lis = "\n".join(f"<li>{i}</li>" for i in items)
    return f"<h2>{title}</h2><ul>{lis}</ul>"

# === Generate output ===
today = datetime.now().strftime("%Y-%m-%d")
folder = f"docs/daily-ioc/ioc-{today}"
os.makedirs(folder, exist_ok=True)
output_file = os.path.join(folder, "index.html")

# === Fetch all IOCs ===
all_ips = fetch_feodo_ips()
all_hashes = fetch_malware_hashes()
all_domains = fetch_threatfox_domains()
all_emails = []  # empty for now, can be added later

# === Generate HTML ===
html = f"""<html><head><meta charset='UTF-8'><title>IOC {today}</title>
<style>body{{background:#121212;color:#fff;font-family:sans-serif;padding:2rem;}}
h1,h2,h3{{color:#ff4500}}ul{{list-style:none;padding:0}}li{{padding:0.2rem 0}}</style>
</head><body>
<h1>Daily IOC Report – {today}</h1>
{html_list("🔴 Malicious IPs", all_ips)}
{html_list("🧬 File Hashes", all_hashes)}
{html_list("🌐 Domains", all_domains)}
{html_list("✉️ Emails", all_emails)}
<p><a href="/daily-ioc/">← Back to archive</a></p>
</body></html>
"""

with open(output_file, "w", encoding="utf-8") as f:
    f.write(html)

# === Update archive index ===
index_path = "docs/daily-ioc/index.html"
entry = f'<li><a href="/daily-ioc/ioc-{today}/">{today}</a></li>'

if os.path.exists(index_path):
    with open(index_path, "r", encoding="utf-8") as f:
        content = f.read()
    if entry not in content:
        content = content.replace("<ul>", f"<ul>\n    {entry}", 1)
        with open(index_path, "w", encoding="utf-8") as f:
            f.write(content)

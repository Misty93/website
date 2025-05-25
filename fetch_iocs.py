import os
import requests
import json
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

# === APPEND funkcija za HTML ===
def append_section_if_missing(section_title, new_items, html_path):
    if not os.path.exists(html_path):
        # ako ne postoji, napravi osnovni dokument
        with open(html_path, "w", encoding="utf-8") as f:
            f.write(f"<html><head><meta charset='UTF-8'><title>IOC {today}</title>\n")
            f.write("<style>body{background:#121212;color:#fff;font-family:sans-serif;padding:2rem;}h1,h2,h3{color:#ff4500}ul{list-style:none;padding:0}li{padding:0.2rem 0}</style>\n")
            f.write("</head><body>\n")
            f.write(f"<h1>Daily IOC Report – {today}</h1>\n")
            f.write("<p><a href=\"/daily-ioc/\">← Back to archive</a></p>\n")
            f.write("</body></html>")

    with open(html_path, "r", encoding="utf-8") as f:
        content = f.read()

    new_lines = []
    for item in new_items:
        if item not in content:
            new_lines.append(f"<li>{item}</li>")

    if new_lines:
        insertion = f"<h2>{section_title}</h2><ul>\n" + "\n".join(new_lines) + "\n</ul>"
        content = content.replace("</body>", insertion + "\n</body>")
        with open(html_path, "w", encoding="utf-8") as f:
            f.write(content)

# === Glavna logika ===
today = datetime.now().strftime("%Y-%m-%d")
folder = f"docs/daily-ioc/ioc-{today}"
os.makedirs(folder, exist_ok=True)
output_file = os.path.join(folder, "index.html")

# === Dohvati IOC-e ===
all_ips = fetch_feodo_ips()
all_hashes = fetch_malware_hashes()
all_domains = fetch_threatfox_domains()
all_emails = []  # opcionalno kasnije

# === Upis u HTML (append) ===
append_section_if_missing("🔴 Malicious IPs", all_ips, output_file)
append_section_if_missing("🧬 File Hashes", all_hashes, output_file)
append_section_if_missing("🌐 Domains", all_domains, output_file)
append_section_if_missing("✉️ Emails", all_emails, output_file)

# === Upis u JSON ===
json_output_file = os.path.join(folder, "index.json")
ioc_data = {
    "date": today,
    "ips": all_ips,
    "hashes": all_hashes,
    "domains": all_domains,
    "emails": all_emails
}
with open(json_output_file, "w", encoding="utf-8") as f:
    json.dump(ioc_data, f, indent=2)

# === Update index.html (arhiva linkova) ===
index_path = "docs/daily-ioc/index.html"
entry = f'<li><a href="/daily-ioc/ioc-{today}/">{today}</a></li>'

if os.path.exists(index_path):
    with open(index_path, "r", encoding="utf-8") as f:
        content = f.read()
    if entry not in content:
        content = content.replace("<ul>", f"<ul>\n    {entry}", 1)
        with open(index_path, "w", encoding="utf-8") as f:
            f.write(content)

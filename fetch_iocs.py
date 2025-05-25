import os
import requests
import json
import re
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

# === Zamjena sekcije u HTML-u ===
def update_section(section_title, new_items, html_path):
    if not os.path.exists(html_path):
        with open(html_path, "w", encoding="utf-8") as f:
            f.write(f"<html><head><meta charset='UTF-8'><title>IOC {today}</title>\n")
            f.write("<style>body{{background:#121212;color:#fff;font-family:sans-serif;padding:2rem;}}h1,h2,h3{{color:#ff4500}}ul{{list-style:none;padding:0}}li{{padding:0.2rem 0}}</style>\n")
            f.write("</head><body>\n")
            f.write(f"<h1>Daily IOC Report – {today}</h1>\n")
            f.write("<p><a href=\"/daily-ioc/\">← Back to archive</a></p>\n")
            f.write("</body></html>")

    with open(html_path, "r", encoding="utf-8") as f:
        content = f.read()

    deduped_items = sorted(set(new_items))
    section_html = f"<h2>{section_title}</h2>\n<ul>\n" + "\n".join(f"<li>{item}</li>" for item in deduped_items) + "\n</ul>"

    pattern = re.compile(rf"<h2>{re.escape(section_title)}</h2>\s*<ul>.*?</ul>", re.DOTALL)

    if pattern.search(content):
        content = pattern.sub(section_html, content)
    else:
        content = content.replace("</body>", section_html + "\n</body>")

    with open(html_path, "w", encoding="utf-8") as f:
        f.write(content)

# === Setup paths and date ===
today = datetime.now().strftime("%Y-%m-%d")
folder = f"docs/daily-ioc/ioc-{today}"
os.makedirs(folder, exist_ok=True)
output_file = os.path.join(folder, "index.html")

# === Fetch all IOC data ===
all_ips = fetch_feodo_ips()
all_hashes = fetch_malware_hashes()
all_domains = fetch_threatfox_domains()
all_emails = []  # opcionalno za kasnije

# === Insert/update data to HTML report ===
update_section("🔴 Malicious IPs", all_ips, output_file)
update_section("🧬 File Hashes", all_hashes, output_file)
update_section("🌐 Domains", all_domains, output_file)
update_section("✉️ Emails", all_emails, output_file)

# === Save to JSON ===
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

# === Rebuild main index.html with all folders ===
index_path = "docs/daily-ioc/index.html"
base_folder = "docs/daily-ioc"
entries = []

for name in os.listdir(base_folder):
    full_path = os.path.join(base_folder, name)
    if name.startswith("ioc-") and os.path.isdir(full_path):
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

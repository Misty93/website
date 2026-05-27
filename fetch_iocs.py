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

# === API KEYS ===
URLSCAN_API_KEY = "YOUR_URLSCAN_API_KEY"
ABUSEIPDB_API_KEY = "YOUR_ABUSEIPDB_API_KEY"

urlscan_headers = {
    "Content-Type": "application/json",
    "API-Key": URLSCAN_API_KEY,
    "User-Agent": "Mozilla/5.0"
}

# =========================================================
# FEODO TRACKER
# =========================================================
def fetch_feodo_ips():

    url = "https://feodotracker.abuse.ch/downloads/ipblocklist.csv"

    headers = {
        "User-Agent": "Mozilla/5.0"
    }

    try:

        r = requests.get(
            url,
            headers=headers,
            timeout=15
        )

        r.raise_for_status()

        ips = []

        for line in r.text.splitlines():

            if line.startswith("#") or not line.strip():
                continue

            parts = line.split(",")

            if len(parts) < 1:
                continue

            ip = parts[0].strip()

            if re.match(r"^\d+\.\d+\.\d+\.\d+$", ip):
                ips.append(ip.replace(".", "[.]"))

        print(f"[+] Feodo IPs fetched: {len(ips)}")

        return ips

    except Exception as e:

        print(f"[!] Error fetching Feodo IPs: {e}")
        return []


# =========================================================
# ABUSEIPDB
# =========================================================
def fetch_abuseipdb_ips():

    headers = {
        "Key": ABUSEIPDB_API_KEY,
        "Accept": "application/json",
        "User-Agent": "Mozilla/5.0"
    }

    try:

        r = requests.get(
            "https://api.abuseipdb.com/api/v2/blacklist?confidenceMinimum=90",
            headers=headers,
            timeout=15
        )

        r.raise_for_status()

        data = r.json().get("data", [])

        ips = []

        for entry in data:

            ip = entry.get("ipAddress")

            if ip and re.match(r"^\d+\.\d+\.\d+\.\d+$", ip):
                ips.append(ip.replace(".", "[.]"))

        print(f"[+] AbuseIPDB IPs fetched: {len(ips)}")

        return ips

    except Exception as e:

        print(f"[!] Error fetching AbuseIPDB IPs: {e}")
        return []


# =========================================================
# MALWAREBAZAAR HASHES
# =========================================================
def fetch_malware_hashes():

    url = "https://bazaar.abuse.ch/export/txt/sha256/recent/"

    headers = {
        "User-Agent": "Mozilla/5.0"
    }

    try:

        r = requests.get(
            url,
            headers=headers,
            timeout=15
        )

        r.raise_for_status()

        hashes = []

        for line in r.text.splitlines():

            if line.startswith("#") or not line.strip():
                continue

            hashes.append(line.strip())

        print(f"[+] Malware hashes fetched: {len(hashes)}")

        return hashes

    except Exception as e:

        print(f"[!] Error fetching hashes: {e}")
        return []


# =========================================================
# THREATFOX DOMAINS
# =========================================================
def fetch_threatfox_domains():

    url = "https://threatfox.abuse.ch/api/v1/"

    headers = {
        "User-Agent": "Mozilla/5.0"
    }

    try:

        r = requests.post(
            url,
            data={
                "query": "recent",
                "limit": 100
            },
            headers=headers,
            timeout=15
        )

        r.raise_for_status()

        results = r.json().get("data", [])

        domains = []

        for item in results:

            domain = item.get("ioc_value", "")

            if "." in domain and not domain.startswith("http"):
                domains.append(domain.replace(".", "[.]"))

        print(f"[+] ThreatFox domains fetched: {len(domains)}")

        return domains

    except Exception as e:

        print(f"[!] Error fetching ThreatFox domains: {e}")
        return []


# =========================================================
# URLSCAN DOMAINS
# =========================================================
def fetch_urlscan_domains():

    search_url = "https://urlscan.io/api/v1/search/?q=visibility:public"

    try:

        r = requests.get(
            search_url,
            headers=urlscan_headers,
            timeout=15
        )

        r.raise_for_status()

        data = r.json().get("results", [])

        domains = []

        for item in data:

            domain = item.get("page", {}).get("domain")

            if domain and "." in domain:
                domains.append(domain.replace(".", "[.]"))

        print(f"[+] URLScan domains fetched: {len(domains)}")

        return domains

    except Exception as e:

        print(f"[!] Error fetching URLScan domains: {e}")
        return []


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

<style>

* {{
    box-sizing: border-box;
}}

html {{
    overflow-x: hidden;
}}

body {{
    margin: 0;
    padding: 1rem;
    background: #121212;
    color: #ffffff;
    font-family: 'Segoe UI', sans-serif;
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
    word-break: break-word;
}}

a {{
    color: #ff4500;
    text-decoration: none;
    word-break: break-word;
}}

a:hover {{
    text-decoration: underline;
}}

.ioc-section {{
    margin-bottom: 2rem;
}}

.ioc-box {{
    background: #1a1a1a;
    border: 1px solid #2a2a2a;
    border-radius: 10px;
    overflow-x: auto;
    width: 100%;
}}

ul {{
    list-style: none;
    padding: 0;
    margin: 0;
}}

li {{
    padding: 0.7rem 1rem;
    border-bottom: 1px solid #2a2a2a;
    font-family: monospace;
    font-size: 0.92rem;
    overflow-wrap: anywhere;
    word-break: break-word;
}}

li:last-child {{
    border-bottom: none;
}}

.back-link {{
    display: inline-block;
    margin-bottom: 1rem;
}}

@media (max-width: 768px) {{

    body {{
        padding: 0.8rem;
    }}

    h1 {{
        font-size: 1.6rem;
    }}

    h2 {{
        font-size: 1.2rem;
    }}

    li {{
        font-size: 0.82rem;
        padding: 0.65rem 0.8rem;
    }}
}}

</style>

</head>

<body>

<div class="container">

<h1>IOC Report</h1>

<a class="back-link" href="/daily-ioc/">
← Back to IOC archive
</a>

<p>Date: {today}</p>

<!-- CONTENT -->

</div>

</body>
</html>
""")


# =========================================================
# UPDATE HTML SECTION
# =========================================================
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
        content = content.replace(
            "<!-- CONTENT -->",
            f"<!-- CONTENT -->\n{section_html}"
        )

    with open(html_path, "w", encoding="utf-8") as f:
        f.write(content)


# =========================================================
# FETCH IOC DATA
# =========================================================
ips = list(set(
    fetch_feodo_ips() +
    fetch_abuseipdb_ips()
))

hashes = fetch_malware_hashes()

domains = list(set(
    fetch_threatfox_domains() +
    fetch_urlscan_domains()
))

emails = []

print(f"[+] Total IPs: {len(ips)}")
print(f"[+] Total Hashes: {len(hashes)}")
print(f"[+] Total Domains: {len(domains)}")


# =========================================================
# WRITE IOC SECTIONS
# =========================================================
update_section("Malicious IPs", ips, output_file)
update_section("File Hashes", hashes, output_file)
update_section("Domains", domains, output_file)
update_section("Emails", emails, output_file)


# =========================================================
# SAVE JSON
# =========================================================
with open(
    os.path.join(folder, "index.json"),
    "w",
    encoding="utf-8"
) as f:

    json.dump({
        "date": today,
        "ips": ips,
        "hashes": hashes,
        "domains": domains,
        "emails": emails
    }, f, indent=2)


# =========================================================
# ARCHIVE PAGE
# =========================================================
base_folder = "docs/daily-ioc"
index_path = os.path.join(base_folder, "index.html")

entries = [
    name.replace("ioc-", "")
    for name in os.listdir(base_folder)
    if name.startswith("ioc-")
    and os.path.isdir(os.path.join(base_folder, name))
]

entries.sort(reverse=True)

with open(index_path, "w", encoding="utf-8") as f:

    f.write("""<!DOCTYPE html>
<html lang="en">

<head>

<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">

<title>IOC Archive</title>

<style>

body {
    background: #121212;
    color: #ffffff;
    font-family: 'Segoe UI', sans-serif;
    padding: 1rem;
    margin: 0;
}

.container {
    max-width: 800px;
    margin: 0 auto;
}

h1 {
    color: #ff4500;
}

ul {
    list-style: none;
    padding: 0;
}

li {
    margin: 0.5rem 0;
}

a {
    color: #ff4500;
    text-decoration: none;
}

a:hover {
    text-decoration: underline;
}

</style>

</head>

<body>

<div class="container">

<h1>IOC Archive</h1>

<p>
<a href="/">← Back to homepage</a>
</p>

<ul>
""")

    for date in entries:

        f.write(
            f'<li><a href="/daily-ioc/ioc-{date}/">{date}</a></li>\n'
        )

    f.write("""
</ul>

</div>

</body>
</html>
""")


# =========================================================
# LAST 3 DAYS JSON
# =========================================================
latest_json_path = "docs/daily-ioc/iocs.json"

today_date = datetime.now().date()

valid_dates = {
    (today_date - timedelta(days=i)).strftime("%Y-%m-%d")
    for i in range(3)
}

items = []

for name in os.listdir(base_folder):

    if (
        name.startswith("ioc-")
        and os.path.isdir(os.path.join(base_folder, name))
    ):

        date_str = name.replace("ioc-", "")

        if date_str in valid_dates:

            items.append({
                "date": date_str,
                "folder": name
            })

items.sort(
    key=lambda x: x["date"],
    reverse=True
)

with open(latest_json_path, "w", encoding="utf-8") as f:

    json.dump({
        "items": items
    }, f, indent=2)

print(f"[+] IOC report generated: {output_file}")

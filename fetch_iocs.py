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

# === API ključevi ===
URLSCAN_API_KEY = "YOUR_URLSCAN_API_KEY"

ABUSEIPDB_API_KEY = "YOUR_ABUSEIPDB_KEY"

urlscan_headers = {
    "Content-Type": "application/json",
    "API-Key": URLSCAN_API_KEY
}

# === Threat feed: Feodo Tracker ===
def fetch_feodo_ips():

    url = "https://feodotracker.abuse.ch/downloads/ipblocklist.csv"

    try:
        r = requests.get(url, timeout=20)

        if r.status_code != 200:
            print(f"[!] Feodo HTTP error: {r.status_code}")
            return []

        lines = r.text.splitlines()

        ips = []

        for line in lines:

            if line.startswith("#") or not line.strip():
                continue

            parts = line.split(",")

            if not parts:
                continue

            ip = parts[0].strip()

            if re.match(r"^\d{1,3}(\.\d{1,3}){3}$", ip):
                ips.append(ip.replace(".", "[.]"))

        print(f"[+] Feodo IPs fetched: {len(ips)}")

        return ips

    except Exception as e:
        print(f"[!] Error fetching Feodo IPs: {e}")
        return []


# === Threat feed: AbuseIPDB ===
def fetch_abuseipdb_ips():

    headers = {
        "Key": ABUSEIPDB_API_KEY,
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
            print(f"[!] AbuseIPDB HTTP error: {r.status_code}")
            print(r.text)
            return []

        data = r.json().get("data", [])

        ips = []

        for entry in data:

            ip = entry.get("ipAddress")

            if ip:
                ips.append(ip.replace(".", "[.]"))

        print(f"[+] AbuseIPDB IPs fetched: {len(ips)}")

        return ips

    except Exception as e:
        print(f"[!] Error fetching AbuseIPDB IPs: {e}")
        return []


# === Threat feed: MalwareBazaar ===
def fetch_malware_hashes():

    url = "https://bazaar.abuse.ch/export/txt/sha256/recent/"

    try:

        r = requests.get(url, timeout=20)

        if r.status_code != 200:
            print(f"[!] MalwareBazaar HTTP error: {r.status_code}")
            return []

        lines = r.text.splitlines()

        hashes = []

        for line in lines:

            line = line.strip()

            if not line or line.startswith("#"):
                continue

            hashes.append(line)

        print(f"[+] Malware hashes fetched: {len(hashes)}")

        return hashes

    except Exception as e:
        print(f"[!] Error fetching MalwareBazaar hashes: {e}")
        return []


# === ThreatFox domains ===
def fetch_threatfox_domains():

    url = "https://threatfox.abuse.ch/api/v1/"

    try:

        payload = {
            "query": "get_iocs",
            "days": 1
        }

        r = requests.post(
            url,
            json=payload,
            timeout=20
        )

        if r.status_code != 200:
            print(f"[!] ThreatFox HTTP error: {r.status_code}")
            return []

        data = r.json().get("data", [])

        domains = []

        for item in data:

            ioc = item.get("ioc")

            if not ioc:
                continue

            if "." not in ioc:
                continue

            if ioc.startswith("http"):
                continue

            if re.match(r"^\d{1,3}(\.\d{1,3}){3}$", ioc):
                continue

            domains.append(ioc.replace(".", "[.]"))

        print(f"[+] ThreatFox domains fetched: {len(domains)}")

        return domains

    except Exception as e:
        print(f"[!] Error fetching ThreatFox domains: {e}")
        return []


# === URLScan domains ===
def fetch_urlscan_domains():

    search_url = "https://urlscan.io/api/v1/search/?q=visibility:public"

    try:

        r = requests.get(
            search_url,
            headers=urlscan_headers,
            timeout=20
        )

        if r.status_code != 200:
            print(f"[!] URLScan HTTP error: {r.status_code}")
            return []

        data = r.json().get("results", [])

        domains = []

        for item in data:

            domain = item.get("page", {}).get("domain")

            if not domain:
                continue

            if "." not in domain:
                continue

            domains.append(domain.replace(".", "[.]"))

        print(f"[+] URLScan domains fetched: {len(domains)}")

        return domains

    except Exception as e:
        print(f"[!] Error fetching URLScan domains: {e}")
        return []


# === Email extraction ===
def extract_emails(domains):

    emails = []

    for domain in domains:

        clean_domain = domain.replace("[.]", ".")

        if clean_domain.startswith("www."):
            clean_domain = clean_domain[4:]

        emails.append(f"abuse@{clean_domain}")

    return sorted(set(emails))


# === HTML template ===
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

p {{
    overflow-wrap: break-word;
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
    font-size: 0.95rem;
    word-break: break-word;
    overflow-wrap: anywhere;
}}

li:last-child {{
    border-bottom: none;
}}

a {{
    color: #ff4500;
    text-decoration: none;
    overflow-wrap: anywhere;
}}

a:hover {{
    text-decoration: underline;
}}

.back-link {{
    display: inline-block;
    margin-bottom: 1rem;
}}

@media (max-width: 768px) {{

    body {{
        padding: 1rem;
        font-size: 0.95rem;
    }}

    .container {{
        max-width: 100%;
    }}

    h1 {{
        font-size: 1.8rem;
        line-height: 1.2;
    }}

    h2 {{
        font-size: 1.3rem;
        line-height: 1.3;
    }}

    li {{
        padding: 0.65rem 0.8rem;
        font-size: 0.82rem;
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

        content = content.replace(
            "<!-- CONTENT -->",
            f"<!-- CONTENT -->\n{section_html}"
        )

    with open(html_path, "w", encoding="utf-8") as f:
        f.write(content)


# === Fetch IOC data ===
feodo_ips = fetch_feodo_ips()

abuse_ips = fetch_abuseipdb_ips()

ips = sorted(set(
    feodo_ips +
    abuse_ips
))

hashes = sorted(set(
    fetch_malware_hashes()
))

domains = sorted(set(
    fetch_threatfox_domains() +
    fetch_urlscan_domains()
))

emails = extract_emails(domains)

print(f"[+] Final IP count: {len(ips)}")
print(f"[+] Final hash count: {len(hashes)}")
print(f"[+] Final domain count: {len(domains)}")
print(f"[+] Final email count: {len(emails)}")


# === Write HTML sections ===
update_section("Malicious IPs", ips, output_file)

update_section("File Hashes", hashes, output_file)

update_section("Domains", domains, output_file)

update_section("Emails", emails, output_file)


# === Save JSON ===
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


# === Archive index ===
index_path = "docs/daily-ioc/index.html"

base_folder = "docs/daily-ioc"

entries = [
    name.replace("ioc-", "")
    for name in os.listdir(base_folder)
    if name.startswith("ioc-")
    and os.path.isdir(os.path.join(base_folder, name))
]

entries.sort(reverse=True)

with open(index_path, "w", encoding="utf-8") as f:

    f.write("""<!DOCTYPE html>
<html lang='en'>

<head>

<meta charset='UTF-8' />

<meta name='viewport' content='width=device-width, initial-scale=1.0' />

<title>IOC Archive</title>

<style>

body {
    background-color: #121212;
    color: #ffffff;
    font-family: 'Segoe UI', sans-serif;
    padding: 2rem;
}

h1 {
    color: #ff4500;
}

ul {
    list-style: none;
    padding: 0;
}

li {
    margin: 0.4rem 0;
}

a {
    color: #ff4500;
    text-decoration: none;
}

a:hover {
    text-decoration: underline;
}

@media (max-width: 768px) {

    body {
        padding: 1rem;
    }
}

</style>

</head>

<body>

<h1>IOC Archive</h1>

<p>
<a href="/">← Back</a>
</p>

<ul>
""")

    for date in entries:

        f.write(
            f'<li><a href="/daily-ioc/ioc-{date}/">{date}</a></li>\n'
        )

    f.write("""
</ul>

</body>
</html>
""")


# === Last 3 days JSON ===
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

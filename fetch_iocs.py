import paramiko
import os
import json
import re
from datetime import datetime

# === SSH credentials from environment ===
host = os.getenv("HONEYPOT_HOST")
user = os.getenv("HONEYPOT_USER")
port = int(os.getenv("HONEYPOT_PORT_SSH", "22"))
key_path = os.path.expanduser("~/.ssh/id_rsa")

# === Log paths on T-Pot ===
logs = {
    "suricata": "/data/suricata/log/eve.json",
    "cowrie": "/data/cowrie/log/cowrie.json",
    "tanner": "/data/tanner/tanner.log"
}

# === Establish SSH connection ===
ssh = paramiko.SSHClient()
ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
ssh.connect(hostname=host, username=user, key_filename=key_path, port=port)

# === IOC collectors ===
ips, hashes, domains, emails = set(), set(), set(), set()

def defang(value):
    return value.replace(".", "[.]").replace("@", "[at]")

def collect_from_json(output):
    for line in output.splitlines():
        try:
            event = json.loads(line)
            if 'src_ip' in event:
                ips.add(event['src_ip'])
            if 'dest_ip' in event:
                ips.add(event['dest_ip'])
            if 'host' in event:
                domains.add(event['host'])
            if 'email' in json.dumps(event):
                found = re.findall(r"[a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+", json.dumps(event))
                emails.update(found)
            if 'sha256' in event:
                hashes.add(event['sha256'])
        except:
            continue

def collect_from_text(output):
    found_ips = re.findall(r"(?:[0-9]{1,3}[.]){3}[0-9]{1,3}", output)
    ips.update(found_ips)
    found_hashes = re.findall(r"\b[a-fA-F0-9]{64}\b", output)
    hashes.update(found_hashes)

# === Read and parse each log ===
for name, path in logs.items():
    stdin, stdout, stderr = ssh.exec_command(f"tail -n 500 {path}")
    output = stdout.read().decode()
    if name in ["suricata", "cowrie"]:
        collect_from_json(output)
    elif name == "tanner":
        collect_from_text(output)

ssh.close()

# === Prepare HTML output ===
today = datetime.now().strftime("%Y-%m-%d")
ioc_dir = f"docs/daily-ioc/ioc-{today}"
os.makedirs(ioc_dir, exist_ok=True)

def html_list(title, items):
    items = sorted(defang(i) for i in items)
    if not items:
        return f"<h3>{title}</h3><p>No data found.</p>"
    return f"<h3>{title}</h3><ul>" + "".join(f"<li>{i}</li>" for i in items) + "</ul>"

html = f"""<!DOCTYPE html>
<html><head><meta charset='UTF-8'><title>IOC {today}</title>
<style>body{{background:#121212;color:#fff;font-family:sans-serif;padding:2rem;}}
h1,h2,h3{{color:#ff4500}}ul{{list-style:none;padding:0}}li{{padding:0.2rem 0}}</style>
</head><body>
<h1>Daily IOC Report – {today}</h1>
{html_list("🔴 Malicious IPs", ips)}
{html_list("🧬 File Hashes", hashes)}
{html_list("🌐 Domains", domains)}
{html_list("✉️ Emails", emails)}
<p><a href="/daily-ioc/">← Back to archive</a></p>
</body></html>
"""

with open(f"{ioc_dir}/index.html", "w", encoding="utf-8") as f:
    f.write(html)

# === Update archive index ===
index_path = "docs/daily-ioc/index.html"
entry = f'<li><a href="/daily-ioc/ioc-{today}/">{today}</a></li>'

if os.path.exists(index_path):
    with open(index_path, "r", encoding="utf-8") as f:
        content = f.read()
    if entry not in content:
        content = content.replace("<ul>", f"<ul>
    {entry}", 1)
        with open(index_path, "w", encoding="utf-8") as f:
            f.write(content)

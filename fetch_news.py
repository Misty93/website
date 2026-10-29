import os
import json
import calendar
import feedparser
import time
import urllib.error
import urllib.parse
import urllib.request

from datetime import datetime
from html import escape


# === Datum i direktorij ===

today = datetime.now().strftime("%Y-%m-%d")
folder = "docs/security-news"

os.makedirs(folder, exist_ok=True)

output_file = os.path.join(folder, "index.html")
json_file = os.path.join(folder, "news.json")


# === RSS feedovi za cybersecurity vijesti i CVE objave ===

rss_feeds = {
    "The Hacker News": "https://feeds.feedburner.com/TheHackersNews",
    "BleepingComputer": "https://www.bleepingcomputer.com/feed/",
    "Security Affairs": "https://securityaffairs.com/feed",
    "Tenable CVE": "https://www.tenable.com/cve/feeds?sort=newest",
    "CISA": "https://www.cisa.gov/cybersecurity-advisories/all.xml",
    "CERT EU": "https://cert.europa.eu/publications/security-advisories-rss",
}


# === Pretvori datum iz RSS zapisa u timestamp ===

def get_entry_timestamp(entry):
    parsed_date = entry.get("published_parsed") or entry.get("updated_parsed")

    if parsed_date:
        return calendar.timegm(parsed_date)

    return 0


# === Dohvati datum za prikaz ===

def get_entry_date(entry):
    return entry.get(
        "published",
        entry.get("updated", today)
    )


# === Parsiraj sve RSS feedove ===

def fetch_news_items():
    articles = []

    headers = {
        "User-Agent": (
            "Mozilla/5.0 SecurityNewsAggregator/1.0 "
            "(https://shehuntsthreats.com)"
        )
    }

    for source, url in rss_feeds.items():
        print(f"Fetching RSS feed: {source}")

        try:
            feed = feedparser.parse(
                url,
                request_headers=headers
            )

            if feed.bozo:
                print(
                    f"RSS warning for {source}: "
                    f"{feed.bozo_exception}"
                )

            if not feed.entries:
                print(f"No RSS entries returned for {source}")
                continue

            for entry in feed.entries[:10]:
                title = entry.get("title", "Untitled article")
                link = entry.get("link", "")

                if not link:
                    continue

                articles.append({
                    "title": title,
                    "link": link,
                    "published": get_entry_date(entry),
                    "published_timestamp": get_entry_timestamp(entry),
                    "source": source
                })

        except Exception as error:
            print(f"Unable to process {source}: {error}")

    return sorted(
        articles,
        key=lambda item: item["published_timestamp"],
        reverse=True
    )


articles = fetch_news_items()


# === Generiraj HTML stranicu ===

html_content = """<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <meta
    name="viewport"
    content="width=device-width, initial-scale=1.0"
  >
  <title>Security News</title>

  <style>
    body {
      background-color: #121212;
      color: #ffffff;
      font-family: sans-serif;
      padding: 2rem;
      margin: 0;
    }

    h1 {
      color: #ff4500;
      font-size: 2rem;
      margin-bottom: 1rem;
    }

    a {
      color: #ff4500;
      text-decoration: none;
    }

    a:hover {
      text-decoration: underline;
    }

    .news-item {
      margin-bottom: 1.5rem;
      padding-bottom: 1rem;
      border-bottom: 1px solid #333333;
    }

    .source {
      font-size: 0.9em;
      color: #aaaaaa;
    }
  </style>
</head>

<body>
  <h1>Security News</h1>

  <p>
    <a href="/">← Back to homepage</a>
  </p>
"""


if articles:
    for article in articles:
        title = escape(article["title"])
        link = escape(article["link"], quote=True)
        source = escape(article["source"])
        published = escape(article["published"])

        html_content += f"""
  <div class="news-item">
    <a href="{link}" target="_blank" rel="noopener noreferrer">
      <strong>{title}</strong>
    </a>

    <br>

    <span class="source">
      {source} · {published}
    </span>
  </div>
"""
else:
    html_content += """
  <div class="news-item">
    No security news is currently available.
  </div>
"""


html_content += """
  <p>
    <a href="/">← Back to homepage</a>
  </p>
</body>
</html>
"""


# === Spremi HTML ===

with open(output_file, "w", encoding="utf-8") as html_file:
    html_file.write(html_content)


# === Generiraj JSON za početnu stranicu ===

latest_items = articles[:3]

json_data = {
    "generated_at": datetime.now().isoformat(),
    "items": [
        {
            "title": item["title"],
            "url": item["link"],
            "published": item["published"],
            "source": item["source"]
        }
        for item in latest_items
    ]
}


# === Spremi JSON ===

with open(json_file, "w", encoding="utf-8") as output_json:
    json.dump(
        json_data,
        output_json,
        ensure_ascii=False,
        indent=2
    )


print(f"Generated {output_file} with {len(articles)} articles.")
print(f"Generated {json_file} with {len(latest_items)} latest articles.")


# === Discord: odvojeno od generiranja vijesti za web ===

discord_state_file = os.path.join(folder, "discord_sent.json")


def save_discord_state(seen_links):
    temporary_file = discord_state_file + ".tmp"

    with open(temporary_file, "w", encoding="utf-8") as state_file:
        json.dump(
            sorted(seen_links),
            state_file,
            ensure_ascii=False,
            indent=2
        )

    os.replace(temporary_file, discord_state_file)


def discord_text(value, limit):
    text = " ".join(str(value).split())

    # Spriječi da naslov iz RSS-a poremeti Discord formatiranje.
    for character in ("\\", "*", "_", "`", "~", "|", "<", ">"):
        text = text.replace(character, "\\" + character)

    return text[:limit]


def send_discord_article(webhook_url, article):
    title = discord_text(article["title"], 500)
    source = discord_text(article["source"], 150)
    published = discord_text(article["published"], 200)
    link = str(article["link"]).strip()

    parsed_link = urllib.parse.urlsplit(link)

    if parsed_link.scheme not in ("https", "http") or not parsed_link.netloc:
        raise ValueError("Invalid article URL")

    if any(character in link for character in ("\r", "\n", "<", ">")):
        raise ValueError("Invalid characters in article URL")

    content = (
        f"**{title}**\n"
        f"Source: {source}\n"
        f"Published: {published}\n"
        f"<{link}>"
    )

    if len(content) > 2000:
        raise ValueError("Discord message is too long")

    payload = json.dumps({
        "content": content,
        "allowed_mentions": {"parse": []}
    }).encode("utf-8")

    for attempt in range(3):
        request = urllib.request.Request(
            webhook_url,
            data=payload,
            headers={
                "Content-Type": "application/json",
                "User-Agent": "CyberCroatiaSecurityNews/1.0"
            },
            method="POST"
        )

        try:
            with urllib.request.urlopen(request, timeout=30) as response:
                result = json.loads(response.read().decode("utf-8"))

            if not result.get("id"):
                raise ValueError("Discord did not confirm the message")

            return

        except urllib.error.HTTPError as error:
            if error.code == 429 and attempt < 2:
                retry_after = float(
                    json.loads(error.read().decode("utf-8"))["retry_after"]
                )

                if not 0 <= retry_after <= 60:
                    raise ValueError("Discord retry delay exceeds limit")

                time.sleep(retry_after + 0.5)
                continue

            # Ne ispisuj webhook URL koji sadrži tajni token.
            raise RuntimeError(
                f"Discord returned HTTP {error.code}"
            ) from None

    raise RuntimeError("Discord sending attempts exhausted")


def publish_discord_news():
    webhook = os.environ.get("DISCORD_WEBHOOK_URL", "").strip()

    if not webhook:
        print("Discord skipped: webhook secret is not configured.")
        return

    parts = urllib.parse.urlsplit(webhook)

    if (
        parts.scheme != "https"
        or parts.hostname != "discord.com"
        or not parts.path.startswith("/api/webhooks/")
    ):
        print("::warning::Discord skipped: unexpected webhook URL format.")
        return

    query = [
        (key, value)
        for key, value in urllib.parse.parse_qsl(parts.query)
        if key != "wait"
    ]
    query.append(("wait", "true"))

    webhook_url = urllib.parse.urlunsplit((
        parts.scheme,
        parts.netloc,
        parts.path,
        urllib.parse.urlencode(query),
        ""
    ))

    unique_articles = []
    current_links = set()

    for article in articles:
        link = article["link"].strip()

        if link and link not in current_links:
            current_links.add(link)
            unique_articles.append(article)

    if not unique_articles:
        print("Discord: no articles available.")
        return

    if os.path.exists(discord_state_file):
        with open(discord_state_file, encoding="utf-8") as state_file:
            saved_links = json.load(state_file)

        if (
            not isinstance(saved_links, list)
            or not all(isinstance(link, str) for link in saved_links)
        ):
            raise ValueError("Invalid Discord state file")

        seen_links = set(saved_links)

    else:
        # Prvi put pošalji samo tri najnovije vijesti.
        # Starije trenutačne stavke označi kao preskočene.
        seen_links = {
            article["link"].strip()
            for article in unique_articles[10:]
        }
        save_discord_state(seen_links)

    pending = [
        article
        for article in unique_articles
        if article["link"].strip() not in seen_links
    ]

    # Obradi do deset stavki, od starijih prema novijima.
    batch = list(reversed(pending))[:20]
    sent_count = 0

    for article in batch:
        try:
            send_discord_article(webhook_url, article)
            seen_links.add(article["link"].strip())
            save_discord_state(seen_links)
            sent_count += 1

        except Exception:
            print(
                "::warning::Discord posting stopped after an error. "
                "Website files have already been generated. "
                "Check webhook access and saved state before retrying."
            )
            break

        time.sleep(1)

    print(f"Discord: sent {sent_count} new articles.")


try:
    publish_discord_news()
except Exception:
    # Discord greška ne prekida spremanje web vijesti u workflowu.
    print(
        "::warning::Discord notifications failed. "
        "Website files have already been generated."
    )

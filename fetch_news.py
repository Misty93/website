import os
import json
import calendar
import feedparser

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

            for entry in feed.entries[:5]:
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

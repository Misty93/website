import os
import requests
import feedparser
from datetime import datetime
from html import escape

# === Datum i direktorij ===
today = datetime.now().strftime("%Y-%m-%d")
folder = f"docs/security-news"
os.makedirs(folder, exist_ok=True)
output_file = os.path.join(folder, "index.html")

# === RSS feedovi za cyber security vijesti ===
rss_feeds = {
    "The Hacker News": "https://feeds.feedburner.com/TheHackersNews",
    "BleepingComputer": "https://www.bleepingcomputer.com/feed/",
    "Security Affairs": "https://securityaffairs.com/feed",
}

# === Parsiraj sve feedove ===
def fetch_news_items():
    articles = []
    for source, url in rss_feeds.items():
        feed = feedparser.parse(url)
        for entry in feed.entries[:5]:  # Uzmi samo zadnjih 5
            articles.append({
                "title": entry.title,
                "link": entry.link,
                "published": entry.get("published", today),
                "source": source
            })
    return sorted(articles, key=lambda x: x["published"], reverse=True)

articles = fetch_news_items()

# === Generiraj HTML ===
html_content = f"""<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <title>Security News</title>
  <style>
    body {{
      background-color: #121212;
      color: #fff;
      font-family: sans-serif;
      padding: 2rem;
    }}
    h1 {{
      color: #ff4500;
    }}
    a {{
      color: #ff4500;
      text-decoration: none;
    }}
    a:hover {{
      text-decoration: underline;
    }}
    .news-item {{
      margin-bottom: 1.5rem;
      padding-bottom: 1rem;
      border-bottom: 1px solid #333;
    }}
    .source {{
      font-size: 0.9em;
      color: #aaa;
    }}
  </style>
</head>
<body>
  <h1>Security News</h1>
  <p><a href="/">← Back to homepage</a></p>
"""

for article in articles:
    html_content += f"""
    <div class="news-item">
      <a href="{escape(article['link'])}" target="_blank"><strong>{escape(article['title'])}</strong></a><br/>
      <span class="source">{escape(article['source'])} – {escape(article['published'])}</span>
    </div>
    """

html_content += """
  <p><a href="/">← Back to homepage</a></p>
</body>
</html>
"""

# === Snimi HTML ===
with open(output_file, "w", encoding="utf-8") as f:
    f.write(html_content)

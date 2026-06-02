import os
import json
import re
from datetime import datetime
from bs4 import BeautifulSoup

BASE_DIR = "docs/security-shenanigans"
OUTPUT_FILE = os.path.join(BASE_DIR, "posts.json")


def slugify(text):
    text = text.lower().strip()
    text = text.replace("’", "").replace("'", "")
    text = re.sub(r"[^a-z0-9čćžšđ\s-]", "", text)
    text = re.sub(r"\s+", "-", text)
    text = text.strip("-")
    return text


def parse_date(date_text):
    date_text = date_text.strip()

    formats = [
        "%d.%m.%Y.",
        "%d.%m.%Y",
        "%Y-%m-%d",
        "%d-%m-%Y",
        "%d/%m/%Y"
    ]

    for fmt in formats:
        try:
            return datetime.strptime(date_text, fmt)
        except ValueError:
            continue

    return datetime.min


def extract_articles_from_file(filepath):
    with open(filepath, "r", encoding="utf-8") as f:
        soup = BeautifulSoup(f.read(), "html.parser")

    articles = []

    date_tags = soup.find_all("div", class_="article-date")

    for date_tag in date_tags:
        date_text = date_tag.get_text(strip=True)

        title_tag = date_tag.find_next("h2")
        if not title_tag:
            continue

        title = title_tag.get_text(strip=True)

        p_tag = title_tag.find_next("p")
        description = p_tag.get_text(" ", strip=True) if p_tag else ""

        anchor_id = title_tag.get("id")
        if not anchor_id:
            anchor_id = slugify(title)

        link = f"{os.path.basename(filepath)}#{anchor_id}"

        articles.append({
            "title": title,
            "file": link,
            "description": description,
            "date": date_text
        })

    return articles


def main():
    all_articles = []

    for file in os.listdir(BASE_DIR):
        if not file.endswith(".html"):
            continue

        path = os.path.join(BASE_DIR, file)

        if os.path.isfile(path):
            all_articles.extend(extract_articles_from_file(path))

    all_articles.sort(
        key=lambda x: parse_date(x["date"]),
        reverse=True
    )

    latest_articles = all_articles[:3]

    data = {
        "items": [
            {
                "title": a["title"],
                "file": a["file"],
                "description": a["description"],
                "date": a["date"]
            }
            for a in latest_articles
        ]
    }

    with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)

    print(f"[+] Generated {OUTPUT_FILE}")
    print(f"[+] Articles found: {len(all_articles)}")


if __name__ == "__main__":
    main()

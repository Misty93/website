import os
import json
from bs4 import BeautifulSoup

BASE_DIR = "docs/security-shenanigans"
OUTPUT_FILE = os.path.join(BASE_DIR, "posts.json")

def extract_articles_from_file(filepath):
    with open(filepath, "r", encoding="utf-8") as f:
        soup = BeautifulSoup(f.read(), "html.parser")

    articles = []

    # Nađi sve datume
    date_tags = soup.find_all("div", class_="article-date")

    for date_tag in date_tags:
        date_text = date_tag.get_text(strip=True)

        # Naslov je odmah nakon date taga
        title_tag = date_tag.find_next("h2")
        if not title_tag:
            continue

        title = title_tag.get_text(strip=True)

        # Opis = prvi paragraf nakon naslova
        p_tag = title_tag.find_next("p")
        description = p_tag.get_text(strip=True) if p_tag else ""

        # Link na članak (anchor)
        # Ako nemaš anchor, možemo generirati anchor ID
        anchor_id = title.lower().replace(" ", "-").replace(":", "").replace("’", "")
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

    # Parsiraj HR i EN datoteke
    for file in os.listdir(BASE_DIR):
        if file.endswith(".html") and file not in ["posts.json", "index.html"]:
            path = os.path.join(BASE_DIR, file)
            all_articles.extend(extract_articles_from_file(path))

    # Sortiraj po datumu (pretvaramo DD.MM.YYYY. → YYYY-MM-DD)
    def normalize_date(d):
        d = d.replace(".", "")
        return "-".join(reversed(d.split("-"))) if "-" in d else d

    all_articles.sort(key=lambda x: normalize_date(x["date"]), reverse=True)

    # Uzmi zadnja 3 članka
    latest_articles = all_articles[:3]

    # JSON format identičan IOC i NEWS
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

if __name__ == "__main__":
    main()

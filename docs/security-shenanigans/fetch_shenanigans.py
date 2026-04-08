import os
import json
from bs4 import BeautifulSoup

BASE_DIR = "docs/security-shenanigans"
OUTPUT_FILE = os.path.join(BASE_DIR, "posts.json")

def extract_info(filepath):
    with open(filepath, "r", encoding="utf-8") as f:
        soup = BeautifulSoup(f.read(), "html.parser")

    # Title extraction
    title_tag = soup.find("h1") or soup.find("title")
    title = title_tag.get_text(strip=True) if title_tag else "Untitled"

    # Description extraction (first 150 chars of text)
    text = soup.get_text(" ", strip=True)
    description = text[:150] + "..." if len(text) > 150 else text

    return title, description

def main():
    posts = []

    for file in os.listdir(BASE_DIR):
        if file.startswith("article-") and file.endswith(".html"):
            path = os.path.join(BASE_DIR, file)
            title, description = extract_info(path)

            posts.append({
                "title": title,
                "file": file,
                "description": description
            })

    # Sort by modification time (newest first)
    posts.sort(
        key=lambda x: os.path.getmtime(os.path.join(BASE_DIR, x["file"])),
        reverse=True
    )

    data = {
        "latest": posts[0] if posts else {},
        "posts": posts
    }

    with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)

if __name__ == "__main__":
    main()

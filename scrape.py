import json
import os
import re
from datetime import datetime, timezone, timedelta

import requests

LIST_URL = "https://www.munpia.com/best/today?displayType=LIST"
DATA_FILE = "data.json"
TARGET_RANK = 200

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/124.0 Safari/537.36"
}


def fetch(url):
    resp = requests.get(url, headers=HEADERS, timeout=20)
    resp.raise_for_status()
    resp.encoding = resp.apparent_encoding
    return resp.text


def find_rank_entry(html, rank):
    pattern = re.compile(
        r'<a href="https://www\.munpia\.com/novel/detail/(\d+)">\s*'
        r'<div class="num">(\d+)</div>(.*?)</a>',
        re.DOTALL,
    )

    for match in pattern.finditer(html):
        novel_id = match.group(1)
        block_rank = int(match.group(2))
        block = match.group(3)

        if block_rank != rank:
            continue

        title_match = re.search(r'class="title-wrap">([^<]+)</span>', block)
        title = title_match.group(1).strip() if title_match else None

        author_match = re.search(r'class="author">([^<]+)</div>', block)
        author = author_match.group(1).strip() if author_match else None

        view_match = re.search(r'class="view-count">([\d,]+)</div>', block)
        view_count = int(view_match.group(1).replace(",", "")) if view_match else None

        return {
            "novel_id": novel_id,
            "rank": block_rank,
            "title": title,
            "author": author,
            "view_count": view_count,
        }

    return None


def load_data():
    if os.path.exists(DATA_FILE):
        with open(DATA_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    return []


def save_data(data):
    with open(DATA_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)


def main():
    list_html = fetch(LIST_URL)
    entry = find_rank_entry(list_html, TARGET_RANK)

    kst = timezone(timedelta(hours=9))
    now = datetime.now(kst).isoformat()

    record = {
        "timestamp": now,
        "rank": TARGET_RANK,
        "novel_id": entry["novel_id"] if entry else None,
        "title": entry["title"] if entry else None,
        "author": entry["author"] if entry else None,
        "view_count": entry["view_count"] if entry else None,
        "ok": entry is not None and entry.get("view_count") is not None,
    }

    data = load_data()
    data.append(record)
    save_data(data)

    print(json.dumps(record, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()

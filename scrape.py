import json
import os
import re
from datetime import datetime, timezone, timedelta

import requests

URL = "https://www.munpia.com/best/today?displayType=LIST"
DATA_FILE = "data.json"
TARGET_RANK = 200

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/124.0 Safari/537.36"
}


def fetch_html():
    resp = requests.get(URL, headers=HEADERS, timeout=20)
    resp.raise_for_status()
    resp.encoding = resp.apparent_encoding
    return resp.text


def find_rank_entry(html, rank):
    pattern = re.compile(
        r'href="(/novel/detail/(\d+))"[^>]*>(.*?)(?=href="/novel/detail/|$)',
        re.DOTALL,
    )

    seen_ids = set()
    for match in pattern.finditer(html):
        novel_id = match.group(2)
        block = match.group(3)

        if novel_id in seen_ids:
            continue

        rank_match = re.search(r'(?:^|[^\d])(\d{1,3})(?:위)?(?:[^\d]|$)', block)
        if not rank_match:
            continue

        seen_ids.add(novel_id)

        block_rank = int(rank_match.group(1))
        if block_rank == rank:
            numbers = re.findall(r'[\d,]{2,}', block)
            numbers = [n for n in numbers if n.replace(",", "").isdigit()]
            view_count = None
            if numbers:
                view_count = max(int(n.replace(",", "")) for n in numbers)

            title_match = re.search(r'>([^<>\d][^<>]{1,60})<', block)
            title = title_match.group(1).strip() if title_match else None

            return {
                "novel_id": novel_id,
                "rank": block_rank,
                "title": title,
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
    html = fetch_html()
    entry = find_rank_entry(html, TARGET_RANK)

    kst = timezone(timedelta(hours=9))
    now = datetime.now(kst).isoformat()

    record = {
        "timestamp": now,
        "rank": TARGET_RANK,
        "novel_id": entry["novel_id"] if entry else None,
        "title": entry["title"] if entry else None,
        "view_count": entry["view_count"] if entry else None,
        "ok": entry is not None,
    }

    if entry is None:
        snippet = html[-60000:] if len(html) > 60000 else html
        with open("debug.html", "w", encoding="utf-8") as f:
            f.write(snippet)

    data = load_data()
    data.append(record)
    save_data(data)

    print(json.dumps(record, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()

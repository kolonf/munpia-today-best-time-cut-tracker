import json
import os
import re
from datetime import datetime, timezone, timedelta

import requests

LIST_URL = "https://www.munpia.com/best/today?displayType=LIST"
DETAIL_URL = "https://www.munpia.com/novel/detail/{}"
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


def find_rank_novel_id(html, rank):
    """
    목록 페이지에서 특정 순위(rank)의 novel_id / 제목 / 작가를 찾는다.
    """
    pattern = re.compile(
        r'<a href="[^"]*?/novel/detail/(\d+)"[^>]*class="novel-wrap"[^>]*>(.*?)</a>',
        re.DOTALL,
    )

    for match in pattern.finditer(html):
        novel_id = match.group(1)
        block = match.group(2)

        rank_match = re.search(r'class="rank-num">\s*<span>(\d+)</span>', block)
        if not rank_match:
            continue

        block_rank = int(rank_match.group(1))
        if block_rank != rank:
            continue

        title_match = re.search(
            r'class="novel-title">(.*?)</div>', block, re.DOTALL
        )
        title = None
        if title_match:
            spans = re.findall(r"<span[^>]*>([^<]+)</span>", title_match.group(1))
            spans = [s.strip() for s in spans if s.strip()]
            if spans:
                title = spans[-1]

        author_match = re.search(r'class="novel-author">([^<]+)</div>', block)
        author = author_match.group(1).strip() if author_match else None

        return {"novel_id": novel_id, "rank": block_rank, "title": title, "author": author}

    return None


def find_view_count(detail_html):
    """
    작품 상세 페이지에서 '조회수: 59,377' 형태의 값을 찾는다.
    """
    match = re.search(r"조회수\s*[:：]?\s*([\d,]+)", detail_html)
    if match:
        return int(match.group(1).replace(",", ""))
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
    entry = find_rank_novel_id(list_html, TARGET_RANK)

    view_count = None
    if entry:
        detail_html = fetch(DETAIL_URL.format(entry["novel_id"]))
        view_count = find_view_count(detail_html)

    kst = timezone(timedelta(hours=9))
    now = datetime.now(kst).isoformat()

    record = {
        "timestamp": now,
        "rank": TARGET_RANK,
        "novel_id": entry["novel_id"] if entry else None,
        "title": entry["title"] if entry else None,
        "author": entry["author"] if entry else None,
        "view_count": view_count,
        "ok": entry is not None and view_count is not None,
    }

    with open("debug.html", "w", encoding="utf-8") as f:
        f.write(list_html)

    data = load_data()
    data.append(record)
    save_data(data)

    print(json.dumps(record, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()

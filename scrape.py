import json
import os
import re
import time
from datetime import datetime, timezone, timedelta

import requests

LIST_URL = "https://www.munpia.com/best/today?displayType=LIST"
DATA_FILE = "data.json"
# 20위 단위 페이지 커트라인 + 200위(추적 대상)
TARGET_RANKS = [20, 40, 60, 80, 100, 120, 140, 160, 180, 200]

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/124.0 Safari/537.36",
    "Cache-Control": "no-cache, no-store, max-age=0",
    "Pragma": "no-cache",
}


def fetch(url):
    cache_bust_url = url + ("&" if "?" in url else "?") + "_cb=" + str(int(time.time() * 1000))
    resp = requests.get(cache_bust_url, headers=HEADERS, timeout=20)
    resp.raise_for_status()
    resp.encoding = resp.apparent_encoding
    return resp.text


def find_all_ranks(html, ranks_wanted):
    """
    'best-rank-list-display' 안의 각 행에서 원하는 순위들의
    제목/작가/조회수를 한 번에 찾는다.
    """
    pattern = re.compile(
        r'<a href="https://www\.munpia\.com/novel/detail/(\d+)">\s*'
        r'<div class="num">(\d+)</div>(.*?)</a>',
        re.DOTALL,
    )

    wanted = set(ranks_wanted)
    found = {}

    for match in pattern.finditer(html):
        novel_id = match.group(1)
        block_rank = int(match.group(2))
        block = match.group(3)

        if block_rank not in wanted or block_rank in found:
            continue

        title_match = re.search(r'class="title-wrap">([^<]+)</span>', block)
        title = title_match.group(1).strip() if title_match else None

        author_match = re.search(r'class="author">([^<]+)</div>', block)
        author = author_match.group(1).strip() if author_match else None

        view_match = re.search(r'class="view-count">([\d,]+)</div>', block)
        view_count = int(view_match.group(1).replace(",", "")) if view_match else None

        found[block_rank] = {
            "novel_id": novel_id,
            "title": title,
            "author": author,
            "view_count": view_count,
        }

        if len(found) == len(wanted):
            break

    return found


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
    found = find_all_ranks(list_html, TARGET_RANKS)

    kst = timezone(timedelta(hours=9))
    now = datetime.now(kst).isoformat()

    ranks_data = {}
    for r in TARGET_RANKS:
        entry = found.get(r)
        ranks_data[str(r)] = {
            "novel_id": entry["novel_id"] if entry else None,
            "title": entry["title"] if entry else None,
            "author": entry["author"] if entry else None,
            "view_count": entry["view_count"] if entry else None,
        }

    ok = all(ranks_data[str(r)]["view_count"] is not None for r in TARGET_RANKS)

    record = {
        "timestamp": now,
        "ranks": ranks_data,
        "ok": ok,
    }

    data = load_data()
    data.append(record)
    save_data(data)

    print(json.dumps(record, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()

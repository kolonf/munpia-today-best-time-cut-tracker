import json
import os
import re
import time
from datetime import datetime, timezone, timedelta

import requests

LIST_URL = "https://www.munpia.com/best/new.novel.today?displayType=LIST"
DATA_FILE = "data_new.json"
# 20위 단위 페이지 커트라인 + 200위(추적 대상)
TARGET_RANKS = [20, 40, 60, 80, 100, 120, 140, 160, 180, 200]
# 목표 순위가 감지 안 될 때, 최대 몇 단계 아래까지 대신 찾아볼지
MAX_FALLBACK_STEPS = 10

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


def extract_fields(block):
    title_match = re.search(r'class="title-wrap">([^<]+)</span>', block)
    if not title_match:
        title_match = re.search(r'class="[^"]*title[^"]*"[^>]*>\s*(?:<span[^>]*>)?([^<]{2,80})', block)
    title = title_match.group(1).strip() if title_match else None

    author_match = re.search(r'class="author">([^<]+)</div>', block)
    author = author_match.group(1).strip() if author_match else None

    view_match = re.search(r'class="view-count">([\d,]+)</div>', block)
    view_count = int(view_match.group(1).replace(",", "")) if view_match else None

    return title, author, view_count


def parse_all_entries(html):
    all_entries = {}

    pattern = re.compile(
        r'<a href="https://www\.munpia\.com/novel/detail/(\d+)">\s*'
        r'<div class="num">(\d+)</div>(.*?)</a>',
        re.DOTALL,
    )
    for match in pattern.finditer(html):
        novel_id = match.group(1)
        rank = int(match.group(2))
        block = match.group(3)
        title, author, view_count = extract_fields(block)
        all_entries[rank] = {
            "novel_id": novel_id,
            "title": title,
            "author": author,
            "view_count": view_count,
        }

    loose_pattern = re.compile(r'<div class="num">(\d+)</div>')
    matches = list(loose_pattern.finditer(html))
    for i, m in enumerate(matches):
        rank = int(m.group(1))
        if rank in all_entries:
            continue
        start = m.end()
        end = matches[i + 1].start() if i + 1 < len(matches) else min(len(html), start + 3000)
        block = html[start:end]

        novel_id_match = re.search(r'/novel/detail/(\d+)', block)
        novel_id = novel_id_match.group(1) if novel_id_match else None
        title, author, view_count = extract_fields(block)

        all_entries[rank] = {
            "novel_id": novel_id,
            "title": title,
            "author": author,
            "view_count": view_count,
        }

    return all_entries


def resolve_target_ranks(all_entries, target_ranks, max_fallback_steps):
    resolved = {}
    for target in target_ranks:
        actual_rank = None
        entry = None
        for step in range(0, max_fallback_steps + 1):
            candidate = target - step
            if candidate < 1:
                break
            c_entry = all_entries.get(candidate)
            if c_entry and c_entry.get("view_count") is not None:
                actual_rank = candidate
                entry = c_entry
                break

        if entry is None:
            entry = all_entries.get(target, {
                "novel_id": None, "title": None, "author": None, "view_count": None,
            })
            actual_rank = target if all_entries.get(target) else None

        resolved[target] = {
            "target_rank": target,
            "actual_rank": actual_rank,
            "novel_id": entry.get("novel_id"),
            "title": entry.get("title"),
            "author": entry.get("author"),
            "view_count": entry.get("view_count"),
            "substituted": actual_rank is not None and actual_rank != target,
        }
    return resolved


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
    all_entries = parse_all_entries(list_html)
    resolved = resolve_target_ranks(all_entries, TARGET_RANKS, MAX_FALLBACK_STEPS)

    kst = timezone(timedelta(hours=9))
    now = datetime.now(kst).isoformat()

    ranks_data = {str(r): resolved[r] for r in TARGET_RANKS}
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

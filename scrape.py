import json
import os
import re
from datetime import datetime, timezone, timedelta

from playwright.sync_api import sync_playwright

URL = "https://www.munpia.com/best/today?displayType=LIST"
DATA_FILE = "data.json"
TARGET_RANK = 200


def fetch_rendered_html():
    with sync_playwright() as p:
        browser = p.chromium.launch()
        page = browser.new_page(
            user_agent=(
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
                "(KHTML, like Gecko) Chrome/124.0 Safari/537.36"
            ),
            viewport={"width": 1280, "height": 2000},
        )
        page.goto(URL, wait_until="networkidle", timeout=30000)
        page.wait_for_timeout(1000)

        prev_height = 0
        for _ in range(40):
            page.evaluate("window.scrollTo(0, document.body.scrollHeight)")
            page.wait_for_timeout(400)
            height = page.evaluate("document.body.scrollHeight")
            if height == prev_height:
                page.wait_for_timeout(800)
                height2 = page.evaluate("document.body.scrollHeight")
                if height2 == height:
                    break
            prev_height = height

        page.wait_for_timeout(1500)
        html = page.content()
        browser.close()
        return html


def find_rank_entry(html, rank):
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

        view_count = None
        view_label_match = re.search(r"조회\D{0,10}([\d,]{2,})", block)
        if view_label_match:
            view_count = int(view_label_match.group(1).replace(",", ""))
        else:
            class_match = re.search(
                r'class="[^"]*(?:view|hit|count)[^"]*"[^>]*>\s*([\d,]{2,})',
                block,
                re.IGNORECASE,
            )
            if class_match:
                view_count = int(class_match.group(1).replace(",", ""))

        author_match = re.search(r'class="novel-author">([^<]+)</div>', block)
        author = author_match.group(1).strip() if author_match else None

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
    html = fetch_rendered_html()
    entry = find_rank_entry(html, TARGET_RANK)

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

    snippet = html[-80000:] if len(html) > 80000 else html
    with open("debug.html", "w", encoding="utf-8") as f:
        f.write(snippet)

    data = load_data()
    data.append(record)
    save_data(data)

    print(json.dumps(record, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()

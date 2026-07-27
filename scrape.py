import json
import os
import re
from datetime import datetime, timezone, timedelta

import requests

LIST_URL = "https://www.munpia.com/best/today?displayType=LIST"
DATA_FILE = "data.json"
TARGET_RANKS = [20, 40, 60, 80, 100, 120, 140, 160, 180, 200]

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/124.0 Safari/537.36"
}


def fetch(url):
    resp = requests.get(url, headers=HEADERS, timeout=20)
    resp.raise_for_status()
    resp.encoding = resp.apparent_encoding
    return resp.text


def find_all_ranks(html, ranks_wanted):
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

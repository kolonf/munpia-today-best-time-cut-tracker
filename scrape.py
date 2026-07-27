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
    """
    문피아 랭킹 페이지에서 특정 순위(rank)에 해당하는 작품 정보를 찾는다.
    사이트 구조가 바뀌면 이 함수의 정규식을 조정해야 할 수 있다.
    각 작품은 '/novel/detail/{id}' 링크를 갖고 있고, 그 주변에 순위/제목/조회수가 있다.
    """
    # 작품 상세 링크를 기준으로 대략적인 블록을 잘라낸다.
    pattern = re.compile(
        r'href="(/novel/detail/(\d+))"[^>]*>(.*?)(?=href="/novel/detail/|$)',
        re.DOTALL,
    )

    seen_ids = set()
    order = 0
    for match in pattern.finditer(html):
        novel_id = match.group(2)
        block = match.group(3)

        if novel_id in seen_ids:
            continue

        # 이 블록에 순위 숫자가 있는지 확인 (예: '>200<' 또는 '200위' 형태)
        rank_match = re.search(r'(?:^|[^\d])(\d{1,3})(?:위)?(?:[^\d]|$)', block)
        if not rank_match:
            continue

        seen_ids.add(novel_id)
        order += 1

        block_rank = int(rank_match.group(1))
        if block_rank == rank:
            # 조회수로 보이는 숫자(콤마 포함 가능, 3자리 이상 또는 별도 표기) 추출
            numbers = re.findall(r'[\d,]{2,}', block)
            numbers = [n for n in numbers if n.replace(",", "").isdigit()]
            view_count = None
            if numbers:
                # 보통 마지막 큰 숫자가 조회수인 경우가 많음 - 가장 큰 값 선택
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

    data = load_data()
    data.append(record)
    save_data(data)

    print(json.dumps(record, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()

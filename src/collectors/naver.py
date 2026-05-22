"""네이버 뉴스 검색 API로 한국 뉴스 수집.

API 키는 .env 파일의 NAVER_CLIENT_ID, NAVER_CLIENT_SECRET 환경변수에서 읽는다.
"""

import re
import time
from datetime import datetime
from email.utils import parsedate_to_datetime

import requests

from .. import config, db


SLEEP = 0.3
ENDPOINT = "https://openapi.naver.com/v1/search/news.json"


def _strip_html(text: str) -> str:
    """네이버 API가 검색어를 감싸 반환하는 <b> 태그 및 HTML 엔티티 제거."""
    text = re.sub(r"<[^>]+>", "", text)
    return (text.replace("&quot;", '"').replace("&amp;", "&")
                .replace("&lt;", "<").replace("&gt;", ">")
                .replace("&apos;", "'").strip())


def _parse_pubdate(s: str) -> str:
    """RFC 2822 → 'YYYY-MM-DD HH:MM:SS'. 실패 시 빈 문자열."""
    try:
        return parsedate_to_datetime(s).strftime("%Y-%m-%d %H:%M:%S")
    except Exception:
        return ""


def _fetch(query: str, display: int = config.NAVER_PER_QUERY) -> list[dict]:
    """단일 쿼리 검색."""
    headers = {
        "X-Naver-Client-Id": config.NAVER_CLIENT_ID,
        "X-Naver-Client-Secret": config.NAVER_CLIENT_SECRET,
    }
    params = {"query": query, "display": display, "start": 1, "sort": "date"}
    try:
        r = requests.get(ENDPOINT, headers=headers, params=params, timeout=15)
        r.raise_for_status()
        return r.json().get("items", [])
    except Exception as e:
        print(f"    error: {e}")
        return []


def _save(conn, items: list[dict]) -> int:
    """news 테이블 적재."""
    rows = []
    for item in items:
        published = _parse_pubdate(item.get("pubDate", ""))
        if not published:
            continue
        title = _strip_html(item.get("title", ""))[:500]
        desc = _strip_html(item.get("description", ""))[:5000]
        link = item.get("originallink") or item.get("link", "")
        if not title or not link:
            continue
        rows.append(("naver_news", published, title, link, desc, "ko"))
    if not rows:
        return 0
    conn.executemany(
        """INSERT OR IGNORE INTO news
           (source, published_at, title, url, body, language)
           VALUES (?, ?, ?, ?, ?, ?)""",
        rows,
    )
    conn.commit()
    return len(rows)


def fetch_all_naver() -> int:
    """설정된 모든 키워드로 네이버 뉴스 검색.

    Raises:
        RuntimeError: API 키가 .env에 설정되지 않은 경우.
    """
    if not config.NAVER_CLIENT_ID or not config.NAVER_CLIENT_SECRET:
        raise RuntimeError(
            "NAVER_CLIENT_ID / NAVER_CLIENT_SECRET이 .env에 설정되어 있지 않습니다. "
            ".env.example을 .env로 복사한 뒤 본인 키를 입력하세요."
        )

    print(f"검색 키워드: {len(config.NAVER_QUERIES)}개")
    print(f"키워드당 최대: {config.NAVER_PER_QUERY}건\n")

    total = 0
    with db.connect() as conn:
        for i, q in enumerate(config.NAVER_QUERIES, 1):
            items = _fetch(q)
            saved = _save(conn, items)
            total += saved
            print(f"[{i:>2}/{len(config.NAVER_QUERIES)}] {q:<20} "
                  f"fetched {len(items):>3}, saved {saved:>3}")
            time.sleep(SLEEP)
    return total

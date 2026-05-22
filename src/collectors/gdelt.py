"""GDELT DOC 2.0 API로 글로벌 뉴스 수집."""

import time
from datetime import datetime

import requests

from .. import config, db


SLEEP = 1.5
ENDPOINT = "https://api.gdeltproject.org/api/v2/doc/doc"


def _fetch(query: str) -> list[dict]:
    """단일 쿼리 호출."""
    params = {
        "query": query,
        "mode": "ArtList",
        "maxrecords": config.GDELT_MAX_RECORDS,
        "format": "json",
        "timespan": config.GDELT_TIMESPAN,
        "sort": "datedesc",
    }
    try:
        r = requests.get(ENDPOINT, params=params, timeout=30)
        r.raise_for_status()
        if not r.text.strip():
            return []
        return r.json().get("articles", [])
    except requests.JSONDecodeError:
        return []
    except Exception as e:
        print(f"    error: {e}")
        return []


def _save(conn, articles: list[dict]) -> int:
    """news 테이블에 적재."""
    rows = []
    for a in articles:
        seen = a.get("seendate", "")
        try:
            dt = datetime.strptime(seen, "%Y%m%dT%H%M%SZ")
        except ValueError:
            continue
        title = a.get("title", "")[:500]
        url = a.get("url", "")
        lang = (a.get("language", "") or "")[:10].lower()
        if not title or not url:
            continue
        rows.append((
            "gdelt",
            dt.strftime("%Y-%m-%d %H:%M:%S"),
            title, url, "", lang,
        ))
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


def fetch_all_gdelt() -> int:
    """설정된 모든 쿼리로 뉴스 수집."""
    print(f"Queries: {len(config.GDELT_QUERIES)}")
    print(f"Timespan: {config.GDELT_TIMESPAN}, Max per query: {config.GDELT_MAX_RECORDS}\n")

    total = 0
    with db.connect() as conn:
        for i, q in enumerate(config.GDELT_QUERIES, 1):
            print(f"[{i}/{len(config.GDELT_QUERIES)}] {q}")
            articles = _fetch(q)
            saved = _save(conn, articles)
            total += saved
            print(f"    fetched {len(articles)}, saved {saved}")
            time.sleep(SLEEP)
    return total

"""Reddit 공개 JSON 엔드포인트로 SNS 게시물 수집."""

import time
from datetime import datetime, timezone

import requests

from .. import config, db


SLEEP = 1.5  # rate limit 회피
HEADERS = {"User-Agent": config.REDDIT_USER_AGENT}


def _fetch_subreddit(sub: str, max_pages: int = config.REDDIT_MAX_PAGES) -> list[dict]:
    """단일 서브레딧의 /new.json을 페이지네이션으로 수집한다."""
    posts: list[dict] = []
    after: str | None = None
    for page in range(max_pages):
        url = f"https://www.reddit.com/r/{sub}/new.json?limit=100"
        if after:
            url += f"&after={after}"
        try:
            r = requests.get(url, headers=HEADERS, timeout=15)
            r.raise_for_status()
            data = r.json()
        except Exception as e:
            print(f"    page {page+1} 실패: {e}")
            break

        children = data.get("data", {}).get("children", [])
        if not children:
            break

        for c in children:
            d = c.get("data", {})
            posts.append({
                "id": d.get("id"),
                "title": d.get("title", ""),
                "selftext": d.get("selftext", ""),
                "url": f"https://www.reddit.com{d.get('permalink', '')}",
                "created": d.get("created_utc"),
                "score": d.get("score", 0),
            })

        after = data.get("data", {}).get("after")
        if not after:
            break
        time.sleep(SLEEP)
    return posts


def _save(conn, sub: str, posts: list[dict]) -> int:
    """news 테이블에 적재 (URL 중복 무시)."""
    rows = []
    for p in posts:
        if not p.get("created"):
            continue
        published = datetime.fromtimestamp(
            p["created"], tz=timezone.utc
        ).strftime("%Y-%m-%d %H:%M:%S")
        rows.append((
            f"reddit_{sub}",
            published,
            p["title"][:500],
            p["url"],
            (p.get("selftext") or "")[:5000],
            "en",
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


def fetch_all_reddit() -> int:
    """설정된 모든 서브레딧에서 게시물을 수집하고 저장된 총 건수 반환."""
    print(f"Target subreddits: {len(config.REDDIT_SUBREDDITS)}")
    print(f"Max posts per sub: {config.REDDIT_MAX_PAGES * 100}\n")

    total = 0
    with db.connect() as conn:
        for i, (sub, _cat) in enumerate(config.REDDIT_SUBREDDITS, 1):
            print(f"[{i}/{len(config.REDDIT_SUBREDDITS)}] r/{sub}")
            posts = _fetch_subreddit(sub)
            saved = _save(conn, sub, posts)
            total += saved
            print(f"    fetched {len(posts)}, saved {saved}")
            time.sleep(SLEEP)
    return total

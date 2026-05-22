"""
데이터베이스 모듈.
스키마 정의, 연결 헬퍼, 자산 마스터 등록 기능을 제공한다.
"""

import sqlite3
from contextlib import contextmanager
from typing import Iterator

from . import config


SCHEMA = """
-- 1. 자산 마스터
CREATE TABLE IF NOT EXISTS assets (
    asset_id      INTEGER PRIMARY KEY AUTOINCREMENT,
    ticker        TEXT    NOT NULL UNIQUE,
    name          TEXT    NOT NULL,
    category      TEXT    NOT NULL CHECK(category IN ('crypto','us_stock','kr_stock')),
    market_cap    REAL,
    added_at      TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- 2. 일 단위 가격
CREATE TABLE IF NOT EXISTS prices_daily (
    asset_id      INTEGER NOT NULL,
    date          DATE    NOT NULL,
    open          REAL,
    high          REAL,
    low           REAL,
    close         REAL    NOT NULL,
    volume        REAL,
    PRIMARY KEY (asset_id, date),
    FOREIGN KEY (asset_id) REFERENCES assets(asset_id)
);
CREATE INDEX IF NOT EXISTS idx_prices_daily_date ON prices_daily(date);

-- 3. 분 단위 가격 (이벤트 기간만)
CREATE TABLE IF NOT EXISTS prices_minute (
    asset_id      INTEGER NOT NULL,
    timestamp     TIMESTAMP NOT NULL,
    open          REAL,
    high          REAL,
    low           REAL,
    close         REAL    NOT NULL,
    volume        REAL,
    PRIMARY KEY (asset_id, timestamp),
    FOREIGN KEY (asset_id) REFERENCES assets(asset_id)
);
CREATE INDEX IF NOT EXISTS idx_prices_minute_ts ON prices_minute(timestamp);

-- 4. 원시 뉴스·SNS
CREATE TABLE IF NOT EXISTS news (
    news_id       INTEGER PRIMARY KEY AUTOINCREMENT,
    source        TEXT    NOT NULL,
    published_at  TIMESTAMP NOT NULL,
    title         TEXT    NOT NULL,
    url           TEXT    UNIQUE,
    body          TEXT,
    language      TEXT,
    fetched_at    TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
CREATE INDEX IF NOT EXISTS idx_news_published ON news(published_at);
CREATE INDEX IF NOT EXISTS idx_news_source ON news(source);

-- 5. NLP 처리 결과
CREATE TABLE IF NOT EXISTS news_sentiment (
    news_id          INTEGER PRIMARY KEY,
    sentiment_score  REAL    NOT NULL CHECK(sentiment_score BETWEEN -1 AND 1),
    keywords         TEXT,
    entities         TEXT,
    processed_at     TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (news_id) REFERENCES news(news_id)
);

-- 6. 주요 이벤트
CREATE TABLE IF NOT EXISTS events (
    event_id      INTEGER PRIMARY KEY AUTOINCREMENT,
    asset_id      INTEGER,
    event_time    TIMESTAMP NOT NULL,
    description   TEXT    NOT NULL,
    magnitude     REAL,
    FOREIGN KEY (asset_id) REFERENCES assets(asset_id)
);
CREATE INDEX IF NOT EXISTS idx_events_time ON events(event_time);

-- 7. 상관 분석 결과
CREATE TABLE IF NOT EXISTS correlation_results (
    id            INTEGER PRIMARY KEY AUTOINCREMENT,
    asset_id      INTEGER NOT NULL,
    ticker        TEXT,
    category      TEXT,
    direction     TEXT    NOT NULL,
    lag           INTEGER NOT NULL,
    pearson_r     REAL,
    p_value       REAL,
    n_obs         INTEGER,
    computed_at   TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (asset_id) REFERENCES assets(asset_id)
);
"""


@contextmanager
def connect() -> Iterator[sqlite3.Connection]:
    """컨텍스트 매니저로 DB 연결을 제공한다 (자동 close)."""
    conn = sqlite3.connect(str(config.DB_PATH))
    try:
        yield conn
    finally:
        conn.close()


def init_schema() -> list[str]:
    """모든 테이블·인덱스를 생성하고 테이블 목록을 반환한다."""
    with connect() as conn:
        conn.executescript(SCHEMA)
        conn.commit()
        cur = conn.execute(
            "SELECT name FROM sqlite_master WHERE type='table' "
            "AND name NOT LIKE 'sqlite_%' ORDER BY name"
        )
        return [row[0] for row in cur.fetchall()]


def populate_assets() -> dict[str, int]:
    """assets 테이블에 자산 마스터를 등록하고 카테고리별 카운트를 반환한다."""
    with connect() as conn:
        conn.executemany(
            "INSERT OR IGNORE INTO assets (ticker, name, category) VALUES (?, ?, ?)",
            config.ASSETS,
        )
        conn.commit()
        cur = conn.execute(
            "SELECT category, COUNT(*) FROM assets GROUP BY category ORDER BY category"
        )
        return dict(cur.fetchall())


def get_all_assets() -> list[tuple[int, str, str, str]]:
    """등록된 모든 자산 목록 반환: (asset_id, ticker, name, category)"""
    with connect() as conn:
        cur = conn.execute(
            "SELECT asset_id, ticker, name, category FROM assets ORDER BY asset_id"
        )
        return cur.fetchall()

"""yfinance를 사용한 일별 가격 수집."""

import time
from datetime import datetime, timedelta

import pandas as pd
import yfinance as yf

from .. import config, db


SLEEP_BETWEEN = 0.5  # rate limit 회피


def _fetch_one(ticker: str, start: str, end: str) -> pd.DataFrame:
    """단일 종목의 일봉을 yfinance로 다운로드한다."""
    df = yf.download(
        ticker, start=start, end=end,
        interval="1d", progress=False, auto_adjust=False,
    )
    if df.empty:
        return df
    # 일부 yfinance 버전이 MultiIndex 컬럼을 반환
    if isinstance(df.columns, pd.MultiIndex):
        df.columns = df.columns.get_level_values(0)
    df = df.reset_index()
    df["Date"] = pd.to_datetime(df["Date"]).dt.strftime("%Y-%m-%d")
    return df


def _save(conn, asset_id: int, df: pd.DataFrame) -> int:
    """DataFrame을 prices_daily에 적재 (중복 PK 무시)."""
    if df.empty:
        return 0
    rows = [
        (
            asset_id,
            row["Date"],
            float(row["Open"]) if pd.notna(row["Open"]) else None,
            float(row["High"]) if pd.notna(row["High"]) else None,
            float(row["Low"]) if pd.notna(row["Low"]) else None,
            float(row["Close"]),
            float(row["Volume"]) if pd.notna(row["Volume"]) else None,
        )
        for _, row in df.iterrows()
        if pd.notna(row["Close"])
    ]
    conn.executemany(
        """INSERT OR IGNORE INTO prices_daily
           (asset_id, date, open, high, low, close, volume)
           VALUES (?, ?, ?, ?, ?, ?, ?)""",
        rows,
    )
    conn.commit()
    return len(rows)


def fetch_all_prices() -> dict:
    """등록된 모든 자산의 일별 가격을 수집한다.

    Returns:
        결과 요약 dict: total_rows, failed (실패한 ticker 목록)
    """
    end = datetime.today()
    start = end - timedelta(days=config.PRICE_HISTORY_DAYS)
    start_s, end_s = start.strftime("%Y-%m-%d"), end.strftime("%Y-%m-%d")

    assets = db.get_all_assets()
    print(f"Period: {start_s} ~ {end_s}")
    print(f"Targets: {len(assets)} assets\n")

    total, failed = 0, []
    with db.connect() as conn:
        for i, (asset_id, ticker, name, _cat) in enumerate(assets, 1):
            try:
                df = _fetch_one(ticker, start_s, end_s)
                saved = _save(conn, asset_id, df)
                total += saved
                print(f"[{i:>2}/{len(assets)}] {ticker:<12} {name:<20} {saved:>4} rows")
            except Exception as e:
                failed.append((ticker, str(e)))
                print(f"[{i:>2}/{len(assets)}] {ticker:<12} FAILED: {e}")
            time.sleep(SLEEP_BETWEEN)

    return {"total_rows": total, "failed": failed}

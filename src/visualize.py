"""시각화 모듈: 5종 그래프를 생성한다.

생성 파일 (outputs/ 디렉토리):
  1_sentiment_vs_price.png
  2_top_keywords.png
  3_keyword_impact.png
  4_lag_correlation.png
  5_pos_neg_keywords.png
"""

import json
import re
from collections import Counter, defaultdict

import matplotlib
import matplotlib.pyplot as plt
import pandas as pd
from matplotlib import font_manager

from . import config, db


# ----------------------------------------------------------------------
# 한글 폰트 (Windows: Malgun Gothic, Mac: AppleGothic)
# ----------------------------------------------------------------------
def _setup_korean_font() -> None:
    available = {f.name for f in font_manager.fontManager.ttflist}
    for name in ("Malgun Gothic", "AppleGothic", "NanumGothic", "Gulim"):
        if name in available:
            matplotlib.rcParams["font.family"] = name
            break
    matplotlib.rcParams["axes.unicode_minus"] = False


def _is_valid_keyword(k: str) -> bool:
    """키워드 필터링: stopwords, 숫자, 너무 짧은 단어 제외."""
    k = k.strip()
    if not k or len(k) < 2:
        return False
    if k.lower() in config.STOPWORDS:
        return False
    if re.match(r"^[\d\$\.,]+\s*(billion|million|thousand|m|b|k|%|원|달러)?$",
                k.lower()):
        return False
    return True


def _output_path(filename: str) -> str:
    config.OUTPUT_DIR.mkdir(exist_ok=True)
    return str(config.OUTPUT_DIR / filename)


# ----------------------------------------------------------------------
# 차트 1: BTC/ETH 가격 + Sentiment
# ----------------------------------------------------------------------
def chart_price_vs_sentiment() -> None:
    with db.connect() as conn:
        prices = pd.read_sql("""
            SELECT a.ticker, p.date, p.close
            FROM prices_daily p JOIN assets a ON p.asset_id = a.asset_id
            WHERE a.ticker IN ('BTC-USD', 'ETH-USD')
            ORDER BY p.date
        """, conn)
        sent = pd.read_sql("""
            SELECT DATE(n.published_at) AS date, AVG(ns.sentiment_score) AS sentiment
            FROM news n JOIN news_sentiment ns ON n.news_id = ns.news_id
            WHERE n.source IN ('reddit_Bitcoin', 'reddit_CryptoCurrency', 'reddit_ethereum')
            GROUP BY DATE(n.published_at)
            ORDER BY date
        """, conn)

    prices["date"] = pd.to_datetime(prices["date"])
    sent["date"] = pd.to_datetime(sent["date"])

    fig, ax1 = plt.subplots(figsize=(12, 6))
    btc = prices[prices["ticker"] == "BTC-USD"]
    eth = prices[prices["ticker"] == "ETH-USD"]

    ax1.plot(btc["date"], btc["close"], color="#F7931A",
             label="BTC 가격", linewidth=2)
    ax1.set_xlabel("날짜")
    ax1.set_ylabel("BTC 가격 (USD)", color="#F7931A")
    ax1.tick_params(axis="y", labelcolor="#F7931A")

    ax1b = ax1.twinx()
    ax1b.plot(eth["date"], eth["close"], color="#627EEA",
              label="ETH 가격", linewidth=1.5, linestyle="--")
    ax1b.set_ylabel("ETH 가격 (USD)", color="#627EEA")
    ax1b.tick_params(axis="y", labelcolor="#627EEA")

    ax2 = ax1.twinx()
    ax2.spines["right"].set_position(("outward", 60))
    ax2.fill_between(sent["date"], sent["sentiment"], 0,
                     where=sent["sentiment"] >= 0, color="green", alpha=0.2)
    ax2.fill_between(sent["date"], sent["sentiment"], 0,
                     where=sent["sentiment"] < 0, color="red", alpha=0.2)
    ax2.axhline(0, color="gray", linewidth=0.5)
    ax2.set_ylabel("Sentiment (-1 ~ +1)", color="gray")
    ax2.set_ylim(-1, 1)

    plt.title("BTC/ETH 가격과 SNS Sentiment 추이",
              fontsize=14, fontweight="bold")
    fig.autofmt_xdate()
    plt.tight_layout()
    plt.savefig(_output_path("1_sentiment_vs_price.png"),
                dpi=150, bbox_inches="tight")
    plt.close()


# ----------------------------------------------------------------------
# 키워드 차트 공통 헬퍼
# ----------------------------------------------------------------------
def _collect_keyword_sentiments() -> dict[str, list[float]]:
    """모든 sentiment 결과를 키워드별 sentiment 리스트로 집계."""
    kw_sentiments: dict[str, list[float]] = defaultdict(list)
    with db.connect() as conn:
        rows = conn.execute(
            "SELECT keywords, sentiment_score FROM news_sentiment "
            "WHERE keywords IS NOT NULL"
        ).fetchall()
    for kw_json, score in rows:
        try:
            kws = json.loads(kw_json)
            if not isinstance(kws, list):
                continue
            for k in kws:
                if _is_valid_keyword(k):
                    kw_sentiments[k.strip()].append(score)
        except Exception:
            continue
    return kw_sentiments


# ----------------------------------------------------------------------
# 차트 2: 자주 언급된 키워드 TOP 20
# ----------------------------------------------------------------------
def chart_top_keywords() -> None:
    counter: Counter = Counter()
    with db.connect() as conn:
        rows = conn.execute(
            "SELECT keywords FROM news_sentiment WHERE keywords IS NOT NULL"
        ).fetchall()
    for (kw_json,) in rows:
        try:
            kws = json.loads(kw_json)
            if isinstance(kws, list):
                counter.update(k.strip() for k in kws if _is_valid_keyword(k))
        except Exception:
            continue

    items = counter.most_common(20)
    if not items:
        return
    keywords, counts = zip(*items)
    plt.figure(figsize=(12, 7))
    plt.barh(range(len(keywords)), counts, color="#4A90E2")
    plt.yticks(range(len(keywords)), keywords)
    plt.gca().invert_yaxis()
    plt.xlabel("등장 횟수")
    plt.title("자주 언급된 키워드 TOP 20", fontsize=14, fontweight="bold")
    plt.grid(axis="x", alpha=0.3)
    plt.tight_layout()
    plt.savefig(_output_path("2_top_keywords.png"),
                dpi=150, bbox_inches="tight")
    plt.close()


# ----------------------------------------------------------------------
# 차트 3: 키워드별 평균 영향력
# ----------------------------------------------------------------------
def chart_keyword_impact() -> None:
    kw_sentiments = _collect_keyword_sentiments()
    items = [(k, sum(v) / len(v), len(v))
             for k, v in kw_sentiments.items() if len(v) >= 5]
    items.sort(key=lambda x: abs(x[1]), reverse=True)
    items = items[:20]
    if not items:
        return

    keywords = [i[0] for i in items]
    avgs = [i[1] for i in items]
    counts = [i[2] for i in items]
    colors = ["#27AE60" if a > 0 else "#E74C3C" for a in avgs]

    plt.figure(figsize=(12, 7))
    plt.barh(range(len(keywords)), avgs, color=colors)
    plt.yticks(range(len(keywords)),
               [f"{k} (n={c})" for k, c in zip(keywords, counts)])
    plt.gca().invert_yaxis()
    plt.axvline(0, color="gray", linewidth=0.5)
    plt.xlabel("평균 sentiment 점수")
    plt.title("키워드별 평균 영향력 TOP 20 (등장 5회 이상)",
              fontsize=14, fontweight="bold")
    plt.grid(axis="x", alpha=0.3)
    plt.tight_layout()
    plt.savefig(_output_path("3_keyword_impact.png"),
                dpi=150, bbox_inches="tight")
    plt.close()


# ----------------------------------------------------------------------
# 차트 4: 시차 상관관계
# ----------------------------------------------------------------------
def chart_lag_correlation() -> None:
    with db.connect() as conn:
        df = pd.read_sql("""
            SELECT ticker, category, direction, lag, pearson_r, p_value, n_obs
            FROM correlation_results
            WHERE direction = 'sent_to_price'
        """, conn)
    if df.empty:
        print("⚠ correlation_results 없음 — 분석 먼저 실행 필요")
        return

    targets = ["TSLA", "AMZN", "BTC-USD", "005930.KS"]
    colors = {"TSLA": "#E74C3C", "AMZN": "#F39C12",
              "BTC-USD": "#F7931A", "005930.KS": "#4A90E2"}

    plt.figure(figsize=(10, 6))
    for ticker in targets:
        sub = df[df["ticker"] == ticker].sort_values("lag")
        if sub.empty:
            continue
        for _, row in sub.iterrows():
            face = colors.get(ticker, "gray") if row["p_value"] < 0.05 else "white"
            plt.scatter(row["lag"], row["pearson_r"],
                        s=80, color=colors.get(ticker, "gray"),
                        facecolors=face,
                        edgecolors=colors.get(ticker, "gray"), zorder=3)
        plt.plot(sub["lag"], sub["pearson_r"],
                 color=colors.get(ticker, "gray"),
                 label=ticker, linewidth=2, alpha=0.7)

    plt.axhline(0, color="gray", linewidth=0.5)
    plt.axhline(0.3, color="green", linewidth=0.5, linestyle="--",
                alpha=0.5, label="유의 기준 (±0.3)")
    plt.axhline(-0.3, color="red", linewidth=0.5, linestyle="--", alpha=0.5)
    plt.xlabel("시차 (Lag, 일)")
    plt.ylabel("상관계수 (Pearson r)")
    plt.title("시차별 sentiment → 가격 상관관계\n(채워진 점: p<0.05 유의)",
              fontsize=14, fontweight="bold")
    plt.legend(loc="best")
    plt.grid(alpha=0.3)
    plt.tight_layout()
    plt.savefig(_output_path("4_lag_correlation.png"),
                dpi=150, bbox_inches="tight")
    plt.close()


# ----------------------------------------------------------------------
# 차트 5: 긍정 vs 부정 키워드
# ----------------------------------------------------------------------
def chart_pos_neg_keywords() -> None:
    kw_sentiments = _collect_keyword_sentiments()
    items = [(k, sum(v) / len(v), len(v))
             for k, v in kw_sentiments.items() if len(v) >= 5]
    pos = sorted([i for i in items if i[1] > 0],
                 key=lambda x: x[1], reverse=True)[:10]
    neg = sorted([i for i in items if i[1] < 0],
                 key=lambda x: x[1])[:10]
    if not pos and not neg:
        return

    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(14, 7))
    if pos:
        pos_kw, pos_avg, pos_n = zip(*pos)
        ax1.barh(range(len(pos_kw)), pos_avg, color="#27AE60")
        ax1.set_yticks(range(len(pos_kw)))
        ax1.set_yticklabels([f"{k} (n={n})" for k, n in zip(pos_kw, pos_n)])
        ax1.invert_yaxis()
        ax1.set_xlabel("평균 sentiment")
        ax1.set_title("긍정 키워드 TOP 10",
                      fontsize=13, fontweight="bold", color="#27AE60")
        ax1.grid(axis="x", alpha=0.3)

    if neg:
        neg_kw, neg_avg, neg_n = zip(*neg)
        ax2.barh(range(len(neg_kw)), neg_avg, color="#E74C3C")
        ax2.set_yticks(range(len(neg_kw)))
        ax2.set_yticklabels([f"{k} (n={n})" for k, n in zip(neg_kw, neg_n)])
        ax2.invert_yaxis()
        ax2.set_xlabel("평균 sentiment")
        ax2.set_title("부정 키워드 TOP 10",
                      fontsize=13, fontweight="bold", color="#E74C3C")
        ax2.grid(axis="x", alpha=0.3)

    plt.suptitle("긍정 vs 부정 키워드 영향력", fontsize=14, fontweight="bold")
    plt.tight_layout()
    plt.savefig(_output_path("5_pos_neg_keywords.png"),
                dpi=150, bbox_inches="tight")
    plt.close()


# ----------------------------------------------------------------------
# 통합 실행
# ----------------------------------------------------------------------
def make_all_charts() -> None:
    """5종 그래프를 모두 생성한다."""
    _setup_korean_font()
    print("그래프 생성 중...")
    chart_price_vs_sentiment(); print("✓ 1_sentiment_vs_price.png")
    chart_top_keywords();       print("✓ 2_top_keywords.png")
    chart_keyword_impact();     print("✓ 3_keyword_impact.png")
    chart_lag_correlation();    print("✓ 4_lag_correlation.png")
    chart_pos_neg_keywords();   print("✓ 5_pos_neg_keywords.png")
    print(f"\n저장 위치: {config.OUTPUT_DIR}")

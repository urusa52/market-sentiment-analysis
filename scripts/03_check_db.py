"""DB 내용 검증 — 자산·가격·뉴스·sentiment 현황을 한눈에 확인.

실행: python -m scripts.03_check_db
"""

from src import db


def main() -> None:
    with db.connect() as conn:
        cur = conn.cursor()

        # 자산
        cur.execute("SELECT COUNT(*) FROM assets")
        print(f"자산 수: {cur.fetchone()[0]}")

        # 가격
        cur.execute("SELECT COUNT(*) FROM prices_daily")
        print(f"가격 행수: {cur.fetchone()[0]:,}")

        # 카테고리별
        print("\n=== 카테고리별 가격 행수 ===")
        cur.execute("""
            SELECT a.category, COUNT(DISTINCT a.asset_id), COUNT(p.date)
            FROM assets a LEFT JOIN prices_daily p ON a.asset_id = p.asset_id
            GROUP BY a.category ORDER BY a.category
        """)
        for cat, n_a, n_r in cur.fetchall():
            print(f"  {cat:<10} 자산 {n_a:>2}개 | 가격 {n_r:>5}행")

        # 뉴스 소스별
        cur.execute("SELECT COUNT(*) FROM news")
        total_news = cur.fetchone()[0]
        print(f"\n=== 뉴스·SNS 소스별 (총 {total_news:,}건) ===")
        cur.execute("""
            SELECT source, COUNT(*), MIN(published_at), MAX(published_at)
            FROM news GROUP BY source ORDER BY source
        """)
        for src, cnt, first, last in cur.fetchall():
            print(f"  {src:<28} {cnt:>5}  {first or '—'}  ~  {last or '—'}")

        # sentiment
        cur.execute("SELECT COUNT(*) FROM news_sentiment")
        print(f"\nSentiment 처리: {cur.fetchone()[0]:,}건")

        # 상관 분석
        cur.execute("SELECT COUNT(*) FROM correlation_results")
        print(f"상관 분석 결과: {cur.fetchone()[0]:,}행")


if __name__ == "__main__":
    main()

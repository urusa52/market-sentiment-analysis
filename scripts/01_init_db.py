"""DB 스키마 생성 및 자산 마스터 등록.

실행: python -m scripts.01_init_db
"""

from src import db


def main() -> None:
    tables = db.init_schema()
    print(f"DB 스키마 생성 완료. 테이블 {len(tables)}개:")
    print(f"  {', '.join(tables)}")

    counts = db.populate_assets()
    total = sum(counts.values())
    print(f"\n자산 마스터 등록: 총 {total}개")
    for cat, n in counts.items():
        print(f"  {cat:<10} {n:>3}")


if __name__ == "__main__":
    main()

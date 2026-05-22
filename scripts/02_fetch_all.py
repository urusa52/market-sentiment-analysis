"""모든 데이터 소스를 한 번에 수집한다.

실행:
  python -m scripts.02_fetch_all           # 전부 수집
  python -m scripts.02_fetch_all prices    # 가격만
  python -m scripts.02_fetch_all reddit    # Reddit만
  python -m scripts.02_fetch_all gdelt     # GDELT만
  python -m scripts.02_fetch_all naver     # 네이버만
"""

import sys

from src.collectors import prices, reddit, gdelt, naver


COLLECTORS = {
    "prices": (prices.fetch_all_prices, "yfinance 일별 가격"),
    "reddit": (reddit.fetch_all_reddit, "Reddit SNS 게시물"),
    "gdelt":  (gdelt.fetch_all_gdelt,   "GDELT 글로벌 뉴스"),
    "naver":  (naver.fetch_all_naver,   "네이버 한국 뉴스"),
}


def _print_section(name: str, desc: str) -> None:
    print(f"\n{'=' * 60}")
    print(f"  [{name}] {desc}")
    print("=" * 60)


def main() -> None:
    target = sys.argv[1] if len(sys.argv) > 1 else "all"

    if target == "all":
        targets = list(COLLECTORS.keys())
    elif target in COLLECTORS:
        targets = [target]
    else:
        print(f"⚠ 알 수 없는 대상: '{target}'")
        print(f"사용 가능: all, {', '.join(COLLECTORS.keys())}")
        return

    for name in targets:
        fn, desc = COLLECTORS[name]
        _print_section(name, desc)
        try:
            fn()
        except Exception as e:
            print(f"⚠ {name} 수집 실패: {e}")


if __name__ == "__main__":
    main()

"""
프로젝트 전역 설정.
모든 경로·상수·자산 리스트·검색 키워드를 한 곳에 모아 관리한다.
환경 변수는 .env 파일에서 자동으로 로드된다.
"""

import os
from pathlib import Path


# ----------------------------------------------------------------------
# 경로
# ----------------------------------------------------------------------
ROOT_DIR = Path(__file__).resolve().parent.parent
DB_PATH = ROOT_DIR / "market_sentiment.db"
OUTPUT_DIR = ROOT_DIR / "outputs"


# ----------------------------------------------------------------------
# .env 로딩 (외부 의존성 없는 간단한 파서)
# ----------------------------------------------------------------------
def _load_env() -> None:
    env_file = ROOT_DIR / ".env"
    if not env_file.exists():
        return
    for line in env_file.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        os.environ.setdefault(key.strip(), value.strip().strip('"').strip("'"))


_load_env()


# ----------------------------------------------------------------------
# API 자격증명
# ----------------------------------------------------------------------
NAVER_CLIENT_ID = os.environ.get("NAVER_CLIENT_ID", "")
NAVER_CLIENT_SECRET = os.environ.get("NAVER_CLIENT_SECRET", "")


# ----------------------------------------------------------------------
# 자산 마스터: (ticker, name, category)
# 기준일: 2026-05-18 (KOSPI 시총 상위 30)
# ----------------------------------------------------------------------
ASSETS: list[tuple[str, str, str]] = [
    # 암호화폐 2종
    ("BTC-USD", "Bitcoin", "crypto"),
    ("ETH-USD", "Ethereum", "crypto"),

    # Magnificent 7
    ("AAPL", "Apple", "us_stock"),
    ("MSFT", "Microsoft", "us_stock"),
    ("GOOGL", "Alphabet", "us_stock"),
    ("AMZN", "Amazon", "us_stock"),
    ("NVDA", "NVIDIA", "us_stock"),
    ("META", "Meta Platforms", "us_stock"),
    ("TSLA", "Tesla", "us_stock"),

    # KOSPI 시총 상위 30
    ("005930.KS", "삼성전자", "kr_stock"),
    ("000660.KS", "SK하이닉스", "kr_stock"),
    ("005935.KS", "삼성전자우", "kr_stock"),
    ("373220.KS", "LG에너지솔루션", "kr_stock"),
    ("207940.KS", "삼성바이오로직스", "kr_stock"),
    ("005380.KS", "현대차", "kr_stock"),
    ("000270.KS", "기아", "kr_stock"),
    ("068270.KS", "셀트리온", "kr_stock"),
    ("005490.KS", "POSCO홀딩스", "kr_stock"),
    ("105560.KS", "KB금융", "kr_stock"),
    ("035420.KS", "NAVER", "kr_stock"),
    ("055550.KS", "신한지주", "kr_stock"),
    ("012330.KS", "현대모비스", "kr_stock"),
    ("028260.KS", "삼성물산", "kr_stock"),
    ("051910.KS", "LG화학", "kr_stock"),
    ("006400.KS", "삼성SDI", "kr_stock"),
    ("035720.KS", "카카오", "kr_stock"),
    ("003550.KS", "LG", "kr_stock"),
    ("086790.KS", "하나금융지주", "kr_stock"),
    ("015760.KS", "한국전력", "kr_stock"),
    ("032830.KS", "삼성생명", "kr_stock"),
    ("066570.KS", "LG전자", "kr_stock"),
    ("009150.KS", "삼성전기", "kr_stock"),
    ("034730.KS", "SK", "kr_stock"),
    ("011200.KS", "HMM", "kr_stock"),
    ("018260.KS", "삼성에스디에스", "kr_stock"),
    ("010130.KS", "고려아연", "kr_stock"),
    ("316140.KS", "우리금융지주", "kr_stock"),
    ("009540.KS", "HD한국조선해양", "kr_stock"),
    ("267260.KS", "HD현대일렉트릭", "kr_stock"),
]


# ----------------------------------------------------------------------
# 데이터 수집 파라미터
# ----------------------------------------------------------------------
PRICE_HISTORY_DAYS = 365

REDDIT_SUBREDDITS: list[tuple[str, str]] = [
    ("Bitcoin", "crypto"),
    ("CryptoCurrency", "crypto"),
    ("ethereum", "crypto"),
    ("wallstreetbets", "us_stock"),
    ("stocks", "us_stock"),
    ("StockMarket", "us_stock"),
    ("investing", "us_stock"),
]
REDDIT_MAX_PAGES = 5
REDDIT_USER_AGENT = "market_sentiment_research/0.1 (academic project)"

GDELT_QUERIES: list[str] = [
    '"bitcoin price"',
    '"ethereum price"',
    '"Apple stock"',
    '"Microsoft stock"',
    '"Nvidia stock"',
    '"Tesla stock"',
    '"Meta stock"',
    '"Amazon stock"',
    '"Google stock" OR "Alphabet stock"',
    '"Samsung Electronics"',
    '"SK Hynix"',
    '"LG Energy Solution"',
    '"Hyundai Motor"',
    "KOSPI",
]
GDELT_TIMESPAN = "3m"
GDELT_MAX_RECORDS = 250

NAVER_QUERIES: list[str] = [
    "삼성전자", "SK하이닉스", "LG에너지솔루션", "삼성바이오로직스",
    "현대차", "기아", "셀트리온", "POSCO홀딩스", "KB금융", "NAVER",
    "신한지주", "현대모비스", "삼성물산", "LG화학", "삼성SDI",
    "카카오", "한국전력", "삼성생명", "LG전자", "고려아연",
    "HMM", "HD한국조선해양", "HD현대일렉트릭",
    "코스피", "코스닥", "한국증시", "외국인 매수", "외국인 매도",
    "코스피 급등", "코스피 급락",
]
NAVER_PER_QUERY = 100


# ----------------------------------------------------------------------
# 시각화: 키워드 필터링용 stopwords
# ----------------------------------------------------------------------
STOPWORDS: set[str] = {
    # 영어 일반
    "the", "and", "for", "is", "are", "be", "to", "of", "in", "on", "at",
    "a", "an", "with", "by", "as", "or", "but", "if", "this", "that",
    # Reddit 메타
    "daily", "question", "general discussion", "discussion", "thread",
    "advice", "general", "weekly", "monthly", "megathread", "guide",
    "help", "newbie", "beginner", "post", "comment", "ama", "dd",
    "what", "how", "why", "when", "where", "who",
    # 한국어 일반
    "그", "이", "저", "것", "수", "등", "및", "또", "는", "을", "를",
    "의", "에", "와", "과", "도", "만", "년", "월", "일",
    # 너무 일반적인 금융 단어
    "price", "market", "stock", "crypto", "investing", "investment",
    "trade", "trading", "buy", "sell", "hold",
    # 메인 자산명
    "bitcoin", "ethereum", "btc", "eth",
    # 모호한 일반 단어
    "day", "days", "time", "today", "yesterday", "tomorrow",
    "week", "month", "year", "new", "old", "first", "last",
    "good", "bad", "big", "small", "high", "low", "more", "less",
    # 스포츠 관련
    "야구", "축구", "농구", "타선", "투수", "타자", "득점", "경기",
    "선수", "감독", "구단", "리그", "kbo", "프로야구", "홈런",
    "samsung lions", "삼성라이온즈", "기아타이거즈",
    # 너무 일반적인 영어
    "people", "world", "company", "country", "case",
}

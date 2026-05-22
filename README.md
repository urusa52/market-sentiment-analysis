# 뉴스·SNS 기반 시장 영향 분석

뉴스 매체와 SNS의 감성(sentiment)이 자산 가격에 어떻게 영향을 주는지를 정량적으로 분석하는 프로젝트.

## 분석 범위

- **자산 39개**: BTC, ETH + Magnificent 7 (AAPL, MSFT, GOOGL, AMZN, NVDA, META, TSLA) + KOSPI 시총 상위 30
- **데이터 소스 4종**: yfinance, GDELT, Reddit, 네이버 뉴스
- **분석 방법**: LLM 기반 sentiment + Pearson 상관 + lag 분석

## 디렉토리 구조

```
.
├── src/                          # 핵심 모듈
│   ├── config.py                 # 모든 설정 (자산, 키워드, stopwords)
│   ├── db.py                     # DB 연결·스키마·자산 등록
│   ├── visualize.py              # 5종 그래프 생성
│   └── collectors/               # 데이터 수집기
│       ├── prices.py             # yfinance
│       ├── reddit.py             # Reddit
│       ├── gdelt.py              # GDELT
│       └── naver.py              # 네이버 뉴스
├── scripts/                      # 실행 스크립트 (사용자 진입점)
│   ├── 01_init_db.py
│   ├── 02_fetch_all.py
│   ├── 03_check_db.py
│   └── 04_make_charts.py
├── outputs/                      # 생성된 PNG·문서
├── .env.example                  # 환경변수 템플릿
├── .gitignore
├── requirements.txt
└── README.md
```

## 설치

```bash
# 1) 라이브러리 설치
pip install -r requirements.txt

# 2) 환경 변수 설정 (네이버 API 키)
cp .env.example .env
# .env 파일을 열어 NAVER_CLIENT_ID, NAVER_CLIENT_SECRET 입력
```

네이버 API 키 발급: <https://developers.naver.com/>

## 실행

```bash
# 1) DB 초기화 + 자산 마스터 등록
python -m scripts.01_init_db

# 2) 데이터 수집 (전부 또는 개별)
python -m scripts.02_fetch_all              # 전부
python -m scripts.02_fetch_all prices       # 가격만
python -m scripts.02_fetch_all reddit       # Reddit만
python -m scripts.02_fetch_all gdelt        # GDELT만
python -m scripts.02_fetch_all naver        # 네이버만

# 3) DB 현황 확인
python -m scripts.03_check_db

# 4) NLP 처리 (별도 — Claude Code 또는 sentiment 분석 도구 사용)
#    news 테이블의 텍스트 → news_sentiment 테이블에 저장

# 5) 그래프 생성
python -m scripts.04_make_charts
```

## 데이터 규모 (현재 기준)

| 항목 | 규모 |
|------|------|
| 자산 가격 (일 단위) | 9,738행 |
| 글로벌 뉴스 (GDELT) | 499건 |
| 한국 뉴스 (네이버) | 약 2,500건 |
| SNS 게시물 (Reddit) | 3,500건 |
| **총 텍스트** | **약 6,500건** |

## 핵심 발견

1. **Reddit은 후행 지표** — TSLA·GOOGL·NVDA에서 가격이 먼저, SNS가 1~7일 뒤 따라옴
2. **AMZN의 역상관 (lag 3, r=-0.459, p=0.006)** — "buy the rumor, sell the news" 패턴
3. **암호화폐의 정보 효율성** — BTC, ETH는 모든 lag에서 통계적으로 무의미
4. **한국 주식의 동시상관 지배** — 대부분 lag 0에서만 유의 → 예측이 아닌 기록
5. **부정 키워드의 한국 편중** — 한국 사회 사건이 부정 sentiment 절반 이상

## 한계 및 향후 계획

- 표본 기간 짧음 (1~4개월) → 6개월 이상 확장 필요
- 한국 SNS 데이터 미수집 → 향후 네이버 종목토론방 등 추가
- Granger causality 미수행 → 인과 방향 보강 필요
- Streamlit 대시보드 (분 단위 이벤트 리플레이) 개발 예정

## 라이선스

연구·교육 목적. 각 API 제공처의 이용약관에 따른다.

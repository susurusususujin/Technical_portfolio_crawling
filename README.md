# Technical_portfolio_crawling
서울과학기술대학교_데이터사이언스학과_24장수진_졸업심사_테크니컬포트폴리오

## Product Hunt Category Crawler

Product Hunt 카테고리 페이지에서 제품 목록과 고객사 데이터를 수집해 엑셀로 저장하는 크롤링 코드

### 주요 설치 라이브러리
pip install playwright pandas openpyxl nest_asyncio
playwright install chromium

### 사용법

크롤링할 카테고리 URL과 출력 파일명을 아래 변수로 설정한 후 실행

- 'BASE_CATEGORY_URL' = "https://www.producthunt.com/categories/payment-processors"
- 'OUT_FILE' = Path("output.xlsx")

> 중요: Cloudflare 감지 시 브라우저 창에서 수동으로 체크박스를 해제

### 결과

`output.xlsx` 파일에 두 개의 시트로 저장

- `platforms` — 플랫폼 목록 (slug, name, tag)
- `platform_customer_edges` — 플랫폼-고객사 관계 (platform_name, platform_tag, customer_name, customer_tag)

# Technical_portfolio_crawling
서울과학기술대학교_데이터사이언스학과_24장수진_졸업심사_테크니컬포트폴리오
# Product Hunt 카테고리 크롤러

Product Hunt 카테고리 페이지에서 플랫폼 목록을 수집하고, 각 플랫폼의 고객사 정보를 함께 크롤링하여 엑셀 파일로 저장하는 Python 스크립트입니다.

이 스크립트는 카테고리 페이지를 순회하며 제품 슬러그를 수집한 뒤, 각 제품의 `/customers` 페이지에 접속하여 다음 정보를 추출합니다.

- 플랫폼 이름
- 플랫폼 태그
- 고객사 이름
- 고객사 태그

최종 결과는 하나의 Excel 파일에 두 개의 시트로 저장됩니다.

---

## 1. 프로젝트 개요

이 코드는 Product Hunt의 특정 카테고리 페이지를 기준으로 플랫폼 데이터를 수집하고, 플랫폼과 고객사 간의 관계를 네트워크 형태로 정리하는 데 목적이 있습니다.

주요 흐름은 다음과 같습니다.

1. 카테고리 페이지에서 전체 플랫폼 슬러그 수집
2. 각 플랫폼의 고객사 페이지(`/products/{slug}/customers`) 방문
3. 플랫폼 정보와 고객사 정보 추출
4. 결과를 Excel 파일로 저장

---

## 2. 주요 기능

### 플랫폼 목록 수집
- 카테고리 페이지의 `main` 영역에서 `/products/{slug}` 링크를 추출합니다.
- 페이지별 중복을 제거하며 전체 플랫폼 슬러그를 수집합니다.
- `Showing X-Y of Z products` 문구를 읽어 전체 수집 범위를 추정합니다.

### 플랫폼 상세 정보 수집
- 각 플랫폼의 고객사 페이지에서 플랫폼 이름과 태그를 추출합니다.
- 헤더 영역의 `h1`, `h2` 및 카테고리 태그 영역을 활용합니다.

### 고객사 정보 수집
- 고객사 페이지에서 고객사 이름, 슬러그, 고객 태그를 수집합니다.
- Lazy loading 대응을 위해 페이지를 아래로 스크롤합니다.

### Excel 저장
- 결과를 하나의 `.xlsx` 파일에 두 개 시트로 저장합니다.
- 시트 구성:
  - `platforms`: 플랫폼 목록
  - `platform_customer_edges`: 플랫폼과 고객사 간 관계

### Cloudflare 대응
- 접속 중 Cloudflare 대기 페이지가 나타나면 사용자가 직접 통과할 수 있도록 대기합니다.

---

## 3. 사용 기술

- Python
- Playwright
- pandas
- asyncio
- nest_asyncio

---

## 4. 파일 구조 및 출력 결과

### 입력
별도의 입력 파일은 필요하지 않습니다.

### 출력
기본 출력 파일명은 아래와 같습니다.

```python
OUT_FILE = Path("ph_ecom_data_pay.xlsx")
```

생성되는 Excel 파일에는 다음 두 시트가 포함됩니다.

#### 1) `platforms`
플랫폼 전체 목록을 저장합니다.

예시 컬럼:
- `slug`
- `name`
- `tag`

#### 2) `platform_customer_edges`
플랫폼과 고객사 간 관계 데이터를 저장합니다.

예시 컬럼:
- `platform_slug`
- `platform_name`
- `platform_tag`
- `customer_name`
- `customer_tag`

---

## 5. 실행 환경

### 필요 패키지 설치

```bash
pip install pandas nest_asyncio playwright
playwright install
```

Chrome 채널을 사용하므로, 실행 환경에 Chrome 브라우저가 설치되어 있어야 합니다.

---

## 6. 실행 방법

```bash
python 12.01_crawling.py
```

실행 후 동작 순서는 다음과 같습니다.

1. 브라우저 실행
2. 카테고리 페이지 순회
3. 플랫폼 슬러그 수집
4. 각 플랫폼의 고객사 페이지 방문
5. 플랫폼 정보 및 고객사 정보 추출
6. Excel 파일 저장

---

## 7. 코드 동작 방식

### `normalize_slug(href)`
`/products/{slug}` 형태의 링크에서 slug를 추출합니다.

### `wait_for_cloudflare(page)`
Cloudflare의 `Just a moment` 또는 `Access denied` 페이지가 나타날 경우, 사용자가 직접 인증을 완료할 때까지 대기합니다.

### `scroll_to_bottom(page)`
고객사 목록이 lazy loading으로 불러와질 수 있으므로 페이지 하단까지 스크롤합니다.

### `extract_showing_info(page)`
카테고리 페이지의 `Showing X-Y of Z products` 문구를 파싱하여 현재 페이지 범위와 전체 제품 수를 반환합니다.

### `extract_page_slugs(page, per_page)`
현재 카테고리 페이지에서 플랫폼 slug를 추출합니다.

### `collect_platform_slugs(page, max_pages=100)`
카테고리 페이지를 여러 페이지 순회하며 전체 플랫폼 slug를 수집합니다.

### `scrape_platform_and_customers(page, slug)`
개별 플랫폼의 고객사 페이지를 방문해 플랫폼 기본 정보와 고객사 목록을 수집합니다.

### `main_async()`
전체 크롤링 파이프라인을 실행하고, 최종 결과를 Excel 파일로 저장합니다.

---

## 8. 주의사항

### 1) Cloudflare 수동 통과 필요 가능
Product Hunt 접속 중 Cloudflare 검증이 발생할 수 있습니다. 이 경우 스크립트가 자동으로 넘어가지 못하므로 사용자가 브라우저에서 직접 인증해야 합니다.

### 2) 브라우저가 눈에 보이는 모드로 실행됨
현재 설정은 아래와 같이 `headless=False` 입니다.

```python
browser = await p.chromium.launch(
    headless=False,
    channel="chrome",
    args=["--disable-blink-features=AutomationControlled"],
)
```

즉, 브라우저 창이 실제로 열리는 상태에서 동작합니다.

### 3) 사이트 구조 변경에 취약
이 코드는 CSS selector와 DOM 구조에 의존하므로, Product Hunt의 프론트엔드 구조가 바뀌면 일부 추출 로직이 동작하지 않을 수 있습니다.

### 4) 요청 속도 조절 포함
각 플랫폼 처리 후 `1.5초~3초` 사이 랜덤 대기를 넣어 과도한 요청을 완화합니다.

---

## 9. 수정해서 활용하기 좋은 부분

### 크롤링 대상 카테고리 변경
현재 카테고리 URL은 아래처럼 설정되어 있습니다.

```python
BASE_CATEGORY_URL = "https://www.producthunt.com/categories/payment-processors"
```

다른 카테고리를 수집하려면 이 URL만 변경하면 됩니다.

예:

```python
BASE_CATEGORY_URL = "https://www.producthunt.com/categories/ecommerce-platforms"
```

### 저장 파일명 변경

```python
OUT_FILE = Path("ph_ecom_data_pay.xlsx")
```

원하는 파일명으로 수정할 수 있습니다.

### 최대 페이지 수 변경

```python
platform_slugs = await collect_platform_slugs(page, max_pages=100)
```

필요에 따라 `max_pages` 값을 조정할 수 있습니다.

---

## 10. 활용 예시

이 스크립트는 다음과 같은 목적에 활용할 수 있습니다.

- Product Hunt 내 특정 카테고리의 플랫폼 목록 수집
- 플랫폼별 고객사 네트워크 분석
- 플랫폼 태그와 고객사 태그 기반 분류 분석
- 플랫폼 생태계 구조 파악
- 후속 그래프 분석 또는 시각화용 데이터 구축

---

## 11. 한 줄 요약

Product Hunt 특정 카테고리의 플랫폼과 고객사 정보를 수집하여, 플랫폼 목록과 플랫폼-고객 관계를 Excel 형태로 저장하는 Playwright 기반 크롤러입니다.

# coding: utf-8
"""
Product Hunt - Ecommerce platforms 크롤러 (정확한 태그 + 고객사)
- 카테고리 페이지에서 ecommerce-platforms 전 제품 슬러그 수집 (456개 근접)
- 각 플랫폼의 이름/태그 + 고객사/고객 태그를
  `/products/{slug}/customers` 페이지 한 번에서 모두 추출
- 결과는 엑셀 한 파일에 두 시트로 저장:
    1) platforms                (플랫폼 전체 목록)
    2) platform_customer_edges  (플랫폼-고객 네트워크)
"""

import sys
import re
import asyncio
import random
import nest_asyncio
from pathlib import Path
from typing import List, Dict, Optional, Tuple

import pandas as pd
from playwright.async_api import async_playwright

nest_asyncio.apply()

# ===== 설정 =====
BASE_CATEGORY_URL = "https://www.producthunt.com/categories/payment-processors"
OUT_FILE = Path("ph_ecom_data_pay.xlsx")

# ---------------- 유틸 ----------------

def normalize_slug(href: Optional[str]) -> Optional[str]:
    """'/products/slug' 형태의 href에서 slug 추출"""
    if not href:
        return None
    href = href.split("?")[0].rstrip("/")
    parts = href.split("/")
    if "products" in parts:
        idx = parts.index("products")
        if idx + 1 < len(parts):
            return parts[idx + 1]
    return None

async def wait_for_cloudflare(page):
    """Cloudflare 'Just a moment' 페이지 만나면 사람이 수동 통과할 수 있게 대기"""
    try:
        title = await page.title()
        if any(x in title for x in ["Just a moment", "Access denied", "Cloudflare"]):
            print("\n[!!!] Cloudflare 감지됨! 사람이 직접 체크박스를 풀어주세요.")
            while True:
                title_now = await page.title()
                if all(s not in title_now for s in ["Just a moment", "Access denied"]):
                    print("[OK] Cloudflare 통과 완료!")
                    break
                await page.wait_for_timeout(2000)
    except Exception:
        pass

async def scroll_to_bottom(page):
    """페이지 끝까지 스크롤 (customers 리스트 Lazy Loading 대비)"""
    print("      ...스크롤 내리는 중 (데이터 로딩)...")
    for _ in range(5):
        await page.mouse.wheel(0, 3000)
        await page.wait_for_timeout(1000)
    await page.evaluate("window.scrollTo(0, document.body.scrollHeight)")
    await page.wait_for_timeout(2000)

async def extract_showing_info(page) -> Optional[Tuple[int, int, int]]:
    """
    "Showing X-YY of ZZZ products" 텍스트에서 (X, Y, Z) 튜플 반환.
    """
    try:
        text = await page.evaluate(
            """
            () => {
                const all = Array.from(document.querySelectorAll("body *"));
                const el = all.find(e => e.textContent &&
                    e.textContent.match(/Showing \\d+-\\d+ of \\d+ products/));
                return el ? el.textContent : null;
            }
            """
        )
        if not text:
            return None
        m = re.search(r"Showing (\d+)-(\d+) of (\d+) products", text)
        if not m:
            return None
        start_i, end_i, total = map(int, m.groups())
        return start_i, end_i, total
    except Exception:
        return None

# ---------------- 카테고리에서 플랫폼 슬러그 수집 ----------------

async def extract_page_slugs(page, per_page: int) -> List[str]:
    """
    현재 카테고리 페이지에서 main 영역의 /products/ 링크 중
    'per_page' 개수만큼 유니크 slug를 앞에서부터 추출.
    (페이지 하단 글로벌 트렌딩/Top reviewed 섹션은 무시)
    """
    slugs = await page.evaluate(
        """
        (perPage) => {
            const anchors = Array.from(
                document.querySelectorAll('main a[href^="/products/"]')
            );
            const seen = new Set();
            const out = [];

            for (const a of anchors) {
                const href = a.getAttribute("href");
                if (!href) continue;
                const parts = href.split("?")[0].split("/");
                const idx = parts.indexOf("products");
                if (idx === -1 || idx + 1 >= parts.length) continue;
                const slug = parts[idx + 1];
                if (!slug || seen.has(slug)) continue;

                seen.add(slug);
                out.push(slug);
                if (out.length >= perPage) break;
            }

            return out;
        }
        """,
        per_page,
    )
    return slugs or []

async def collect_platform_slugs(page, max_pages: int = 100) -> List[str]:
    """
    ecommerce-platforms 카테고리 페이지들을 돌면서
    각 페이지에서 per_page 개수만큼 product slug를 모은다.
    목표는 'Showing 1-15 of 456 products'의 456개 전체.
    """
    seen = set()
    print(f"[1단계] 플랫폼 목록 수집 중... (최대 {max_pages}페이지)")

    last_total = None
    per_page_default = 15

    for i in range(1, max_pages + 1):
        url = BASE_CATEGORY_URL if i == 1 else f"{BASE_CATEGORY_URL}?page={i}"
        print(f"\n  [카테고리 페이지 {i}] {url}")

        try:
            await page.goto(url, wait_until="domcontentloaded", timeout=60000)
            await wait_for_cloudflare(page)
            await page.wait_for_timeout(1500)

            showing = await extract_showing_info(page)
            if showing:
                start_i, end_i, total = showing
                last_total = total
                per_page = end_i - start_i + 1
                print(f"    - Showing {start_i}-{end_i} of {total} products")
            else:
                per_page = per_page_default
                print(f"    - Showing 정보 없음, per_page={per_page_default} 가정")

            slugs = await extract_page_slugs(page, per_page)

            if not slugs:
                print("    - 이 페이지에서 슬러그를 하나도 찾지 못해 종료합니다.")
                break

            prev_len = len(seen)
            for s in slugs:
                seen.add(s)
            added = len(seen) - prev_len

            print(f"    - 이 페이지에서 신규 {added}개, 누적 {len(seen)}개 플랫폼")

            # Showing 정보가 있고, 이번 페이지 end가 total 이상이면 마지막 페이지
            if showing and end_i >= total:
                print("    - 마지막 페이지에 도달했으므로 플랫폼 수집 종료.")
                break

            # Showing 정보가 없는데 새로 추가된 슬러그가 없다면 종료
            if not showing and added == 0:
                print("    - Showing 텍스트 없음 + 신규 슬러그 없음 → 수집 종료.")
                break

        except Exception as e:
            print(f"    ! 에러 (페이지 {i}): {e}")
            break

    print(f"\n[1단계 완료] 플랫폼 슬러그 {len(seen)}개 수집됨 (텍스트상의 총 제품 수: {last_total})")
    return sorted(list(seen))

# ---------------- 플랫폼 + 고객사 수집 (customers 페이지에서 한 번에) ----------------

async def scrape_platform_and_customers(page, slug: str) -> Tuple[Dict, List[Dict]]:
    """
    /products/{slug}/customers 페이지에서:
      - 플랫폼 기본 정보 (slug, name, tag)
      - 고객사 목록 (customer_name, customer_tag)
    를 한 번에 수집해서 (platform_info, customer_rows)로 반환.
    """
    url = f"https://www.producthunt.com/products/{slug}/customers"
    platform_info: Dict = {"slug": slug, "name": slug, "tag": ""}
    rows: List[Dict] = []

    try:
        await page.goto(url, wait_until="domcontentloaded", timeout=60000)
        await wait_for_cloudflare(page)
        await page.wait_for_timeout(1000)

        # 1) 플랫폼 이름 (헤더의 H2 또는 H1)
        p_name = await page.evaluate(
            """
            () => {
                const h2 = document.querySelector('h2.text-24.font-semibold.text-gray-900');
                if (h2) return h2.textContent.trim();

                const h1 = document.querySelector('main h1');
                if (h1) return h1.textContent.trim();

                const h2any = document.querySelector('main h2');
                if (h2any) return h2any.textContent.trim();

                return "";
            }
            """
        )
        platform_info["name"] = p_name or slug

        # 2) 플랫폼 태그
        #    - 제품 헤더 아래의 태그 바: div.flex.flex-wrap.items-center.gap-2.text-14
        #    - #customers-content / #alternatives-content 내부는 고객/대체제품용이므로 제외
        p_tags = await page.evaluate(
            """
            () => {
                const containers = Array.from(
                    document.querySelectorAll('div.flex.flex-wrap.items-center.gap-2.text-14')
                );

                let target = null;
                for (const c of containers) {
                    if (c.closest('#customers-content') || c.closest('#alternatives-content')) {
                        continue;
                    }
                    if (c.querySelector('a[href^="/categories/"]')) {
                        target = c;
                        break;
                    }
                }

                if (!target) return "";

                const labels = Array.from(
                    target.querySelectorAll('a[href^="/categories/"]')
                ).map(a => (a.textContent || "").trim()).filter(Boolean);

                return labels.join(", ");
            }
            """
        )
        platform_info["tag"] = (p_tags or "").strip()

        # 3) 고객사 리스트 로딩 (스크롤)
        await scroll_to_bottom(page)

        # 4) 고객사 + customer_tag 수집
        customers_data = await page.evaluate(
            """
            (platformSlug) => {
                const section = document.querySelector('#customers-content');
                if (!section) return [];

                const results = [];
                const links = Array.from(
                    section.querySelectorAll('a[href^="/products/"]')
                );

                links.forEach(link => {
                    const href = link.getAttribute("href");
                    if (!href) return;

                    const parts = href.split("?")[0].split("/");
                    const idx = parts.indexOf("products");
                    if (idx === -1 || idx + 1 >= parts.length) return;

                    const cSlug = parts[idx + 1];
                    if (!cSlug || cSlug === platformSlug) return;

                    const rawText = (link.textContent || "").split("\\n")[0].trim();
                    const cName = rawText || cSlug;

                    // link가 속한 카드(div.relative isolate grid ...)를 찾고,
                    // 그 카드 안에서 태그 컨테이너(div.flex.flex-wrap.items-center.gap-2.text-14)를 찾는다.
                    let card = link.closest('div.relative.isolate.grid');
                    let cTags = "";

                    if (card) {
                        const tagDiv = card.querySelector(
                            'div.flex.flex-wrap.items-center.gap-2.text-14'
                        );
                        if (tagDiv) {
                            cTags = Array.from(
                                tagDiv.querySelectorAll('a[href^="/categories/"]')
                            ).map(a => (a.textContent || "").trim())
                             .filter(Boolean)
                             .join(", ");
                        }
                    }

                    results.push({
                        customer_name: cName,
                        customer_tag: cTags,
                        customer_slug: cSlug
                    });
                });

                return results;
            }
            """,
            slug,
        )

        seen_c = set()
        for item in customers_data or []:
            c_slug = item.get("customer_slug")
            if not c_slug or c_slug in seen_c:
                continue
            seen_c.add(c_slug)

            rows.append(
                {
                    "platform_slug": platform_info["slug"],
                    "platform_name": platform_info["name"],
                    "platform_tag": platform_info.get("tag", ""),
                    "customer_name": item.get("customer_name", ""),
                    "customer_tag": item.get("customer_tag", ""),
                }
            )

    except Exception as e:
        print(f"  ! 에러 ({slug}): {e}")

    return platform_info, rows

# ---------------- 메인 ----------------

async def main_async():
    async with async_playwright() as p:
        browser = await p.chromium.launch(
            headless=False,
            channel="chrome",
            args=["--disable-blink-features=AutomationControlled"],
        )
        context = await browser.new_context(
            user_agent=(
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                "AppleWebKit/537.36 (KHTML, like Gecko) "
                "Chrome/119.0.0.0 Safari/537.36"
            )
        )
        page = await context.new_page()
        await page.add_init_script(
            "Object.defineProperty(navigator, 'webdriver', {get: () => undefined})"
        )

        # 1. 카테고리에서 플랫폼 슬러그 전체 수집
        platform_slugs = await collect_platform_slugs(page, max_pages=100)
        print(f"\n[디버그] 최종 플랫폼 수(슬러그 기준): {len(platform_slugs)}개")

        platform_rows: List[Dict] = []
        edge_rows: List[Dict] = []

        # 2. 각 플랫폼에 대해 customers 페이지 크롤링
        print(f"\n[2단계] 상세 데이터 수집 시작 (플랫폼 {len(platform_slugs)}개)")
        for idx, slug in enumerate(platform_slugs):
            print(f"[{idx + 1}/{len(platform_slugs)}] '{slug}' 처리 중...")

            platform_info, data_rows = await scrape_platform_and_customers(page, slug)
            platform_rows.append(platform_info)
            edge_rows.extend(data_rows)

            print(
                f"  -> 고객사 {len(data_rows)}명 수집 "
                f"(플랫폼 태그: {platform_info.get('tag','')})"
            )

            await page.wait_for_timeout(random.randint(1500, 3000))

        await browser.close()

        # 3. 저장
        if not platform_rows:
            print("\n[알림] 플랫폼 데이터가 없습니다.")
            return

        df_platforms = pd.DataFrame(platform_rows)
        df_platforms = df_platforms.drop_duplicates(subset=["slug"]).reset_index(drop=True)
        print(f"\n[요약] 플랫폼 시트: {len(df_platforms)}개 (slug uniq)")

        df_edges = pd.DataFrame(edge_rows) if edge_rows else pd.DataFrame(
            columns=[
                "platform_slug",
                "platform_name",
                "platform_tag",
                "customer_name",
                "customer_tag",
            ]
        )
        print(f"[요약] 플랫폼-고객 엣지 시트: {len(df_edges)}개 행")

        with pd.ExcelWriter(OUT_FILE) as writer:
            df_platforms.to_excel(writer, sheet_name="platforms", index=False)
            df_edges.to_excel(writer, sheet_name="platform_customer_edges", index=False)

        print(f"\n[성공] '{OUT_FILE}' 파일에 저장 완료.")
        print("  - Sheet 'platforms'               : 플랫폼 전체 목록")
        print("  - Sheet 'platform_customer_edges' : 플랫폼-고객 관계")

if __name__ == "__main__":
    if sys.platform.startswith("win"):
        asyncio.set_event_loop_policy(asyncio.WindowsProactorEventLoopPolicy())
    asyncio.run(main_async())

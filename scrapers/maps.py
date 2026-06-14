"""
Google Maps scraper — Playwright, two-phase:
  Phase 1: collect place URLs from the search feed
  Phase 2: navigate to each URL and extract details
"""
import re
import asyncio
from urllib.parse import quote
from playwright.async_api import async_playwright


async def scrape_google_maps(query: str, location: str, max_results: int = 50) -> list[dict]:  # noqa: C901
    search_term = f"{query} {location}".strip()
    search_url = f"https://www.google.com/maps/search/{quote(search_term)}"

    async with async_playwright() as pw:
        browser = await pw.chromium.launch(headless=True)
        ctx = await browser.new_context(
            locale="pl-PL",
            user_agent=(
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                "AppleWebKit/537.36 (KHTML, like Gecko) "
                "Chrome/124.0.0.0 Safari/537.36"
            ),
        )

        # ── Phase 1: collect place URLs ───────────────────────────────────────
        page = await ctx.new_page()
        print(f"  Otwieram: {search_url}")
        await page.goto(search_url, wait_until="domcontentloaded", timeout=30000)
        await page.wait_for_timeout(3000)

        # Dismiss cookie dialog
        for sel in [
            'button[aria-label="Odrzuc wszystko"]',
            'button[aria-label="Reject all"]',
            'form:has(button) button:first-child',
        ]:
            try:
                await page.click(sel, timeout=2000)
                await page.wait_for_timeout(500)
                break
            except Exception:
                pass

        hrefs: list[str] = []
        collect_limit = min(max_results * 2, 80)  # zbierz 2x więcej żeby mieć z czego odwrócić

        for _ in range(50):
            if len(hrefs) >= collect_limit:
                break

            links = await page.locator('a[href*="/maps/place/"]').all()
            for link in links:
                try:
                    href = await link.get_attribute("href", timeout=2000)
                except Exception:
                    continue
                if href and href not in hrefs:
                    hrefs.append(href)

            # Scroll the results feed
            try:
                await page.locator('[role="feed"]').evaluate(
                    "el => el.scrollBy(0, 1200)"
                )
            except Exception:
                pass
            await page.wait_for_timeout(1500)

            # End-of-results markers
            for end_text in ["Koniec wynikow", "You've reached the end", "wynikow na stronie"]:
                if await page.locator(f"text='{end_text}'").count() > 0:
                    break

        # Odwróć — mniej popularne firmy (koniec listy) częściej nie mają stron
        hrefs.reverse()

        await page.close()
        print(f"  Zebrano {len(hrefs)} linkow, odwiedzam od najmniej popularnych")

        # ── Phase 2: visit each place URL ─────────────────────────────────────
        results: list[dict] = []
        detail = await ctx.new_page()

        for i, href in enumerate(hrefs[:max_results]):
            if not href.startswith("http"):
                href = "https://www.google.com" + href

            try:
                await detail.goto(href, wait_until="domcontentloaded", timeout=20000)
                await detail.wait_for_timeout(1800)
                biz = await _extract_details(detail)
                if biz:
                    results.append(biz)
                    phone_str = biz.get("phone") or "brak tel."
                    print(f"  [{len(results):>2}] {biz['name'][:35]:<35} {location:<15} {phone_str}")
            except Exception as e:
                print(f"  [{i+1:>2}] Blad: {e}")

        await detail.close()
        await browser.close()

    return results


async def _extract_details(page) -> dict | None:
    try:
        await page.wait_for_selector("h1", timeout=7000)
    except Exception:
        return None

    async def txt(selector: str, timeout: int = 3000) -> str:
        try:
            return (await page.locator(selector).first.text_content(timeout=timeout) or "").strip()
        except Exception:
            return ""

    async def attr(selector: str, attribute: str, timeout: int = 3000) -> str:
        try:
            return (await page.locator(selector).first.get_attribute(attribute, timeout=timeout) or "").strip()
        except Exception:
            return ""

    name = await txt("h1")
    if not name or name.lower() in ("wyniki", "results", "google maps", ""):
        return None

    # Category: small button just below the name
    category = await txt("button.DkEaL")
    if not category:
        category = await txt('[jsaction*="category"]')

    # Address
    address = await txt('[data-item-id="address"] .Io6YTe')
    if not address:
        raw = await attr('button[aria-label*="adres"]', "aria-label")
        address = raw.replace("Kopiuj adres: ", "").replace("Adres: ", "").strip()

    # Phone — try data-item-id, then tel: link
    phone = await txt('[data-item-id^="phone:tel:"] .Io6YTe')
    if not phone:
        tel_href = await attr('a[href^="tel:"]', "href")
        phone = tel_href.replace("tel:", "").strip()

    # Website
    website = await attr('a[data-item-id="authority"]', "href")
    if not website:
        website = await attr('a[aria-label*="itryna"]', "href")

    # Rating & review count
    # Rating is in the aria-hidden span (e.g. "4,8")
    rating = await txt('.F7nice span[aria-hidden="true"]')
    # Review count is displayed as "(1 234)" — extract from the F7nice text content
    f7_text = await txt('.F7nice')
    m = re.search(r'\(([\d\s]+)\)', f7_text)
    reviews = re.sub(r'\s', '', m.group(1)) if m else ""

    return {
        "name":      name,
        "category":  category,
        "address":   address,
        "phone":     phone,
        "website":   website,
        "rating":    rating,
        "reviews":   reviews,
        "email":     "",
        "phone_site": "",
    }

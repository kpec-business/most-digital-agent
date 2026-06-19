"""
Most Digital — Scraper Core
Shared logic used by scraper_pl.py / scraper_uk.py / scraper_de.py
"""
import asyncio
import os
import random

from scrapers.maps import scrape_google_maps
from output import save_to_excel
from supabase_sync import sync_leads

MAX_PER_QUERY    = 30
MAX_REVIEWS_HOT  = 10
MAX_REVIEWS_WARM = 50
MAX_TOTAL        = int(os.environ.get("MAX_LEADS", 180))  # limit leadów na jedno uruchomienie

PRIORITY_ORDER = {"GORACY": 0, "CIEPLY": 1, "POMIJAJ": 99}


def classify(biz: dict, country: str = "pl") -> tuple[str, str]:
    """
    PL  — tylko bez strony (GORACY). Wiele PL firm nie ma stron.
    UK/DE — bez strony = GORACY, mało opinii (≤30) = CIEPLY.
           W rozwiniętych rynkach prawie każda firma ma stronę,
           więc filtr "tylko bez strony" daje za mało leadów.
    """
    has_website = bool(biz.get("website", "").strip())
    has_phone   = bool(biz.get("phone", "").strip())
    try:
        reviews = int(biz.get("reviews", "0") or "0")
    except ValueError:
        reviews = 0

    if not has_website:
        reason = "Brak strony" + (", ma tel" if has_phone else ", brak tel")
        return "GORACY", reason

    warm_limit = 30 if country in ("uk", "de") else 10
    if reviews <= warm_limit:
        return "CIEPLY", f"Strona + tylko {reviews} opinii"

    return "POMIJAJ", ""


async def scrape_city(city: str, queries: list, seen: set, all_biz: list, label: str, max_total: int = 0, country: str = "pl"):
    total_q = len(queries)
    for qi, query in enumerate(queries, 1):
        if max_total and len(all_biz) >= max_total:
            break
        print(f"  [{label}] [{qi:>2}/{total_q}] '{query} {city}'...")
        try:
            results = await scrape_google_maps(query, city, MAX_PER_QUERY)
        except Exception as e:
            print(f"    Blad: {e}")
            continue

        added = 0
        for biz in results:
            if max_total and len(all_biz) >= max_total:
                break
            key = f"{biz['name'].lower()}|{biz['address'].lower()}"
            if key in seen or not biz["name"]:
                continue
            priorytet, powod = classify(biz, country=country)
            if priorytet == "POMIJAJ":
                continue
            seen.add(key)
            biz["priorytet"] = priorytet
            biz["powod"]     = powod
            biz["city"]      = city
            all_biz.append(biz)
            added += 1

        limit_info = f" ✓ LIMIT {max_total}" if (max_total and len(all_biz) >= max_total) else ""
        print(f"    +{added} | lacznie: {len(all_biz)}{limit_info}")


async def run_scraper(region_keys: list, regions_config: dict,
                      base_queries: list, district_niches: list,
                      country: str, label: str, max_total: int = 0):
    """
    Universal scraper loop.
    country: 'pl' | 'uk' | 'de'  — stored in Supabase leads.country
    """
    print("=" * 62)
    print(f"  Most Digital — Scraper [{country.upper()}] — {label}")
    print(f"  Regiony: {', '.join(region_keys)}")
    print("=" * 62)

    all_biz: list[dict] = []
    seen:    set[str]   = set()

    limit = max_total or MAX_TOTAL
    print(f"  Cel: {limit} leadów na to uruchomienie")
    base_queries = list(base_queries)
    random.shuffle(base_queries)
    district_niches = list(district_niches)
    random.shuffle(district_niches)
    print(f"  Kolejnosc zapytan: {base_queries[:5]}...")

    for region_key in region_keys:
        if limit and len(all_biz) >= limit:
            break
        if region_key not in regions_config:
            print(f"\n  [WARN] Nieznany region: '{region_key}'")
            print(f"  Dostepne: {', '.join(regions_config.keys())}")
            continue

        region = regions_config[region_key]
        print(f"\n{'=' * 50}")
        print(f"  REGION: {region['label']}")
        print(f"{'=' * 50}")

        for city_name, districts in region["cities"]:
            if limit and len(all_biz) >= limit:
                print(f"\n  ✓ Osiagnieto cel {limit} leadów — kończę scraping")
                break
            if districts:
                queries = base_queries + [
                    f"{niche} {district}"
                    for niche in district_niches
                    for district in districts
                ]
            else:
                queries = base_queries

            lbl = city_name[:3].upper()
            print(f"\n>>> {city_name.upper()} ({len(queries)} zapytan)")
            await scrape_city(city_name, queries, seen, all_biz, lbl, max_total=limit, country=country)

    all_biz.sort(key=lambda b: (
        PRIORITY_ORDER.get(b.get("priorytet", "POMIJAJ"), 99),
        int(b.get("reviews", "0") or "0"),
    ))

    gorące = sum(1 for b in all_biz if b.get("priorytet") == "GORACY")
    cieple = sum(1 for b in all_biz if b.get("priorytet") == "CIEPLY")

    print(f"\n{'=' * 62}")
    print(f"  Scraped: {len(all_biz)} | GORACY: {gorące} | CIEPLY: {cieple}")

    out = save_to_excel(all_biz)
    with_phone = sum(1 for b in all_biz if b.get("phone"))

    source = "_".join(region_keys) + "_batch"
    print(f"\n  Synchronizuje z Supabase (country={country})...")
    try:
        n_new = sync_leads(all_biz,
                           city=",".join(region_keys),
                           source_query=source,
                           country=country)
        print(f"  Supabase: +{n_new} nowych leadow")
    except Exception as e:
        print(f"  Blad sync: {e}")
        n_new = 0

    print(f"\n{'=' * 62}")
    print(f"  GOTOWE! Leady sa w bazie — kliknij 'Dystrybuuj' w panelu admina.")
    print(f"  Plik Excel:      {out}")
    print(f"  Firm bez strony: {len(all_biz)}")
    print(f"  Nowe w Supabase: {n_new}")
    print(f"  GORACY:          {gorące}")
    print(f"  Z telefonem:     {with_phone}")
    print(f"{'=' * 62}")

    if not os.environ.get("CI"):
        input("\n  Nacisnij Enter zeby zamknac...")

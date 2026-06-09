import asyncio
import os
import sys

if sys.stdout.encoding != "utf-8":
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

from scrapers.maps import scrape_google_maps
from scrapers.website import extract_contacts
from output import save_to_excel
from supabase_sync import sync_leads
from distribute import distribute

MAX_PER_QUERY    = 30
MAX_REVIEWS_HOT  = 10
MAX_REVIEWS_WARM = 50

BASE_QUERIES = [
    "hydraulik",
    "elektryk",
    "instalacje klimatyzacji",
    "instalacje solarne fotowoltaika",
    "firma remontowa",
    "stolarz na wymiar",
    "malarz pokojowy",
    "glazurnik kafelkarz",
    "sluszarz",
    "dekarz",
    "sprzatanie biur",
    "sprzatanie mieszkan",
    "przeprowadzki",
    "pranie tapicerek",
    "serwis komputerowy",
    "naprawa telefonow",
    "naprawa AGD",
    "szkola jezykowa",
    "korepetycje",
    "nauka jazdy",
    "gabinet masazu",
    "kosmetyczka",
    "tatuaz studio",
    "fotograf",
    "tlumacz przysiegy",
    "uslugi ksiegowe",
]

LODZ_DISTRICTS  = ["Baluty", "Gorna", "Polesie", "Srodmiescie", "Widzew"]
DISTRICT_NICHES = ["hydraulik", "elektryk", "firma remontowa", "malarz pokojowy", "sprzatanie"]

OTHER_CITIES = [
    "Pabianice",
    "Zgierz",
    "Tomaszow Mazowiecki",
    "Piotrkow Trybunalski",
    "Skierniewice",
    "Leczyce",
    "Kutno",
    "Radomsko",
    "Belchatow",
    "Sieradz",
    "Wielun",
    "Lowicz",
    "Zdunska Wola",
    "Opoczno",
]

PRIORITY_ORDER = {"GORACY": 0, "CIEPLY": 1, "POMIJAJ": 99}


def classify(biz: dict) -> tuple[str, str]:
    has_website = bool(biz.get("website", "").strip())
    try:
        reviews = int(biz.get("reviews", "0") or "0")
    except ValueError:
        reviews = 0

    if not has_website:
        if reviews <= MAX_REVIEWS_HOT:
            return "GORACY", "Brak strony, malo opinii"
        return "GORACY", f"Brak strony ({reviews} opinii)"

    if reviews <= MAX_REVIEWS_WARM:
        return "CIEPLY", f"Strona + tylko {reviews} opinii"

    return "POMIJAJ", ""


async def scrape_city(city: str, queries: list[str], seen: set, all_biz: list, label: str):
    for qi, query in enumerate(queries, 1):
        print(f"  [{label}] [{qi:>2}/{len(queries)}] '{query} {city}'...")
        try:
            results = await scrape_google_maps(query, city, MAX_PER_QUERY)
        except Exception as e:
            print(f"    Blad: {e}")
            continue

        added = 0
        for biz in results:
            key = f"{biz['name'].lower()}|{biz['address'].lower()}"
            if key in seen or not biz["name"]:
                continue
            priorytet, powod = classify(biz)
            if priorytet == "POMIJAJ":
                continue
            seen.add(key)
            biz["priorytet"] = priorytet
            biz["powod"]     = powod
            biz["city"]      = city
            all_biz.append(biz)
            added += 1

        print(f"    +{added} | lacznie: {len(all_biz)}")


async def main():
    print("=" * 62)
    print("  Most Digital — Lodz Lead Collector")
    lodz_queries = BASE_QUERIES + [
        f"{niche} {district}"
        for niche in DISTRICT_NICHES
        for district in LODZ_DISTRICTS
    ]
    print(f"  Lodz: {len(lodz_queries)} zapytan | Inne miasta: {len(OTHER_CITIES)} x {len(BASE_QUERIES)}")
    print("  Filtr: brak strony LUB < 50 opinii")
    print("=" * 62)

    all_biz: list[dict] = []
    seen:    set[str]  = set()

    print(f"\n>>> LODZ ({len(lodz_queries)} zapytan)")
    await scrape_city("Lodz", lodz_queries, seen, all_biz, "LDZ")

    for city in OTHER_CITIES:
        print(f"\n>>> {city.upper()}")
        await scrape_city(city, BASE_QUERIES, seen, all_biz, city[:3].upper())

    all_biz.sort(key=lambda b: (
        PRIORITY_ORDER.get(b.get("priorytet", "POMIJAJ"), 99),
        int(b.get("reviews", "0") or "0"),
    ))

    print(f"\n{'=' * 62}")
    gorące = sum(1 for b in all_biz if b.get("priorytet") == "GORACY")
    cieple = sum(1 for b in all_biz if b.get("priorytet") == "CIEPLY")
    print(f"  Znaleziono: {len(all_biz)} | GORACY: {gorące} | CIEPLY: {cieple}")

    with_site = [b for b in all_biz if b.get("website")]
    print(f"\n  Wyciagam emaile z {len(with_site)} stron...")
    for i, biz in enumerate(all_biz):
        if not biz.get("website"):
            continue
        try:
            contacts = extract_contacts(biz["website"])
            biz.update(contacts)
            if contacts.get("email"):
                print(f"  [{i+1:>3}] {biz['name'][:38]:<38} {contacts['email']}")
        except Exception:
            pass

    out = save_to_excel(all_biz)

    print(f"\n  Synchronizuję z Supabase...")
    try:
        n_new = sync_leads(all_biz, city="Lodz", source_query="lodz_batch")
        print(f"  Supabase: +{n_new} nowych leadow")
    except Exception as e:
        print(f"  Blad sync: {e}")
        n_new = 0

    print(f"\n  Przydzielam leady sprzedawcom...")
    try:
        dist = distribute(dry_run=False)
        dist_count = dist.get("count", 0)
        print(f"  Przydzielono: {dist_count} leadow")
    except Exception as e:
        print(f"  Blad dystrybucji: {e}")
        dist_count = 0

    with_email = sum(1 for b in all_biz if b.get("email"))
    with_phone = sum(1 for b in all_biz if b.get("phone") or b.get("phone_site"))

    print(f"\n{'=' * 62}")
    print(f"  GOTOWE!")
    print(f"  Plik Excel:      {out}")
    print(f"  Firm scraped:    {len(all_biz)}")
    print(f"  Nowe w Supabase: {n_new}")
    print(f"  Przydzielono:    {dist_count}")
    print(f"  GORACY:          {gorące}")
    print(f"  CIEPLY:          {cieple}")
    print(f"  Z emailem:       {with_email}")
    print(f"  Z telefonem:     {with_phone}")
    print(f"{'=' * 62}")

    if not os.environ.get("CI"):
        input("\n  Nacisnij Enter zeby zamknac...")


if __name__ == "__main__":
    asyncio.run(main())

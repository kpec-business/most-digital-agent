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

POZNAN_DISTRICTS = ["Jezyce", "Grunwald", "Stare Miasto", "Nowe Miasto", "Wilda", "Rataje", "Piatkowo"]
DISTRICT_NICHES  = ["hydraulik", "elektryk", "firma remontowa", "malarz pokojowy", "sprzatanie"]

OTHER_CITIES = [
    "Kalisz",
    "Konin",
    "Gniezno",
    "Ostrow Wielkopolski",
    "Leszno",
    "Pila",
    "Szamotuly",
    "Jarocin",
    "Wagrowiec",
    "Koscian",
    "Srem",
    "Sroda Wielkopolska",
    "Turku Wielkopolski",
    "Kolo",
    "Chodzież",
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
    total_q = len(queries)
    for qi, query in enumerate(queries, 1):
        print(f"  [{label}] [{qi:>2}/{total_q}] '{query} {city}'...")
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
    print("  Most Digital — Wielkopolska Lead Collector")
    print(f"  Poznan ({len(BASE_QUERIES)} zapytan + {len(DISTRICT_NICHES)*len(POZNAN_DISTRICTS)} dzielnice)")
    print(f"  Inne miasta: {len(OTHER_CITIES)} x {len(BASE_QUERIES)} zapytan")
    print("  Filtr: brak strony LUB < 50 opinii")
    print("=" * 62)

    all_biz: list[dict] = []
    seen:    set[str]  = set()

    poznan_queries = BASE_QUERIES + [
        f"{niche} {district}"
        for niche in DISTRICT_NICHES
        for district in POZNAN_DISTRICTS
    ]
    print(f"\n>>> POZNAN ({len(poznan_queries)} zapytan)")
    await scrape_city("Poznan", poznan_queries, seen, all_biz, "POZ")

    for city in OTHER_CITIES:
        short = city[:3].upper()
        print(f"\n>>> {city.upper()} ({len(BASE_QUERIES)} zapytan)")
        await scrape_city(city, BASE_QUERIES, seen, all_biz, short)

    all_biz.sort(key=lambda b: (
        PRIORITY_ORDER.get(b.get("priorytet", "POMIJAJ"), 99),
        int(b.get("reviews", "0") or "0"),
    ))

    print(f"\n{'=' * 62}")
    print(f"  Znaleziono {len(all_biz)} leadow")
    gorące = sum(1 for b in all_biz if b.get("priorytet") == "GORACY")
    cieple = sum(1 for b in all_biz if b.get("priorytet") == "CIEPLY")
    print(f"  GORACY:  {gorące}")
    print(f"  CIEPLY:  {cieple}")

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

    with_email = sum(1 for b in all_biz if b.get("email"))
    with_phone = sum(1 for b in all_biz if b.get("phone") or b.get("phone_site"))

    print(f"\n  Synchronizuję z Supabase...")
    try:
        n_new = sync_leads(all_biz, city="Wielkopolska", source_query="wielkopolska_batch")
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

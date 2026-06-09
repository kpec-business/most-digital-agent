"""
Most Digital — Wroclaw batch lead collector.
Targets: firms with NO website OR very few Google reviews.
These are the hottest leads for AI marketing services.
"""
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

LOCATION = "Wroclaw"

# Non-seasonal, service-based niches — typically low digital sophistication
# Wroclaw districts — searching by district surfaces smaller, local businesses
DISTRICTS = ["Krzyki", "Fabryczna", "Psie Pole", "Srodmiescie", "Stare Miasto"]

# Base queries — non-seasonal, service niches with low digital sophistication
BASE_QUERIES = [
    # Rzemioslo / instalacje
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
    # Uslugi lokalne
    "sprzatanie biur",
    "sprzatanie mieszkan",
    "przeprowadzki",
    "pranie tapicerek",
    # Serwis
    "serwis komputerowy",
    "naprawa telefonow",
    "naprawa AGD",
    # Edukacja
    "szkola jezykowa",
    "korepetycje",
    "nauka jazdy",
    # Zdrowie / uroda (mniejsze gabinety)
    "gabinet masazu",
    "kosmetyczka",
    "tatuaz studio",
    # Inne
    "fotograf",
    "tlumacz przysiegy",
    "uslugi ksiegowe",
]

# Build final query list: base queries + top niches searched by district
DISTRICT_NICHES = ["hydraulik", "elektryk", "firma remontowa", "malarz pokojowy", "sprzatanie"]
QUERIES = BASE_QUERIES + [
    f"{niche} {district}" for niche in DISTRICT_NICHES for district in DISTRICTS
]

MAX_PER_QUERY    = 30
MAX_REVIEWS_HOT  = 10   # bez strony + <= 10 opinii  -> GORACY "brak strony, malo opinii"
MAX_REVIEWS_WARM = 50   # ma strone ale <= 50 opinii -> CIEPLY


def classify(biz: dict) -> tuple[str, str]:
    """Returns (priorytet_label, powod) for a business."""
    has_website = bool(biz.get("website", "").strip())
    try:
        reviews = int(biz.get("reviews", "0") or "0")
    except ValueError:
        reviews = 0

    # No website = always the hottest lead, regardless of review count
    if not has_website:
        if reviews <= MAX_REVIEWS_HOT:
            return "GORACY", "Brak strony, malo opinii"
        return "GORACY", f"Brak strony ({reviews} opinii)"

    # Has website but small online presence
    if reviews <= MAX_REVIEWS_WARM:
        return "CIEPLY", f"Strona + tylko {reviews} opinii"

    return "POMIJAJ", ""   # well-established, skip


PRIORITY_ORDER = {"GORACY": 0, "CIEPLY": 1, "POMIJAJ": 99}


async def main():
    print("=" * 60)
    print("  Most Digital — Wroclaw Lead Collector")
    print(f"  {len(QUERIES)} kategorii x max {MAX_PER_QUERY} firm")
    print("  Filtr: brak strony LUB < 25 opinii na Google")
    print("=" * 60)

    all_biz: list[dict] = []
    seen: set[str] = set()

    for qi, query in enumerate(QUERIES, 1):
        print(f"\n[{qi:>2}/{len(QUERIES)}] '{query}'...")
        try:
            results = await scrape_google_maps(query, LOCATION, MAX_PER_QUERY)
        except Exception as e:
            print(f"  Blad: {e}")
            continue

        added = 0
        for biz in results:
            key = f"{biz['name'].lower()}|{biz['address'].lower()}"
            if key in seen or not biz["name"]:
                continue

            priorytet, powod = classify(biz)
            if priorytet == "POMIJAJ":
                continue   # skip well-established firms

            seen.add(key)
            biz["priorytet"] = priorytet
            biz["powod"]     = powod
            all_biz.append(biz)
            added += 1

        print(f"  +{added} leadow | lacznie: {len(all_biz)}")

    # Sort: GORACY first, then CIEPLY; within same priority by review count asc
    all_biz.sort(key=lambda b: (
        PRIORITY_ORDER.get(b.get("priorytet", "POMIJAJ"), 99),
        int(b.get("reviews", "0") or "0"),
    ))

    print(f"\n{'=' * 60}")
    print(f"  Znaleziono {len(all_biz)} leadow do obrobienia")
    gorące = sum(1 for b in all_biz if b.get("priorytet") == "GORACY")
    cieple = sum(1 for b in all_biz if b.get("priorytet") == "CIEPLY")
    print(f"  GORACY (brak strony):    {gorące}")
    print(f"  CIEPLY (malo opinii):    {cieple}")

    # Enrich: extract emails from sites where available
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

    # ── Sync to Supabase + master CSV ─────────────────────────
    print(f"\n  Synchronizuję z Supabase...")
    try:
        n_new = sync_leads(all_biz, city=LOCATION, source_query="wroclaw_batch")
        print(f"  Supabase: +{n_new} nowych leadów")
    except Exception as e:
        print(f"  Blad Supabase sync: {e}")
        n_new = 0

    # ── Distribute 108 leads to sellers ───────────────────────
    print(f"\n  Przydzielam leady sprzedawcom...")
    try:
        dist = distribute(dry_run=False)
        dist_count = dist.get("count", 0)
        print(f"  Przydzielono: {dist_count} leadów")
    except Exception as e:
        print(f"  Blad dystrybucji: {e}")
        dist_count = 0

    print(f"\n{'=' * 60}")
    print(f"  GOTOWE!")
    print(f"  Plik Excel:      {out}")
    print(f"  Firm scraped:    {len(all_biz)}")
    print(f"  Nowe w Supabase: {n_new}")
    print(f"  Przydzielono:    {dist_count}")
    print(f"  GORACY:          {gorące}")
    print(f"  CIEPLY:          {cieple}")
    print(f"  Z emailem:       {with_email}")
    print(f"  Z telefonem:     {with_phone}")
    print(f"{'=' * 60}")
    if not os.environ.get("CI"):
        input("\n  Nacisnij Enter zeby zamknac...")


if __name__ == "__main__":
    asyncio.run(main())

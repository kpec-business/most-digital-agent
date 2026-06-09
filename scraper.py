"""
Most Digital — Universal Lead Scraper
Reads CITIES env var (comma-separated region keys):
  wroclaw | lodz | wielkopolska | zielona_gora
Example: CITIES=wroclaw,lodz
"""
import asyncio
import os
import sys

if sys.stdout.encoding != "utf-8":
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

# Load .env (local dev)
try:
    _env_path = os.path.join(os.path.dirname(__file__), ".env")
    with open(_env_path) as _f:
        for _line in _f:
            _line = _line.strip()
            if _line and not _line.startswith("#") and "=" in _line:
                _k, _v = _line.split("=", 1)
                os.environ.setdefault(_k.strip(), _v.strip())
except FileNotFoundError:
    pass

from scrapers.maps import scrape_google_maps
from scrapers.website import extract_contacts
from output import save_to_excel
from supabase_sync import sync_leads

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

DISTRICT_NICHES = [
    "hydraulik",
    "elektryk",
    "firma remontowa",
    "malarz pokojowy",
    "sprzatanie",
]

# ── Region config ────────────────────────────────────────────────
# Each region: list of (city_ascii, districts_or_None)
# districts=None → BASE_QUERIES only
# districts=[...] → BASE_QUERIES + DISTRICT_NICHES × districts
REGIONS = {
    "wroclaw": {
        "label": "Wrocław / Dolnośląskie",
        "source": "wroclaw_batch",
        "cities": [
            ("Wroclaw", ["Krzyki", "Fabryczna", "Psie Pole", "Srodmiescie", "Stare Miasto"]),
        ],
    },
    "lodz": {
        "label": "Łódź / region łódzki",
        "source": "lodz_batch",
        "cities": [
            ("Lodz", ["Baluty", "Gorna", "Polesie", "Srodmiescie", "Widzew"]),
            ("Pabianice",            None),
            ("Zgierz",               None),
            ("Tomaszow Mazowiecki",  None),
            ("Piotrkow Trybunalski", None),
            ("Skierniewice",         None),
            ("Leczyce",              None),
            ("Kutno",                None),
            ("Radomsko",             None),
            ("Belchatow",            None),
            ("Sieradz",              None),
            ("Wielun",               None),
            ("Lowicz",               None),
            ("Zdunska Wola",         None),
            ("Opoczno",              None),
        ],
    },
    "wielkopolska": {
        "label": "Wielkopolska (Poznań)",
        "source": "wielkopolska_batch",
        "cities": [
            ("Poznan", ["Jezyce", "Grunwald", "Stare Miasto", "Nowe Miasto", "Wilda", "Rataje", "Piatkowo"]),
            ("Kalisz",              None),
            ("Konin",               None),
            ("Gniezno",             None),
            ("Ostrow Wielkopolski", None),
            ("Leszno",              None),
            ("Pila",                None),
            ("Szamotuly",           None),
            ("Jarocin",             None),
            ("Wagrowiec",           None),
            ("Koscian",             None),
            ("Srem",                None),
            ("Sroda Wielkopolska",  None),
            ("Turku Wielkopolski",  None),
            ("Kolo",                None),
            ("Chodziezs",           None),
        ],
    },
    "zielona_gora": {
        "label": "Lubuskie (Zielona Góra / Gorzów)",
        "source": "zielona_gora_batch",
        "cities": [
            ("Zielona Gora",       ["Srodmiescie", "Nowe Miasto", "Zacisze", "Stary Kisielin"]),
            ("Gorzow Wielkopolski", ["Srodmiescie", "Zawarcie", "Staszica", "Siedlice"]),
            ("Zary",               None),
            ("Zagan",              None),
            ("Nowa Sol",           None),
            ("Swiebodzin",         None),
            ("Krosno Odrzanskie",  None),
            ("Gubin",              None),
            ("Lubsko",             None),
            ("Szprotawa",          None),
            ("Zbaszynek",          None),
            ("Sulecin",            None),
            ("Slubice",            None),
            ("Wschowa",            None),
        ],
    },
}

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


async def scrape_city(city: str, queries: list, seen: set, all_biz: list, label: str):
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
    cities_env  = os.environ.get("CITIES", "wroclaw")
    region_keys = [k.strip() for k in cities_env.split(",") if k.strip()]

    print("=" * 62)
    print("  Most Digital — Universal Lead Scraper")
    print(f"  Regiony: {', '.join(region_keys)}")
    print("=" * 62)

    all_biz: list[dict] = []
    seen:    set[str]   = set()

    for region_key in region_keys:
        if region_key not in REGIONS:
            print(f"\n  [WARN] Nieznany region: '{region_key}' — pomijam")
            print(f"  Dostepne: {', '.join(REGIONS.keys())}")
            continue

        region = REGIONS[region_key]
        print(f"\n{'=' * 50}")
        print(f"  REGION: {region['label']}")
        print(f"{'=' * 50}")

        for city_name, districts in region["cities"]:
            if districts:
                queries = BASE_QUERIES + [
                    f"{niche} {district}"
                    for niche in DISTRICT_NICHES
                    for district in districts
                ]
            else:
                queries = BASE_QUERIES

            label = city_name[:3].upper()
            print(f"\n>>> {city_name.upper()} ({len(queries)} zapytan)")
            await scrape_city(city_name, queries, seen, all_biz, label)

    # ── Summary ───────────────────────────────────────────────
    all_biz.sort(key=lambda b: (
        PRIORITY_ORDER.get(b.get("priorytet", "POMIJAJ"), 99),
        int(b.get("reviews", "0") or "0"),
    ))

    gorące = sum(1 for b in all_biz if b.get("priorytet") == "GORACY")
    cieple = sum(1 for b in all_biz if b.get("priorytet") == "CIEPLY")

    print(f"\n{'=' * 62}")
    print(f"  Scraped: {len(all_biz)} leadow | GORACY: {gorące} | CIEPLY: {cieple}")

    # ── Enrich: extract emails ────────────────────────────────
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

    # ── Save Excel ────────────────────────────────────────────
    out = save_to_excel(all_biz)

    with_email = sum(1 for b in all_biz if b.get("email"))
    with_phone = sum(1 for b in all_biz if b.get("phone") or b.get("phone_site"))

    # ── Sync to Supabase ──────────────────────────────────────
    source = "_".join(region_keys) + "_batch"
    print(f"\n  Synchronizuje z Supabase...")
    try:
        n_new = sync_leads(all_biz, city=",".join(region_keys), source_query=source)
        print(f"  Supabase: +{n_new} nowych leadow")
    except Exception as e:
        print(f"  Blad sync: {e}")
        n_new = 0

    print(f"\n{'=' * 62}")
    print(f"  GOTOWE! Leady sa w bazie — teraz kliknij 'Dystrybuuj' w panelu admina.")
    print(f"  Plik Excel:      {out}")
    print(f"  Firm scraped:    {len(all_biz)}")
    print(f"  Nowe w Supabase: {n_new}")
    print(f"  GORACY:          {gorące}")
    print(f"  CIEPLY:          {cieple}")
    print(f"  Z emailem:       {with_email}")
    print(f"  Z telefonem:     {with_phone}")
    print(f"{'=' * 62}")

    if not os.environ.get("CI"):
        input("\n  Nacisnij Enter zeby zamknac...")


if __name__ == "__main__":
    asyncio.run(main())

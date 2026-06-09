"""
Most Digital — Scraper POLSKA
Uruchomienie: CITIES=wroclaw,lodz,mazowieckie,...  python -u scraper_pl.py
Dostepne regiony: wroclaw | lodz | wielkopolska | zielona_gora |
  mazowieckie | malopolskie | slaskie | pomorskie | kujawsko_pomorskie |
  warminsko_mazurskie | podlaskie | lubelskie | podkarpackie |
  swietokrzyskie | opolskie | zachodniopomorskie
"""
import asyncio
import os
import sys

if sys.stdout.encoding != "utf-8":
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

try:
    from pathlib import Path
    _env = Path(__file__).parent / ".env"
    if _env.exists():
        for _line in _env.read_text().splitlines():
            if "=" in _line and not _line.startswith("#"):
                _k, _v = _line.split("=", 1)
                os.environ.setdefault(_k.strip(), _v.strip())
except Exception:
    pass

from scraper_core import run_scraper

BASE_QUERIES = [
    # ── Budowlanka & Dom ──────────────────────────────────────────
    "hydraulik", "elektryk", "instalacje klimatyzacji",
    "instalacje solarne fotowoltaika", "firma remontowa",
    "stolarz na wymiar", "malarz pokojowy", "glazurnik kafelkarz",
    "sluszarz", "dekarz",
    # ── Sprzatanie & Logistyka ────────────────────────────────────
    "sprzatanie biur", "sprzatanie mieszkan",
    "przeprowadzki", "pranie tapicerek",
    # ── Serwis tech ──────────────────────────────────────────────
    "serwis komputerowy", "naprawa telefonow", "naprawa AGD",
    # ── Uroda & Cialo ─────────────────────────────────────────────
    "salon fryzjerski", "barber shop",
    "kosmetyczka salon urody", "paznokcie manicure salon",
    "gabinet masazu", "studio depilacji laser",
    "studio rzesy przedluzanie",
    # ── Zdrowie & Medycyna ────────────────────────────────────────
    "gabinet stomatologiczny klinika",
    "fizjoterapia rehabilitacja",
    "dietetyk poradnia",
    "centrum medyczne prywatne",
    # ── Fitness & Sport ───────────────────────────────────────────
    "klub fitness silownia",
    "trener personalny",
    "studio jogi pilates",
    "szkola tanca",
    "szkola sztuk walki",
    # ── Edukacja ─────────────────────────────────────────────────
    "szkola jezykowa", "nauka jazdy",
    "korepetycje",
    "przedszkole prywatne",
    # ── Motoryzacja ───────────────────────────────────────────────
    "warsztat samochodowy serwis",
    "auto detailing polerowanie",
    # ── Zwierzeta ─────────────────────────────────────────────────
    "klinika weterynaryjna",
    "groomer pielegnacja psow",
    "hotel dla zwierzat",
    # ── Events & Kreacja ──────────────────────────────────────────
    "fotograf slubny studio",
    "kamerzysta wideofilmowanie",
    "firma cateringowa",
    "dj muzyk weselny",
    # ── Projektowanie & Ogrod ─────────────────────────────────────
    "projektant wnetrz architekt",
    "firma ogrodnicza uslug ogrodniczych",
    # ── Uslugi profesjonalne ──────────────────────────────────────
    "uslugi ksiegowe biuro rachunkowe",
    "tlumacz przysiegy biuro tlumaczen",
    "fotograf",
    "tatuaz studio",
]

DISTRICT_NICHES = [
    # Remontowe
    "hydraulik", "elektryk", "firma remontowa", "malarz pokojowy",
    # Uslugowe
    "sprzatanie", "warsztat samochodowy",
    # Beauty & Health
    "salon fryzjerski", "kosmetyczka", "silownia fitness",
    "dentysta", "fizjoterapia",
    # Zwierzeta & Edukacja
    "weterynarz", "szkola jezykowa",
]

REGIONS = {
    "wroclaw": {
        "label": "Dolnośląskie (Wrocław)",
        "cities": [
            ("Wroclaw", ["Krzyki", "Fabryczna", "Psie Pole", "Srodmiescie", "Stare Miasto"]),
        ],
    },
    "lodz": {
        "label": "Łódźkie",
        "cities": [
            ("Lodz", ["Baluty", "Gorna", "Polesie", "Srodmiescie", "Widzew"]),
            ("Pabianice", None), ("Zgierz", None), ("Tomaszow Mazowiecki", None),
            ("Piotrkow Trybunalski", None), ("Skierniewice", None), ("Leczyce", None),
            ("Kutno", None), ("Radomsko", None), ("Belchatow", None),
            ("Sieradz", None), ("Wielun", None), ("Lowicz", None),
            ("Zdunska Wola", None), ("Opoczno", None),
        ],
    },
    "wielkopolska": {
        "label": "Wielkopolskie (Poznań)",
        "cities": [
            ("Poznan", ["Jezyce", "Grunwald", "Stare Miasto", "Nowe Miasto", "Wilda", "Rataje", "Piatkowo"]),
            ("Kalisz", None), ("Konin", None), ("Gniezno", None),
            ("Ostrow Wielkopolski", None), ("Leszno", None), ("Pila", None),
            ("Szamotuly", None), ("Jarocin", None), ("Wagrowiec", None),
            ("Koscian", None), ("Srem", None), ("Sroda Wielkopolska", None),
            ("Turek", None), ("Kolo", None), ("Chodzież", None),
        ],
    },
    "zielona_gora": {
        "label": "Lubuskie (Zielona Góra / Gorzów)",
        "cities": [
            ("Zielona Gora", ["Srodmiescie", "Nowe Miasto", "Zacisze", "Stary Kisielin"]),
            ("Gorzow Wielkopolski", ["Srodmiescie", "Zawarcie", "Staszica", "Siedlice"]),
            ("Zary", None), ("Zagan", None), ("Nowa Sol", None),
            ("Swiebodzin", None), ("Krosno Odrzanskie", None), ("Gubin", None),
            ("Lubsko", None), ("Szprotawa", None), ("Zbaszynek", None),
            ("Sulecin", None), ("Slubice", None), ("Wschowa", None),
        ],
    },
    "mazowieckie": {
        "label": "Mazowieckie (Warszawa)",
        "cities": [
            ("Warszawa", ["Srodmiescie", "Mokotow", "Wola", "Praga Polnoc",
                          "Praga Poludnie", "Ursynow", "Zoliborz", "Bemowo",
                          "Bielany", "Targowek"]),
            ("Radom", None), ("Plock", None), ("Siedlce", None),
            ("Ostroleka", None), ("Pruszkow", None), ("Legionowo", None),
            ("Wolomin", None), ("Minsk Mazowiecki", None), ("Zyrardow", None),
            ("Ciechanow", None), ("Piastow", None),
        ],
    },
    "malopolskie": {
        "label": "Małopolskie (Kraków)",
        "cities": [
            ("Krakow", ["Krowodrza", "Podgorze", "Nowa Huta", "Bronowice",
                        "Pradnik Czerwony", "Biezanow-Prokocim", "Debniki", "Zwierzyniec"]),
            ("Tarnow", None), ("Nowy Sacz", None), ("Oswiecim", None),
            ("Chrzanow", None), ("Olkusz", None), ("Nowy Targ", None),
            ("Wieliczka", None), ("Zakopane", None), ("Gorlice", None),
            ("Myslenice", None), ("Limanowa", None),
        ],
    },
    "slaskie": {
        "label": "Śląskie (Katowice / GOP)",
        "cities": [
            ("Katowice", ["Srodmiescie", "Ligota", "Koszutka", "Brynow", "Dab", "Szopienice"]),
            ("Gliwice", None), ("Zabrze", None), ("Bytom", None),
            ("Sosnowiec", None), ("Tychy", None), ("Rybnik", None),
            ("Bielsko-Biala", None), ("Czestochowa", None),
            ("Dabrowa Gornicza", None), ("Chorzow", None), ("Jaworzno", None),
            ("Siemianowice Slaskie", None), ("Myslowice", None),
        ],
    },
    "pomorskie": {
        "label": "Pomorskie (Trójmiasto)",
        "cities": [
            ("Gdansk", ["Srodmiescie", "Oliwa", "Wrzeszcz", "Morena", "Przymorze", "Nowy Port"]),
            ("Gdynia", None), ("Sopot", None), ("Slupsk", None),
            ("Starogard Gdanski", None), ("Tczew", None), ("Wejherowo", None),
            ("Pruszcz Gdanski", None), ("Koscierzyna", None),
            ("Chojnice", None), ("Malbork", None),
        ],
    },
    "kujawsko_pomorskie": {
        "label": "Kujawsko-Pomorskie (Bydgoszcz)",
        "cities": [
            ("Bydgoszcz", ["Srodmiescie", "Fordon", "Wyzyny", "Szwederowo", "Kapusciska"]),
            ("Torun", None), ("Wloclawek", None), ("Grudziadz", None),
            ("Inowroclaw", None), ("Naklo", None), ("Brodnica", None), ("Lipno", None),
        ],
    },
    "warminsko_mazurskie": {
        "label": "Warmińsko-Mazurskie (Olsztyn)",
        "cities": [
            ("Olsztyn", ["Srodmiescie", "Zatorze", "Jaroty", "Dajtki", "Nagory"]),
            ("Elblag", None), ("Elk", None), ("Ostróda", None),
            ("Gizycko", None), ("Ketrzyn", None), ("Szczytno", None),
            ("Bartoszyce", None), ("Ilawa", None), ("Lidzbark Warminski", None),
        ],
    },
    "podlaskie": {
        "label": "Podlaskie (Białystok)",
        "cities": [
            ("Bialystok", ["Srodmiescie", "Bojary", "Nowe Miasto", "Centrum", "Bagnowka"]),
            ("Suwalki", None), ("Lomza", None), ("Augustow", None),
            ("Zambrow", None), ("Hajnowka", None), ("Bielsk Podlaski", None),
        ],
    },
    "lubelskie": {
        "label": "Lubelskie (Lublin)",
        "cities": [
            ("Lublin", ["Srodmiescie", "Czuby", "Wieniawa", "Bronowice", "LSM", "Kalinowszczyzna"]),
            ("Zamosc", None), ("Chelm", None), ("Pulawy", None),
            ("Swidnik", None), ("Krasnik", None), ("Leczna", None),
            ("Biala Podlaska", None), ("Lubartow", None),
        ],
    },
    "podkarpackie": {
        "label": "Podkarpackie (Rzeszów)",
        "cities": [
            ("Rzeszow", ["Srodmiescie", "Drabinianka", "Biala", "Slocina", "Budziwoj"]),
            ("Przemysl", None), ("Stalowa Wola", None), ("Mielec", None),
            ("Tarnobrzeg", None), ("Krosno", None), ("Sanok", None),
            ("Jaroslaw", None), ("Debica", None), ("Lezajsk", None),
        ],
    },
    "swietokrzyskie": {
        "label": "Świętokrzyskie (Kielce)",
        "cities": [
            ("Kielce", ["Srodmiescie", "Bocianek", "Barwinek", "Ksm", "Czarnow"]),
            ("Skarzysko-Kamienna", None), ("Starachowice", None),
            ("Ostrowiec Swietokrzyski", None), ("Busko-Zdroj", None),
            ("Jedrzejow", None), ("Konskie", None), ("Wloszczowa", None),
        ],
    },
    "opolskie": {
        "label": "Opolskie (Opole)",
        "cities": [
            ("Opole", ["Srodmiescie", "Nowa Wies Krolewska", "Goslawice", "Zaodrze", "Malinka"]),
            ("Kedzierzyn-Kozle", None), ("Nysa", None), ("Brzeg", None),
            ("Kluczbork", None), ("Strzelce Opolskie", None),
            ("Prudnik", None), ("Namyslow", None),
        ],
    },
    "zachodniopomorskie": {
        "label": "Zachodniopomorskie (Szczecin)",
        "cities": [
            ("Szczecin", ["Srodmiescie", "Niebuszewo", "Pogodno", "Turzyn", "Drzetowo", "Nad Odra"]),
            ("Koszalin", None), ("Stargard", None), ("Kolobrzeg", None),
            ("Swinoujscie", None), ("Gryfino", None), ("Police", None),
            ("Goleniow", None), ("Szczecinek", None), ("Walcz", None),
        ],
    },
}

if __name__ == "__main__":
    cities_env  = os.environ.get("CITIES", "wroclaw")
    region_keys = [k.strip() for k in cities_env.split(",") if k.strip()]
    asyncio.run(run_scraper(
        region_keys  = region_keys,
        regions_config = REGIONS,
        base_queries   = BASE_QUERIES,
        district_niches = DISTRICT_NICHES,
        country        = "pl",
        label          = "Polska",
    ))

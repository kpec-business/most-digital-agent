"""
Most Digital — Scraper UNITED KINGDOM
CITIES=uk_london,uk_midlands,uk_north_west  python -u scraper_uk.py
Available regions:
  uk_london | uk_south_east | uk_south_west | uk_east_england |
  uk_midlands | uk_yorkshire | uk_north_west | uk_north_east |
  uk_scotland | uk_wales | uk_northern_ireland
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
    # ── Building & Home ───────────────────────────────────────────
    "plumber", "electrician", "air conditioning installation",
    "solar panels installation", "renovation company",
    "carpenter joinery", "painter decorator", "tiler",
    "locksmith", "roofer",
    # ── Cleaning & Logistics ──────────────────────────────────────
    "office cleaning company", "domestic cleaning service",
    "removal company", "upholstery carpet cleaning",
    # ── Tech Repair ───────────────────────────────────────────────
    "computer repair", "phone repair", "appliance repair",
    # ── Hair & Beauty ─────────────────────────────────────────────
    "hairdresser barbershop",
    "beauty salon nail bar",
    "eyelash extension studio",
    "massage therapy spa",
    "laser hair removal studio",
    # ── Health & Wellness ─────────────────────────────────────────
    "private dental clinic",
    "physiotherapy rehabilitation clinic",
    "nutritionist dietitian clinic",
    "private medical centre",
    # ── Fitness & Sport ───────────────────────────────────────────
    "gym fitness club",
    "personal trainer",
    "yoga pilates studio",
    "dance studio",
    "martial arts school",
    # ── Education ─────────────────────────────────────────────────
    "language school", "driving school",
    "private tutor tutoring",
    "private nursery day care",
    # ── Automotive ────────────────────────────────────────────────
    "car garage MOT service",
    "car detailing valeting",
    # ── Pets ──────────────────────────────────────────────────────
    "veterinary practice clinic",
    "dog grooming parlour",
    "pet boarding kennels",
    # ── Events & Creative ─────────────────────────────────────────
    "wedding photographer studio",
    "videographer wedding",
    "catering company events",
    "DJ wedding entertainment",
    # ── Design & Garden ───────────────────────────────────────────
    "interior designer decorator",
    "landscaping garden maintenance",
    # ── Professional Services ─────────────────────────────────────
    "accounting services bookkeeper",
    "certified translator interpreting",
    "tattoo studio",
    "photographer portrait",
]

DISTRICT_NICHES = [
    # Trades
    "plumber", "electrician", "renovation", "painter decorator",
    # Services
    "cleaning", "car garage",
    # Beauty & Health
    "hairdresser", "beauty salon", "gym fitness",
    "dentist", "physiotherapy",
    # Pets & Education
    "vet", "language school",
]

REGIONS = {
    "uk_london": {
        "label": "London",
        "cities": [
            ("London", ["Westminster", "Camden", "Islington", "Hackney",
                        "Tower Hamlets", "Southwark", "Lambeth", "Wandsworth",
                        "Hammersmith", "Ealing", "Brent", "Barnet", "Haringey",
                        "Lewisham", "Greenwich"]),
        ],
    },
    "uk_south_east": {
        "label": "South East England",
        "cities": [
            ("Brighton", None), ("Southampton", None), ("Oxford", None),
            ("Reading", None), ("Milton Keynes", None), ("Portsmouth", None),
            ("Guildford", None), ("Canterbury", None), ("Maidstone", None),
            ("Basingstoke", None), ("Crawley", None), ("Woking", None),
        ],
    },
    "uk_south_west": {
        "label": "South West England",
        "cities": [
            ("Bristol", ["Clifton", "Redland", "Bedminster", "Easton", "Fishponds"]),
            ("Plymouth", None), ("Exeter", None), ("Bath", None),
            ("Bournemouth", None), ("Swindon", None), ("Gloucester", None),
            ("Cheltenham", None), ("Salisbury", None), ("Taunton", None),
            ("Torquay", None), ("Truro", None),
        ],
    },
    "uk_east_england": {
        "label": "East of England",
        "cities": [
            ("Cambridge", None), ("Norwich", None), ("Ipswich", None),
            ("Luton", None), ("Peterborough", None), ("Colchester", None),
            ("Stevenage", None), ("Southend-on-Sea", None),
            ("Watford", None), ("Bedford", None), ("Chelmsford", None),
        ],
    },
    "uk_midlands": {
        "label": "Midlands",
        "cities": [
            ("Birmingham", ["City Centre", "Edgbaston", "Erdington",
                            "Hall Green", "Handsworth", "Moseley", "Northfield",
                            "Sutton Coldfield", "Yardley"]),
            ("Nottingham", None), ("Leicester", None), ("Derby", None),
            ("Coventry", None), ("Wolverhampton", None), ("Lincoln", None),
            ("Northampton", None), ("Stoke-on-Trent", None),
            ("Walsall", None), ("Dudley", None), ("Worcester", None),
            ("Shrewsbury", None), ("Hereford", None),
        ],
    },
    "uk_yorkshire": {
        "label": "Yorkshire & Humber",
        "cities": [
            ("Leeds", ["City Centre", "Headingley", "Chapel Allerton",
                       "Beeston", "Morley", "Horsforth", "Roundhay"]),
            ("Sheffield", None), ("Bradford", None), ("Hull", None),
            ("York", None), ("Doncaster", None), ("Wakefield", None),
            ("Huddersfield", None), ("Harrogate", None), ("Barnsley", None),
        ],
    },
    "uk_north_west": {
        "label": "North West England",
        "cities": [
            ("Manchester", ["City Centre", "Didsbury", "Chorlton",
                            "Salford", "Trafford", "Rusholme", "Levenshulme"]),
            ("Liverpool", None), ("Bolton", None), ("Stockport", None),
            ("Blackpool", None), ("Preston", None), ("Wigan", None),
            ("Warrington", None), ("Chester", None), ("Blackburn", None),
            ("Burnley", None), ("Carlisle", None),
        ],
    },
    "uk_north_east": {
        "label": "North East England",
        "cities": [
            ("Newcastle upon Tyne", ["City Centre", "Jesmond", "Gosforth",
                                      "Byker", "Walker", "Fenham"]),
            ("Sunderland", None), ("Middlesbrough", None),
            ("Gateshead", None), ("Durham", None), ("Hartlepool", None),
            ("Darlington", None), ("Stockton-on-Tees", None),
        ],
    },
    "uk_scotland": {
        "label": "Scotland",
        "cities": [
            ("Glasgow", ["City Centre", "West End", "South Side",
                         "East End", "Govan", "Partick", "Shawlands"]),
            ("Edinburgh", None), ("Aberdeen", None), ("Dundee", None),
            ("Inverness", None), ("Stirling", None), ("Perth", None),
            ("Falkirk", None), ("Livingston", None), ("Ayr", None),
        ],
    },
    "uk_wales": {
        "label": "Wales",
        "cities": [
            ("Cardiff", ["City Centre", "Canton", "Roath", "Pontprennau",
                         "Grangetown", "Splott"]),
            ("Swansea", None), ("Newport", None), ("Wrexham", None),
            ("Bridgend", None), ("Barry", None), ("Rhondda", None),
            ("Merthyr Tydfil", None), ("Caerphilly", None),
        ],
    },
    "uk_northern_ireland": {
        "label": "Northern Ireland",
        "cities": [
            ("Belfast", ["City Centre", "South Belfast", "North Belfast",
                         "East Belfast", "West Belfast", "Lisburn Road"]),
            ("Derry", None), ("Lisburn", None), ("Newry", None),
            ("Armagh", None), ("Bangor", None), ("Antrim", None),
        ],
    },
}

if __name__ == "__main__":
    cities_env  = os.environ.get("CITIES", "uk_london")
    region_keys = [k.strip() for k in cities_env.split(",") if k.strip()]
    asyncio.run(run_scraper(
        region_keys    = region_keys,
        regions_config = REGIONS,
        base_queries   = BASE_QUERIES,
        district_niches = DISTRICT_NICHES,
        country        = "uk",
        label          = "United Kingdom",
    ))

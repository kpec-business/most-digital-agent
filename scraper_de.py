"""
Most Digital — Scraper DEUTSCHLAND
CITIES=de_berlin,de_nrw,de_bayern  python -u scraper_de.py
Verfuegbare Regionen:
  de_nrw | de_bayern | de_bw | de_berlin | de_hamburg |
  de_sachsen | de_niedersachsen | de_hessen | de_rheinland_pfalz |
  de_schleswig_holstein | de_thueringen | de_sachsen_anhalt |
  de_mecklenburg | de_saarland | de_bremen | de_brandenburg
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
    "Klempner Sanitaer", "Elektriker", "Klimaanlage Installation",
    "Solaranlage Photovoltaik", "Renovierungsunternehmen",
    "Schreiner Tischler", "Maler Lackierer", "Fliesenleger",
    "Schlosser", "Dachdecker", "Bueroreinigung", "Wohnungsreinigung",
    "Umzugsunternehmen", "Polsterreinigung", "Computerreparatur",
    "Handyreparatur", "Haushaltsgeraete Reparatur", "Sprachschule",
    "Nachhilfe", "Fahrschule", "Massagesalon", "Kosmetikstudio",
    "Tattoostudio", "Fotograf", "Steuerberater Buchhalter", "Uebersetzungsbuero",
]

DISTRICT_NICHES = [
    "Klempner", "Elektriker", "Renovierung", "Maler", "Reinigung",
]

REGIONS = {
    "de_nrw": {
        "label": "Nordrhein-Westfalen",
        "cities": [
            ("Koeln", ["Innenstadt", "Ehrenfeld", "Nippes", "Muengersdorf",
                       "Kalk", "Porz", "Chorweiler", "Rodenkirchen"]),
            ("Duesseldorf", None), ("Dortmund", None), ("Essen", None),
            ("Duisburg", None), ("Bochum", None), ("Wuppertal", None),
            ("Bielefeld", None), ("Bonn", None), ("Muenster", None),
            ("Gelsenkirchen", None), ("Aachen", None), ("Krefeld", None),
            ("Oberhausen", None), ("Hagen", None), ("Hamm", None),
        ],
    },
    "de_bayern": {
        "label": "Bayern (München)",
        "cities": [
            ("Muenchen", ["Schwabing", "Maxvorstadt", "Bogenhausen",
                          "Sendling", "Neuhausen", "Haidhausen",
                          "Giesing", "Pasing", "Riem"]),
            ("Nuernberg", None), ("Augsburg", None), ("Regensburg", None),
            ("Wuerzburg", None), ("Fuerth", None), ("Erlangen", None),
            ("Landshut", None), ("Ingolstadt", None), ("Rosenheim", None),
            ("Kempten", None), ("Bamberg", None),
        ],
    },
    "de_bw": {
        "label": "Baden-Württemberg (Stuttgart)",
        "cities": [
            ("Stuttgart", ["Stadtmitte", "Bad Cannstatt", "Zuffenhausen",
                           "Moehringen", "Vaihingen", "Weilimdorf", "Feuerbach"]),
            ("Karlsruhe", None), ("Mannheim", None), ("Freiburg im Breisgau", None),
            ("Heidelberg", None), ("Ulm", None), ("Heilbronn", None),
            ("Pforzheim", None), ("Reutlingen", None), ("Tuebingen", None),
            ("Konstanz", None), ("Villingen-Schwenningen", None),
        ],
    },
    "de_berlin": {
        "label": "Berlin",
        "cities": [
            ("Berlin", ["Mitte", "Prenzlauer Berg", "Friedrichshain",
                        "Kreuzberg", "Charlottenburg", "Neukoelln",
                        "Spandau", "Tempelhof", "Lichtenberg",
                        "Reinickendorf", "Treptow", "Marzahn"]),
        ],
    },
    "de_hamburg": {
        "label": "Hamburg",
        "cities": [
            ("Hamburg", ["Altona", "Eimsbuettel", "Hamburg-Mitte",
                         "Hamburg-Nord", "Wandsbek", "Bergedorf", "Harburg"]),
            ("Luebeck", None), ("Norderstedt", None), ("Ahrensburg", None),
        ],
    },
    "de_sachsen": {
        "label": "Sachsen (Dresden / Leipzig)",
        "cities": [
            ("Dresden", ["Altstadt", "Neustadt", "Prohlis", "Pieschen",
                         "Leuben", "Plauen", "Cotta"]),
            ("Leipzig", None), ("Chemnitz", None), ("Zwickau", None),
            ("Goerlitz", None), ("Plauen", None), ("Meissen", None),
        ],
    },
    "de_niedersachsen": {
        "label": "Niedersachsen (Hannover)",
        "cities": [
            ("Hannover", ["Mitte", "Linden", "Vahrenwald", "Kirchrode",
                          "Bothfeld", "Ricklingen", "Misburg"]),
            ("Braunschweig", None), ("Osnabrueck", None), ("Oldenburg", None),
            ("Wolfsburg", None), ("Goettingen", None), ("Hildesheim", None),
            ("Salzgitter", None), ("Wilhelmshaven", None),
        ],
    },
    "de_hessen": {
        "label": "Hessen (Frankfurt)",
        "cities": [
            ("Frankfurt am Main", ["Innenstadt", "Sachsenhausen", "Bockenheim",
                                   "Bornheim", "Nordend", "Gallus", "Niederrad"]),
            ("Wiesbaden", None), ("Kassel", None), ("Darmstadt", None),
            ("Offenbach", None), ("Hanau", None), ("Giessen", None),
            ("Fulda", None), ("Marburg", None),
        ],
    },
    "de_rheinland_pfalz": {
        "label": "Rheinland-Pfalz (Mainz)",
        "cities": [
            ("Mainz", ["Altstadt", "Neustadt", "Hartenberg", "Mombach", "Bretzenheim"]),
            ("Ludwigshafen", None), ("Koblenz", None), ("Trier", None),
            ("Kaiserslautern", None), ("Worms", None), ("Neuwied", None),
            ("Bad Kreuznach", None),
        ],
    },
    "de_schleswig_holstein": {
        "label": "Schleswig-Holstein (Kiel)",
        "cities": [
            ("Kiel", ["Innenstadt", "Gaarden", "Russee", "Mettenhof", "Ellerbek"]),
            ("Luebeck", None), ("Flensburg", None), ("Neumuenster", None),
            ("Norderstedt", None), ("Neumunster", None), ("Heide", None),
        ],
    },
    "de_thueringen": {
        "label": "Thüringen (Erfurt)",
        "cities": [
            ("Erfurt", ["Altstadt", "Krämpfervorstadt", "Daberstedt", "Südost", "Gispersleben"]),
            ("Jena", None), ("Gera", None), ("Weimar", None),
            ("Gotha", None), ("Eisenach", None), ("Nordhausen", None),
        ],
    },
    "de_sachsen_anhalt": {
        "label": "Sachsen-Anhalt (Magdeburg)",
        "cities": [
            ("Magdeburg", ["Altstadt", "Sudenburg", "Buckau", "Stadtfeld", "Neue Neustadt"]),
            ("Halle Saale", None), ("Dessau-Rosslau", None),
            ("Wittenberg", None), ("Stendal", None), ("Bernburg", None),
        ],
    },
    "de_mecklenburg": {
        "label": "Mecklenburg-Vorpommern (Rostock)",
        "cities": [
            ("Rostock", ["Stadtmitte", "Kröpeliner-Tor-Vorstadt", "Lichtenhagen",
                         "Evershagen", "Dierkow", "Reutershagen"]),
            ("Schwerin", None), ("Greifswald", None), ("Stralsund", None),
            ("Neubrandenburg", None), ("Wismar", None),
        ],
    },
    "de_saarland": {
        "label": "Saarland (Saarbrücken)",
        "cities": [
            ("Saarbruecken", ["Alt-Saarbruecken", "St. Johann", "Burbach", "Dudweiler"]),
            ("Neunkirchen", None), ("Homburg", None), ("Merzig", None),
            ("St. Ingbert", None), ("Voelklingen", None),
        ],
    },
    "de_bremen": {
        "label": "Bremen",
        "cities": [
            ("Bremen", ["Mitte", "Neustadt", "Schwachhausen", "Walle",
                        "Findorff", "Horn-Lehe", "Hemelingen"]),
            ("Bremerhaven", None),
        ],
    },
    "de_brandenburg": {
        "label": "Brandenburg (Potsdam)",
        "cities": [
            ("Potsdam", ["Innenstadt", "Babelsberg", "Drewitz", "Golm", "Sacrow"]),
            ("Cottbus", None), ("Frankfurt Oder", None),
            ("Brandenburg an der Havel", None), ("Oranienburg", None),
            ("Eberswalde", None),
        ],
    },
}

if __name__ == "__main__":
    cities_env  = os.environ.get("CITIES", "de_berlin")
    region_keys = [k.strip() for k in cities_env.split(",") if k.strip()]
    asyncio.run(run_scraper(
        region_keys    = region_keys,
        regions_config = REGIONS,
        base_queries   = BASE_QUERIES,
        district_niches = DISTRICT_NICHES,
        country        = "de",
        label          = "Deutschland",
    ))

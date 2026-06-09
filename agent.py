"""
Most Digital — Agent pozyskiwania leadów

Użycie:
  python agent.py --query "restauracja" --location "Warszawa" --max 30
  python agent.py --query "salon urody" --location "Kraków" --max 50
  python agent.py --query "sklep meblowy" --max 40          (cała Polska)

Wynik: plik Excel na Pulpicie z kontaktami (nazwa, adres, tel, email, strona).
"""
import asyncio
import argparse
import sys

# Fix Polish characters in Windows console
if sys.stdout.encoding != "utf-8":
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
from scrapers.maps import scrape_google_maps
from scrapers.website import extract_contacts
from output import save_to_excel


async def run(query: str, location: str, max_results: int, output: str | None):
    print(f"\n{'='*55}")
    print(f"  Most Digital — Agent Leadów")
    print(f"{'='*55}")
    print(f"  Szukam: '{query}' | Lokalizacja: '{location or 'cała Polska'}'")
    print(f"  Cel: {max_results} firm\n")

    # ── 1. Google Maps ────────────────────────────────────────────────────────
    print("[1/3] Scrapuję Google Maps...")
    businesses = await scrape_google_maps(query, location, max_results)
    print(f"      Znaleziono {len(businesses)} firm\n")

    if not businesses:
        print("Brak wyników. Spróbuj zmienić zapytanie lub lokalizację.")
        sys.exit(1)

    # ── 2. Enrichment — email z www ───────────────────────────────────────────
    with_website = [b for b in businesses if b.get("website")]
    print(f"[2/3] Wyciągam emaile ze stron www ({len(with_website)} firm ma stronę)...")

    for i, biz in enumerate(businesses):
        if not biz.get("website"):
            continue
        try:
            contacts = extract_contacts(biz["website"])
            biz.update(contacts)
            status = f"email: {contacts['email']}" if contacts["email"] else "brak emaila"
            print(f"      [{i+1}/{len(businesses)}] {biz['name'][:35]:<35} {status}")
        except Exception as e:
            print(f"      [{i+1}/{len(businesses)}] {biz['name'][:35]:<35} blad: {e}")

    # ── 3. Zapis do Excel ─────────────────────────────────────────────────────
    print(f"\n[3/3] Zapisuję do Excela...")
    out_path = save_to_excel(businesses, output)

    # Stats
    with_email   = sum(1 for b in businesses if b.get("email"))
    with_phone   = sum(1 for b in businesses if b.get("phone") or b.get("phone_site"))
    with_website = sum(1 for b in businesses if b.get("website"))

    print(f"\n{'='*55}")
    print(f"  Gotowe! Plik: {out_path}")
    print(f"  Firmy:    {len(businesses)}")
    print(f"  Z email:  {with_email}")
    print(f"  Z tel.:   {with_phone}")
    print(f"  Ze stroną: {with_website}")
    print(f"{'='*55}\n")


def main():
    parser = argparse.ArgumentParser(
        description="Most Digital — agent do pozyskiwania leadów lokalnych firm"
    )
    parser.add_argument("--query",    required=True,  help='Typ firmy, np. "restauracja"')
    parser.add_argument("--location", default="",     help='Miasto, np. "Warszawa" (opcjonalne)')
    parser.add_argument("--max",      type=int, default=30, help="Maks. liczba firm (domyślnie 30)")
    parser.add_argument("--output",   default=None,   help="Ścieżka pliku .xlsx (opcjonalne)")
    args = parser.parse_args()

    asyncio.run(run(args.query, args.location, args.max, args.output))


if __name__ == "__main__":
    main()

"""
Most Digital — Weekly Lead Distributor
Assigns WEEKLY_TARGET leads equally among active sellers.
Run every Monday (or after a scraping session).

Usage:
  python distribute.py
  python distribute.py --dry-run    (preview without writing)
"""
import datetime
import os
import sys
from pathlib import Path
from supabase import create_client

_env = Path(__file__).parent / ".env"
if _env.exists():
    for _line in _env.read_text().splitlines():
        if "=" in _line and not _line.startswith("#"):
            _k, _v = _line.split("=", 1)
            os.environ.setdefault(_k.strip(), _v.strip())

SUPABASE_URL         = os.environ.get("SUPABASE_URL",         "")
SUPABASE_SERVICE_KEY = os.environ.get("SUPABASE_SERVICE_KEY", "")
WEEKLY_TARGET        = 108

if sys.stdout.encoding != "utf-8":
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")


def get_monday() -> datetime.date:
    today = datetime.date.today()
    return today - datetime.timedelta(days=today.weekday())


def distribute(dry_run: bool = False) -> dict:
    sb = create_client(SUPABASE_URL, SUPABASE_SERVICE_KEY)
    week_start = get_monday()
    week_str   = week_start.isoformat()

    print(f"{'='*55}")
    print(f"  Most Digital — Dystrybucja leadów")
    print(f"  Tydzień: {week_str}  |  Cel: {WEEKLY_TARGET}")
    print(f"  Tryb: {'PODGLĄD (dry-run)' if dry_run else 'ZAPIS'}")
    print(f"{'='*55}")

    # ── Sellers ───────────────────────────────────────────────
    sellers_resp = sb.table("profiles").select("id, full_name").eq("role", "seller").execute()
    sellers = sellers_resp.data or []
    if not sellers:
        print("  BRAK aktywnych sprzedawców!")
        return {"error": "no sellers"}

    n_sellers    = len(sellers)
    per_seller   = WEEKLY_TARGET // n_sellers
    remainder    = WEEKLY_TARGET % n_sellers
    print(f"\n  Sprzedawcy: {n_sellers}  |  Na osobę: {per_seller}  (+1 dla pierwszych {remainder})")

    # ── Already assigned this week ────────────────────────────
    week_resp     = sb.table("lead_assignments").select("lead_id").eq("week_start", week_str).execute()
    this_week_ids = {r["lead_id"] for r in (week_resp.data or [])}
    if this_week_ids:
        print(f"\n  Już przydzielono w tym tygodniu: {len(this_week_ids)} leadów")

    # ── Permanently excluded: leads that were TOUCHED (status != nowy) ───────
    # Untouched leads (status=nowy from past weeks) return to the recycling pool
    touched_resp     = sb.table("lead_assignments").select("lead_id").neq("status", "nowy").execute()
    touched_ids      = {r["lead_id"] for r in (touched_resp.data or [])}
    exclude_ids      = list(touched_ids | this_week_ids)

    # ── Fetch pool: leads not touched and not assigned this week ─────────────
    query = sb.table("leads").select("id, name, priorytet")
    if exclude_ids:
        query = query.not_.in_("id", exclude_ids)

    pool_resp = query.execute()
    pool = pool_resp.data or []

    # Sort: GORACY first, then CIEPLY
    pool.sort(key=lambda l: (0 if l.get("priorytet") == "GORACY" else 1))

    available = len(pool)
    needed    = WEEKLY_TARGET
    print(f"\n  Dostępnych nowych leadów: {available}")

    if available == 0:
        print("\n  BRAK nowych leadów do przydzielenia — uruchom agenta scrapującego!")
        return {"error": "no leads"}

    if available < needed:
        print(f"\n  Uwaga: mniej leadów ({available}) niż cel ({needed}) — przydzielam ile jest")
        needed = available

    # ── Distribute ────────────────────────────────────────────
    assignments = []
    idx = 0
    for i, seller in enumerate(sellers):
        count = per_seller + (1 if i < remainder else 0)
        count = min(count, needed - idx)  # don't exceed available
        if count <= 0:
            break
        batch = pool[idx: idx + count]
        idx  += count
        for lead in batch:
            assignments.append({
                "lead_id":     lead["id"],
                "employee_id": seller["id"],
                "status":      "nowy",
                "week_start":  week_str,
            })
        goracy = sum(1 for l in batch if l.get("priorytet") == "GORACY")
        print(f"  {seller['full_name']:<25} {len(batch)} leadów  (GORĄCYCH: {goracy})")

    print(f"\n  Razem do przydzielenia: {len(assignments)}")

    if dry_run:
        print("\n  [DRY-RUN] Brak zapisu do bazy.")
        return {"dry_run": True, "count": len(assignments)}

    if assignments:
        # Insert in batches
        for i in range(0, len(assignments), 200):
            sb.table("lead_assignments").insert(assignments[i:i+200]).execute()
        print(f"\n  Zapisano {len(assignments)} przydziałów do Supabase.")

    return {"week": week_str, "count": len(assignments), "sellers": n_sellers}


if __name__ == "__main__":
    dry = "--dry-run" in sys.argv
    result = distribute(dry_run=dry)
    if "error" not in result:
        print(f"\n{'='*55}")
        print(f"  GOTOWE — tydzień {result.get('week')}")
        print(f"  Przydzielono: {result.get('count')} leadów")
        print(f"{'='*55}")
    if not os.environ.get("CI"):
        input("\n  Naciśnij Enter żeby zamknąć...")

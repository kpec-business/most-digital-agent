"""
Synchronizes scraped leads with Supabase and the local master CSV.
Uses service role key — bypasses RLS for inserts.
"""
import csv
import os
import sys
from pathlib import Path
from supabase import create_client, Client

_env = Path(__file__).parent / ".env"
if _env.exists():
    for _line in _env.read_text().splitlines():
        if "=" in _line and not _line.startswith("#"):
            _k, _v = _line.split("=", 1)
            os.environ.setdefault(_k.strip(), _v.strip())

SUPABASE_URL         = os.environ.get("SUPABASE_URL",         "")
SUPABASE_SERVICE_KEY = os.environ.get("SUPABASE_SERVICE_KEY", "")

MASTER_CSV = os.path.join(os.path.dirname(__file__), "master_leads.csv")

CSV_FIELDS = [
    "name", "category", "address", "phone", "email",
    "website", "rating", "reviews", "priorytet", "powod",
    "city", "source_query",
]

_sb: Client | None = None


def _client() -> Client:
    global _sb
    if _sb is None:
        _sb = create_client(SUPABASE_URL, SUPABASE_SERVICE_KEY)
    return _sb


def sync_leads(leads: list[dict], city: str = "", source_query: str = "",
               country: str = "pl") -> int:
    """
    Insert new leads into Supabase and append to master CSV.
    country: 'pl' | 'uk' | 'de'
    Returns number of records sent to Supabase.
    """
    if not leads:
        return 0

    sb = _client()

    # Fetch existing (name, address) pairs from Supabase to deduplicate
    existing_resp = sb.table("leads").select("name, address").execute()
    existing_keys = {
        f"{r['name'].lower().strip()}|{(r['address'] or '').lower().strip()}"
        for r in (existing_resp.data or [])
    }

    records = []
    for lead in leads:
        key = f"{lead.get('name','').lower().strip()}|{lead.get('address','').lower().strip()}"
        if not lead.get("name") or key in existing_keys:
            continue
        existing_keys.add(key)
        records.append({
            "name":         lead.get("name", ""),
            "category":     lead.get("category", ""),
            "address":      lead.get("address", ""),
            "phone":        lead.get("phone", ""),
            "email":        lead.get("email", ""),
            "website":      lead.get("website", ""),
            "rating":       lead.get("rating", ""),
            "reviews":      _safe_int(lead.get("reviews")),
            "priorytet":    lead.get("priorytet", ""),
            "powod":        lead.get("powod", ""),
            "city":         city or lead.get("city", ""),
            "source_query": source_query or lead.get("source_query", ""),
            "country":      country,
        })

    if records:
        # Insert in batches of 200
        for i in range(0, len(records), 200):
            batch = records[i:i + 200]
            sb.table("leads").insert(batch).execute()

    # Append to master CSV (also deduplicated)
    _append_csv(records)

    return len(records)


def _append_csv(records: list[dict]):
    if not records:
        return
    write_header = not os.path.exists(MASTER_CSV)
    with open(MASTER_CSV, "a", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=CSV_FIELDS, extrasaction="ignore")
        if write_header:
            writer.writeheader()
        writer.writerows(records)
    print(f"  CSV: +{len(records)} nowych leadów → {MASTER_CSV}")


def _safe_int(val) -> int | None:
    try:
        return int(val) if val not in (None, "", "0") else None
    except (ValueError, TypeError):
        return None


def total_leads_in_db() -> int:
    sb = _client()
    resp = sb.table("leads").select("id", count="exact").execute()
    return resp.count or 0


def unassigned_count() -> int:
    """Leads not yet in lead_assignments."""
    sb = _client()
    assigned = sb.table("lead_assignments").select("lead_id").execute()
    assigned_ids = [r["lead_id"] for r in (assigned.data or [])]
    if not assigned_ids:
        return total_leads_in_db()
    resp = (
        sb.table("leads")
        .select("id", count="exact")
        .not_.in_("id", assigned_ids)
        .execute()
    )
    return resp.count or 0

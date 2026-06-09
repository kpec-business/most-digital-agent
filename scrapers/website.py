"""
Extracts email addresses and phone numbers from a business website.
Checks the homepage and common contact pages (/kontakt, /contact, /o-nas).
"""
import re
import requests
from urllib.parse import urljoin, urlparse
from bs4 import BeautifulSoup

EMAIL_RE = re.compile(r"[a-zA-Z0-9._%+\-]+@[a-zA-Z0-9.\-]+\.[a-zA-Z]{2,}")
PHONE_RE = re.compile(r"(?:\+48[\s\-]?)?(?:\d[\s\-]?){9,11}")

CONTACT_PATHS = ["/kontakt", "/contact", "/o-nas", "/about", "/firma", "/napisz-do-nas"]

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/124.0.0.0 Safari/537.36"
    ),
    "Accept-Language": "pl-PL,pl;q=0.9",
}

_IGNORED_EMAIL_DOMAINS = {"example.com", "sentry.io", "gmail.com", "wp.pl", "onet.pl"}


def extract_contacts(url: str, timeout: int = 8) -> dict:
    """Return {'email': str, 'phone_site': str} for the given URL."""
    if not url:
        return {"email": "", "phone_site": ""}

    if not url.startswith("http"):
        url = "https://" + url

    emails: set[str] = set()
    phones: set[str] = set()

    pages_to_check = [url] + [urljoin(url, p) for p in CONTACT_PATHS]

    for page_url in pages_to_check:
        try:
            resp = requests.get(page_url, headers=HEADERS, timeout=timeout, allow_redirects=True)
            if resp.status_code != 200:
                continue
            soup = BeautifulSoup(resp.text, "html.parser")

            # mailto links are most reliable
            for a in soup.find_all("a", href=True):
                href = a["href"]
                if href.startswith("mailto:"):
                    email = href[7:].split("?")[0].strip().lower()
                    if email and _valid_email(email):
                        emails.add(email)
                if href.startswith("tel:"):
                    ph = re.sub(r"[^\d+]", "", href[4:])
                    if len(ph) >= 9:
                        phones.add(_format_phone(ph))

            # Fallback: scan visible text
            text = soup.get_text(" ")
            for m in EMAIL_RE.findall(text):
                if _valid_email(m.lower()):
                    emails.add(m.lower())

            if emails:
                break  # got what we need, stop early

        except Exception:
            continue

    best_email = sorted(emails)[0] if emails else ""
    best_phone = sorted(phones, key=len)[0] if phones else ""

    return {"email": best_email, "phone_site": best_phone}


def _valid_email(email: str) -> bool:
    domain = email.split("@")[-1]
    if domain in _IGNORED_EMAIL_DOMAINS:
        return False
    if any(kw in email for kw in ("wpcf7", "noreply", "no-reply", "example", "test@", "your@")):
        return False
    return bool(EMAIL_RE.match(email))


def _format_phone(raw: str) -> str:
    raw = raw.lstrip("+")
    if raw.startswith("48") and len(raw) == 11:
        raw = raw[2:]
    if len(raw) == 9:
        return f"+48 {raw[:3]} {raw[3:6]} {raw[6:]}"
    return "+" + raw

#!/usr/bin/env python3
from __future__ import annotations

import hashlib
import json
import re
from pathlib import Path
from urllib.parse import urljoin

import pdfplumber
import requests
from bs4 import BeautifulSoup

ROOT = Path(__file__).resolve().parent
PLAN_URL = "https://arch.pk.edu.pl/dziekanat/plan-zajec/"
TARGET_TEXT = "Year 1/II: Semester 1 – M.D. in English"
STATE_FILE = ROOT / "source-state.json"
TEXT_FILE = ROOT / "latest_schedule.txt"
TABLE_FILE = ROOT / "latest_tables.json"

HEADERS = {
    "User-Agent": "Mozilla/5.0 (compatible; pk-architecture-calendar/1.0; +https://github.com/jay-max-c/pk-architecture-calendar)"
}

def sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()

def fetch(url: str) -> bytes:
    r = requests.get(url, headers=HEADERS, timeout=45)
    r.raise_for_status()
    return r.content

def find_target_pdf(page_html: bytes) -> str:
    """Resolve ONLY Year 1 / Semester 1 / second-cycle English timetable.

    The timetable index also contains Year 2 / Semester 3 M.D. in English.
    Never select by the generic phrase "M.D. in English".
    """
    soup = BeautifulSoup(page_html, "html.parser")
    exact = []

    for a in soup.find_all("a", href=True):
        label = " ".join(a.stripped_strings)
        href = urljoin(PLAN_URL, a["href"])
        norm = re.sub(r"\\s+", " ", label).strip().lower()

        # Current page label:
        # "Year 1/II: Semester 1 – M.D. in English"
        if (
            "year 1/ii" in norm
            and "semester 1" in norm
            and "m.d. in english" in norm
            and ".pdf" in href.lower()
        ):
            exact.append(href)

    if len(exact) != 1:
        raise RuntimeError(
            "Safety stop: expected exactly one Year 1/II Semester 1 M.D. in English PDF, "
            f"found {len(exact)}: {exact}"
        )

    pdf_url = exact[0]

    # Additional filename-level safety. This prevents accidental Year-2/semester-3 ingestion.
    low = pdf_url.lower()
    bad = ("rok_2" in low or "sem_3" in low or "semester_3" in low)
    good = (
        ("rok_1" in low and ("sem_1" in low or "semestr_1" in low))
        or ("st_2" in low and "semestr_1" in low)
    )
    if bad or not good:
        raise RuntimeError(f"Safety stop: resolved suspicious timetable URL: {pdf_url}")

    return pdf_url

def extract_pdf(pdf_bytes: bytes):
    tmp = ROOT / ".latest_schedule.pdf"
    tmp.write_bytes(pdf_bytes)
    pages_text = []
    all_tables = []
    try:
        with pdfplumber.open(tmp) as pdf:
            for i, page in enumerate(pdf.pages, start=1):
                text = page.extract_text(x_tolerance=1, y_tolerance=3, layout=True) or ""
                pages_text.append(f"===== PAGE {i} =====\n{text.rstrip()}\n")
                tables = page.extract_tables()
                all_tables.append({"page": i, "tables": tables})
    finally:
        tmp.unlink(missing_ok=True)
    return "\n".join(pages_text).strip() + "\n", all_tables

def main():
    page = fetch(PLAN_URL)
    pdf_url = find_target_pdf(page)
    pdf = fetch(pdf_url)
    text, tables = extract_pdf(pdf)

    # Semantic safety check: the downloaded PDF itself must identify Year 1 / Semester I.
    upper = text.upper()
    if "SEMESTER I YEAR 1 MASTER" not in upper:
        raise RuntimeError(
            "Safety stop: downloaded PDF is not Semester I / Year 1 Master's Degree Studies."
        )
    if "SEMESTER III YEAR 2 MASTER" in upper:
        raise RuntimeError(
            "Safety stop: Year 2 / Semester III timetable was downloaded by mistake."
        )

    previous = {}
    if STATE_FILE.exists():
        try:
            previous = json.loads(STATE_FILE.read_text(encoding="utf-8"))
        except Exception:
            previous = {}

    state = {
        "source_page": PLAN_URL,
        "pdf_url": pdf_url,
        "pdf_sha256": sha256_bytes(pdf),
        "previous_pdf_sha256": previous.get("pdf_sha256"),
        "changed": previous.get("pdf_sha256") != sha256_bytes(pdf),
    }

    TEXT_FILE.write_text(
        f"Official source: {pdf_url}\n"
        f"PDF SHA256: {state['pdf_sha256']}\n\n"
        + text,
        encoding="utf-8",
    )
    TABLE_FILE.write_text(json.dumps(tables, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    STATE_FILE.write_text(json.dumps(state, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    print(json.dumps(state, ensure_ascii=False, indent=2))

if __name__ == "__main__":
    main()

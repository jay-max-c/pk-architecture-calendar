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
TARGET_TEXT = "M.D. in English"
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
    soup = BeautifulSoup(page_html, "html.parser")
    candidates = []
    for a in soup.find_all("a", href=True):
        label = " ".join(a.stripped_strings)
        href = a["href"]
        parent_text = " ".join(a.parent.stripped_strings) if a.parent else label
        context = f"{label} {parent_text}"
        if TARGET_TEXT.lower() in context.lower():
            candidates.append(urljoin(PLAN_URL, href))
    pdfs = [u for u in candidates if ".pdf" in u.lower()]
    if not pdfs:
        # Conservative fallback: inspect all PDF links for English / semester-1 / second-cycle hints.
        for a in soup.find_all("a", href=True):
            href = urljoin(PLAN_URL, a["href"])
            label = " ".join(a.stripped_strings)
            ctx = f"{label} {href}".lower()
            if ".pdf" in href.lower() and ("english" in ctx or "_en" in ctx) and ("st_2" in ctx or "ii" in ctx):
                pdfs.append(href)
    if not pdfs:
        raise RuntimeError("Could not find the Year 1 / Semester 1 M.D. in English timetable PDF.")
    # Prefer links that explicitly look like semester 1 / second-cycle / English.
    pdfs = sorted(set(pdfs), key=lambda u: (
        "semestr_1" not in u.lower(),
        "st_2" not in u.lower(),
        "_en" not in u.lower(),
        len(u)
    ))
    return pdfs[0]

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

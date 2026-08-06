from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
import json
import re
import time

import requests

from core.config import Settings
from core.utils import normalize_whitespace, compact_join, write_json


@dataclass(frozen=True)
class PaperRecord:
    paper_id: str
    title: str
    summary: str
    authors: list[str]
    categories: list[str]
    primary_category: str
    published: str
    updated: str
    abs_url: str
    pdf_url: str
    comment: str


CROSSREF_API_URL = "https://api.crossref.org/works"

RETRYABLE_STATUS = {408, 425, 429, 500, 502, 503, 504}
MAX_ATTEMPTS = 5
TIMEOUT_SECONDS = 30
BASE_BACKOFF_SECONDS = 2.0

_HTML_TAG_RE = re.compile(r"<[^>]+>")
_MULTI_SPACE_RE = re.compile(r"\s+")


def _strip_html(text: str | None) -> str:
    if not text:
        return ""
    cleaned = _HTML_TAG_RE.sub(" ", text)
    return normalize_whitespace(cleaned)


def _parse_authors(item: dict) -> list[str]:
    authors = []
    for a in item.get("author", []) or []:
        family = (a.get("family") or "").strip()
        given = (a.get("given") or "").strip()
        if family or given:
            authors.append(f"{given} {family}".strip())
    return authors


def _parse_categories(item: dict) -> list[str]:
    cats = []
    for s in item.get("subject", []) or []:
        name = (s or "").strip()
        if name:
            cats.append(name)
    return cats


def _parse_date(date_parts: list[list[int]] | None) -> str | None:
    if not date_parts:
        return None
    first = date_parts[0]
    if len(first) >= 3:
        return f"{first[0]:04d}-{first[1]:02d}-{first[2]:02d}"
    if len(first) == 2:
        return f"{first[0]:04d}-{first[1]:02d}"
    if len(first) == 1:
        return f"{first[0]:04d}"
    return None


def _extract_published(item: dict) -> str:
    published = item.get("published") or {}
    dp = published.get("date-parts")
    if dp:
        result = _parse_date(dp)
        if result:
            return result
    return (item.get("created") or {}).get("date-time", "")[:10]


def _extract_urls(item: dict) -> tuple[str, str]:
    resource = item.get("resource") or {}
    primary = resource.get("primary", {})
    abs_url = (primary.get("URL") or "").strip()
    pdf_url = ""
    for link in item.get("link", []) or []:
        if (link.get("content-type") or "") == "application/pdf":
            pdf_url = (link.get("URL") or "").strip()
            break
    return abs_url, pdf_url


def parse_crossref_payload(payload: dict) -> list[PaperRecord]:
    records: list[PaperRecord] = []
    seen_dois: set[str] = set()

    items = payload.get("message", {}).get("items", [])
    if not items:
        return records

    for item in items:
        doi = (item.get("DOI") or "").strip().lower()
        if not doi:
            continue

        title_list = item.get("title") or []
        title = normalize_whitespace(title_list[0]) if title_list else ""
        if not title:
            continue

        if doi in seen_dois:
            continue
        seen_dois.add(doi)

        abstract = _strip_html(item.get("abstract"))

        authors = _parse_authors(item)
        categories = _parse_categories(item)

        published = _extract_published(item)
        updated = item.get("issued", {}).get("date-time", "")[:10]

        abs_url, pdf_url = _extract_urls(item)

        comment = item.get("subtitle", [""])[0] or ""

        records.append(PaperRecord(
            paper_id=doi,
            title=title,
            summary=abstract,
            authors=authors,
            categories=categories,
            primary_category=categories[0] if categories else "",
            published=published,
            updated=updated,
            abs_url=abs_url,
            pdf_url=pdf_url,
            comment=comment,
        ))

    return records


def _build_params(settings: Settings) -> dict:
    return {
        "query": settings.source_query,
        "filter": settings.source_filter,
        "rows": str(settings.max_results),
        "select": "DOI,title,abstract,author,subject,published,issued,created,resource,link,subtitle",
    }


def _request_with_retry(url: str, params: dict) -> requests.Response:
    last_exc = None
    for attempt in range(1, MAX_ATTEMPTS + 1):
        try:
            resp = requests.get(url, params=params, timeout=TIMEOUT_SECONDS)
            if resp.status_code not in RETRYABLE_STATUS:
                resp.raise_for_status()
                return resp
        except (requests.RequestException, requests.Timeout) as exc:
            last_exc = exc

        if attempt == MAX_ATTEMPTS:
            break

        retry_after = None
        if "resp" in locals():
            retry_after = resp.headers.get("Retry-After")
        if retry_after:
            try:
                time.sleep(float(retry_after))
            except (ValueError, TypeError):
                time.sleep(BASE_BACKOFF_SECONDS * (2 ** (attempt - 1)))
        else:
            time.sleep(BASE_BACKOFF_SECONDS * (2 ** (attempt - 1)))

    if last_exc:
        raise last_exc
    raise RuntimeError(f"Crossref API failed after {MAX_ATTEMPTS} attempts")


def fetch_source_records(settings: Settings) -> list[PaperRecord]:
    params = _build_params(settings)
    resp = _request_with_retry(CROSSREF_API_URL, params)
    payload = resp.json()

    write_json(settings.paths.raw_api_response, payload)

    records = parse_crossref_payload(payload)

    records_data = [
        {
            "paper_id": r.paper_id,
            "title": r.title,
            "summary": r.summary,
            "authors": r.authors,
            "categories": r.categories,
            "primary_category": r.primary_category,
            "published": r.published,
            "updated": r.updated,
            "abs_url": r.abs_url,
            "pdf_url": r.pdf_url,
            "comment": r.comment,
        }
        for r in records
    ]
    write_json(settings.paths.raw_records_json, records_data)

    return records


def load_raw_records(path: Path) -> list[PaperRecord]:
    with open(path, encoding="utf-8") as f:
        data = json.load(f)

    records: list[PaperRecord] = []
    for item in data:
        records.append(PaperRecord(
            paper_id=item.get("paper_id", ""),
            title=item.get("title", ""),
            summary=item.get("summary", ""),
            authors=item.get("authors", []),
            categories=item.get("categories", []),
            primary_category=item.get("primary_category", ""),
            published=item.get("published", ""),
            updated=item.get("updated", ""),
            abs_url=item.get("abs_url", ""),
            pdf_url=item.get("pdf_url", ""),
            comment=item.get("comment", ""),
        ))
    return records

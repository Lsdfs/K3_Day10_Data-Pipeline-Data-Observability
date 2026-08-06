from __future__ import annotations

from dataclasses import dataclass
from dataclasses import asdict
from datetime import UTC, datetime
import html
from pathlib import Path
import re
import time

import requests

from core.config import Settings
from core.utils import normalize_whitespace, read_json, write_json


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


def parse_crossref_payload(payload: dict) -> list[PaperRecord]:
    """Parse a Crossref response into a stable, serializable record schema."""

    def first_text(value) -> str:
        if isinstance(value, list):
            value = value[0] if value else ""
        return normalize_whitespace(str(value or ""))

    def strip_markup(value: str) -> str:
        without_tags = re.sub(r"<[^>]+>", " ", html.unescape(value or ""))
        return normalize_whitespace(without_tags)

    def crossref_date(item: dict, *keys: str) -> str:
        for key in keys:
            parts = item.get(key, {}).get("date-parts", [])
            if not parts or not parts[0]:
                continue
            values = [int(value) for value in parts[0][:3]]
            year = values[0]
            month = values[1] if len(values) > 1 else 1
            day = values[2] if len(values) > 2 else 1
            try:
                return datetime(year, month, day, tzinfo=UTC).date().isoformat()
            except ValueError:
                continue
        return ""

    items = payload.get("message", {}).get("items", [])
    if not isinstance(items, list):
        raise ValueError("Invalid Crossref payload: message.items must be a list.")

    records: list[PaperRecord] = []
    seen_ids: set[str] = set()
    for item in items:
        if not isinstance(item, dict):
            continue
        paper_id = first_text(item.get("DOI")).lower()
        title = strip_markup(first_text(item.get("title")))
        summary = strip_markup(first_text(item.get("abstract")))
        if not paper_id or not title:
            continue
        if paper_id in seen_ids:
            continue

        authors = []
        for author in item.get("author", []) or []:
            if not isinstance(author, dict):
                continue
            name = normalize_whitespace(
                " ".join(part for part in [str(author.get("given", "")), str(author.get("family", ""))] if part)
            )
            if name:
                authors.append(name)
        categories = list(dict.fromkeys(first_text(subject) for subject in item.get("subject", []) if first_text(subject)))
        published = crossref_date(item, "published-print", "published-online", "published", "issued", "created")
        updated = crossref_date(item, "indexed", "deposited", "created") or published
        resource_url = first_text(item.get("URL"))
        pdf_url = ""
        for link in item.get("link", []) or []:
            if isinstance(link, dict) and (
                str(link.get("content-type", "")).lower() == "application/pdf"
                or str(link.get("URL", "")).lower().endswith(".pdf")
            ):
                pdf_url = first_text(link.get("URL"))
                break
        records.append(
            PaperRecord(
                paper_id=paper_id,
                title=title,
                summary=summary,
                authors=list(dict.fromkeys(authors)),
                categories=categories,
                primary_category=categories[0] if categories else "Uncategorized",
                published=published,
                updated=updated,
                abs_url=resource_url or f"https://doi.org/{paper_id}",
                pdf_url=pdf_url,
                comment=first_text(item.get("subtitle")),
            )
        )
        seen_ids.add(paper_id)
    return records


def fetch_source_records(settings: Settings) -> list[PaperRecord]:
    """Fetch Crossref with timeout and exponential backoff, then persist raw artifacts."""
    params = {
        "query": settings.source_query,
        "filter": settings.source_filter,
        "rows": settings.max_results,
        "select": "DOI,title,abstract,author,subject,published-print,published-online,published,issued,created,indexed,deposited,URL,link,subtitle",
    }
    headers = {
        "User-Agent": "day10-data-observability-lab/1.0 (mailto:student@example.invalid)",
        "Accept": "application/json",
    }
    retryable_statuses = {408, 425, 429, 500, 502, 503, 504}
    last_error: Exception | None = None
    payload: dict | None = None
    for attempt in range(1, settings.request_max_attempts + 1):
        try:
            response = requests.get(
                settings.source_url,
                params=params,
                headers=headers,
                timeout=settings.request_timeout_seconds,
            )
            if response.status_code in retryable_statuses:
                raise requests.HTTPError(f"Retryable Crossref status {response.status_code}", response=response)
            response.raise_for_status()
            payload = response.json()
            break
        except (requests.RequestException, ValueError) as exc:
            last_error = exc
            if attempt >= settings.request_max_attempts:
                break
            retry_after = None
            response = getattr(exc, "response", None)
            if response is not None:
                retry_after = response.headers.get("Retry-After")
            try:
                delay = float(retry_after) if retry_after else settings.request_backoff_seconds * (2 ** (attempt - 1))
            except ValueError:
                delay = settings.request_backoff_seconds * (2 ** (attempt - 1))
            time.sleep(delay)

    if payload is None:
        raise RuntimeError(
            f"Crossref request failed after {settings.request_max_attempts} attempts: {last_error}"
        ) from last_error
    write_json(settings.paths.raw_api_response, payload)
    records = parse_crossref_payload(payload)
    if not records:
        raise RuntimeError("Crossref returned no usable records for the configured query/filter.")
    write_json(settings.paths.raw_records_json, [asdict(record) for record in records])
    return records


def load_raw_records(path: Path) -> list[PaperRecord]:
    """Load a validated JSON snapshot into ``PaperRecord`` instances."""
    payload = read_json(path)
    if not isinstance(payload, list):
        raise ValueError(f"Raw records file must contain a JSON list: {path}")
    records: list[PaperRecord] = []
    field_names = set(PaperRecord.__dataclass_fields__)
    for position, item in enumerate(payload):
        if not isinstance(item, dict):
            raise ValueError(f"Raw record at position {position} is not an object.")
        missing = field_names - set(item)
        if missing:
            raise ValueError(f"Raw record at position {position} misses fields: {sorted(missing)}")
        item = {key: item[key] for key in field_names}
        item["authors"] = list(item["authors"] or [])
        item["categories"] = list(item["categories"] or [])
        records.append(PaperRecord(**item))
    return records

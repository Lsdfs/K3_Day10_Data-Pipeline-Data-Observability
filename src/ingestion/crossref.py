from __future__ import annotations

from dataclasses import asdict, dataclass
from datetime import UTC, datetime
import hashlib
import html
import logging
from pathlib import Path
import re
import time
from typing import Any

import requests

from core.config import Settings
from core.utils import normalize_whitespace, read_json, write_json


LOGGER = logging.getLogger(__name__)


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


def _first_text(value: Any) -> str:
    if isinstance(value, list):
        value = value[0] if value else ""
    return normalize_whitespace(str(value or ""))


def _strip_markup(value: Any) -> str:
    decoded = html.unescape(_first_text(value))
    return normalize_whitespace(re.sub(r"<[^>]+>", " ", decoded))


def _crossref_date(item: dict[str, Any], *keys: str) -> str:
    for key in keys:
        value = item.get(key)
        if not isinstance(value, dict):
            continue
        date_time = value.get("date-time")
        if date_time:
            parsed = datetime.fromisoformat(str(date_time).replace("Z", "+00:00"))
            return parsed.date().isoformat()
        parts = value.get("date-parts", [])
        if not parts or not parts[0]:
            continue
        numbers = [int(number) for number in parts[0][:3]]
        try:
            return datetime(
                numbers[0], numbers[1] if len(numbers) > 1 else 1,
                numbers[2] if len(numbers) > 2 else 1, tzinfo=UTC,
            ).date().isoformat()
        except (TypeError, ValueError):
            continue
    return ""


def _fallback_id(title: str, published: str, url: str) -> str:
    identity = "|".join([title.lower(), published, url.lower()])
    return "crossref-" + hashlib.sha256(identity.encode("utf-8")).hexdigest()[:20]


def _parse_crossref_payload(payload: dict[str, Any]) -> tuple[list[PaperRecord], dict[str, int]]:
    if not isinstance(payload, dict):
        raise ValueError("Crossref payload must be a JSON object.")
    items = payload.get("message", {}).get("items")
    if not isinstance(items, list):
        raise ValueError("Invalid Crossref payload: message.items must be a list.")

    records: list[PaperRecord] = []
    seen_ids: set[str] = set()
    invalid_count = 0
    duplicate_count = 0
    fallback_id_count = 0
    for item in items:
        if not isinstance(item, dict):
            invalid_count += 1
            continue
        title = _strip_markup(item.get("title"))
        published = _crossref_date(
            item, "published-print", "published-online", "published", "issued", "created"
        )
        url = _first_text(item.get("URL"))
        paper_id = _first_text(item.get("DOI")).lower()
        if not title:
            invalid_count += 1
            continue
        if not paper_id:
            paper_id = _fallback_id(title, published, url)
            fallback_id_count += 1
        if paper_id in seen_ids:
            duplicate_count += 1
            continue

        authors: list[str] = []
        for author in item.get("author", []) or []:
            if not isinstance(author, dict):
                continue
            name = normalize_whitespace(
                " ".join(
                    part for part in [
                        _first_text(author.get("given")),
                        _first_text(author.get("family")),
                    ] if part
                )
            ) or _first_text(author.get("name"))
            if name:
                authors.append(name)
        authors = list(dict.fromkeys(authors))
        categories = list(dict.fromkeys(
            text for subject in item.get("subject", []) or [] if (text := _first_text(subject))
        ))
        summary = _strip_markup(item.get("abstract"))
        updated = _crossref_date(item, "indexed", "deposited", "created") or published
        pdf_url = ""
        for link in item.get("link", []) or []:
            if not isinstance(link, dict):
                continue
            link_url = _first_text(link.get("URL"))
            content_type = _first_text(link.get("content-type")).lower()
            if content_type == "application/pdf" or link_url.lower().endswith(".pdf"):
                pdf_url = link_url
                break
        records.append(PaperRecord(
            paper_id=paper_id,
            title=title,
            summary=summary,
            authors=authors,
            categories=categories,
            primary_category=categories[0] if categories else "Uncategorized",
            published=published,
            updated=updated,
            abs_url=url or (f"https://doi.org/{paper_id}" if not paper_id.startswith("crossref-") else ""),
            pdf_url=pdf_url,
            comment=_strip_markup(item.get("subtitle")),
        ))
        seen_ids.add(paper_id)
    summary = {
        "received_records": len(items),
        "valid_records": len(records),
        "invalid_records": invalid_count,
        "duplicate_records": duplicate_count,
        "fallback_ids": fallback_id_count,
    }
    return records, summary


def parse_crossref_payload(payload: dict) -> list[PaperRecord]:
    """Parse a Crossref response into a stable normalized record schema."""
    return _parse_crossref_payload(payload)[0]


def fetch_source_records(settings: Settings) -> list[PaperRecord]:
    """Fetch Crossref with finite timeout/retries and persist auditable raw artifacts."""
    params = {
        "query": settings.source_query,
        "filter": settings.source_filter,
        "rows": settings.max_results,
    }
    headers = {
        "Accept": "application/json",
        "User-Agent": (
            "day10-data-observability/1.0 "
            "(+https://github.com/Lsdfs/K3_Day10_Data-Pipeline-Data-Observability)"
        ),
    }
    retryable = {408, 425, 429, 500, 502, 503, 504}
    payload: dict[str, Any] | None = None
    last_error: Exception | None = None
    attempts_used = 0
    for attempt in range(1, settings.request_max_attempts + 1):
        attempts_used = attempt
        try:
            response = requests.get(
                settings.source_url,
                params=params,
                headers=headers,
                timeout=settings.request_timeout_seconds,
            )
            if response.status_code in retryable:
                raise requests.HTTPError(
                    f"Retryable Crossref status {response.status_code}", response=response
                )
            response.raise_for_status()
            decoded = response.json()
            if not isinstance(decoded, dict):
                raise ValueError("Crossref response JSON must be an object.")
            payload = decoded
            break
        except (requests.RequestException, ValueError) as exc:
            last_error = exc
            if attempt >= settings.request_max_attempts:
                break
            response = getattr(exc, "response", None)
            retry_after = response.headers.get("Retry-After") if response is not None else None
            try:
                delay = float(retry_after) if retry_after else settings.request_backoff_seconds * 2 ** (attempt - 1)
            except (TypeError, ValueError):
                delay = settings.request_backoff_seconds * 2 ** (attempt - 1)
            LOGGER.warning("Crossref attempt %s failed; retrying in %.1fs", attempt, delay)
            time.sleep(delay)
    if payload is None:
        raise RuntimeError(
            f"Crossref ingestion failed after {settings.request_max_attempts} attempts: {last_error}"
        ) from last_error

    write_json(settings.paths.raw_api_response, payload)
    records, parse_summary = _parse_crossref_payload(payload)
    if not records:
        raise RuntimeError("Crossref returned no usable records for the configured query/filter.")
    write_json(settings.paths.raw_records_json, [asdict(record) for record in records])
    ingestion_summary = {
        "source": settings.source_api,
        "endpoint": settings.source_url,
        "query": settings.source_query,
        "filter": settings.source_filter,
        "requested_records": settings.max_results,
        "attempts": attempts_used,
        "fetched_at": datetime.now(UTC).isoformat(),
        **parse_summary,
    }
    write_json(settings.paths.ingestion_summary, ingestion_summary)
    LOGGER.info("Crossref ingestion complete: %s", ingestion_summary)
    return records


def load_raw_records(path: Path) -> list[PaperRecord]:
    """Load and validate a parsed raw-record JSON snapshot."""
    payload = read_json(path)
    if not isinstance(payload, list):
        raise ValueError(f"Raw records file must contain a JSON list: {path}")
    fields = set(PaperRecord.__dataclass_fields__)
    records: list[PaperRecord] = []
    for position, item in enumerate(payload):
        if not isinstance(item, dict):
            raise ValueError(f"Raw record {position} is not an object.")
        missing = fields - set(item)
        if missing:
            raise ValueError(f"Raw record {position} misses fields: {sorted(missing)}")
        values = {name: item[name] for name in fields}
        values["authors"] = list(values["authors"] or [])
        values["categories"] = list(values["categories"] or [])
        records.append(PaperRecord(**values))
    return records

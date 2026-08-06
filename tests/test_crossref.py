from __future__ import annotations

from dataclasses import replace

import requests

from ingestion.crossref import fetch_source_records, load_raw_records, parse_crossref_payload


def payload(doi="10.1234/ABC", title="A <b>Useful</b> Paper"):
    item = {
        "title": [title],
        "abstract": "<jats:p>An &amp; abstract with enough verifiable content for testing.</jats:p>",
        "author": [{"given": "Ada", "family": "Lovelace"}],
        "subject": ["AI", "Retrieval"],
        "published-online": {"date-parts": [[2026, 7, 4]]},
        "indexed": {"date-time": "2026-07-05T00:00:00Z"},
        "URL": "https://example.test/paper",
    }
    if doi is not None:
        item["DOI"] = doi
    return {"message": {"items": [item]}}


def test_parse_normalizes_and_supports_stable_fallback_id():
    normal = parse_crossref_payload(payload())[0]
    assert normal.paper_id == "10.1234/abc"
    assert normal.title == "A Useful Paper"
    assert normal.summary.startswith("An & abstract")
    assert normal.authors == ["Ada Lovelace"]
    first = parse_crossref_payload(payload(doi=None))[0]
    second = parse_crossref_payload(payload(doi=None))[0]
    assert first.paper_id.startswith("crossref-") and first.paper_id == second.paper_id


def test_parse_handles_missing_fields_and_deduplicates():
    data = payload()
    data["message"]["items"].extend([payload()["message"]["items"][0], {"DOI": "missing-title"}, None])
    records = parse_crossref_payload(data)
    assert len(records) == 1


def test_fetch_retries_without_real_network(monkeypatch, settings):
    class Response:
        def __init__(self, status, data=None):
            self.status_code, self.data, self.headers = status, data, {}
        def raise_for_status(self):
            if self.status_code >= 400:
                raise requests.HTTPError(response=self)
        def json(self):
            return self.data
    replies = iter([Response(503), Response(200, payload())])
    monkeypatch.setattr("ingestion.crossref.requests.get", lambda *args, **kwargs: next(replies))
    monkeypatch.setattr("ingestion.crossref.time.sleep", lambda _: None)
    configured = replace(settings, request_max_attempts=2, request_backoff_seconds=0)
    records = fetch_source_records(configured)
    assert load_raw_records(configured.paths.raw_records_json) == records
    assert configured.paths.raw_api_response.exists()
    assert configured.paths.ingestion_summary.exists()

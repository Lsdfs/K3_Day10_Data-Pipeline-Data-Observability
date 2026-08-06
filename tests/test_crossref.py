from __future__ import annotations

from dataclasses import replace

import requests

from ingestion.crossref import fetch_source_records, load_raw_records, parse_crossref_payload


def sample_payload():
    return {
        "message": {
            "items": [
                {
                    "DOI": "10.1234/ABC",
                    "title": ["  A <b>Useful</b> Paper  "],
                    "abstract": "<jats:p>An &amp; abstract with enough content.</jats:p>",
                    "author": [{"given": "Ada", "family": "Lovelace"}],
                    "subject": ["AI", "Retrieval"],
                    "published-online": {"date-parts": [[2026, 7, 4]]},
                    "indexed": {"date-parts": [[2026, 7, 5]]},
                    "URL": "https://doi.org/10.1234/ABC",
                    "link": [{"content-type": "application/pdf", "URL": "https://example.test/paper.pdf"}],
                }
            ]
        }
    }


def test_parse_crossref_payload_normalizes_schema():
    records = parse_crossref_payload(sample_payload())
    assert len(records) == 1
    assert records[0].paper_id == "10.1234/abc"
    assert records[0].title == "A Useful Paper"
    assert records[0].summary == "An & abstract with enough content."
    assert records[0].authors == ["Ada Lovelace"]
    assert records[0].published == "2026-07-04"


def test_fetch_retries_and_persists(monkeypatch, settings):
    class Response:
        def __init__(self, status, payload=None):
            self.status_code = status
            self._payload = payload
            self.headers = {}

        def raise_for_status(self):
            if self.status_code >= 400:
                raise requests.HTTPError(response=self)

        def json(self):
            return self._payload

    responses = iter([Response(503), Response(200, sample_payload())])
    monkeypatch.setattr("ingestion.crossref.requests.get", lambda *args, **kwargs: next(responses))
    monkeypatch.setattr("ingestion.crossref.time.sleep", lambda _: None)
    configured = replace(settings, request_max_attempts=2, request_backoff_seconds=0)
    records = fetch_source_records(configured)
    assert len(records) == 1
    assert configured.paths.raw_api_response.exists()
    assert load_raw_records(configured.paths.raw_records_json) == records

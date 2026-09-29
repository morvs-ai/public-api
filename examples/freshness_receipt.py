#!/usr/bin/env python3
"""Record a bounded receipt for MORVS's public dataset-freshness response."""

from __future__ import annotations

import argparse
import hashlib
import http.client
import json
import sys
import urllib.error
import urllib.request
from datetime import datetime, timezone
from typing import Any


FRESHNESS_URL = "https://api.morvs.ai/api/v1/freshness"
MAX_RESPONSE_BYTES = 4 * 1024 * 1024
STATUSES = ("FRESH", "AGING", "STALE", "UNKNOWN")


def build_receipt(raw: bytes, retrieved_at: str, slug: str | None = None) -> dict[str, Any]:
    """Validate the public response and select only the requested summary/entry."""
    payload = json.loads(raw)
    if not isinstance(payload, dict):
        raise ValueError("Expected a JSON object from the freshness endpoint")

    summary = payload.get("summary")
    datasets = payload.get("datasets")
    if not isinstance(summary, dict) or not isinstance(datasets, list):
        raise ValueError("Freshness response is missing summary or datasets")
    if any(not isinstance(summary.get(status), int) for status in STATUSES):
        raise ValueError("Freshness summary has an unexpected status shape")

    source = payload.get("_source")
    if source is not None and not isinstance(source, dict):
        raise ValueError("Freshness response has an unexpected _source shape")

    receipt: dict[str, Any] = {
        "receipt_version": 2,
        "endpoint": FRESHNESS_URL,
        "retrieved_at_utc": retrieved_at,
        "response_sha256": hashlib.sha256(raw).hexdigest(),
        "api_generated_at": (source or {}).get("generated_at"),
        "total_datasets": payload.get("total_datasets"),
        "summary": {status: summary[status] for status in STATUSES},
        "license_url": payload.get("license"),
    }

    if slug is not None:
        match = next(
            (item for item in datasets if isinstance(item, dict) and item.get("slug") == slug),
            None,
        )
        if match is None:
            raise ValueError(f"Dataset slug not found: {slug}")
        if match.get("status") not in STATUSES:
            raise ValueError(f"Unexpected status for dataset: {slug}")
        receipt["dataset"] = {
            key: match.get(key)
            for key in (
                "slug",
                "row_count",
                "status",
                "status_basis",
                "cadence",
                "expected_days",
                "age_days",
                "last_successful_source_observation",
                "content_watermark",
            )
        }
    return receipt


def fetch_response() -> bytes:
    request = urllib.request.Request(
        FRESHNESS_URL,
        headers={"Accept": "application/json", "User-Agent": "morvs-public-api-example/1.0"},
    )
    with urllib.request.urlopen(request, timeout=15) as response:
        if response.geturl() != FRESHNESS_URL:
            raise ValueError("Freshness endpoint redirected to an unexpected URL")
        if response.headers.get_content_type() != "application/json":
            raise ValueError("Freshness endpoint did not return application/json")
        raw = response.read(MAX_RESPONSE_BYTES + 1)
    if len(raw) > MAX_RESPONSE_BYTES:
        raise ValueError("Freshness response exceeds the 4 MiB safety limit")
    return raw


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--slug", help="Exact dataset slug; omit for the summary")
    parser.add_argument(
        "--require-fresh", action="store_true", help="Exit 2 unless the selected dataset reports FRESH"
    )
    args = parser.parse_args()
    if args.require_fresh and not args.slug:
        parser.error("--require-fresh requires --slug")

    try:
        raw = fetch_response()
        retrieved_at = datetime.now(timezone.utc).isoformat(timespec="seconds")
        receipt = build_receipt(raw, retrieved_at, args.slug)
    except (OSError, urllib.error.URLError, ValueError, http.client.HTTPException) as exc:
        print(f"freshness receipt failed: {exc}", file=sys.stderr)
        return 1

    print(json.dumps(receipt, indent=2, sort_keys=True))
    if args.require_fresh and receipt["dataset"]["status"] != "FRESH":
        print("dataset does not currently report FRESH", file=sys.stderr)
        return 2
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

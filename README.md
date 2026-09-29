<p align="center">
  <a href="https://morvs.ai/"><img src="assets/morvs-banner.png" alt="MORVS — private intelligence infrastructure" width="100%"></a>
</p>

<p align="center"><strong>PUBLIC DATA. VISIBLE PROVENANCE. CONTROLLED USE.</strong></p>

MORVS exposes public regulatory and institutional data through a source-aware API. This repository contains a small, independently runnable example for checking a dataset's published freshness state and recording exactly what the API returned. It contains no production services, private data, or credentials.

### Start at the source

| Interface | Purpose |
| --- | --- |
| [API catalog](https://api.morvs.ai/datasets/) | Browse datasets, their original sources, and applicable terms. |
| [OpenAPI contract](https://api.morvs.ai/openapi.json) | Inspect current routes and response schemas. |
| [Freshness response](https://api.morvs.ai/api/v1/freshness) | Read published status, cadence, timestamps, and status methodology. |
| [Coverage](https://api.morvs.ai/coverage) | Check current row counts and refresh information. |
| [Source and license policy](https://api.morvs.ai/license) | Review attribution and source-specific reuse limits. |

The public routes above were checked on **29 September 2026**. Check the live contract before integrating: routes, counts, and source status can change.

### Make a freshness receipt

Python 3.10+; standard library only. No API key or package installation is needed for this example.

```bash
python3 examples/freshness_receipt.py --slug sec-filings > sec-filings-receipt.json
```

The receipt records the response URL, retrieval time, SHA-256 of the exact response body, the API's generation time, and the selected dataset's published status and watermarks. Omit `--slug` for the API's summary counts. Add `--require-fresh` with a slug to exit nonzero unless its reported status is `FRESH`.

```bash
python3 examples/freshness_receipt.py --slug sec-filings --require-fresh
```

**Interpretation matters.** `UNKNOWN` is not zero records and is not proof that the upstream source stopped publishing. `FRESH` reflects the API's stated cadence and timestamps; it is not a guarantee that every upstream record is present or correct. `content_watermark` describes indexed content. `last_successful_source_observation`, where available, describes an upstream check. The response explains which timestamp its status uses. Preserve the source URL and original terms when citing or reusing a dataset.

### Boundaries

This example uses only the public freshness endpoint. It does not include MORVS backend code, ingestion logic, private queries, or individual records. The MIT license covers the example code and documentation text; [brand assets](NOTICE.md) and underlying datasets retain their own rights.

MORVS is the public brand of AI Analytics LLC. [Explore the systems](https://morvs.ai/) · [API overview](https://morvs.ai/api/)

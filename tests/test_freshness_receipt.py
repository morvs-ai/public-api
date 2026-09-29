"""Contract checks for the public example; no live request is needed."""

import importlib.util
import json
import pathlib
import unittest


SOURCE = pathlib.Path(__file__).resolve().parents[1] / "examples" / "freshness_receipt.py"
SPEC = importlib.util.spec_from_file_location("freshness_receipt", SOURCE)
assert SPEC and SPEC.loader
MODULE = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(MODULE)


class FreshnessReceiptTests(unittest.TestCase):
    def setUp(self):
        self.raw = json.dumps(
            {
                "summary": {"FRESH": 1, "AGING": 0, "STALE": 0, "UNKNOWN": 1},
                "total_datasets": 2,
                "license": "https://api.morvs.ai/license",
                "_source": {"generated_at": "2026-09-29T12:00:00Z"},
                "datasets": [
                    {"slug": "example", "status": "FRESH", "content_watermark": None},
                    {"slug": "unknown", "status": "UNKNOWN", "row_count": 10},
                ],
            }
        ).encode()

    def test_receipt_keeps_hash_and_unknown_distinct_from_zero(self):
        receipt = MODULE.build_receipt(self.raw, "2026-09-29T12:01:00+00:00", "unknown")
        self.assertEqual(receipt["response_sha256"], MODULE.hashlib.sha256(self.raw).hexdigest())
        self.assertEqual(receipt["dataset"]["status"], "UNKNOWN")
        self.assertEqual(receipt["dataset"]["row_count"], 10)

    def test_unknown_slug_fails_instead_of_silent_empty_receipt(self):
        with self.assertRaisesRegex(ValueError, "slug not found"):
            MODULE.build_receipt(self.raw, "2026-09-29T12:01:00+00:00", "missing")

    def test_changed_contract_fails_closed(self):
        with self.assertRaisesRegex(ValueError, "missing summary or datasets"):
            MODULE.build_receipt(b'{"summary": {}}', "2026-09-29T12:01:00+00:00")


if __name__ == "__main__":
    unittest.main()

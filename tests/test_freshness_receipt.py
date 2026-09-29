"""Contract checks for the public example; no live request is needed."""

import importlib.util
import json
import pathlib
import unittest
from unittest import mock
from contextlib import redirect_stderr, redirect_stdout
from io import StringIO


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

    def test_api_generation_time_is_not_labeled_upstream_source_time(self):
        receipt = MODULE.build_receipt(self.raw, "2026-09-29T12:01:00+00:00")
        self.assertEqual(receipt["receipt_version"], 2)
        self.assertEqual(receipt["api_generated_at"], "2026-09-29T12:00:00Z")
        self.assertNotIn("source_generated_at", receipt)

    def test_malformed_source_metadata_is_rejected(self):
        for source in ("unexpected", ["unexpected"], [], 1, False):
            with self.subTest(source=source):
                payload = json.loads(self.raw)
                payload["_source"] = source
                with self.assertRaisesRegex(ValueError, "unexpected _source shape"):
                    MODULE.build_receipt(json.dumps(payload).encode(), "2026-09-29T12:01:00Z")

    def test_missing_source_metadata_does_not_invent_a_timestamp(self):
        payload = json.loads(self.raw)
        del payload["_source"]
        receipt = MODULE.build_receipt(json.dumps(payload).encode(), "2026-09-29T12:01:00Z")
        self.assertIsNone(receipt["api_generated_at"])

    def run_main(self, argv, response=None, error=None):
        stdout, stderr = StringIO(), StringIO()
        with mock.patch.object(MODULE.sys, "argv", ["freshness_receipt.py", *argv]), \
                mock.patch.object(MODULE, "fetch_response", return_value=response, side_effect=error), \
                redirect_stdout(stdout), redirect_stderr(stderr):
            code = MODULE.main()
        return code, stdout.getvalue(), stderr.getvalue()

    def test_incomplete_or_timed_out_response_has_no_partial_receipt(self):
        for error in (TimeoutError("read timed out"), MODULE.http.client.IncompleteRead(b"partial")):
            with self.subTest(error=type(error).__name__):
                code, output, diagnostic = self.run_main([], error=error)
                self.assertEqual(code, 1)
                self.assertEqual(output, "")
                self.assertIn("freshness receipt failed:", diagnostic)
                self.assertNotIn("Traceback", diagnostic)

    def test_freshness_gate_prints_unknown_receipt_but_exits_two(self):
        code, output, diagnostic = self.run_main(["--slug", "unknown", "--require-fresh"], response=self.raw)
        self.assertEqual(code, 2)
        self.assertEqual(json.loads(output)["dataset"]["status"], "UNKNOWN")
        self.assertIn("does not currently report FRESH", diagnostic)

    def test_freshness_gate_accepts_fresh_entry(self):
        code, output, diagnostic = self.run_main(["--slug", "example", "--require-fresh"], response=self.raw)
        self.assertEqual(code, 0)
        self.assertEqual(json.loads(output)["dataset"]["status"], "FRESH")
        self.assertEqual(diagnostic, "")


if __name__ == "__main__":
    unittest.main()

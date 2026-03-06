import unittest
from unittest import mock

from platform.legacy.jobs import judge_quality_report as jq


class JudgeQualityReportJobTests(unittest.TestCase):
    def test_run_judge_quality_report_persists_judge_quality_payload(self):
        captured = {}

        def _fake_build(**kwargs):
            self.assertEqual(kwargs["horizon_days"], 5)
            self.assertEqual(kwargs["min_samples"], 20)
            return {
                "as_of": "2026-03-04T04:23:11Z",
                "overall": {"n": 12, "sample_status": "insufficient"},
                "windows": {},
                "recommendation": {"status": "neutral", "message": "ok"},
            }

        def _fake_save_json(*args, **kwargs):
            captured["args"] = args
            captured["kwargs"] = kwargs
            return "ok"

        with mock.patch.object(jq, "build_judge_quality_report", side_effect=_fake_build), mock.patch.object(
            jq, "save_json", side_effect=_fake_save_json
        ):
            report = jq.run_judge_quality_report(horizon_days=5, min_samples=20)

        self.assertIsInstance(report, dict)
        self.assertEqual(report["job_type"], "judge_quality_report")
        self.assertEqual(report["as_of"], "2026-03-04T04:23:11Z")
        self.assertEqual(captured["args"][0], "judge_quality")
        self.assertIsInstance(captured["args"][1], dict)
        self.assertEqual(captured["kwargs"]["source"][0], "job:judge_quality_report")

    def test_run_judge_quality_report_falls_back_when_service_unavailable(self):
        captured = {}

        def _fake_save_json(*args, **kwargs):
            captured["args"] = args
            captured["kwargs"] = kwargs
            return "ok"

        with mock.patch.object(jq, "build_judge_quality_report", None), mock.patch.object(
            jq, "save_json", side_effect=_fake_save_json
        ):
            report = jq.run_judge_quality_report(horizon_days=5, min_samples=20)

        self.assertIsInstance(report, dict)
        self.assertTrue(report["generated_by_fallback"])
        self.assertEqual(report["overall"]["sample_status"], "insufficient")
        self.assertEqual(captured["args"][0], "judge_quality")


if __name__ == "__main__":
    unittest.main()

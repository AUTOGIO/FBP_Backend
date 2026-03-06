from __future__ import annotations

import sys
import unittest
from pathlib import Path

ROOT_DIR = Path(__file__).resolve().parents[1]
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

from tests.test_jobs_api import run_request


class WorkflowsAPITest(unittest.TestCase):
    def test_daily_briefing_job_submission(self) -> None:
        status, data = run_request("POST", "/workflows/daily-briefing", {"priorities": ["A", "B"]})
        self.assertEqual(status, 202)
        self.assertEqual(data["workflow"], "daily-briefing")

    def test_risk_scan_job_submission(self) -> None:
        status, data = run_request("POST", "/workflows/risk-scan", {"diff": "+line\n-line"})
        self.assertEqual(status, 202)
        self.assertEqual(data["workflow"], "risk-scan")


if __name__ == "__main__":
    unittest.main()

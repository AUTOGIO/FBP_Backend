from __future__ import annotations

import sys
import unittest
from pathlib import Path

ROOT_DIR = Path(__file__).resolve().parents[1]
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

from tests.test_jobs_api import run_request


class CLICompatAPITest(unittest.TestCase):
    def test_nfa_and_status_shape(self) -> None:
        status, created = run_request(
            "POST",
            "/nfa/consult",
            {"data_inicial": "01/01/2026", "data_final": "05/01/2026", "matricula": "1595504"},
        )
        self.assertEqual(status, 200)
        self.assertIn("job_id", created)

        status, payload = run_request("GET", f"/nfa/consult/status/{created['job_id']}")
        self.assertEqual(status, 200)
        self.assertIn("job_type", payload)
        self.assertIn("status", payload)

    def test_cep_and_executor(self) -> None:
        status, cep_payload = run_request("POST", "/api/utils/cep", {"cep": "58010120", "enrich": True})
        self.assertEqual(status, 200)
        self.assertTrue(cep_payload["success"])

        status, exec_payload = run_request(
            "POST",
            "/api/executor/run-bash",
            {"script_content": "echo hello", "timeout": 5},
        )
        self.assertEqual(status, 200)
        self.assertEqual(exec_payload["exit_code"], 0)


if __name__ == "__main__":
    unittest.main()

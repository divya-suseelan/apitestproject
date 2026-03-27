"""
Agent 6 — Results Uploader
Downloads test artifacts from GitLab and uploads results to the test management tool.
Supports Xray (Jira), Zephyr Scale, and qTest.
"""
from __future__ import annotations

import logging
import os
import tempfile
import xml.etree.ElementTree as ET
from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional

import requests

from .base import BaseAgent, AgentConfig

logger = logging.getLogger(__name__)


@dataclass
class TestResult:
    test_id: str
    ticket_id: str
    status: str          # PASS | FAIL | SKIP
    duration_ms: Optional[float] = None
    error_message: Optional[str] = None


class ResultsUploaderAgent(BaseAgent):
    """Downloads pipeline artifacts and uploads results to the test management tool."""

    name = "ResultsUploaderAgent"

    def __init__(self, config: AgentConfig):
        super().__init__(config)
        tm_cfg = config.raw.get("test_management", {})
        self.tool = tm_cfg.get("tool", "none").lower()
        self.jira_base_url = tm_cfg.get("jira_base_url", "").rstrip("/")
        self.env = config.env
        self.results_dir = Path(config.raw.get("output", {}).get("results_dir", "./output"))
        self.results_dir.mkdir(parents=True, exist_ok=True)

    def run(self, pipeline_result: dict) -> list[TestResult]:
        """
        Download artifacts, parse results, upload to test management.
        Returns parsed TestResult list.
        """
        artifact_urls: list[str] = pipeline_result.get("artifact_urls", [])
        results: list[TestResult] = []

        for url in artifact_urls:
            junit_file = self._download_artifact(url)
            if junit_file:
                results.extend(self._parse_junit(junit_file))

        if results:
            self._upload_results(results, pipeline_result.get("pipeline_id", 0))
        else:
            logger.warning("No test results found to upload.")

        return results

    # ------------------------------------------------------------------
    # Private helpers
    # ------------------------------------------------------------------

    def _download_artifact(self, url: str) -> Optional[Path]:
        gitlab_token = self.env.get("GITLAB_TOKEN", "")
        headers = {"PRIVATE-TOKEN": gitlab_token}
        try:
            resp = requests.get(url, headers=headers, timeout=60, stream=True)
            resp.raise_for_status()
            dest = self.results_dir / f"artifact_{abs(hash(url))}.zip"
            dest.write_bytes(resp.content)

            # Extract XML from zip
            import zipfile  # noqa: PLC0415
            with zipfile.ZipFile(dest) as zf:
                for name in zf.namelist():
                    if name.endswith(".xml"):
                        extracted = self.results_dir / name
                        extracted.write_bytes(zf.read(name))
                        logger.info("Extracted artifact: %s", extracted)
                        return extracted
        except Exception as exc:
            logger.error("Failed to download artifact %s: %s", url, exc)
        return None

    @staticmethod
    def _parse_junit(junit_path: Path) -> list[TestResult]:
        results: list[TestResult] = []
        try:
            tree = ET.parse(junit_path)
            for testcase in tree.iter("testcase"):
                name = testcase.get("name", "")
                # Expect test name format: <ticket_id>_TC_<n> - <title>
                test_id = name.split(" - ")[0].strip()
                ticket_id = "_".join(test_id.split("_")[:2]) if "_TC_" in test_id else ""
                duration_ms = float(testcase.get("time", 0)) * 1000

                failure = testcase.find("failure")
                error = testcase.find("error")
                skipped = testcase.find("skipped")

                if failure is not None:
                    status, msg = "FAIL", failure.get("message", "")
                elif error is not None:
                    status, msg = "FAIL", error.get("message", "")
                elif skipped is not None:
                    status, msg = "SKIP", ""
                else:
                    status, msg = "PASS", ""

                results.append(TestResult(
                    test_id=test_id,
                    ticket_id=ticket_id,
                    status=status,
                    duration_ms=duration_ms,
                    error_message=msg or None,
                ))
        except Exception as exc:
            logger.error("Failed to parse JUnit XML %s: %s", junit_path, exc)
        return results

    def _upload_results(self, results: list[TestResult], pipeline_id: int) -> None:
        if self.tool == "xray":
            self._upload_to_xray(results)
        elif self.tool == "zephyr_scale":
            self._upload_to_zephyr(results)
        elif self.tool == "qtest":
            self._upload_to_qtest(results, pipeline_id)
        else:
            logger.info("test_management.tool=none — skipping results upload.")

    # --- Xray ---

    def _upload_to_xray(self, results: list[TestResult]) -> None:
        token = self._get_xray_token()
        headers = {"Authorization": f"Bearer {token}", "Content-Type": "application/json"}
        payload = {
            "info": {"summary": "Auto-generated test execution", "description": "Uploaded by multi-agent pipeline"},
            "tests": [
                {
                    "testKey": r.ticket_id,
                    "status": r.status,
                    "comment": r.error_message or "",
                }
                for r in results
            ],
        }
        resp = requests.post(
            f"{self.jira_base_url}/rest/raven/1.0/import/execution",
            headers=headers,
            json=payload,
            timeout=30,
        )
        resp.raise_for_status()
        logger.info("Xray: execution uploaded — %s", resp.json())

    def _get_xray_token(self) -> str:
        resp = requests.post(
            "https://xray.cloud.getxray.app/api/v1/authenticate",
            json={
                "client_id": self.env["XRAY_CLIENT_ID"],
                "client_secret": self.env["XRAY_CLIENT_SECRET"],
            },
            timeout=15,
        )
        resp.raise_for_status()
        return resp.text.strip('"')

    # --- Zephyr Scale ---

    def _upload_to_zephyr(self, results: list[TestResult]) -> None:
        token = self.env.get("ZEPHYR_API_TOKEN", "")
        headers = {"Authorization": f"Bearer {token}", "Content-Type": "application/json"}
        for result in results:
            payload = {
                "projectKey": result.ticket_id.rsplit("-", 1)[0],
                "testCaseKey": result.ticket_id,
                "statusName": "Pass" if result.status == "PASS" else "Fail",
                "comment": result.error_message or "",
            }
            resp = requests.post(
                "https://api.zephyrscale.smartbear.com/v2/testexecutions",
                headers=headers,
                json=payload,
                timeout=30,
            )
            if not resp.ok:
                logger.warning("Zephyr: failed for %s — %s", result.ticket_id, resp.text)
        logger.info("Zephyr Scale: uploaded %d results", len(results))

    # --- qTest ---

    def _upload_to_qtest(self, results: list[TestResult], pipeline_id: int) -> None:
        base_url = self.env.get("QTEST_BASE_URL", "").rstrip("/")
        token = self.env.get("QTEST_API_TOKEN", "")
        headers = {"Authorization": f"Bearer {token}", "Content-Type": "application/json"}

        for result in results:
            payload = {
                "name": result.test_id,
                "status": {"name": "PASS" if result.status == "PASS" else "FAILED"},
                "note": result.error_message or "",
            }
            resp = requests.post(
                f"{base_url}/api/v3/projects/0/test-runs",
                headers=headers,
                json=payload,
                timeout=30,
            )
            if not resp.ok:
                logger.warning("qTest: failed for %s — %s", result.test_id, resp.text)
        logger.info("qTest: uploaded %d results", len(results))

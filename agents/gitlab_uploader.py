"""
Agent 5 — GitLab Uploader
Commits generated test files to GitLab and triggers the CI pipeline.
Optionally creates a Merge Request instead of pushing directly.
"""
from __future__ import annotations

import base64
import logging
import time
from pathlib import Path
from typing import Optional

import gitlab
from gitlab.v4.objects import Project

from .base import BaseAgent, AgentConfig

logger = logging.getLogger(__name__)


class GitLabUploaderAgent(BaseAgent):
    """Pushes test files to GitLab and triggers a CI pipeline."""

    name = "GitLabUploaderAgent"

    def __init__(self, config: AgentConfig):
        super().__init__(config)
        cfg = config.raw["gitlab"]
        self.gl = gitlab.Gitlab(cfg["base_url"], private_token=config.env["GITLAB_TOKEN"])
        self.project: Project = self.gl.projects.get(cfg["namespace"])
        self.default_branch: str = cfg["default_branch"]
        self.branch_prefix: str = cfg.get("test_branch_prefix", "auto-tests")
        self.create_mr: bool = cfg.get("create_merge_request", True)
        self.mr_target: str = cfg.get("mr_target_branch", "main")
        pipeline_cfg = config.raw.get("pipeline", {})
        self.poll_interval: int = pipeline_cfg.get("poll_interval_seconds", 15)
        self.timeout: int = pipeline_cfg.get("timeout_seconds", 1800)
        self.artifact_job: str = pipeline_cfg.get("artifact_job_name", "test-results")

    def run(self, file_paths: list[str], ticket_ids: list[str]) -> dict:
        """
        Upload files to GitLab, trigger pipeline, wait for result.
        Returns dict with branch, pipeline_id, pipeline_status, artifact_urls.
        """
        branch_name = f"{self.branch_prefix}/{'-'.join(ticket_ids[:3])}"
        self._ensure_branch(branch_name)
        self._commit_files(branch_name, file_paths)

        if self.create_mr:
            mr = self._create_merge_request(branch_name, ticket_ids)
            logger.info("Merge Request created: %s", mr.web_url)

        pipeline = self._trigger_pipeline(branch_name)
        logger.info("Pipeline #%d triggered on branch '%s'", pipeline.id, branch_name)

        status = self._wait_for_pipeline(pipeline.id)
        artifact_urls = self._collect_artifact_urls(pipeline.id)

        return {
            "branch": branch_name,
            "pipeline_id": pipeline.id,
            "pipeline_status": status,
            "artifact_urls": artifact_urls,
            "mr_url": mr.web_url if self.create_mr else None,
        }

    # ------------------------------------------------------------------
    # Private helpers
    # ------------------------------------------------------------------

    def _ensure_branch(self, branch_name: str) -> None:
        existing = [b.name for b in self.project.branches.list(all=True)]
        if branch_name not in existing:
            self.project.branches.create({"branch": branch_name, "ref": self.default_branch})
            logger.info("Created branch: %s", branch_name)
        else:
            logger.info("Branch already exists: %s", branch_name)

    def _commit_files(self, branch_name: str, file_paths: list[str]) -> None:
        actions = []
        for fp in file_paths:
            path = Path(fp)
            if not path.exists():
                logger.warning("File not found, skipping: %s", fp)
                continue
            content = path.read_text(encoding="utf-8")
            try:
                self.project.files.get(file_path=fp, ref=branch_name)
                action = "update"
            except Exception:
                action = "create"
            actions.append({
                "action": action,
                "file_path": fp,
                "content": content,
            })

        if not actions:
            logger.warning("No files to commit.")
            return

        self.project.commits.create({
            "branch": branch_name,
            "commit_message": f"chore(auto-tests): add/update generated tests [{', '.join({a['file_path'].split('/')[0] for a in actions})}]",
            "actions": actions,
        })
        logger.info("Committed %d file(s) to %s", len(actions), branch_name)

    def _create_merge_request(self, branch_name: str, ticket_ids: list[str]):
        ticket_str = ", ".join(ticket_ids)
        return self.project.mergerequests.create({
            "source_branch": branch_name,
            "target_branch": self.mr_target,
            "title": f"[Auto-Tests] Generated tests for {ticket_str}",
            "description": (
                f"Auto-generated Cypress and Playwright tests for Jira tickets: {ticket_str}\n\n"
                "Please review before merging."
            ),
            "remove_source_branch": True,
        })

    def _trigger_pipeline(self, branch_name: str):
        return self.project.pipelines.create({"ref": branch_name})

    def _wait_for_pipeline(self, pipeline_id: int) -> str:
        elapsed = 0
        while elapsed < self.timeout:
            pipeline = self.project.pipelines.get(pipeline_id)
            status = pipeline.status
            logger.info("Pipeline #%d status: %s", pipeline_id, status)
            if status in ("success", "failed", "canceled", "skipped"):
                return status
            time.sleep(self.poll_interval)
            elapsed += self.poll_interval
        logger.warning("Pipeline #%d timed out after %ds", pipeline_id, self.timeout)
        return "timeout"

    def _collect_artifact_urls(self, pipeline_id: int) -> list[str]:
        urls: list[str] = []
        for job in self.project.pipelines.get(pipeline_id).jobs.list(all=True):
            if job.name == self.artifact_job and job.artifacts:
                urls.append(f"{self.project.web_url}/-/jobs/{job.id}/artifacts/download")
        return urls

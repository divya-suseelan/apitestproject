"""
Agent 1 — Jira Reader
Connects to Jira and extracts acceptance criteria from stories matching a JQL filter.
"""
from __future__ import annotations

import logging
from dataclasses import dataclass, field
from typing import Optional

import requests
from requests.auth import HTTPBasicAuth

from .base import BaseAgent, AgentConfig

logger = logging.getLogger(__name__)


@dataclass
class JiraTicket:
    ticket_id: str
    summary: str
    description: str
    acceptance_criteria: str
    labels: list[str] = field(default_factory=list)
    story_points: Optional[float] = None


class JiraReaderAgent(BaseAgent):
    """Fetches Jira stories and extracts acceptance criteria."""

    name = "JiraReaderAgent"

    def __init__(self, config: AgentConfig):
        super().__init__(config)
        jira_cfg = config.raw["jira"]
        self.base_url = jira_cfg["base_url"].rstrip("/")
        self.project_key = jira_cfg["project_key"]
        self.jql = jira_cfg["jql_filter"]
        self.ac_field = jira_cfg.get("acceptance_criteria_field", "description")
        self.auth = HTTPBasicAuth(config.env["JIRA_EMAIL"], config.env["JIRA_API_TOKEN"])
        self.headers = {"Accept": "application/json"}

    def run(self) -> list[JiraTicket]:
        """Return a list of JiraTicket objects with acceptance criteria."""
        logger.info("Fetching Jira tickets with JQL: %s", self.jql)
        tickets = self._search_issues()
        logger.info("Found %d tickets", len(tickets))
        return tickets

    # ------------------------------------------------------------------
    # Private helpers
    # ------------------------------------------------------------------

    def _search_issues(self) -> list[JiraTicket]:
        start_at = 0
        max_results = 50
        all_issues: list[dict] = []

        while True:
            response = requests.get(
                f"{self.base_url}/rest/api/3/search",
                auth=self.auth,
                headers=self.headers,
                params={
                    "jql": self.jql,
                    "startAt": start_at,
                    "maxResults": max_results,
                    "fields": f"summary,description,labels,story_points,{self.ac_field}",
                },
                timeout=30,
            )
            response.raise_for_status()
            data = response.json()
            all_issues.extend(data.get("issues", []))
            if start_at + max_results >= data.get("total", 0):
                break
            start_at += max_results

        return [self._parse_issue(issue) for issue in all_issues]

    def _parse_issue(self, issue: dict) -> JiraTicket:
        fields = issue["fields"]
        description = self._extract_text(fields.get("description") or {})

        # Support separate AC custom field or fall back to description
        if self.ac_field == "description":
            ac_text = description
        else:
            raw_ac = fields.get(self.ac_field) or {}
            ac_text = self._extract_text(raw_ac) if isinstance(raw_ac, dict) else str(raw_ac or "")

        return JiraTicket(
            ticket_id=issue["key"],
            summary=fields.get("summary", ""),
            description=description,
            acceptance_criteria=ac_text,
            labels=[lbl for lbl in (fields.get("labels") or [])],
            story_points=fields.get("story_points"),
        )

    @staticmethod
    def _extract_text(adf_node: dict) -> str:
        """Recursively extract plain text from Atlassian Document Format (ADF) node."""
        if not adf_node:
            return ""
        node_type = adf_node.get("type", "")
        text_parts: list[str] = []

        if node_type == "text":
            return adf_node.get("text", "")

        for child in adf_node.get("content", []):
            text_parts.append(JiraReaderAgent._extract_text(child))

        separator = "\n" if node_type in ("paragraph", "heading", "bulletList", "orderedList", "listItem") else ""
        return separator.join(filter(None, text_parts))

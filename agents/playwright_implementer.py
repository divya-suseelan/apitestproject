"""
Agent 4 — Playwright Implementer
Generates Playwright spec files and Page Object Model classes from test cases.
"""
from __future__ import annotations

import logging
from pathlib import Path

from jinja2 import Environment, FileSystemLoader

from .base import BaseAgent, AgentConfig
from .test_case_generator import TestCase

logger = logging.getLogger(__name__)


class PlaywrightImplementerAgent(BaseAgent):
    """Renders Playwright test files (specs + POM) using Jinja2 templates."""

    name = "PlaywrightImplementerAgent"

    def __init__(self, config: AgentConfig, templates_dir: str = "templates"):
        super().__init__(config)
        self.language = config.raw["test_generation"].get("language", "typescript")
        self.ext = "ts" if self.language == "typescript" else "js"
        self.output_dir = Path("playwright")
        self.jinja_env = Environment(
            loader=FileSystemLoader(templates_dir),
            trim_blocks=True,
            lstrip_blocks=True,
        )

    def run(self, test_cases: list[TestCase]) -> list[str]:
        """
        Generate Playwright files grouped by Jira ticket.
        Returns list of generated file paths.
        """
        grouped = self._group_by_ticket(test_cases)
        generated: list[str] = []

        for ticket_id, cases in grouped.items():
            page_name = self._ticket_to_page_name(ticket_id)

            # Generate Page Object Model
            pom_path = self._render(
                template="playwright_pom.j2",
                dest=self.output_dir / "pages" / f"{page_name}Page.{self.ext}",
                context={"ticket_id": ticket_id, "page_name": page_name, "test_cases": cases, "language": self.language},
            )
            generated.append(pom_path)

            # Generate spec file
            spec_path = self._render(
                template="playwright_spec.j2",
                dest=self.output_dir / "tests" / f"{ticket_id}.spec.{self.ext}",
                context={"ticket_id": ticket_id, "page_name": page_name, "test_cases": cases, "language": self.language},
            )
            generated.append(spec_path)

        logger.info("Playwright: generated %d files", len(generated))
        return generated

    # ------------------------------------------------------------------
    # Private helpers
    # ------------------------------------------------------------------

    def _render(self, template: str, dest: Path, context: dict) -> str:
        dest.parent.mkdir(parents=True, exist_ok=True)
        tmpl = self.jinja_env.get_template(template)
        content = tmpl.render(**context)
        dest.write_text(content, encoding="utf-8")
        logger.debug("  wrote %s", dest)
        return str(dest)

    @staticmethod
    def _group_by_ticket(cases: list[TestCase]) -> dict[str, list[TestCase]]:
        grouped: dict[str, list[TestCase]] = {}
        for case in cases:
            grouped.setdefault(case.ticket_id, []).append(case)
        return grouped

    @staticmethod
    def _ticket_to_page_name(ticket_id: str) -> str:
        """PROJ-123 → Proj123"""
        return ticket_id.replace("-", "")

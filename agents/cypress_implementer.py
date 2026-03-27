"""
Agent 3 — Cypress Implementer
Generates Cypress test files from test cases.

Supports two modes controlled by config:
  bdd: false  → classic spec + Page Object Model (native Cypress)
  bdd: true   → Cucumber .feature file + step definitions + self-healing POM
                (requires @badeball/cypress-cucumber-preprocessor)

Self-healing locators are seeded into a JSON registry so teams can add
fallback selectors without changing agent-generated code.
"""
from __future__ import annotations

import logging
from pathlib import Path

from jinja2 import Environment, FileSystemLoader

from .base import BaseAgent, AgentConfig
from .self_healing import LocatorRegistry
from .test_case_generator import TestCase

logger = logging.getLogger(__name__)


class CypressImplementerAgent(BaseAgent):
    """Renders Cypress test files (specs or Cucumber) using Jinja2 templates."""

    name = "CypressImplementerAgent"

    def __init__(self, config: AgentConfig, templates_dir: str = "templates"):
        super().__init__(config)
        tg = config.raw["test_generation"]
        self.language = tg.get("language", "typescript")
        self.ext = "ts" if self.language == "typescript" else "js"
        self.bdd = tg.get("bdd", False)
        self.self_healing = tg.get("self_healing", False)
        self.output_dir = Path("cypress")
        self.jinja_env = Environment(
            loader=FileSystemLoader(templates_dir),
            trim_blocks=True,
            lstrip_blocks=True,
        )

    def run(self, test_cases: list[TestCase]) -> list[str]:
        """
        Generate Cypress files grouped by Jira ticket.
        Returns list of generated file paths.
        """
        grouped = self._group_by_ticket(test_cases)
        generated: list[str] = []

        for ticket_id, cases in grouped.items():
            page_name = self._ticket_to_page_name(ticket_id)

            # --- Self-healing locator registry ---
            locators_const = ""
            if self.self_healing:
                action_ids = [c.test_id.replace("-", "").replace("_", "") for c in cases]
                registry_path = self.output_dir / "support" / "locator_registry.json"
                registry = LocatorRegistry.seed_from_test_cases(registry_path, page_name, action_ids)
                locators_const = registry.as_ts_const(page_name)
                generated.append(str(registry_path))

            ctx = {
                "ticket_id": ticket_id,
                "page_name": page_name,
                "test_cases": cases,
                "language": self.language,
                "self_healing": self.self_healing,
                "locators_const": locators_const,
            }

            if self.bdd:
                generated += self._generate_bdd(ticket_id, page_name, cases, ctx)
            else:
                generated += self._generate_classic(ticket_id, page_name, ctx)

        logger.info("Cypress: generated %d files", len(generated))
        return generated

    # ------------------------------------------------------------------
    # Mode: BDD (Cucumber)
    # ------------------------------------------------------------------

    def _generate_bdd(
        self,
        ticket_id: str,
        page_name: str,
        cases: list[TestCase],
        ctx: dict,
    ) -> list[str]:
        generated: list[str] = []

        # .feature file
        generated.append(self._render(
            template="cypress_feature.j2",
            dest=self.output_dir / "e2e" / f"{ticket_id}.feature",
            context=ctx,
        ))

        # Step definitions
        generated.append(self._render(
            template="cypress_steps.j2",
            dest=self.output_dir / "support" / "step_definitions" / f"{ticket_id}.steps.{self.ext}",
            context=ctx,
        ))

        # Page Object Model
        generated.append(self._render(
            template="cypress_pom.j2",
            dest=self.output_dir / "pages" / f"{page_name}Page.{self.ext}",
            context=ctx,
        ))

        return generated

    # ------------------------------------------------------------------
    # Mode: classic spec
    # ------------------------------------------------------------------

    def _generate_classic(self, ticket_id: str, page_name: str, ctx: dict) -> list[str]:
        generated: list[str] = []

        generated.append(self._render(
            template="cypress_pom.j2",
            dest=self.output_dir / "pages" / f"{page_name}Page.{self.ext}",
            context=ctx,
        ))

        generated.append(self._render(
            template="cypress_spec.j2",
            dest=self.output_dir / "e2e" / f"{ticket_id}.cy.{self.ext}",
            context=ctx,
        ))

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


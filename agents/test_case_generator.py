"""
Agent 2 — Test Case Generator
Uses an LLM to generate structured test cases from Jira acceptance criteria.
"""
from __future__ import annotations

import json
import logging
from dataclasses import dataclass, field
from typing import Any

from langchain_core.messages import HumanMessage, SystemMessage

from .base import BaseAgent, AgentConfig
from .jira_reader import JiraTicket

logger = logging.getLogger(__name__)

SYSTEM_PROMPT = """You are an expert QA engineer. Given a Jira story's acceptance criteria, \
generate thorough test cases covering positive paths, negative paths, and edge cases.

Return ONLY a valid JSON array with this schema per item:
{
  "test_id": "<ticket_id>_TC_<n>",
  "ticket_id": "<ticket_id>",
  "title": "<short test title>",
  "type": "positive|negative|edge",
  "given": "<precondition>",
  "when": "<action>",
  "then": "<expected result>",
  "tags": ["<tag>"]
}
No extra text, no markdown fences — only the raw JSON array."""


@dataclass
class TestCase:
    test_id: str
    ticket_id: str
    title: str
    type: str          # positive | negative | edge
    given: str
    when: str
    then: str
    tags: list[str] = field(default_factory=list)


class TestCaseGeneratorAgent(BaseAgent):
    """Generates test cases from acceptance criteria using an LLM."""

    name = "TestCaseGeneratorAgent"

    def __init__(self, config: AgentConfig):
        super().__init__(config)
        self.llm = self._build_llm(config)
        self.include_negative = config.raw["test_generation"].get("include_negative_tests", True)
        self.include_edge = config.raw["test_generation"].get("include_edge_cases", True)

    def run(self, tickets: list[JiraTicket]) -> list[TestCase]:
        """Generate test cases for all tickets."""
        all_cases: list[TestCase] = []
        for ticket in tickets:
            logger.info("Generating test cases for %s", ticket.ticket_id)
            cases = self._generate_for_ticket(ticket)
            all_cases.extend(cases)
            logger.info("  → %d test cases generated", len(cases))
        return all_cases

    # ------------------------------------------------------------------
    # Private helpers
    # ------------------------------------------------------------------

    def _generate_for_ticket(self, ticket: JiraTicket) -> list[TestCase]:
        user_msg = (
            f"Jira Ticket: {ticket.ticket_id}\n"
            f"Summary: {ticket.summary}\n\n"
            f"Acceptance Criteria:\n{ticket.acceptance_criteria}\n\n"
            f"Include negative tests: {self.include_negative}\n"
            f"Include edge cases: {self.include_edge}"
        )
        messages = [SystemMessage(content=SYSTEM_PROMPT), HumanMessage(content=user_msg)]
        response = self.llm.invoke(messages)
        return self._parse_response(response.content)

    @staticmethod
    def _parse_response(content: str) -> list[TestCase]:
        # Strip accidental markdown fences
        content = content.strip()
        if content.startswith("```"):
            content = content.split("```")[1]
            if content.lower().startswith("json"):
                content = content[4:]
        raw_cases: list[dict[str, Any]] = json.loads(content)
        return [
            TestCase(
                test_id=c["test_id"],
                ticket_id=c["ticket_id"],
                title=c["title"],
                type=c.get("type", "positive"),
                given=c["given"],
                when=c["when"],
                then=c["then"],
                tags=c.get("tags", []),
            )
            for c in raw_cases
        ]

    @staticmethod
    def _build_llm(config: AgentConfig):
        llm_cfg = config.raw["llm"]
        provider = llm_cfg["provider"]
        model = llm_cfg["model"]
        temperature = llm_cfg.get("temperature", 0.2)
        max_tokens = llm_cfg.get("max_tokens", 4096)

        if provider == "openai":
            from langchain_openai import ChatOpenAI  # noqa: PLC0415
            return ChatOpenAI(
                model=model,
                temperature=temperature,
                max_tokens=max_tokens,
                api_key=config.env["OPENAI_API_KEY"],
            )
        if provider == "anthropic":
            from langchain_anthropic import ChatAnthropic  # noqa: PLC0415
            return ChatAnthropic(
                model=model,
                temperature=temperature,
                max_tokens=max_tokens,
                api_key=config.env["ANTHROPIC_API_KEY"],
            )
        if provider == "azure_openai":
            from langchain_openai import AzureChatOpenAI  # noqa: PLC0415
            return AzureChatOpenAI(
                azure_deployment=config.env["AZURE_OPENAI_DEPLOYMENT"],
                azure_endpoint=config.env["AZURE_OPENAI_ENDPOINT"],
                api_key=config.env["AZURE_OPENAI_API_KEY"],
                temperature=temperature,
                max_tokens=max_tokens,
            )
        raise ValueError(f"Unsupported LLM provider: {provider}")

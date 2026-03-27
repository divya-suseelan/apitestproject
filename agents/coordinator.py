"""
Orchestrator — Coordinator Agent
Runs all agents in sequence and manages the end-to-end pipeline.
"""
from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import Optional

from rich.console import Console
from rich.table import Table

from agents.base import AgentConfig
from agents.cypress_implementer import CypressImplementerAgent
from agents.gitlab_uploader import GitLabUploaderAgent
from agents.jira_reader import JiraReaderAgent
from agents.playwright_implementer import PlaywrightImplementerAgent
from agents.results_uploader import ResultsUploaderAgent, TestResult
from agents.test_case_generator import TestCaseGeneratorAgent

logger = logging.getLogger(__name__)
console = Console()

SUPPORTED_FRAMEWORKS = ("cypress", "playwright")


@dataclass
class PipelineResult:
    tickets_processed: int
    test_cases_generated: int
    framework: str
    test_files: int
    pipeline_id: Optional[int]
    pipeline_status: Optional[str]
    results: list[TestResult]
    mr_url: Optional[str]


class Orchestrator:
    """Coordinates all agents in the test automation pipeline."""

    def __init__(self, config_path: str = "config/config.yaml", framework_override: Optional[str] = None):
        self.config = AgentConfig.from_file(config_path)
        # CLI flag overrides config file
        if framework_override:
            self.config.raw["test_generation"]["framework"] = framework_override

        self.framework: str = self.config.raw["test_generation"].get("framework", "cypress").lower()
        if self.framework not in SUPPORTED_FRAMEWORKS:
            raise ValueError(
                f"Unsupported framework '{self.framework}'. "
                f"Choose one of: {', '.join(SUPPORTED_FRAMEWORKS)}"
            )

    def run(self) -> PipelineResult:
        """Execute the full pipeline end-to-end."""
        console.rule("[bold blue]Multi-Agent Test Automation Pipeline[/bold blue]")
        console.print(f"  Framework : [bold magenta]{self.framework}[/bold magenta]")
        bdd = self.config.raw["test_generation"].get("bdd", False)
        sh = self.config.raw["test_generation"].get("self_healing", False)
        console.print(f"  BDD       : {'[green]enabled[/green]' if bdd else '[yellow]disabled[/yellow]'}")
        console.print(f"  Self-heal : {'[green]enabled[/green]' if sh else '[yellow]disabled[/yellow]'}")

        # Step 1 — Read Jira
        console.print("\n[cyan]Step 1/5[/cyan] Reading Jira tickets…")
        jira_agent = JiraReaderAgent(self.config)
        tickets = jira_agent.run()
        console.print(f"  ✔ {len(tickets)} tickets fetched")

        if not tickets:
            console.print("[yellow]No tickets found. Exiting.[/yellow]")
            return PipelineResult(0, 0, self.framework, 0, None, None, [], None)

        # Step 2 — Generate test cases
        console.print("\n[cyan]Step 2/5[/cyan] Generating test cases…")
        gen_agent = TestCaseGeneratorAgent(self.config)
        test_cases = gen_agent.run(tickets)
        console.print(f"  ✔ {len(test_cases)} test cases generated")

        # Step 3 — Implement tests with the chosen framework
        mode = "BDD (Cucumber)" if bdd else "classic spec"
        console.print(f"\n[cyan]Step 3/5[/cyan] Implementing {self.framework} tests [{mode}]…")
        test_files = self._run_implementer(test_cases)
        console.print(f"  ✔ {len(test_files)} files generated")

        # Step 4 — Upload to GitLab + trigger pipeline
        console.print("\n[cyan]Step 4/5[/cyan] Uploading tests to GitLab…")
        ticket_ids = [t.ticket_id for t in tickets]
        uploader = GitLabUploaderAgent(self.config)
        pipeline_result = uploader.run(test_files, ticket_ids)
        console.print(f"  ✔ Pipeline #{pipeline_result['pipeline_id']} — {pipeline_result['pipeline_status']}")
        if pipeline_result.get("mr_url"):
            console.print(f"  ✔ MR: {pipeline_result['mr_url']}")

        # Step 5 — Upload results to test management
        console.print("\n[cyan]Step 5/5[/cyan] Uploading results to test management tool…")
        results_agent = ResultsUploaderAgent(self.config)
        test_results = results_agent.run(pipeline_result)
        console.print(f"  ✔ {len(test_results)} results uploaded")

        pipeline_run = PipelineResult(
            tickets_processed=len(tickets),
            test_cases_generated=len(test_cases),
            framework=self.framework,
            test_files=len(test_files),
            pipeline_id=pipeline_result.get("pipeline_id"),
            pipeline_status=pipeline_result.get("pipeline_status"),
            results=test_results,
            mr_url=pipeline_result.get("mr_url"),
        )
        self._print_summary(pipeline_run)
        return pipeline_run

    # ------------------------------------------------------------------
    # Private helpers
    # ------------------------------------------------------------------

    def _run_implementer(self, test_cases) -> list[str]:
        if self.framework == "cypress":
            return CypressImplementerAgent(self.config).run(test_cases)
        return PlaywrightImplementerAgent(self.config).run(test_cases)

    @staticmethod
    def _print_summary(result: PipelineResult) -> None:
        console.rule("[bold green]Pipeline Summary[/bold green]")
        table = Table(show_header=False, box=None)
        table.add_column(style="bold")
        table.add_column()
        table.add_row("Framework", result.framework)
        table.add_row("Tickets processed", str(result.tickets_processed))
        table.add_row("Test cases generated", str(result.test_cases_generated))
        table.add_row("Test files generated", str(result.test_files))
        table.add_row("Pipeline ID", str(result.pipeline_id or "N/A"))
        table.add_row("Pipeline status", str(result.pipeline_status or "N/A"))
        if result.mr_url:
            table.add_row("Merge Request", result.mr_url)

        passed = sum(1 for r in result.results if r.status == "PASS")
        failed = sum(1 for r in result.results if r.status == "FAIL")
        table.add_row("Tests passed", f"[green]{passed}[/green]")
        table.add_row("Tests failed", f"[red]{failed}[/red]")
        console.print(table)

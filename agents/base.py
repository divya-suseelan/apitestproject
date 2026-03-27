"""
Base classes shared by all agents.
"""
from __future__ import annotations

import logging
import os
from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Any

import yaml
from dotenv import load_dotenv

load_dotenv()
logger = logging.getLogger(__name__)


@dataclass
class AgentConfig:
    """Holds parsed config.yaml and resolved environment variables."""
    raw: dict[str, Any]
    env: dict[str, str]

    @classmethod
    def from_file(cls, path: str = "config/config.yaml") -> "AgentConfig":
        with open(path, "r", encoding="utf-8") as fh:
            raw = yaml.safe_load(fh)

        env_keys = [
            "JIRA_EMAIL", "JIRA_API_TOKEN",
            "OPENAI_API_KEY", "ANTHROPIC_API_KEY",
            "AZURE_OPENAI_API_KEY", "AZURE_OPENAI_ENDPOINT", "AZURE_OPENAI_DEPLOYMENT",
            "GITLAB_TOKEN",
            "XRAY_CLIENT_ID", "XRAY_CLIENT_SECRET",
            "ZEPHYR_API_TOKEN",
            "QTEST_BASE_URL", "QTEST_API_TOKEN",
        ]
        env = {k: os.getenv(k, "") for k in env_keys}
        return cls(raw=raw, env=env)


class BaseAgent(ABC):
    """Abstract base for all pipeline agents."""

    name: str = "BaseAgent"

    def __init__(self, config: AgentConfig):
        self.config = config
        logging.basicConfig(
            level=config.raw.get("output", {}).get("log_level", "INFO"),
            format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
        )

    @abstractmethod
    def run(self, *args, **kwargs) -> Any:
        """Execute the agent and return its output."""

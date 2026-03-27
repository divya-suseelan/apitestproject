"""
Self-Healing Locator support
Provides a LocatorRegistry that stores multiple fallback selectors per element,
and helper utilities that are referenced from the generated POM/step templates.

The registry JSON lives alongside the test files so teams can evolve selectors
without touching agent-generated code.
"""
from __future__ import annotations

import json
import logging
from pathlib import Path

logger = logging.getLogger(__name__)

# Shape of a single element entry in the registry
LocatorEntry = list[str]   # ordered list of CSS/XPath selectors (first = preferred)


class LocatorRegistry:
    """
    Manages a JSON file that maps page-class → element-name → [selector1, selector2, …].

    Example file content:
    {
      "PROJ123Page": {
        "submitButton": [
          "[data-testid='submit']",
          "button[type='submit']",
          "#submit-btn",
          "button:text('Submit')"
        ]
      }
    }
    """

    def __init__(self, registry_path: str | Path):
        self.path = Path(registry_path)
        self._data: dict[str, dict[str, LocatorEntry]] = {}
        if self.path.exists():
            self._load()

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def get(self, page_name: str, element_name: str) -> LocatorEntry:
        """Return the ordered list of selectors for an element (empty list if unknown)."""
        return self._data.get(page_name, {}).get(element_name, [])

    def set(self, page_name: str, element_name: str, locators: LocatorEntry) -> None:
        """Register (or update) locators for an element."""
        self._data.setdefault(page_name, {})[element_name] = locators
        self._save()

    def seed_page(self, page_name: str, elements: dict[str, LocatorEntry]) -> None:
        """Register multiple elements for a page at once (does not overwrite existing)."""
        page = self._data.setdefault(page_name, {})
        for element, locators in elements.items():
            if element not in page:
                page[element] = locators
        self._save()

    def as_ts_const(self, page_name: str) -> str:
        """
        Return a TypeScript const declaration for this page's locators,
        suitable for embedding directly into a generated POM file.

        Example output:
          export const PROJ123PageLocators = {
            submitButton: ["[data-testid='submit']", "button[type='submit']"],
          };
        """
        entries = self._data.get(page_name, {})
        if not entries:
            return f"export const {page_name}Locators: Record<string, string[]> = {{}};"

        lines = [f"export const {page_name}Locators: Record<string, string[]> = {{"]
        for name, selectors in entries.items():
            serialised = json.dumps(selectors)
            lines.append(f"  {name}: {serialised},")
        lines.append("};")
        return "\n".join(lines)

    # ------------------------------------------------------------------
    # Private helpers
    # ------------------------------------------------------------------

    def _load(self) -> None:
        try:
            self._data = json.loads(self.path.read_text(encoding="utf-8"))
        except Exception as exc:
            logger.warning("Could not load locator registry %s: %s", self.path, exc)
            self._data = {}

    def _save(self) -> None:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self.path.write_text(json.dumps(self._data, indent=2), encoding="utf-8")

    # ------------------------------------------------------------------
    # Factory helpers for seeding an empty registry from test cases
    # ------------------------------------------------------------------

    @classmethod
    def seed_from_test_cases(
        cls,
        registry_path: str | Path,
        page_name: str,
        action_ids: list[str],
    ) -> "LocatorRegistry":
        """
        Bootstrap a registry with placeholder locator arrays for each action.
        Teams fill in the real selectors from their application.
        """
        registry = cls(registry_path)
        placeholders: dict[str, LocatorEntry] = {
            action_id: [
                f"[data-testid='{action_id}']",
                f"#{action_id}",
                f"[aria-label='{action_id}']",
            ]
            for action_id in action_ids
        }
        registry.seed_page(page_name, placeholders)
        return registry

#!/usr/bin/env python3
"""
main.py — Entry point for the multi-agent test automation pipeline.

Usage:
    python main.py                              # Run with default config
    python main.py --config path/to/cfg.yaml
    python main.py --framework cypress          # Override framework from CLI
    python main.py --framework playwright
"""
from __future__ import annotations

import argparse
import sys

from agents.coordinator import Orchestrator, SUPPORTED_FRAMEWORKS


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Multi-Agent Test Automation Pipeline",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument(
        "--config",
        default="config/config.yaml",
        help="Path to config YAML (default: config/config.yaml)",
    )
    parser.add_argument(
        "--framework",
        choices=list(SUPPORTED_FRAMEWORKS),
        default=None,
        help="Testing framework to use. Overrides test_generation.framework in config.yaml.",
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    try:
        orchestrator = Orchestrator(config_path=args.config, framework_override=args.framework)
        result = orchestrator.run()
        failed = sum(1 for r in result.results if r.status == "FAIL")
        return 1 if failed > 0 else 0
    except KeyboardInterrupt:
        print("\nAborted.")
        return 130
    except Exception as exc:
        print(f"[ERROR] Pipeline failed: {exc}", file=sys.stderr)
        raise


if __name__ == "__main__":
    sys.exit(main())

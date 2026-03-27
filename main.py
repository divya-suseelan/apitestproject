#!/usr/bin/env python3
"""
main.py — Entry point for the multi-agent test automation pipeline.

Usage:
    python main.py                          # Run with default config
    python main.py --config path/to/cfg.yaml
    python main.py --tickets PROJ-1 PROJ-2  # Run for specific tickets only
"""
from __future__ import annotations

import argparse
import sys

from agents.coordinator import Orchestrator


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
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    try:
        orchestrator = Orchestrator(config_path=args.config)
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

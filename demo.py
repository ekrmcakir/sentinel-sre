#!/usr/bin/env python3
"""
Sentinel-SRE: Interactive Live Demonstration
Runs a complete simulated cloud failure and autonomous self-healing recovery.
"""
import sys
from pathlib import Path

# Ensure package root is in sys.path
sys.path.insert(0, str(Path(__file__).parent))

from rich.console import Console
from rich.panel import Panel
from sentinel_sre.cli import simulate_incident

console = Console()

if __name__ == "__main__":
    console.print(
        Panel.fit(
            "[bold cyan]🚀 SENTINEL-SRE: AUTONOMOUS CLOUD RELIABILITY ENGINE[/bold cyan]\n"
            "[dim]Simulating real-world AWS CloudWatch alarm breach, deterministic RCA, policy guardrails, and self-healing remediation.[/dim]",
            border_style="cyan",
        )
    )
    # Run Lambda Concurrency Exhaustion scenario
    simulate_incident(scenario_id="sc-lambda-01", save_postmortem=True)

import asyncio
import sys
from typing import Optional
import typer
from rich.console import Console
from rich.panel import Panel
from rich.table import Table
from rich.progress import Progress, SpinnerColumn, TextColumn
from rich.markdown import Markdown

from sentinel_sre.config import settings
from sentinel_sre.models.incident import Incident
from sentinel_sre.orchestrator.engine import orchestrator
from sentinel_sre.simulator.chaos_engine import chaos_engine

app = typer.Typer(
    name="sentinel",
    help="Sentinel-SRE: Autonomous Cloud Reliability & Self-Healing Platform",
    add_completion=False,
)
console = Console()


@app.command("scenarios")
def list_scenarios():
    """List all available chaos and outage scenarios."""
    scenarios = chaos_engine.list_scenarios()
    table = Table(title="🚨 Sentinel-SRE Simulated Outage Scenarios", show_header=True, header_style="bold cyan")
    table.add_column("ID", style="bold yellow")
    table.add_column("Scenario Name", style="bold white")
    table.add_column("Service", style="green")
    table.add_column("Severity", style="red")
    table.add_column("Alarm Metric", style="blue")

    for sc in scenarios:
        table.add_row(
            sc["scenario_id"],
            sc["name"],
            sc["service"].upper(),
            sc.get("severity", "P2_HIGH"),
            f"{sc['metric_name']} (breached: {sc['current_value']})",
        )

    console.print(table)


@app.command("simulate")
def simulate_incident(
    scenario_id: str = typer.Argument("sc-lambda-01", help="Scenario ID (e.g. sc-lambda-01, sc-sqs-02, sc-ecs-03)"),
    save_postmortem: bool = typer.Option(True, "--save-report", help="Save generated markdown post-mortem to disk"),
):
    """Inject a cloud outage scenario and run the autonomous remediation lifecycle."""
    try:
        scenario = chaos_engine.load_scenario(scenario_id)
    except FileNotFoundError:
        console.print(f"[bold red]❌ Error:[/bold red] Scenario '{scenario_id}' not found. Run `sentinel scenarios` to see available scenarios.")
        raise typer.Exit(code=1)

    console.print(
        Panel(
            f"[bold red]🚨 CLOUD OUTAGE INJECTED[/bold red]\n"
            f"[bold white]Title:[/bold white] {scenario['name']}\n"
            f"[bold white]Resource:[/bold white] {scenario['resource_name']} ({scenario['service'].upper()})\n"
            f"[bold white]Alarm Breach:[/bold white] {scenario['metric_name']} reached [bold red]{scenario['current_value']}[/bold red] (Threshold: {scenario['threshold']})\n"
            f"[bold white]Impact:[/bold white] {scenario['description']}",
            title="[bold yellow]Sentinel-SRE Telemetry Ingress[/bold yellow]",
            border_style="red",
        )
    )

    incident: Incident = chaos_engine.trigger_incident(scenario)

    with Progress(
        SpinnerColumn(),
        TextColumn("[progress.description]{task.description}"),
        transient=True,
    ) as progress:
        task = progress.add_task("[cyan]Ingesting telemetry & conducting Root-Cause Analysis...", total=None)
        
        async def run():
            return await orchestrator.handle_incident(incident)

        resolved_incident, postmortem_md = asyncio.run(run())

    # Display Resolution Summary
    status_color = "green" if resolved_incident.status.value == "RESOLVED" else "red"
    console.print(
        Panel(
            f"[bold {status_color}]✨ INCIDENT STATUS: {resolved_incident.status.value}[/bold {status_color}]\n"
            f"[bold white]Incident ID:[/bold white] {resolved_incident.incident_id}\n"
            f"[bold white]Total MTTR (Resolution Time):[/bold white] [bold green]{resolved_incident.mttr_seconds:.2f} seconds[/bold green]\n"
            f"[bold white]Timeline Steps Executed:[/bold white] {len(resolved_incident.timeline)}",
            title="[bold green]Autonomous Remediation Summary[/bold green]",
            border_style=status_color,
        )
    )

    # Timeline Table
    t_table = Table(title="⏱️ Incident Execution Timeline", show_header=True, header_style="bold magenta")
    t_table.add_column("Phase", style="cyan")
    t_table.add_column("Event Description", style="white")

    for event in resolved_incident.timeline:
        t_table.add_row(f"[{event['phase']}]", event["message"])
    console.print(t_table)

    if postmortem_md and save_postmortem:
        report_file = f"postmortem_{resolved_incident.incident_id}.md"
        with open(report_file, "w", encoding="utf-8") as f:
            f.write(postmortem_md)
        console.print(f"\n[bold green]📄 Post-Mortem Report generated & saved to:[/bold green] [underline]{report_file}[/underline]")


@app.command("serve")
def start_server(
    host: str = typer.Option(settings.api_host, "--host", help="API Host"),
    port: int = typer.Option(settings.api_port, "--port", help="API Port"),
):
    """Start the Sentinel-SRE webhook server for live CloudWatch alerts."""
    import uvicorn
    console.print(f"[bold green]🚀 Starting Sentinel-SRE Webhook Server on http://{host}:{port}[/bold green]")
    uvicorn.run("sentinel_sre.api.server:app", host=host, port=port, reload=False)


def main():
    app()


if __name__ == "__main__":
    main()

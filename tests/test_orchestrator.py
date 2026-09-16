import pytest
from sentinel_sre.models.incident import IncidentStatus
from sentinel_sre.orchestrator.engine import SentinelOrchestrator
from sentinel_sre.simulator.chaos_engine import chaos_engine
from sentinel_sre.telemetry.mock_collector import MockTelemetryCollector


@pytest.mark.asyncio
async def test_full_orchestration_lifecycle_lambda():
    orchestrator = SentinelOrchestrator(telemetry_collector=MockTelemetryCollector())
    scenario_data = chaos_engine.load_scenario("sc-lambda-01")
    incident = chaos_engine.trigger_incident(scenario_data)

    resolved_incident, postmortem_md = await orchestrator.handle_incident(incident)

    assert resolved_incident.status == IncidentStatus.RESOLVED
    assert resolved_incident.mttr_seconds is not None
    assert resolved_incident.mttr_seconds >= 0.0
    assert len(resolved_incident.timeline) >= 6
    assert postmortem_md is not None
    assert "Incident Post-Mortem" in postmortem_md
    assert "Root Cause Analysis" in postmortem_md
    assert "Safety & Policy-as-Code" in postmortem_md


@pytest.mark.asyncio
async def test_full_orchestration_lifecycle_sqs():
    orchestrator = SentinelOrchestrator(telemetry_collector=MockTelemetryCollector())
    scenario_data = chaos_engine.load_scenario("sc-sqs-02")
    incident = chaos_engine.trigger_incident(scenario_data)

    resolved_incident, postmortem_md = await orchestrator.handle_incident(incident)

    assert resolved_incident.status == IncidentStatus.RESOLVED
    assert "sqs:start_dlq_redrive" in postmortem_md


@pytest.mark.asyncio
async def test_full_orchestration_lifecycle_ecs():
    orchestrator = SentinelOrchestrator(telemetry_collector=MockTelemetryCollector())
    scenario_data = chaos_engine.load_scenario("sc-ecs-03")
    incident = chaos_engine.trigger_incident(scenario_data)

    resolved_incident, postmortem_md = await orchestrator.handle_incident(incident)

    assert resolved_incident.status == IncidentStatus.RESOLVED
    assert "ecs:recycle_service" in postmortem_md

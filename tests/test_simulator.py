from sentinel_sre.simulator.chaos_engine import ChaosSimulationEngine


def test_scenario_loader():
    engine = ChaosSimulationEngine()
    scenarios = engine.list_scenarios()
    assert len(scenarios) >= 3

    scenario_ids = [s["scenario_id"] for s in scenarios]
    assert "sc-lambda-01" in scenario_ids
    assert "sc-sqs-02" in scenario_ids
    assert "sc-ecs-03" in scenario_ids


def test_trigger_incident_creates_valid_model():
    engine = ChaosSimulationEngine()
    data = engine.load_scenario("sc-lambda-01")
    incident = engine.trigger_incident(data)

    assert incident.incident_id.startswith("INC-")
    assert incident.alarm.service == "lambda"
    assert incident.alarm.threshold == 5.0
    assert len(incident.timeline) == 1

import json
from pathlib import Path
from typing import Dict, List, Optional

from sentinel_sre.models.incident import CloudAlarm, Incident, IncidentSeverity


class ChaosSimulationEngine:
    """Manages failure scenario loading and cloud incident injection."""

    def __init__(self, scenarios_dir: Optional[Path] = None):
        self.scenarios_dir = scenarios_dir or Path(__file__).parent / "scenarios"

    def list_scenarios(self) -> List[Dict]:
        scenarios = []
        for file in sorted(self.scenarios_dir.glob("*.json")):
            with open(file, "r", encoding="utf-8") as f:
                scenarios.append(json.load(f))
        return scenarios

    def load_scenario(self, scenario_id_or_name: str) -> Dict:
        for file in self.scenarios_dir.glob("*.json"):
            with open(file, "r", encoding="utf-8") as f:
                data = json.load(f)
                if data.get("scenario_id") == scenario_id_or_name or file.stem == scenario_id_or_name:
                    return data
        raise FileNotFoundError(f"Scenario '{scenario_id_or_name}' not found.")

    def trigger_incident(self, scenario_data: Dict) -> Incident:
        alarm = CloudAlarm(
            alarm_name=scenario_data["alarm_name"],
            service=scenario_data["service"],
            resource_arn=scenario_data["resource_arn"],
            resource_name=scenario_data["resource_name"],
            metric_name=scenario_data["metric_name"],
            threshold=scenario_data["threshold"],
            current_value=scenario_data["current_value"],
            description=scenario_data.get("description"),
            raw_payload=scenario_data,
        )

        incident = Incident(
            title=f"[{alarm.service.upper()}] {scenario_data['name']}",
            severity=IncidentSeverity(scenario_data.get("severity", "P2_HIGH")),
            alarm=alarm,
            metadata={"scenario_id": scenario_data.get("scenario_id")},
        )
        incident.add_timeline_event("TRIGGER", f"CloudWatch alarm '{alarm.alarm_name}' fired.")
        return incident


chaos_engine = ChaosSimulationEngine()

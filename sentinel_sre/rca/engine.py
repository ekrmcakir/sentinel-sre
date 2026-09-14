import uuid
from datetime import datetime, timezone
from typing import Optional

from sentinel_sre.config import settings
from sentinel_sre.models.incident import CloudAlarm, Incident
from sentinel_sre.models.rca import Hypothesis, RootCauseAnalysis
from sentinel_sre.models.telemetry import TelemetrySnapshot
from sentinel_sre.rca.heuristics import DeterministicHeuristicEngine


class RootCauseAnalysisEngine:
    """
    Orchestrates deterministic heuristics and structured AI reasoning.
    """

    def __init__(self):
        self.heuristic_engine = DeterministicHeuristicEngine()

    async def diagnose(
        self, incident: Incident, telemetry: TelemetrySnapshot
    ) -> RootCauseAnalysis:
        # 1. Deterministic Heuristic Analysis
        hypotheses = self.heuristic_engine.analyze(incident.alarm, telemetry)
        primary = hypotheses[0]
        alternatives = hypotheses[1:] if len(hypotheses) > 1 else []

        reasoning_summary = (
            f"Automated RCA identified '{primary.summary}' as the leading root cause "
            f"with confidence {primary.confidence_score*100:.1f}%. "
            f"Key evidence: {'; '.join(primary.evidence[:2])}."
        )

        analysis = RootCauseAnalysis(
            analysis_id=f"RCA-{uuid.uuid4().hex[:6].upper()}",
            incident_id=incident.incident_id,
            primary_hypothesis=primary,
            alternative_hypotheses=alternatives,
            diagnosed_at=datetime.now(timezone.utc),
            reasoning_summary=reasoning_summary,
            telemetry_summary={
                "total_logs_analyzed": len(telemetry.logs),
                "metrics_analyzed": len(telemetry.metrics),
                "anomalies_detected": len(telemetry.anomalies),
            },
            confidence=primary.confidence_score,
        )

        return analysis


rca_engine = RootCauseAnalysisEngine()

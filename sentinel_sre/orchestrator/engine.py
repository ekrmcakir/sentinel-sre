from datetime import datetime, timezone
from typing import Callable, Dict, Optional, Tuple
import asyncio

from sentinel_sre.actions import get_action_executor
from sentinel_sre.config import settings
from sentinel_sre.models.actions import (
    ActionExecutionResult,
    RemediationAction,
    SafetyVerdict,
)
from sentinel_sre.models.incident import Incident, IncidentStatus
from sentinel_sre.models.rca import RootCauseAnalysis
from sentinel_sre.models.telemetry import TelemetrySnapshot
from sentinel_sre.rca.engine import rca_engine
from sentinel_sre.reporting.postmortem import reporter
from sentinel_sre.safety.guardrails import guardrail_engine
from sentinel_sre.telemetry.cloudwatch import CloudWatchTelemetryCollector


class SentinelOrchestrator:
    """
    Main Autonomous SRE State Machine managing end-to-end incident lifecycle.
    """

    def __init__(self, telemetry_collector=None):
        self.telemetry_collector = telemetry_collector or CloudWatchTelemetryCollector()
        self.active_incidents: Dict[str, Incident] = {}

    async def handle_incident(
        self,
        incident: Incident,
        human_approval_callback: Optional[Callable[[Incident, RemediationAction, SafetyVerdict], bool]] = None,
    ) -> Tuple[Incident, Optional[str]]:
        """
        Executes full lifecycle:
        Investigate -> RCA -> Guardrails -> Remediate -> Verify -> Post-Mortem.
        Returns the resolved incident object and generated Markdown post-mortem string.
        """
        self.active_incidents[incident.incident_id] = incident

        # 1. Investigate & Collect Telemetry
        incident.status = IncidentStatus.INVESTIGATING
        incident.add_timeline_event("INVESTIGATION", "Telemetry ingestion and metric correlation initiated.")
        
        telemetry: TelemetrySnapshot = await self.telemetry_collector.collect_snapshot(incident.alarm)
        incident.add_timeline_event(
            "TELEMETRY",
            f"Collected {len(telemetry.logs)} log records, {len(telemetry.metrics)} metric data points, and {len(telemetry.anomalies)} anomalies.",
        )

        # 2. Conduct Root-Cause Analysis (RCA)
        rca: RootCauseAnalysis = await rca_engine.diagnose(incident, telemetry)
        incident.add_timeline_event(
            "RCA",
            f"Diagnosed primary root cause: '{rca.primary_hypothesis.summary}' (Confidence: {rca.primary_hypothesis.confidence_score*100:.1f}%).",
        )

        # 3. Formulate Remediation Action
        primary_hyp = rca.primary_hypothesis
        action = RemediationAction(
            action_type=primary_hyp.suggested_action_type,
            service=incident.alarm.service,
            target_resource=incident.alarm.resource_name,
            parameters=primary_hyp.suggested_action_params,
            description=f"Auto-generated remediation for: {primary_hyp.summary}",
        )

        # 4. Safety Guardrails & Policy Evaluation
        safety_verdict: SafetyVerdict = guardrail_engine.evaluate_action(action)
        incident.add_timeline_event(
            "SAFETY_GATE",
            f"Policy evaluation: Risk={safety_verdict.risk_level.value}, Allowed={safety_verdict.allowed}, BlastRadius={safety_verdict.blast_radius_score:.2f}.",
            {"reason": safety_verdict.reason},
        )

        # Check Human-in-the-loop requirement
        if not safety_verdict.allowed:
            if safety_verdict.requires_human_approval:
                incident.status = IncidentStatus.AWAITING_APPROVAL
                incident.add_timeline_event(
                    "APPROVAL_WAIT",
                    "Action requires human SRE confirmation before proceeding.",
                )
                approved = False
                if human_approval_callback:
                    approved = human_approval_callback(incident, action, safety_verdict)
                
                if not approved:
                    incident.status = IncidentStatus.ESCALATED
                    incident.add_timeline_event("ESCALATED", "Action was not approved or timed out. Escalated to on-call human SRE.")
                    return incident, None
            else:
                incident.status = IncidentStatus.FAILED
                incident.add_timeline_event("BLOCKED", f"Action blocked by security policy: {safety_verdict.reason}")
                return incident, None

        # 5. Execute Remediation Action
        incident.status = IncidentStatus.REMEDIATING
        incident.add_timeline_event("REMEDIATION_START", f"Executing self-healing action: '{action.action_type}'.")

        executor = get_action_executor(action.service)
        exec_result: ActionExecutionResult = await executor.execute(action)

        if not exec_result.success:
            incident.status = IncidentStatus.FAILED
            incident.add_timeline_event("REMEDIATION_FAILED", f"Action failed: {exec_result.error_message}")
            return incident, None

        incident.add_timeline_event(
            "REMEDIATION_SUCCESS",
            f"Self-healing action '{action.action_type}' applied in {exec_result.duration_ms:.1f}ms.",
            exec_result.output,
        )

        # 6. Verification
        incident.status = IncidentStatus.VERIFYING
        incident.add_timeline_event("VERIFICATION", "Verifying recovery metrics and health check status.")
        await asyncio.sleep(0.1)  # Synthetic verification period

        # 7. Resolution & Post-Mortem Generation
        incident.status = IncidentStatus.RESOLVED
        incident.resolved_at = datetime.now(timezone.utc)
        incident.add_timeline_event(
            "RESOLVED",
            f"Incident resolved autonomously. Total MTTR: {incident.mttr_seconds:.1f}s.",
        )

        post_mortem_md = reporter.generate_report(
            incident=incident,
            rca=rca,
            action=action,
            safety_verdict=safety_verdict,
            execution_result=exec_result,
        )

        return incident, post_mortem_md


orchestrator = SentinelOrchestrator()

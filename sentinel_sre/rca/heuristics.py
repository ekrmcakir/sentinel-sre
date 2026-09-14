import re
from typing import Dict, List, Optional
from sentinel_sre.models.incident import CloudAlarm
from sentinel_sre.models.rca import Hypothesis
from sentinel_sre.models.telemetry import TelemetrySnapshot


class DeterministicHeuristicEngine:
    """
    High-speed deterministic pattern matching and signature correlation.
    """

    LAMBDA_PATTERNS = [
        (
            r"(TooManyRequestsException|ConcurrencyLimitExceeded|Rate exceeded)",
            "Lambda Concurrency Saturation & Throttling",
            "lambda:set_concurrency",
            {"concurrency": 100},
            0.95,
        ),
        (
            r"Task timed out after.*seconds",
            "Lambda Execution Timeout / Downstream Latency",
            "lambda:update_memory",
            {"memory_mb": 1024},
            0.88,
        ),
    ]

    SQS_PATTERNS = [
        (
            r"(DLQ|DeadLetterQueue|DBConnectionTimeout|ConnectionResetError)",
            "Downstream Processing Failure causing DLQ Accumulation",
            "sqs:start_dlq_redrive",
            {"max_number_of_messages": 5000},
            0.92,
        ),
    ]

    ECS_PATTERNS = [
        (
            r"(exit_code=137|OOMKilled|OutOfMemoryError)",
            "ECS Task Out-Of-Memory (OOM) CrashLoop",
            "ecs:recycle_service",
            {"force_new_deployment": True},
            0.94,
        ),
        (
            r"(Health check failed|HTTP 502|unhealthy target)",
            "Unhealthy Container Task State",
            "ecs:recycle_service",
            {"force_new_deployment": True},
            0.89,
        ),
    ]

    def analyze(self, alarm: CloudAlarm, telemetry: TelemetrySnapshot) -> List[Hypothesis]:
        hypotheses: List[Hypothesis] = []
        all_logs_text = " ".join([l.message for l in telemetry.logs] + telemetry.error_patterns)

        patterns = []
        if alarm.service == "lambda":
            patterns = self.LAMBDA_PATTERNS
        elif alarm.service == "sqs":
            patterns = self.SQS_PATTERNS
        elif alarm.service == "ecs":
            patterns = self.ECS_PATTERNS

        for idx, (regex, summary, action_type, action_params, base_conf) in enumerate(patterns):
            matches = re.findall(regex, all_logs_text, re.IGNORECASE)
            if matches:
                evidence = [
                    f"Found {len(matches)} occurrences of signature '{matches[0]}'",
                    f"Correlated with CloudAlarm {alarm.alarm_name} (metric value {alarm.current_value:.1f})",
                ]
                for anomaly in telemetry.anomalies:
                    evidence.append(
                        f"Metric anomaly detected on '{anomaly['metric']}' with sigma {anomaly['deviation_sigma']:.1f}"
                    )

                hypotheses.append(
                    Hypothesis(
                        id=f"HYP-{alarm.service.upper()}-{idx+1}",
                        summary=summary,
                        confidence_score=base_conf,
                        evidence=evidence,
                        contributing_factors=[
                            f"Service: {alarm.service}",
                            f"Resource: {alarm.resource_name}",
                            f"Alarm Threshold: {alarm.threshold}",
                        ],
                        suggested_action_type=action_type,
                        suggested_action_params=action_params,
                    )
                )

        if not hypotheses:
            # Generic fallback hypothesis
            hypotheses.append(
                Hypothesis(
                    id="HYP-GEN-1",
                    summary=f"Unclassified performance degradation on {alarm.resource_name}",
                    confidence_score=0.60,
                    evidence=[f"Alarm {alarm.alarm_name} breached threshold {alarm.threshold}"],
                    contributing_factors=[f"Metric {alarm.metric_name} = {alarm.current_value}"],
                    suggested_action_type=f"{alarm.service}:recycle_service" if alarm.service == "ecs" else f"{alarm.service}:inspect",
                    suggested_action_params={},
                )
            )

        return sorted(hypotheses, key=lambda h: h.confidence_score, reverse=True)

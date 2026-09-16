from typing import Any, Dict
from fastapi import FastAPI, HTTPException, status
from pydantic import BaseModel

from sentinel_sre.models.incident import CloudAlarm, Incident, IncidentSeverity
from sentinel_sre.orchestrator.engine import orchestrator

app = FastAPI(
    title="Sentinel-SRE Autonomous API",
    description="Webhook ingress and self-healing orchestration API for CloudWatch & Alertmanager",
    version="1.0.0",
)


class WebhookAlarmPayload(BaseModel):
    AlarmName: str
    Service: str
    ResourceArn: str
    ResourceName: str
    MetricName: str
    Threshold: float
    CurrentValue: float
    Severity: str = "P2_HIGH"
    Description: str = ""


@app.get("/healthz")
async def healthz():
    return {"status": "healthy", "service": "sentinel-sre"}


@app.post("/api/v1/webhook/cloudwatch", status_code=status.HTTP_200_OK)
async def handle_cloudwatch_alarm(payload: WebhookAlarmPayload):
    """Ingests AWS CloudWatch Alarms and triggers autonomous resolution."""
    alarm = CloudAlarm(
        alarm_name=payload.AlarmName,
        service=payload.Service.lower(),
        resource_arn=payload.ResourceArn,
        resource_name=payload.ResourceName,
        metric_name=payload.MetricName,
        threshold=payload.Threshold,
        current_value=payload.CurrentValue,
        description=payload.Description,
    )

    incident = Incident(
        title=f"[{alarm.service.upper()}] CloudWatch Alarm: {alarm.alarm_name}",
        severity=IncidentSeverity(payload.Severity),
        alarm=alarm,
    )

    resolved_incident, postmortem = await orchestrator.handle_incident(incident)

    return {
        "incident_id": resolved_incident.incident_id,
        "status": resolved_incident.status.value,
        "mttr_seconds": resolved_incident.mttr_seconds,
        "postmortem_preview": postmortem[:300] if postmortem else None,
    }


@app.get("/api/v1/incidents/{incident_id}")
async def get_incident(incident_id: str):
    if incident_id not in orchestrator.active_incidents:
        raise HTTPException(status_code=404, detail=f"Incident {incident_id} not found.")
    return orchestrator.active_incidents[incident_id]

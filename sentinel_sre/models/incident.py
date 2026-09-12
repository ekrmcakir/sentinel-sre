from datetime import datetime, timezone
from enum import Enum
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field
import uuid


class IncidentSeverity(str, Enum):
    P1_CRITICAL = "P1_CRITICAL"
    P2_HIGH = "P2_HIGH"
    P3_MEDIUM = "P3_MEDIUM"
    P4_LOW = "P4_LOW"


class IncidentStatus(str, Enum):
    TRIGGERED = "TRIGGERED"
    INVESTIGATING = "INVESTIGATING"
    AWAITING_APPROVAL = "AWAITING_APPROVAL"
    REMEDIATING = "REMEDIATING"
    VERIFYING = "VERIFYING"
    RESOLVED = "RESOLVED"
    FAILED = "FAILED"
    ESCALATED = "ESCALATED"


class CloudAlarm(BaseModel):
    alarm_id: str = Field(default_factory=lambda: f"alm-{uuid.uuid4().hex[:8]}")
    alarm_name: str
    service: str  # e.g., "lambda", "sqs", "ecs", "rds"
    resource_arn: str
    resource_name: str
    metric_name: str
    threshold: float
    current_value: float
    evaluation_periods: int = 1
    description: Optional[str] = None
    region: str = "us-east-1"
    timestamp: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    raw_payload: Dict[str, Any] = Field(default_factory=dict)


class Incident(BaseModel):
    incident_id: str = Field(default_factory=lambda: f"INC-{uuid.uuid4().hex[:6].upper()}")
    title: str
    severity: IncidentSeverity
    status: IncidentStatus = IncidentStatus.TRIGGERED
    alarm: CloudAlarm
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    updated_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    resolved_at: Optional[datetime] = None
    timeline: List[Dict[str, Any]] = Field(default_factory=list)
    metadata: Dict[str, Any] = Field(default_factory=dict)

    def add_timeline_event(self, phase: str, message: str, details: Optional[Dict[str, Any]] = None):
        event = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "phase": phase,
            "message": message,
            "details": details or {},
        }
        self.timeline.append(event)
        self.updated_at = datetime.now(timezone.utc)

    @property
    def mttr_seconds(self) -> Optional[float]:
        if self.resolved_at:
            return (self.resolved_at - self.created_at).total_seconds()
        return None

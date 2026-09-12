from datetime import datetime, timezone
from enum import Enum
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field
import uuid


class ActionRiskLevel(str, Enum):
    LOW = "LOW"            # Safe auto-remediation (e.g. DLQ redrive, safe restart)
    MEDIUM = "MEDIUM"      # Scale changes, task recycle
    HIGH = "HIGH"          # Schema changes, node teardown, DB restarts (requires human gate)
    CRITICAL = "CRITICAL"  # Destructive changes (strictly blocked or multi-admin gate)


class SafetyVerdict(BaseModel):
    allowed: bool
    requires_human_approval: bool
    risk_level: ActionRiskLevel
    reason: str
    violations: List[str] = Field(default_factory=list)
    blast_radius_score: float = 0.0


class RemediationAction(BaseModel):
    action_id: str = Field(default_factory=lambda: f"ACT-{uuid.uuid4().hex[:6].upper()}")
    action_type: str  # e.g., "lambda:set_concurrency", "sqs:start_dlq_redrive", "ecs:recycle_service"
    service: str
    target_resource: str
    parameters: Dict[str, Any] = Field(default_factory=dict)
    risk_level: ActionRiskLevel = ActionRiskLevel.LOW
    description: str
    rollback_parameters: Optional[Dict[str, Any]] = None
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


class ActionExecutionResult(BaseModel):
    action_id: str
    success: bool
    executed_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    duration_ms: float
    output: Dict[str, Any] = Field(default_factory=dict)
    error_message: Optional[str] = None
    rolled_back: bool = False
    rollback_result: Optional[Dict[str, Any]] = None

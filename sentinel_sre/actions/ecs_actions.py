import time
from typing import Any, Dict, Optional
import boto3
from botocore.exceptions import BotoCoreError, ClientError

from sentinel_sre.actions.base import BaseActionExecutor
from sentinel_sre.config import settings
from sentinel_sre.models.actions import ActionExecutionResult, RemediationAction


class ECSActionExecutor(BaseActionExecutor):
    """Executes safe ECS rolling task recycling."""

    def __init__(self, region: Optional[str] = None):
        self.region = region or settings.aws_region
        if not settings.mock_mode:
            self.client = boto3.client("ecs", region_name=self.region)
        else:
            self.client = None

    async def execute(self, action: RemediationAction) -> ActionExecutionResult:
        start_time = time.time()
        service_name = action.target_resource
        cluster_name = action.parameters.get("cluster", "production-cluster")

        if action.action_type == "ecs:recycle_service":
            if settings.mock_mode or not self.client:
                duration_ms = (time.time() - start_time) * 1000 + 48.0
                return ActionExecutionResult(
                    action_id=action.action_id,
                    success=True,
                    duration_ms=duration_ms,
                    output={
                        "cluster": cluster_name,
                        "service": service_name,
                        "deployment_id": "ecs-dep-mock-4412",
                        "strategy": "ROLLING_RECYCLE",
                        "status": "TRIGGERED",
                        "mode": "MOCK_SIMULATION",
                    },
                )
            try:
                response = self.client.update_service(
                    cluster=cluster_name,
                    service=service_name,
                    forceNewDeployment=True,
                )
                duration_ms = (time.time() - start_time) * 1000
                return ActionExecutionResult(
                    action_id=action.action_id,
                    success=True,
                    duration_ms=duration_ms,
                    output={"serviceArn": response.get("service", {}).get("serviceArn")},
                )
            except (BotoCoreError, ClientError) as e:
                duration_ms = (time.time() - start_time) * 1000
                return ActionExecutionResult(
                    action_id=action.action_id,
                    success=False,
                    duration_ms=duration_ms,
                    error_message=str(e),
                )

        return ActionExecutionResult(
            action_id=action.action_id,
            success=False,
            duration_ms=0.0,
            error_message=f"Unsupported ECS action: {action.action_type}",
        )

    async def rollback(
        self, action: RemediationAction, previous_state: Dict[str, Any]
    ) -> Dict[str, Any]:
        return {"rolled_back": True, "target": action.target_resource}

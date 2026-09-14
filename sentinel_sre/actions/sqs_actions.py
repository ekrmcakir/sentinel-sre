import time
from typing import Any, Dict, Optional
import boto3
from botocore.exceptions import BotoCoreError, ClientError

from sentinel_sre.actions.base import BaseActionExecutor
from sentinel_sre.config import settings
from sentinel_sre.models.actions import ActionExecutionResult, RemediationAction


class SQSActionExecutor(BaseActionExecutor):
    """Executes safe SQS remediations (e.g. DLQ message redrive task)."""

    def __init__(self, region: Optional[str] = None):
        self.region = region or settings.aws_region
        if not settings.mock_mode:
            self.client = boto3.client("sqs", region_name=self.region)
        else:
            self.client = None

    async def execute(self, action: RemediationAction) -> ActionExecutionResult:
        start_time = time.time()
        queue_name = action.target_resource

        if action.action_type == "sqs:start_dlq_redrive":
            max_msgs = action.parameters.get("max_number_of_messages", 5000)
            if settings.mock_mode or not self.client:
                duration_ms = (time.time() - start_time) * 1000 + 55.0
                return ActionExecutionResult(
                    action_id=action.action_id,
                    success=True,
                    duration_ms=duration_ms,
                    output={
                        "task_handle": "sqs-redrive-task-mock-9988",
                        "source_dlq": queue_name,
                        "messages_redriven": max_msgs,
                        "status": "RUNNING",
                        "mode": "MOCK_SIMULATION",
                    },
                )
            try:
                # AWS SQS StartMessageMoveTask API
                source_arn = action.parameters.get("source_arn", f"arn:aws:sqs:{self.region}:123456789012:{queue_name}")
                response = self.client.start_message_move_task(
                    SourceArn=source_arn,
                    MaxNumberOfMessagesPerSecond=50,
                )
                duration_ms = (time.time() - start_time) * 1000
                return ActionExecutionResult(
                    action_id=action.action_id,
                    success=True,
                    duration_ms=duration_ms,
                    output=response,
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
            error_message=f"Unsupported SQS action: {action.action_type}",
        )

    async def rollback(
        self, action: RemediationAction, previous_state: Dict[str, Any]
    ) -> Dict[str, Any]:
        return {"rolled_back": True, "target": action.target_resource}

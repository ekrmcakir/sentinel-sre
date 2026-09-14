import time
from typing import Any, Dict, Optional
import boto3
from botocore.exceptions import BotoCoreError, ClientError

from sentinel_sre.actions.base import BaseActionExecutor
from sentinel_sre.config import settings
from sentinel_sre.models.actions import ActionExecutionResult, RemediationAction


class LambdaActionExecutor(BaseActionExecutor):
    """Executes safe Lambda adjustments (concurrency, memory scaling)."""

    def __init__(self, region: Optional[str] = None):
        self.region = region or settings.aws_region
        if not settings.mock_mode:
            self.client = boto3.client("lambda", region_name=self.region)
        else:
            self.client = None

    async def execute(self, action: RemediationAction) -> ActionExecutionResult:
        start_time = time.time()
        fn_name = action.target_resource

        if action.action_type == "lambda:set_concurrency":
            concurrency = action.parameters.get("concurrency", 100)
            if settings.mock_mode or not self.client:
                duration_ms = (time.time() - start_time) * 1000 + 42.0
                return ActionExecutionResult(
                    action_id=action.action_id,
                    success=True,
                    duration_ms=duration_ms,
                    output={
                        "resource": fn_name,
                        "reserved_concurrency": concurrency,
                        "status": "APPLIED",
                        "mode": "MOCK_SIMULATION",
                    },
                )
            try:
                self.client.put_function_concurrency(
                    FunctionName=fn_name,
                    ReservedConcurrentExecutions=concurrency,
                )
                duration_ms = (time.time() - start_time) * 1000
                return ActionExecutionResult(
                    action_id=action.action_id,
                    success=True,
                    duration_ms=duration_ms,
                    output={"FunctionName": fn_name, "ReservedConcurrentExecutions": concurrency},
                )
            except (BotoCoreError, ClientError) as e:
                duration_ms = (time.time() - start_time) * 1000
                return ActionExecutionResult(
                    action_id=action.action_id,
                    success=False,
                    duration_ms=duration_ms,
                    error_message=str(e),
                )

        elif action.action_type == "lambda:update_memory":
            memory_mb = action.parameters.get("memory_mb", 1024)
            if settings.mock_mode or not self.client:
                duration_ms = (time.time() - start_time) * 1000 + 38.0
                return ActionExecutionResult(
                    action_id=action.action_id,
                    success=True,
                    duration_ms=duration_ms,
                    output={
                        "resource": fn_name,
                        "memory_mb": memory_mb,
                        "status": "APPLIED",
                        "mode": "MOCK_SIMULATION",
                    },
                )
            try:
                self.client.update_function_configuration(
                    FunctionName=fn_name,
                    MemorySize=memory_mb,
                )
                duration_ms = (time.time() - start_time) * 1000
                return ActionExecutionResult(
                    action_id=action.action_id,
                    success=True,
                    duration_ms=duration_ms,
                    output={"FunctionName": fn_name, "MemorySize": memory_mb},
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
            error_message=f"Unsupported lambda action: {action.action_type}",
        )

    async def rollback(
        self, action: RemediationAction, previous_state: Dict[str, Any]
    ) -> Dict[str, Any]:
        return {"rolled_back": True, "target": action.target_resource, "state": previous_state}

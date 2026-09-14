from typing import Dict
from sentinel_sre.actions.base import BaseActionExecutor
from sentinel_sre.actions.lambda_actions import LambdaActionExecutor
from sentinel_sre.actions.sqs_actions import SQSActionExecutor
from sentinel_sre.actions.ecs_actions import ECSActionExecutor


def get_action_executor(service: str) -> BaseActionExecutor:
    """Factory returning the appropriate executor for a given service."""
    registry: Dict[str, BaseActionExecutor] = {
        "lambda": LambdaActionExecutor(),
        "sqs": SQSActionExecutor(),
        "ecs": ECSActionExecutor(),
    }
    if service not in registry:
        raise ValueError(f"No registered executor for service '{service}'")
    return registry[service]


__all__ = [
    "BaseActionExecutor",
    "LambdaActionExecutor",
    "SQSActionExecutor",
    "ECSActionExecutor",
    "get_action_executor",
]

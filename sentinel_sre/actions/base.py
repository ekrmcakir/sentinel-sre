from abc import ABC, abstractmethod
from typing import Any, Dict, Optional
import time

from sentinel_sre.config import settings
from sentinel_sre.models.actions import ActionExecutionResult, RemediationAction


class BaseActionExecutor(ABC):
    """
    Abstract interface for executing idempotent remediation actions with rollback capabilities.
    """

    @abstractmethod
    async def execute(self, action: RemediationAction) -> ActionExecutionResult:
        """Executes the action on cloud infrastructure."""
        pass

    @abstractmethod
    async def rollback(
        self, action: RemediationAction, previous_state: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Rolls back the action to previous state."""
        pass

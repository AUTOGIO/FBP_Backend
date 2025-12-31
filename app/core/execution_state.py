"""Execution state tracking for system automation.

This module provides execution state management independent of jobs.
ExecutionState owns progress, checkpoints, and recovery information.
Jobs only reference execution via execution_id.

Phase 2: In-memory only. Persistence is a future phase.

⚠️ ARCHITECTURAL GUARDRAIL:
This module OWNS execution state. Do NOT store execution state in external
systems (FoKS, n8n, databases). Do NOT synchronize state with external systems.
Execution state MUST remain within FBP boundaries.
"""

from __future__ import annotations

import uuid
from datetime import datetime
from enum import Enum
from typing import Any

from app.core.logging_config import setup_logger

logger = setup_logger(__name__)


class ExecutionPhase(str, Enum):
    """Execution phase enumeration.

    Phases represent deterministic system automation steps.
    Each phase is idempotent and checkpointed.
    """

    LOGIN = "login"
    FORM_FILL = "form_fill"
    SUBMIT = "submit"
    DOWNLOAD = "download"
    COMPLETED = "completed"
    FAILED = "failed"


class ExecutionState:
    """Execution state representation.

    ExecutionState owns execution progress, checkpoints, and recovery.
    It is independent of Job, which serves only as metadata envelope.

    Attributes:
        execution_id: Unique execution identifier
        job_id: Associated job identifier (for backward compatibility)
        phase: Current execution phase
        checkpoint_data: Phase-specific checkpoint data for recovery
        created_at: Execution creation timestamp
        started_at: Execution start timestamp
        phase_entered_at: Timestamp when current phase was entered
        completed_at: Execution completion timestamp
        error: Error message if execution failed
    """

    def __init__(
        self,
        execution_id: str,
        job_id: str,
        phase: ExecutionPhase = ExecutionPhase.LOGIN,
    ) -> None:
        """Initialize execution state.

        Args:
            execution_id: Unique execution identifier
            job_id: Associated job identifier
            phase: Initial execution phase (default: LOGIN)
        """
        self.execution_id = execution_id
        self.job_id = job_id
        self.phase = phase
        self.checkpoint_data: dict[str, Any] = {}
        self.created_at = datetime.utcnow()
        self.started_at: datetime | None = None
        self.phase_entered_at = datetime.utcnow()
        self.completed_at: datetime | None = None
        self.error: str | None = None

    def start(self) -> None:
        """Mark execution as started."""
        self.started_at = datetime.utcnow()
        logger.info(
            f"Execution {self.execution_id} started " f"(job_id: {self.job_id})"
        )

    def transition_to_phase(
        self,
        phase: ExecutionPhase,
        checkpoint_data: dict[str, Any] | None = None,
    ) -> None:
        """Transition to a new execution phase with checkpoint data.

        Args:
            phase: Target execution phase
            checkpoint_data: Optional checkpoint data for recovery
        """
        self.phase = phase
        self.phase_entered_at = datetime.utcnow()
        if checkpoint_data:
            self.checkpoint_data.update(checkpoint_data)
        logger.info(
            f"Execution {self.execution_id} transitioned to phase: " f"{phase.value}"
        )

    def update_checkpoint(self, checkpoint_data: dict[str, Any]) -> None:
        """Update checkpoint data for current phase.

        Args:
            checkpoint_data: Checkpoint data to merge with existing
        """
        self.checkpoint_data.update(checkpoint_data)
        logger.debug(
            f"Execution {self.execution_id} checkpoint updated in phase: "
            f"{self.phase.value}"
        )

    def complete(self, result: dict[str, Any] | None = None) -> None:
        """Mark execution as completed.

        Args:
            result: Optional final result data to store in checkpoint
        """
        self.phase = ExecutionPhase.COMPLETED
        self.completed_at = datetime.utcnow()
        if result:
            self.checkpoint_data["result"] = result
        logger.info(
            f"Execution {self.execution_id} completed " f"(job_id: {self.job_id})"
        )

    def fail(self, error: str, error_data: dict[str, Any] | None = None) -> None:
        """Mark execution as failed.

        Args:
            error: Error message
            error_data: Optional error context data
        """
        self.phase = ExecutionPhase.FAILED
        self.completed_at = datetime.utcnow()
        self.error = error
        if error_data:
            self.checkpoint_data["error_data"] = error_data
        logger.error(
            f"Execution {self.execution_id} failed " f"(job_id: {self.job_id}): {error}"
        )

    def to_dict(self) -> dict[str, Any]:
        """Convert execution state to dictionary for API/serialization.

        Returns:
            Dictionary representation of execution state
        """
        return {
            "execution_id": self.execution_id,
            "job_id": self.job_id,
            "phase": self.phase.value,
            "checkpoint_data": self.checkpoint_data,
            "created_at": self.created_at.isoformat(),
            "started_at": (self.started_at.isoformat() if self.started_at else None),
            "phase_entered_at": self.phase_entered_at.isoformat(),
            "completed_at": (
                self.completed_at.isoformat() if self.completed_at else None
            ),
            "error": self.error,
        }

    def is_terminal(self) -> bool:
        """Check if execution is in a terminal state.

        Returns:
            True if execution is COMPLETED or FAILED
        """
        return self.phase in (
            ExecutionPhase.COMPLETED,
            ExecutionPhase.FAILED,
        )


class ExecutionStateStore:
    """In-memory execution state store.

    Phase 2: In-memory only (can be extended to Redis/DB later).
    Provides CRUD operations for ExecutionState instances.

    This store is independent of JobStore. ExecutionState owns execution
    progress, while Job serves as metadata envelope.
    """

    def __init__(self) -> None:
        """Initialize execution state store."""
        self._states: dict[str, ExecutionState] = {}

    def create_execution(
        self, job_id: str, phase: ExecutionPhase = ExecutionPhase.LOGIN
    ) -> ExecutionState:
        """Create a new execution state.

        Args:
            job_id: Associated job identifier
            phase: Initial execution phase (default: LOGIN)

        Returns:
            Created execution state
        """
        execution_id = str(uuid.uuid4())
        state = ExecutionState(execution_id, job_id, phase)
        self._states[execution_id] = state
        logger.info(
            f"Created execution {execution_id} for job {job_id} "
            f"(phase: {phase.value})"
        )
        return state

    def get_execution(self, execution_id: str) -> ExecutionState | None:
        """Get execution state by ID.

        Args:
            execution_id: Execution identifier

        Returns:
            Execution state if found, None otherwise
        """
        return self._states.get(execution_id)

    def get_execution_by_job_id(self, job_id: str) -> ExecutionState | None:
        """Get execution state by job ID.

        Args:
            job_id: Job identifier

        Returns:
            Execution state if found, None otherwise
        """
        for state in self._states.values():
            if state.job_id == job_id:
                return state
        return None

    def update_execution(self, state: ExecutionState) -> None:
        """Update execution state in store.

        Args:
            state: Execution state to update
        """
        self._states[state.execution_id] = state
        logger.debug(f"Updated execution {state.execution_id}")

    def list_executions(
        self,
        job_id: str | None = None,
        phase: ExecutionPhase | None = None,
        limit: int = 100,
    ) -> list[ExecutionState]:
        """List executions with optional filters.

        Args:
            job_id: Filter by job identifier
            phase: Filter by execution phase
            limit: Maximum number of executions to return

        Returns:
            List of matching execution states
        """
        executions = list(self._states.values())

        if job_id:
            executions = [e for e in executions if e.job_id == job_id]

        if phase:
            executions = [e for e in executions if e.phase == phase]

        # Sort by created_at descending (most recent first)
        executions.sort(key=lambda e: e.created_at, reverse=True)

        return executions[:limit]

    def delete_execution(self, execution_id: str) -> bool:
        """Delete execution state from store.

        Args:
            execution_id: Execution identifier

        Returns:
            True if execution was deleted, False if not found
        """
        if execution_id in self._states:
            del self._states[execution_id]
            logger.info(f"Deleted execution {execution_id}")
            return True
        return False


# Global execution state store instance
execution_state_store = ExecutionStateStore()

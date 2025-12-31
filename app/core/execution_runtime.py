"""Execution runtime for owned execution contexts.

This module provides execution runtime management for system automation.
Executions run in owned async contexts, not as fire-and-forget tasks.

Phase 3: Owned execution management.

⚠️ ARCHITECTURAL GUARDRAIL:
This module OWNS execution and state. Do NOT add orchestration logic here.
Do NOT delegate execution to external systems. Do NOT add workflow engines,
background job frameworks, schedulers, or worker pools.
"""

from __future__ import annotations

import asyncio
from typing import Any

from app.core.execution_state import ExecutionState, execution_state_store
from app.core.logging_config import setup_logger

logger = setup_logger(__name__)


class ExecutionRuntime:
    """Runtime for managing owned execution contexts.

    This runtime owns execution lifecycle, ensuring executions are
    tracked and managed properly. Executions are NOT fire-and-forget.
    """

    def __init__(self) -> None:
        """Initialize execution runtime."""
        self._running_executions: dict[str, asyncio.Task] = {}

    async def start_execution(
        self,
        execution_state: ExecutionState,
        execution_fn: Any,  # Callable that performs the work
    ) -> None:
        """Start execution in owned async context.

        Args:
            execution_state: Execution state to track
            execution_fn: Async function that performs the execution work
        """
        execution_id = execution_state.execution_id

        # Check if already running
        if execution_id in self._running_executions:
            logger.warning(f"Execution {execution_id} already running, ignoring start")
            return

        # Create owned task
        task = asyncio.create_task(self._run_execution(execution_state, execution_fn))
        self._running_executions[execution_id] = task

        logger.info(
            f"Started execution {execution_id} " f"(job_id: {execution_state.job_id})"
        )

    async def _run_execution(
        self, execution_state: ExecutionState, execution_fn: Any
    ) -> None:
        """Run execution with proper state tracking.

        Args:
            execution_state: Execution state to track
            execution_fn: Async function that performs the execution work
        """
        execution_id = execution_state.execution_id

        try:
            execution_state.start()
            execution_state_store.update_execution(execution_state)

            await execution_fn(execution_state)

            # If not already completed/failed by execution_fn
            if not execution_state.is_terminal():
                execution_state.complete()
                execution_state_store.update_execution(execution_state)

        except Exception as e:
            error_msg = str(e)
            logger.exception(f"Execution {execution_id} failed: {error_msg}")
            if not execution_state.is_terminal():
                execution_state.fail(error_msg)
        finally:
            execution_state_store.update_execution(execution_state)
            # Remove from running executions
            self._running_executions.pop(execution_id, None)

    async def cancel_execution(self, execution_id: str) -> bool:
        """Cancel a running execution.

        Args:
            execution_id: Execution identifier

        Returns:
            True if execution was cancelled, False if not found/running
        """
        task = self._running_executions.get(execution_id)
        if not task:
            return False

        task.cancel()
        try:
            await task
        except asyncio.CancelledError:
            pass

        execution_state = execution_state_store.get_execution(execution_id)
        if execution_state and not execution_state.is_terminal():
            execution_state.fail("Execution cancelled")
            execution_state_store.update_execution(execution_state)

        self._running_executions.pop(execution_id, None)
        logger.info(f"Cancelled execution {execution_id}")
        return True

    def is_running(self, execution_id: str) -> bool:
        """Check if execution is currently running.

        Args:
            execution_id: Execution identifier

        Returns:
            True if execution is running
        """
        return execution_id in self._running_executions

    async def shutdown(self) -> None:
        """Shutdown runtime, cancelling all running executions."""
        running_ids = list(self._running_executions.keys())
        logger.info(f"Shutting down execution runtime: {len(running_ids)} executions")

        for execution_id in running_ids:
            await self.cancel_execution(execution_id)

        logger.info("Execution runtime shutdown complete")


# Global execution runtime instance
execution_runtime = ExecutionRuntime()

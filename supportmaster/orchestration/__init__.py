"""Bounded, fail-closed orchestration primitives for read-only work."""

from .contracts import (
    BranchResult,
    BranchStatus,
    ForkJoinResult,
    ForkGroupSpec,
    TaskSpec,
)
from .fork_join import BranchHandler, ForkJoinExecutor, record_fork_join_result

__all__ = [
    "BranchHandler",
    "BranchResult",
    "BranchStatus",
    "ForkGroupSpec",
    "ForkJoinExecutor",
    "ForkJoinResult",
    "TaskSpec",
    "record_fork_join_result",
]

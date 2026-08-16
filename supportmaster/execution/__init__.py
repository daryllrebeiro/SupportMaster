"""Verified side-effect adapters and executors for SupportMaster."""

from .adapters import (
    GitHubAdapter,
    GitRepositoryAdapter,
    InMemoryGitHubAdapter,
    SubprocessGitAdapter,
    SubprocessTestRunner,
    TestRunnerAdapter,
)
from .publication import (
    PublicationExecutor,
    build_github_publish_result,
    persist_publication_receipts,
)
from .contracts import PublicationExecutionResult
from .contracts import EngineeringExecutionResult
from .engineering import CodeChangeAdapter, ControlledEngineeringExecutor, persist_engineering_receipts

__all__ = [
    "GitHubAdapter",
    "GitRepositoryAdapter",
    "InMemoryGitHubAdapter",
    "SubprocessGitAdapter",
    "SubprocessTestRunner",
    "TestRunnerAdapter",
    "PublicationExecutor",
    "build_github_publish_result",
    "persist_publication_receipts",
    "PublicationExecutionResult",
    "CodeChangeAdapter",
    "ControlledEngineeringExecutor",
    "EngineeringExecutionResult",
    "persist_engineering_receipts",
]

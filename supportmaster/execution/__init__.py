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
]

"""Least-privilege integration adapters and deterministic test doubles."""

from .adapters import (
    InMemoryCIAdapter,
    InMemoryIssueTrackerAdapter,
    InMemoryMonitoringAdapter,
    InMemoryNotificationAdapter,
)
from .http import JsonHttpTransport, UrllibJsonTransport
from .github import PolicyGuardedGitHubAdapter
from .bundle import IntegrationEvidenceBundle, ReadOnlyIntegrationBundle
from .http_adapters import (
    HttpCIAdapter,
    HttpIssueTrackerAdapter,
    HttpMonitoringAdapter,
    HttpNotificationAdapter,
)
from .contracts import (
    CIStatus,
    IncidentRecord,
    IntegrationPermission,
    IssueRecord,
    MetricSample,
)
from .policy import (
    IntegrationGateway,
    IntegrationPolicy,
    record_integration_receipt,
    record_integration_result,
)

__all__ = [
    "CIStatus",
    "IncidentRecord",
    "IntegrationGateway",
    "IntegrationPermission",
    "IntegrationPolicy",
    "InMemoryCIAdapter",
    "InMemoryIssueTrackerAdapter",
    "InMemoryMonitoringAdapter",
    "InMemoryNotificationAdapter",
    "HttpCIAdapter",
    "HttpIssueTrackerAdapter",
    "HttpMonitoringAdapter",
    "HttpNotificationAdapter",
    "IssueRecord",
    "JsonHttpTransport",
    "MetricSample",
    "PolicyGuardedGitHubAdapter",
    "IntegrationEvidenceBundle",
    "ReadOnlyIntegrationBundle",
    "record_integration_receipt",
    "record_integration_result",
    "UrllibJsonTransport",
]

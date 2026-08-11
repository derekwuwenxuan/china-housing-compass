"""Provider protocol used by refresh orchestration."""

from typing import Any, List, Mapping, Protocol, Union, runtime_checkable

from ..models import EvidenceRecord


class ProviderError(RuntimeError):
    """Raised when a provider cannot safely produce fresh normalized evidence."""


@runtime_checkable
class Provider(Protocol):
    """A source adapter that returns normalized, source-graded evidence."""

    def fetch(self, context: Mapping[str, Any]) -> List[EvidenceRecord]:
        ...


@runtime_checkable
class SnapshotProvider(Protocol):
    """A provider that supplies a complete normalized snapshot."""

    def fetch_snapshot(self, context: Mapping[str, Any]) -> Mapping[str, Any]:
        ...


RefreshProvider = Union[Provider, SnapshotProvider]

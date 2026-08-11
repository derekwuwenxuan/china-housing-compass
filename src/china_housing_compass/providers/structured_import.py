"""Provider adapter for a saved normalized JSON snapshot."""

from pathlib import Path
from typing import Any, List, Mapping

from ..importers import evidence_records, load_snapshot
from ..models import EvidenceRecord


class StructuredImportProvider:
    def __init__(self, path: Any):
        self.path = Path(path)

    def fetch(self, context: Mapping[str, Any]) -> List[EvidenceRecord]:
        del context
        return evidence_records(self.fetch_snapshot({}))

    def fetch_snapshot(self, context: Mapping[str, Any]) -> Mapping[str, Any]:
        del context
        return load_snapshot(self.path)

"""Resilient category refresh orchestration that preserves prior evidence."""

from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Mapping, Optional, Sequence, Tuple

from .database import ResearchDatabase
from .importers import import_snapshot
from .models import PropertyRef, ValidationError
from .providers.base import RefreshProvider, SnapshotProvider


@dataclass(frozen=True)
class RefreshRequest:
    property_id: int
    categories: Sequence[str] = ()
    context: Mapping[str, Any] = field(default_factory=dict)
    dashboard_dir: Optional[Path] = None

    def __post_init__(self) -> None:
        if self.property_id <= 0:
            raise ValidationError("property_id must be greater than zero")
        if len(self.categories) != len(set(self.categories)):
            raise ValidationError("refresh categories must be unique")
        if any(not category.strip() for category in self.categories):
            raise ValidationError("refresh category cannot be empty")


@dataclass(frozen=True)
class RefreshResult:
    status: str
    attempted: Tuple[str, ...]
    succeeded: Tuple[str, ...]
    failures: Mapping[str, str]
    stale_categories: Tuple[str, ...]
    added_records: int
    dashboard_outputs: Tuple[str, ...] = ()
    unchanged: Tuple[str, ...] = ()


def run_refresh(
    db: ResearchDatabase,
    providers: Mapping[str, RefreshProvider],
    request: RefreshRequest,
) -> RefreshResult:
    """Refresh requested categories independently and retain old rows on failure."""

    db.get_property(request.property_id)
    selected = tuple(request.categories) if request.categories else tuple(providers)
    started_at = datetime.now(timezone.utc)
    succeeded = []
    unchanged = []
    failures = {}
    added_records = 0

    for category in selected:
        provider = providers.get(category)
        if provider is None:
            failures[category] = "provider is not configured"
            continue
        try:
            context = dict(request.context)
            if isinstance(provider, SnapshotProvider):
                snapshot = provider.fetch_snapshot(context)
                snapshot_ref = PropertyRef(**dict(snapshot.get("property", {})))
                existing = db.get_property(request.property_id)
                expected_identity = (
                    existing["city"], existing["district"], existing["project_name"],
                    existing["community_name"], existing["building"], existing["unit_name"],
                )
                snapshot_identity = (
                    snapshot_ref.city, snapshot_ref.district, snapshot_ref.project_name,
                    snapshot_ref.community_name, snapshot_ref.building, snapshot_ref.unit_name,
                )
                if snapshot_identity != expected_identity:
                    raise ValidationError("snapshot property_id does not match refresh request")
                imported = import_snapshot(db, snapshot)
                if imported["property_id"] != request.property_id:
                    raise ValidationError("snapshot property_id does not match refresh request")
                added_records += imported["imported_evidence"] + sum(
                    imported.get("imported_layers", {}).values()
                )
                if imported.get("unchanged"):
                    unchanged.append(category)
                    continue
            else:
                records = provider.fetch(context)
                if records is None:
                    raise ValidationError("provider returned no record list")
                snapshot_id = f"refresh:{started_at.isoformat()}:{category}"
                ids = db.add_evidence_batch(request.property_id, records, snapshot_id=snapshot_id)
                added_records += len(ids)
            succeeded.append(category)
        except Exception as exc:
            failures[category] = f"{type(exc).__name__}: {exc}"

    if failures and (succeeded or unchanged):
        status = "partial"
    elif failures:
        status = "failed"
    elif unchanged and not succeeded:
        status = "unchanged"
    else:
        status = "success"
    finished_at = datetime.now(timezone.utc)
    db.record_refresh(
        request.property_id,
        status,
        selected,
        tuple(succeeded),
        failures,
        started_at,
        finished_at,
        unchanged=tuple(unchanged),
    )

    dashboard_outputs: Tuple[str, ...] = ()
    if request.dashboard_dir is not None:
        try:
            from .dashboard import build_dashboard

            dashboard_outputs = tuple(
                str(path) for path in build_dashboard(db.path, request.dashboard_dir)
            )
        except Exception as exc:
            failures = dict(failures)
            failures["dashboard"] = f"{type(exc).__name__}: {exc}"
            if status in {"success", "unchanged"}:
                status = "partial"

    return RefreshResult(
        status=status,
        attempted=selected,
        succeeded=tuple(succeeded),
        failures=failures,
        stale_categories=tuple(category for category in selected if category in failures),
        added_records=added_records,
        dashboard_outputs=dashboard_outputs,
        unchanged=tuple(unchanged),
    )

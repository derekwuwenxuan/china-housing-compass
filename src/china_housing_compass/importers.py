"""Strict, atomic imports for normalized China Housing Compass snapshots."""

from datetime import date, datetime, timezone
from decimal import Decimal
import json
from pathlib import Path
from typing import Any, Dict, List, Mapping

from .database import ResearchDatabase, _encode
from .models import (
    SUPPORTED_UNITS,
    EvidenceGrade,
    EvidenceRecord,
    PropertyRef,
    ValidationError,
)
from .research_layers import LAYER_KEYS, validate_research_layers


NUMERIC_UNITS = {"RMB", "RMB/㎡", "RMB/month", "㎡", "ratio", "index", "months", "years"}


def _date(value: Any, name: str) -> date:
    if not isinstance(value, str):
        raise ValidationError(f"{name} must use ISO date format")
    try:
        return date.fromisoformat(value)
    except ValueError as exc:
        raise ValidationError(f"{name} must use ISO date format") from exc


def _grade(value: Any, name: str) -> EvidenceGrade:
    try:
        return EvidenceGrade(value)
    except (ValueError, TypeError) as exc:
        raise ValidationError(f"{name} must be A, B, C, or D") from exc


def load_snapshot(path: Any) -> Dict[str, Any]:
    """Read JSON without converting decimal values through binary floats."""

    try:
        payload = json.loads(
            Path(path).read_text(encoding="utf-8"),
            parse_float=Decimal,
        )
    except (OSError, json.JSONDecodeError) as exc:
        raise ValidationError(f"cannot load snapshot: {exc}") from exc
    validate_snapshot(payload)
    return payload


def validate_snapshot(payload: Mapping[str, Any]) -> None:
    """Validate identity, sources, dates, units, grades, and source references."""

    if not isinstance(payload, Mapping):
        raise ValidationError("snapshot must be an object")
    version = payload.get("schema_version")
    if isinstance(version, bool) or not isinstance(version, int) or version not in {1, 2}:
        raise ValidationError("schema_version must be 1 or 2")
    snapshot_id = payload.get("snapshot_id")
    if not isinstance(snapshot_id, str) or not snapshot_id.strip():
        raise ValidationError("snapshot_id is required")

    property_data = payload.get("property")
    if not isinstance(property_data, Mapping):
        raise ValidationError("property is required")
    try:
        PropertyRef(**dict(property_data))
    except TypeError as exc:
        raise ValidationError(f"invalid property fields: {exc}") from exc

    sources = payload.get("sources")
    evidence = payload.get("evidence")
    if not isinstance(sources, list) or not sources:
        raise ValidationError("sources must be a non-empty list")
    if not isinstance(evidence, list):
        raise ValidationError("evidence must be a list")
    layers = _research_layers(payload)
    if version == 1 and not evidence:
        raise ValidationError("evidence must be a non-empty list")
    if version == 2 and not evidence and not any(layers.values()):
        raise ValidationError("version 2 snapshots require evidence or research layers")

    source_registry = {}
    for index, source in enumerate(sources):
        if not isinstance(source, Mapping):
            raise ValidationError(f"sources[{index}] must be an object")
        source_id = source.get("source_id")
        if not isinstance(source_id, str) or not source_id.strip():
            raise ValidationError(f"sources[{index}].source_id is required")
        if source_id in source_registry:
            raise ValidationError(f"duplicate source_id: {source_id}")
        url = source.get("url")
        if not isinstance(url, str) or not url.strip():
            raise ValidationError(f"sources[{index}].url is required")
        _grade(source.get("grade"), f"sources[{index}].grade")
        _date(source.get("retrieved_on"), f"sources[{index}].retrieved_on")
        source_registry[source_id] = source

    identities = set()
    for index, item in enumerate(evidence):
        if not isinstance(item, Mapping):
            raise ValidationError(f"evidence[{index}] must be an object")
        evidence_type = item.get("evidence_type")
        if not isinstance(evidence_type, str) or not evidence_type.strip():
            raise ValidationError(f"evidence[{index}].evidence_type is required")
        unit = item.get("unit")
        if unit not in SUPPORTED_UNITS:
            raise ValidationError(f"unsupported unit: {unit}")
        source_id = item.get("source_id")
        if source_id not in source_registry:
            raise ValidationError(f"evidence[{index}] references unknown source_id: {source_id}")
        item_grade = _grade(item.get("grade"), f"evidence[{index}].grade")
        source_grade = _grade(source_registry[source_id].get("grade"), f"source:{source_id}.grade")
        if item_grade != source_grade:
            raise ValidationError(f"evidence[{index}] grade must match its registered source")
        observed_on = _date(item.get("observed_on"), f"evidence[{index}].observed_on")
        retrieved_on = _date(item.get("retrieved_on"), f"evidence[{index}].retrieved_on")
        if retrieved_on < observed_on:
            raise ValidationError(f"evidence[{index}] retrieved_on precedes observed_on")
        if evidence_type == "user_forecast":
            _validate_user_forecast(item.get("metadata"), index)
        identity = (evidence_type, source_id)
        if identity in identities:
            raise ValidationError("snapshot cannot repeat the same evidence_type and source_id")
        identities.add(identity)

    if version == 2:
        validate_research_layers(layers, tuple(source_registry))


def _research_layers(payload: Mapping[str, Any]) -> Mapping[str, Any]:
    """Return version-2 layer content, accepting the explicit nested form."""

    nested = payload.get("research_layers", {})
    if not isinstance(nested, Mapping):
        raise ValidationError("research_layers must be an object")
    direct_layers = {layer: payload[layer] for layer in LAYER_KEYS if layer in payload}
    if nested and direct_layers:
        raise ValidationError("research layers must use one representation")
    return nested if nested else direct_layers


def _validate_user_forecast(metadata: Any, index: int) -> None:
    """Keep personal forecasts non-transferable and out of valuation weights."""

    if not isinstance(metadata, Mapping):
        raise ValidationError(f"evidence[{index}].metadata is required for user_forecast")
    speaker = metadata.get("speaker")
    if speaker != "user":
        raise ValidationError(f"evidence[{index}].metadata.speaker must be user for user_forecast")
    if metadata.get("case_scope") != "exact_property":
        raise ValidationError(f"evidence[{index}].metadata.case_scope must be exact_property")
    valuation_weight = metadata.get("valuation_weight")
    if isinstance(valuation_weight, bool) or valuation_weight != 0:
        raise ValidationError(f"evidence[{index}].metadata.valuation_weight must be 0")
    if metadata.get("transferable") is not False:
        raise ValidationError(f"evidence[{index}].metadata.transferable must be false")


def evidence_records(payload: Mapping[str, Any]) -> List[EvidenceRecord]:
    """Convert a validated snapshot into domain records."""

    validate_snapshot(payload)
    sources = {item["source_id"]: item for item in payload["sources"]}
    records = []
    for item in payload["evidence"]:
        source = sources[item["source_id"]]
        value = item.get("value")
        if item["unit"] in NUMERIC_UNITS:
            try:
                value = Decimal(str(value))
            except Exception as exc:
                raise ValidationError(f"{item['evidence_type']} must be numeric") from exc
        records.append(
            EvidenceRecord(
                evidence_type=item["evidence_type"],
                value=value,
                unit=item["unit"],
                observed_on=_date(item["observed_on"], "observed_on"),
                retrieved_on=_date(item["retrieved_on"], "retrieved_on"),
                source=source.get("title") or source["url"],
                source_id=item["source_id"],
                grade=_grade(item["grade"], "grade"),
                scope=item.get("scope", "property"),
                metadata=item.get("metadata", {}),
            )
        )
    return records


def import_snapshot(db: ResearchDatabase, payload: Mapping[str, Any]) -> Dict[str, Any]:
    """Import sources, property, and evidence atomically; repeated snapshots are no-ops."""

    validate_snapshot(payload)
    records = evidence_records(payload)
    ref = PropertyRef(**dict(payload["property"]))
    snapshot_id = payload["snapshot_id"]
    version = payload["schema_version"]
    layers = _research_layers(payload)
    now = datetime.now(timezone.utc).isoformat()

    with db.connection:
        existing = db.connection.execute(
            """
            SELECT id FROM properties
            WHERE city=? AND district=? AND project_name=? AND community_name=?
              AND building=? AND unit_name=?
            """,
            (ref.city, ref.district, ref.project_name, ref.community_name, ref.building, ref.unit_name),
        ).fetchone()
        if existing is not None:
            property_id = int(existing["id"])
            prior_snapshot = db.connection.execute(
                "SELECT 1 FROM imported_snapshots WHERE property_id=? AND snapshot_id=? LIMIT 1",
                (property_id, snapshot_id),
            ).fetchone()
            if prior_snapshot is not None:
                return {
                    "property_id": property_id,
                    "schema_version": version,
                    "imported_evidence": 0,
                    "imported_layers": {},
                    "unchanged": True,
                }
            legacy_snapshot = (
                db.connection.execute(
                    "SELECT 1 FROM evidence WHERE property_id=? AND snapshot_id=? LIMIT 1",
                    (property_id, snapshot_id),
                ).fetchone()
                if version == 1
                else None
            )
            if legacy_snapshot is not None:
                db.connection.execute(
                    """
                    INSERT INTO imported_snapshots(property_id, snapshot_id, schema_version, imported_at)
                    VALUES (?, ?, ?, ?)
                    ON CONFLICT(property_id, snapshot_id) DO NOTHING
                    """,
                    (property_id, snapshot_id, version, now),
                )
                return {
                    "property_id": property_id,
                    "schema_version": version,
                    "imported_evidence": 0,
                    "imported_layers": {},
                    "unchanged": True,
                }

        db.connection.execute(
            """
            INSERT INTO properties(
                city, district, project_name, community_name, submarket,
                building, unit_name, developer_brand, project_company,
                official_project_id, parcel_id, created_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT(city, district, project_name, community_name, building, unit_name)
            DO UPDATE SET
                submarket=excluded.submarket,
                developer_brand=excluded.developer_brand,
                project_company=excluded.project_company,
                official_project_id=excluded.official_project_id,
                parcel_id=excluded.parcel_id
            """,
            (
                ref.city, ref.district, ref.project_name, ref.community_name,
                ref.submarket, ref.building, ref.unit_name, ref.developer_brand,
                ref.project_company, ref.official_project_id, ref.parcel_id, now,
            ),
        )
        row = db.connection.execute(
            """
            SELECT id FROM properties
            WHERE city=? AND district=? AND project_name=? AND community_name=?
              AND building=? AND unit_name=?
            """,
            (ref.city, ref.district, ref.project_name, ref.community_name, ref.building, ref.unit_name),
        ).fetchone()
        property_id = int(row["id"])

        snapshot = db.connection.execute(
            """
            INSERT INTO imported_snapshots(property_id, snapshot_id, schema_version, imported_at)
            VALUES (?, ?, ?, ?)
            ON CONFLICT(property_id, snapshot_id) DO NOTHING
            """,
            (property_id, snapshot_id, version, now),
        )
        if snapshot.rowcount == 0:
            return {
                "property_id": property_id,
                "schema_version": version,
                "imported_evidence": 0,
                "imported_layers": {},
                "unchanged": True,
            }

        for source in payload["sources"]:
            db.connection.execute(
                """
                INSERT INTO sources(source_key, url, title, grade, retrieved_on, metadata_json)
                VALUES (?, ?, ?, ?, ?, ?)
                ON CONFLICT(source_key) DO UPDATE SET
                    url=excluded.url, title=excluded.title, grade=excluded.grade,
                    retrieved_on=excluded.retrieved_on, metadata_json=excluded.metadata_json
                """,
                (
                    source["source_id"], source["url"], source.get("title", ""),
                    source["grade"], source["retrieved_on"], _encode(source.get("metadata", {})),
                ),
            )
            db.connection.execute(
                """
                INSERT INTO source_observations(
                    property_id, snapshot_id, source_key, url, title, grade,
                    retrieved_on, metadata_json, created_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(property_id, snapshot_id, source_key) DO NOTHING
                """,
                (
                    property_id, snapshot_id, source["source_id"], source["url"],
                    source.get("title", ""), source["grade"], source["retrieved_on"],
                    _encode(source.get("metadata", {})), now,
                ),
            )
        for record in records:
            db._insert_evidence(property_id, record, snapshot_id)
        imported_layers = (
            db.insert_research_layers(property_id, snapshot_id, layers)
            if version == 2
            else {}
        )

    return {
        "property_id": property_id,
        "schema_version": version,
        "imported_evidence": len(records),
        "imported_layers": imported_layers,
        "unchanged": False,
    }

"""Defensive parsers for saved Nanjing official project pages.

These functions parse only caller-supplied HTML. They neither execute embedded
JavaScript nor crawl the source site.
"""

from datetime import date
import json
import re
from typing import Any, Dict, List, Mapping

from ..models import EvidenceGrade, EvidenceRecord, ValidationError


def _extract_object(html: str, object_name: str) -> Dict[str, Any]:
    pattern = rf"(?:var\s+|window\.)?{re.escape(object_name)}\s*=\s*(\{{.*?\}})\s*;"
    match = re.search(pattern, html, flags=re.DOTALL)
    if not match:
        raise ValidationError(f"missing embedded {object_name} object; page structure may have changed")
    try:
        value = json.loads(match.group(1))
    except json.JSONDecodeError as exc:
        raise ValidationError(f"invalid embedded {object_name} JSON") from exc
    if not isinstance(value, dict):
        raise ValidationError(f"embedded {object_name} must be an object")
    return value


def _dates(dates: Mapping[str, Any]) -> tuple:
    try:
        observed_on = dates["observed_on"]
        retrieved_on = dates["retrieved_on"]
    except (KeyError, TypeError) as exc:
        raise ValidationError("dates must contain observed_on and retrieved_on") from exc
    if not isinstance(observed_on, date) or not isinstance(retrieved_on, date):
        raise ValidationError("observed_on and retrieved_on must be dates")
    return observed_on, retrieved_on


def _record(
    evidence_type: str,
    value: Any,
    unit: str,
    source: str,
    observed_on: date,
    retrieved_on: date,
    *,
    scope: str = "property",
    metadata: Mapping[str, Any] = None,
) -> EvidenceRecord:
    return EvidenceRecord(
        evidence_type=evidence_type,
        value=value,
        unit=unit,
        observed_on=observed_on,
        retrieved_on=retrieved_on,
        source=source,
        source_id=source,
        grade=EvidenceGrade.A,
        scope=scope,
        metadata=metadata or {},
    )


def _unit_count(value: Any, label: str) -> int:
    if isinstance(value, bool) or not isinstance(value, int) or value < 0:
        raise ValidationError(f"{label} must be a non-negative integer")
    return value


def parse_njhouse_sale_info(
    html: str, source: str, dates: Mapping[str, Any]
) -> List[EvidenceRecord]:
    """Parse official released, unsold, and sold counts by building and total."""

    if not source.strip():
        raise ValidationError("source URL is required")
    observed_on, retrieved_on = _dates(dates)
    data = _extract_object(html, "projectInfoBuildingSaleInfo")
    project_name = data.get("projectName")
    buildings = data.get("buildings")
    if not isinstance(project_name, str) or not project_name.strip():
        raise ValidationError("sale page is missing project identity")
    if not isinstance(buildings, list) or not buildings:
        raise ValidationError("sale page is missing building inventory")

    records: List[EvidenceRecord] = []
    totals = {"released": 0, "unsold": 0, "sold": 0}
    metric_types = {
        "released": "official_released_units",
        "unsold": "official_unsold_units",
        "sold": "official_sold_units",
    }
    seen_buildings = set()
    for index, building in enumerate(buildings):
        if not isinstance(building, dict):
            raise ValidationError(f"building row {index} must be an object")
        building_name = building.get("buildingName")
        if not isinstance(building_name, str) or not building_name.strip():
            raise ValidationError(f"building row {index} is missing building identity")
        if building_name in seen_buildings:
            raise ValidationError(f"duplicate building identity: {building_name}")
        seen_buildings.add(building_name)
        counts = {key: _unit_count(building.get(key), f"{building_name}.{key}") for key in totals}
        if counts["released"] != counts["unsold"] + counts["sold"]:
            raise ValidationError(f"inconsistent inventory totals for {building_name}")
        for key, value in counts.items():
            totals[key] += value
            records.append(
                _record(
                    metric_types[key],
                    value,
                    "count",
                    source,
                    observed_on,
                    retrieved_on,
                    scope="building",
                    metadata={"building": building_name, "project_name": project_name},
                )
            )

    if totals["released"] != totals["unsold"] + totals["sold"]:
        raise ValidationError("inconsistent project inventory totals")
    for key, value in totals.items():
        records.append(
            _record(
                metric_types[key],
                value,
                "count",
                source,
                observed_on,
                retrieved_on,
                metadata={
                    "project_name": project_name,
                    "official_project_id": data.get("officialProjectId", ""),
                },
            )
        )
    return records


def parse_njhouse_project_page(
    html: str, source: str, dates: Mapping[str, Any]
) -> List[EvidenceRecord]:
    """Parse official project, entity, and planned-delivery identity fields."""

    if not source.strip():
        raise ValidationError("source URL is required")
    observed_on, retrieved_on = _dates(dates)
    data = _extract_object(html, "projectInfo")
    project_name = data.get("projectName")
    if not isinstance(project_name, str) or not project_name.strip():
        raise ValidationError("project page is missing project identity")

    fields = (
        ("official_project_name", project_name, "text"),
        ("official_project_id", data.get("officialProjectId"), "text"),
        ("official_developer_brand", data.get("developerBrand"), "text"),
        ("official_project_company", data.get("projectCompany"), "text"),
        ("official_planned_delivery_date", data.get("plannedDeliveryDate"), "date"),
    )
    records = []
    for evidence_type, value, unit in fields:
        if value is None or value == "":
            continue
        if not isinstance(value, str):
            raise ValidationError(f"{evidence_type} must be text")
        if unit == "date":
            try:
                date.fromisoformat(value)
            except ValueError as exc:
                raise ValidationError("official planned delivery date must be ISO format") from exc
        records.append(
            _record(
                evidence_type,
                value,
                unit,
                source,
                observed_on,
                retrieved_on,
                metadata={"project_name": project_name},
            )
        )
    return records

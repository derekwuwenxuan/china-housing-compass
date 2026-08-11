"""Validation for normalized social and land-history research records."""

from datetime import date
from typing import Any, Mapping, Sequence

from .models import EvidenceGrade, ValidationError


LAYER_KEYS = (
    "social_research_runs", "social_items", "social_comments",
    "parcel_history_findings", "environmental_findings", "cultural_factors",
)
ACCESS_MODES = {"public_web", "indexed_snippet", "authorized_browser", "user_supplied", "unavailable"}
STANCES = {"positive", "negative", "mixed", "neutral", "unknown"}
FINDING_STATES = {"officially_verified", "multi_source_supported", "lead_only", "unverified_rumor", "unknown"}
GEOGRAPHY_SCOPES = {"exact_parcel", "within_500m", "within_1km", "submarket", "district", "city"}
BUYER_SENSITIVITIES = {"ignore", "standard", "high"}


_KEY_FIELDS = {
    "social_research_runs": "run_key",
    "social_items": "item_key",
    "social_comments": "comment_key",
    "parcel_history_findings": "finding_key",
    "environmental_findings": "finding_key",
    "cultural_factors": "factor_key",
}
_SENSITIVE_KEY_MARKERS = ("credential", "password", "cookie", "token")
_SENSITIVE_SESSION_KEYS = {"session", "session_id", "browser_session", "browser_session_id"}


def _date(value: Any, name: str) -> date:
    if not isinstance(value, str):
        raise ValidationError(f"{name} must use ISO date format")
    try:
        return date.fromisoformat(value)
    except ValueError as exc:
        raise ValidationError(f"{name} must use ISO date format") from exc


def _optional_date(item: Mapping[str, Any], field: str, label: str) -> Any:
    value = item.get(field)
    if value is None:
        return None
    return _date(value, f"{label}.{field}")


def _required_text(item: Mapping[str, Any], field: str, label: str) -> str:
    value = item.get(field)
    if not isinstance(value, str) or not value.strip():
        raise ValidationError(f"{label}.{field} is required")
    return value


def _enum(item: Mapping[str, Any], field: str, allowed: set, label: str) -> None:
    if item.get(field) not in allowed:
        raise ValidationError(f"{label}.{field} is not permitted")


def _reject_sensitive_values(value: Any, label: str) -> None:
    if isinstance(value, Mapping):
        for key, nested in value.items():
            if isinstance(key, str):
                normalized_key = key.lower()
                if (
                    normalized_key in _SENSITIVE_SESSION_KEYS
                    or any(marker in normalized_key for marker in _SENSITIVE_KEY_MARKERS)
                ):
                    raise ValidationError(f"{label} cannot contain browser credentials or session tokens")
            _reject_sensitive_values(nested, label)
    elif isinstance(value, Sequence) and not isinstance(value, (str, bytes, bytearray)):
        for nested in value:
            _reject_sensitive_values(nested, label)


def _validate_item(layer: str, index: int, item: Mapping[str, Any], source_ids: set) -> None:
    label = f"{layer}[{index}]"
    _required_text(item, _KEY_FIELDS[layer], label)
    source_id = _required_text(item, "source_id", label)
    if source_id not in source_ids:
        raise ValidationError(f"{label}.source_id is not registered")
    observed_on = _date(item.get("observed_on"), f"{label}.observed_on")
    retrieved_on = _date(item.get("retrieved_on"), f"{label}.retrieved_on")
    if retrieved_on < observed_on:
        raise ValidationError(f"{label}.retrieved_on cannot precede observed_on")
    try:
        grade = EvidenceGrade(item.get("grade"))
    except (TypeError, ValueError) as exc:
        raise ValidationError(f"{label}.grade must be A, B, C, or D") from exc
    if layer in {"social_items", "social_comments"} and grade not in {
        EvidenceGrade.C,
        EvidenceGrade.D,
    }:
        raise ValidationError(f"{label}.grade must be C or D for ordinary social evidence")

    if layer == "social_research_runs":
        _enum(item, "access_mode", ACCESS_MODES, label)
        for field in ("requested_count", "obtained_count"):
            value = item.get(field)
            if isinstance(value, bool) or not isinstance(value, int) or value < 0:
                raise ValidationError(f"{label}.{field} must be a non-negative integer")
    elif layer == "social_items":
        _required_text(item, "platform", label)
        _required_text(item, "locator", label)
        _required_text(item, "author_role", label)
        _required_text(item, "content_type", label)
        _required_text(item, "summary", label)
        _enum(item, "access_mode", ACCESS_MODES, label)
        _enum(item, "stance", STANCES, label)
        published_on = _optional_date(item, "published_on", label)
        if published_on is not None and published_on > observed_on:
            raise ValidationError(f"{label}.published_on cannot follow observed_on")
    elif layer == "social_comments":
        _required_text(item, "parent_item_key", label)
        _enum(item, "stance", STANCES, label)
    elif layer == "parcel_history_findings":
        _required_text(item, "historical_use", label)
        _enum(item, "geography_scope", GEOGRAPHY_SCOPES, label)
        _enum(item, "finding_state", FINDING_STATES, label)
        start_on = _optional_date(item, "start_on", label)
        end_on = _optional_date(item, "end_on", label)
        if start_on is not None and end_on is not None and end_on < start_on:
            raise ValidationError(f"{label}.end_on cannot precede start_on")
    elif layer == "environmental_findings":
        _required_text(item, "hazard_type", label)
        _enum(item, "geography_scope", GEOGRAPHY_SCOPES, label)
        _enum(item, "finding_state", FINDING_STATES, label)
    elif layer == "cultural_factors":
        _required_text(item, "geography_scope", label)
        _required_text(item, "observable_feature", label)
        _enum(item, "geography_scope", GEOGRAPHY_SCOPES, label)
        _enum(item, "buyer_sensitivity", BUYER_SENSITIVITIES, label)

    _reject_sensitive_values(item, label)


def validate_research_layers(payload: Mapping[str, Any], source_ids: Sequence[str]) -> None:
    """Validate source-linked research layers before an atomic snapshot import."""

    if not isinstance(payload, Mapping):
        raise ValidationError("research layers must be an object")
    source_registry = set(source_ids)
    unknown = set(payload) - set(LAYER_KEYS)
    if unknown:
        raise ValidationError(f"unknown research layer: {sorted(unknown)[0]}")

    social_items = {}
    for layer in LAYER_KEYS:
        items = payload.get(layer, [])
        if not isinstance(items, Sequence) or isinstance(items, (str, bytes, bytearray)):
            raise ValidationError(f"{layer} must be a list")
        keys = set()
        for index, item in enumerate(items):
            if not isinstance(item, Mapping):
                raise ValidationError(f"{layer}[{index}] must be an object")
            _validate_item(layer, index, item, source_registry)
            stable_key = item[_KEY_FIELDS[layer]]
            if stable_key in keys:
                raise ValidationError(f"{layer} cannot repeat stable key: {stable_key}")
            keys.add(stable_key)
        if layer == "social_items":
            social_items = {item["item_key"]: item for item in items}

    for index, comment in enumerate(payload.get("social_comments", [])):
        parent = social_items.get(comment["parent_item_key"])
        if parent is None:
            raise ValidationError(
                f"social_comments[{index}].parent_item_key must link to a social item in the same snapshot"
            )
        if parent.get("access_mode") in {"indexed_snippet", "unavailable"}:
            raise ValidationError(
                f"social_comments[{index}].parent_item_key access_mode cannot be "
                "indexed_snippet or unavailable"
            )

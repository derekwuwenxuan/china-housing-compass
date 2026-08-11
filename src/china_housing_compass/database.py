"""SQLite persistence with append-only evidence snapshots."""

from datetime import date, datetime, timezone
from decimal import Decimal
import json
from pathlib import Path
import sqlite3
from typing import Any, Dict, Iterable, List, Mapping, Optional, Sequence

from .models import EvidenceGrade, EvidenceRecord, PropertyRef
from .research_layers import LAYER_KEYS, validate_research_layers


_RESEARCH_LAYER_COLUMNS = {
    "social_research_runs": (
        "run_key", "source_id", "access_mode", "platforms_json", "queries_json",
        "requested_count", "obtained_count", "failures_json", "observed_on",
        "retrieved_on", "grade", "metadata_json",
    ),
    "social_items": (
        "item_key", "source_id", "platform", "locator", "access_mode", "author_role",
        "content_type", "stance", "summary", "published_on", "engagement_json",
        "commercial_json", "observed_on", "retrieved_on", "grade", "metadata_json",
    ),
    "social_comments": (
        "comment_key", "source_id", "parent_item_key", "stance", "themes_json",
        "engagement_json", "summary", "privacy_json", "observed_on", "retrieved_on",
        "grade", "metadata_json",
    ),
    "parcel_history_findings": (
        "finding_key", "source_id", "geography_scope", "historical_use", "finding_state",
        "start_on", "end_on", "distance_meters", "direction", "observed_on",
        "retrieved_on", "grade", "metadata_json",
    ),
    "environmental_findings": (
        "finding_key", "source_id", "geography_scope", "hazard_type", "finding_state",
        "remediation_status", "acceptance_status", "residual_uncertainty",
        "valuation_treatment", "observed_on", "retrieved_on", "grade", "metadata_json",
    ),
    "cultural_factors": (
        "factor_key", "source_id", "geography_scope", "observable_feature",
        "cultural_interpretation", "buyer_sensitivity", "objective_counterpart",
        "liquidity_treatment", "observed_on", "retrieved_on", "grade", "metadata_json",
    ),
}
_RESEARCH_JSON_DEFAULTS = {
    "platforms_json": [], "queries_json": [], "failures_json": {}, "engagement_json": {},
    "commercial_json": {}, "themes_json": [], "privacy_json": {}, "metadata_json": {},
}
_RESEARCH_SCALAR_DEFAULTS = {
    "summary": "", "direction": "", "remediation_status": "", "acceptance_status": "",
    "residual_uncertainty": "", "valuation_treatment": "", "cultural_interpretation": "",
    "objective_counterpart": "", "liquidity_treatment": "",
}
_RESEARCH_LAYER_KEY_COLUMNS = {
    "social_research_runs": "run_key",
    "social_items": "item_key",
    "social_comments": "comment_key",
    "parcel_history_findings": "finding_key",
    "environmental_findings": "finding_key",
    "cultural_factors": "factor_key",
}


def _json_default(value: Any) -> Any:
    if isinstance(value, Decimal):
        return {"__type__": "decimal", "value": str(value)}
    if isinstance(value, (date, datetime)):
        return {"__type__": "date", "value": value.isoformat()}
    raise TypeError(f"unsupported JSON value: {type(value).__name__}")


def _object_hook(value: Dict[str, Any]) -> Any:
    if value.get("__type__") == "decimal":
        return Decimal(value["value"])
    if value.get("__type__") == "date":
        return value["value"]
    return value


def _encode(value: Any) -> str:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, default=_json_default)


def _decode(value: str) -> Any:
    return json.loads(value, object_hook=_object_hook)


class ResearchDatabase:
    def __init__(self, path: Any):
        self.path = str(path)
        self.connection = sqlite3.connect(self.path)
        self.connection.row_factory = sqlite3.Row
        self.connection.execute("PRAGMA foreign_keys = ON")
        self._migrate_runtime_schema()

    def _migrate_runtime_schema(self) -> None:
        """Bring an existing local workspace forward without losing history."""

        tables = {
            row["name"]
            for row in self.connection.execute(
                "SELECT name FROM sqlite_master WHERE type='table'"
            )
        }
        changed = False
        if "refresh_runs" in tables:
            columns = {
                row["name"]
                for row in self.connection.execute("PRAGMA table_info(refresh_runs)")
            }
            if "unchanged_json" not in columns:
                self.connection.execute(
                    "ALTER TABLE refresh_runs ADD COLUMN unchanged_json TEXT NOT NULL DEFAULT '[]'"
                )
                changed = True
        if "properties" in tables:
            if "source_observations" not in tables:
                self.connection.execute(
                    """
                    CREATE TABLE source_observations (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        property_id INTEGER NOT NULL REFERENCES properties(id),
                        snapshot_id TEXT NOT NULL,
                        source_key TEXT NOT NULL,
                        url TEXT NOT NULL,
                        title TEXT NOT NULL DEFAULT '',
                        grade TEXT NOT NULL,
                        retrieved_on TEXT NOT NULL,
                        metadata_json TEXT NOT NULL DEFAULT '{}',
                        created_at TEXT NOT NULL,
                        UNIQUE(property_id, snapshot_id, source_key)
                    )
                    """
                )
                changed = True
            index = self.connection.execute(
                """
                SELECT 1 FROM sqlite_master
                WHERE type='index' AND name='source_observations_snapshot'
                """
            ).fetchone()
            if index is None:
                self.connection.execute(
                    """
                    CREATE INDEX source_observations_snapshot
                    ON source_observations(property_id, snapshot_id, source_key)
                    """
                )
                changed = True
            if "sources" in tables:
                created_at = datetime.now(timezone.utc).isoformat()
                for layer in LAYER_KEYS:
                    if layer not in tables:
                        continue
                    missing = self.connection.execute(
                        f"""
                        SELECT 1
                        FROM {layer} AS layer
                        JOIN sources AS source ON source.source_key=layer.source_id
                        LEFT JOIN source_observations AS observation
                          ON observation.property_id=layer.property_id
                         AND observation.snapshot_id=layer.snapshot_id
                         AND observation.source_key=layer.source_id
                        WHERE observation.id IS NULL
                        LIMIT 1
                        """
                    ).fetchone()
                    if missing is None:
                        continue
                    self.connection.execute(
                        f"""
                        INSERT INTO source_observations(
                            property_id, snapshot_id, source_key, url, title, grade,
                            retrieved_on, metadata_json, created_at
                        )
                        SELECT DISTINCT layer.property_id, layer.snapshot_id,
                               layer.source_id, source.url, source.title, source.grade,
                               source.retrieved_on, source.metadata_json, ?
                        FROM {layer} AS layer
                        JOIN sources AS source ON source.source_key=layer.source_id
                        ON CONFLICT(property_id, snapshot_id, source_key) DO NOTHING
                        """,
                        (created_at,),
                    )
                    changed = True
        if "schema_version" in tables:
            version = self.connection.execute(
                "SELECT 1 FROM schema_version WHERE version=3"
            ).fetchone()
            if version is None:
                self.connection.execute(
                    "INSERT INTO schema_version(version, applied_at) VALUES (3, CURRENT_TIMESTAMP)"
                )
                changed = True
        if changed:
            self.connection.commit()

    def close(self) -> None:
        self.connection.close()

    def initialize(self) -> None:
        schema_path = Path(__file__).with_name("schema.sql")
        self.connection.executescript(schema_path.read_text(encoding="utf-8"))
        self._migrate_runtime_schema()
        self.connection.commit()

    def upsert_property(self, ref: PropertyRef) -> int:
        values = (
            ref.city,
            ref.district,
            ref.project_name,
            ref.community_name,
            ref.submarket,
            ref.building,
            ref.unit_name,
            ref.developer_brand,
            ref.project_company,
            ref.official_project_id,
            ref.parcel_id,
            datetime.now(timezone.utc).isoformat(),
        )
        with self.connection:
            self.connection.execute(
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
                values,
            )
            row = self.connection.execute(
                """
                SELECT id FROM properties
                WHERE city=? AND district=? AND project_name=? AND community_name=?
                  AND building=? AND unit_name=?
                """,
                (ref.city, ref.district, ref.project_name, ref.community_name, ref.building, ref.unit_name),
            ).fetchone()
        return int(row["id"])

    def get_property(self, property_id: int) -> Mapping[str, Any]:
        row = self.connection.execute("SELECT * FROM properties WHERE id=?", (property_id,)).fetchone()
        if row is None:
            raise KeyError(f"unknown property_id: {property_id}")
        return dict(row)

    def list_properties(self) -> List[Mapping[str, Any]]:
        return [dict(row) for row in self.connection.execute("SELECT * FROM properties ORDER BY city, district, project_name, community_name")]

    def add_evidence(self, property_id: int, record: EvidenceRecord, snapshot_id: str = "") -> int:
        with self.connection:
            return self._insert_evidence(property_id, record, snapshot_id)

    def add_evidence_batch(
        self,
        property_id: int,
        records: Iterable[EvidenceRecord],
        snapshot_id: str = "",
    ) -> List[int]:
        ids: List[int] = []
        with self.connection:
            for record in records:
                ids.append(self._insert_evidence(property_id, record, snapshot_id))
        return ids

    def _insert_evidence(self, property_id: int, record: EvidenceRecord, snapshot_id: str) -> int:
        cursor = self.connection.execute(
            """
            INSERT INTO evidence(
                property_id, evidence_type, value_json, unit, observed_on,
                retrieved_on, source, source_id, grade, scope, metadata_json,
                snapshot_id, created_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                property_id,
                record.evidence_type,
                _encode(record.value),
                record.unit,
                record.observed_on.isoformat(),
                record.retrieved_on.isoformat(),
                record.source,
                record.source_id,
                record.grade.value,
                record.scope,
                _encode(dict(record.metadata)),
                snapshot_id,
                datetime.now(timezone.utc).isoformat(),
            ),
        )
        return int(cursor.lastrowid)

    def list_evidence(self, property_id: int, evidence_type: str = "") -> List[EvidenceRecord]:
        sql = "SELECT * FROM evidence WHERE property_id=?"
        params: Sequence[Any] = (property_id,)
        if evidence_type:
            sql += " AND evidence_type=?"
            params = (property_id, evidence_type)
        sql += " ORDER BY observed_on, id"
        return [self._record_from_row(row) for row in self.connection.execute(sql, params)]

    def latest_evidence(self, property_id: int) -> Dict[str, EvidenceRecord]:
        result: Dict[str, EvidenceRecord] = {}
        for record in self.list_evidence(property_id):
            result[record.evidence_type] = record
        return result

    def insert_research_layers(
        self,
        property_id: int,
        snapshot_id: str,
        layers: Mapping[str, Sequence[Mapping[str, Any]]],
    ) -> Dict[str, int]:
        """Append normalized research-layer records within the caller transaction."""

        unknown = set(layers) - set(LAYER_KEYS)
        if unknown:
            raise ValueError(f"unknown research layer: {sorted(unknown)[0]}")
        if not isinstance(snapshot_id, str) or not snapshot_id.strip():
            raise ValueError("snapshot_id is required")
        source_ids = {
            row["source_key"]
            for row in self.connection.execute("SELECT source_key FROM sources")
        }
        validation_layers = dict(layers)
        comments = layers.get("social_comments", ())
        supplied_items = layers.get("social_items", ())
        if (
            isinstance(comments, Sequence)
            and not isinstance(comments, (str, bytes, bytearray))
            and isinstance(supplied_items, Sequence)
            and not isinstance(supplied_items, (str, bytes, bytearray))
        ):
            supplied_keys = {
                item.get("item_key")
                for item in supplied_items
                if isinstance(item, Mapping)
            }
            existing_items = [
                item
                for item in self.list_research_layer(property_id, "social_items")
                if item["snapshot_id"] == snapshot_id and item["item_key"] not in supplied_keys
            ]
            if existing_items:
                validation_layers["social_items"] = [*supplied_items, *existing_items]
        validate_research_layers(validation_layers, source_ids)

        counts = {layer: 0 for layer in LAYER_KEYS}
        created_at = datetime.now(timezone.utc).isoformat()
        for layer in LAYER_KEYS:
            items = layers.get(layer, ())
            if not isinstance(items, Sequence) or isinstance(items, (str, bytes, bytearray)):
                raise ValueError(f"{layer} must be a sequence")
            columns = _RESEARCH_LAYER_COLUMNS[layer]
            sql_columns = ("property_id", "snapshot_id", *columns, "created_at")
            placeholders = ", ".join("?" for _ in sql_columns)
            sql = (
                f"INSERT INTO {layer} ({', '.join(sql_columns)}) "
                f"VALUES ({placeholders}) ON CONFLICT(property_id, snapshot_id, "
                f"{_RESEARCH_LAYER_KEY_COLUMNS[layer]}) DO NOTHING"
            )
            for item in items:
                if not isinstance(item, Mapping):
                    raise ValueError(f"{layer} items must be mappings")
                values = [property_id, snapshot_id]
                for column in columns:
                    if column.endswith("_json"):
                        source_name = column[:-5]
                        value = item.get(source_name, item.get(column, _RESEARCH_JSON_DEFAULTS[column]))
                        if value is None:
                            value = _RESEARCH_JSON_DEFAULTS[column]
                        values.append(_encode(value))
                    else:
                        value = item.get(column, _RESEARCH_SCALAR_DEFAULTS.get(column))
                        if value is None and column in _RESEARCH_SCALAR_DEFAULTS:
                            value = _RESEARCH_SCALAR_DEFAULTS[column]
                        values.append(value)
                cursor = self.connection.execute(sql, (*values, created_at))
                counts[layer] += cursor.rowcount
        return counts

    def list_research_layer(self, property_id: int, layer: str) -> List[Mapping[str, Any]]:
        """List one append-only research layer with JSON fields decoded."""

        if layer not in LAYER_KEYS:
            raise ValueError(f"unknown research layer: {layer}")
        result = []
        for row in self.connection.execute(
            f"""
            SELECT layer.*,
                   COALESCE(observation.url, registry.url) AS source_url,
                   COALESCE(observation.title, registry.title) AS source_title,
                   COALESCE(observation.grade, registry.grade) AS source_grade,
                   COALESCE(observation.retrieved_on, registry.retrieved_on) AS source_retrieved_on
            FROM {layer} AS layer
            LEFT JOIN source_observations AS observation
              ON observation.property_id=layer.property_id
             AND observation.snapshot_id=layer.snapshot_id
             AND observation.source_key=layer.source_id
            LEFT JOIN sources AS registry ON registry.source_key=layer.source_id
            WHERE layer.property_id=?
            ORDER BY layer.observed_on, layer.id
            """,
            (property_id,),
        ):
            item = dict(row)
            for key, value in tuple(item.items()):
                if key.endswith("_json"):
                    item[key] = _decode(value)
            result.append(item)
        return result

    @staticmethod
    def _record_from_row(row: sqlite3.Row) -> EvidenceRecord:
        return EvidenceRecord(
            evidence_type=row["evidence_type"],
            value=_decode(row["value_json"]),
            unit=row["unit"],
            observed_on=date.fromisoformat(row["observed_on"]),
            retrieved_on=date.fromisoformat(row["retrieved_on"]),
            source=row["source"],
            source_id=row["source_id"],
            grade=EvidenceGrade(row["grade"]),
            scope=row["scope"],
            metadata=_decode(row["metadata_json"]),
        )

    def record_refresh(
        self,
        property_id: Optional[int],
        status: str,
        attempted: Sequence[str],
        succeeded: Sequence[str],
        failures: Mapping[str, str],
        started_at: datetime,
        finished_at: datetime,
        unchanged: Sequence[str] = (),
    ) -> int:
        if status not in {"success", "partial", "failed", "unchanged"}:
            raise ValueError(f"unsupported refresh status: {status}")
        with self.connection:
            cursor = self.connection.execute(
                """
                INSERT INTO refresh_runs(
                    property_id, status, attempted_json, succeeded_json,
                    unchanged_json, failures_json, started_at, finished_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    property_id,
                    status,
                    _encode(list(attempted)),
                    _encode(list(succeeded)),
                    _encode(list(unchanged)),
                    _encode(dict(failures)),
                    started_at.isoformat(),
                    finished_at.isoformat(),
                ),
            )
        return int(cursor.lastrowid)

    def latest_refresh(self, property_id: int) -> Optional[Mapping[str, Any]]:
        row = self.connection.execute(
            "SELECT * FROM refresh_runs WHERE property_id=? ORDER BY id DESC LIMIT 1",
            (property_id,),
        ).fetchone()
        if row is None:
            return None
        result = dict(row)
        result["attempted"] = _decode(result.pop("attempted_json"))
        result["succeeded"] = _decode(result.pop("succeeded_json"))
        result["unchanged"] = _decode(result.pop("unchanged_json", "[]"))
        result["failures"] = _decode(result.pop("failures_json"))
        return result

    def latest_successful_refresh(self, property_id: int) -> Optional[Mapping[str, Any]]:
        """Return the latest refresh that added fresh data to a fully successful run."""

        row = self.connection.execute(
            """
            SELECT * FROM refresh_runs
            WHERE property_id=? AND status='success'
            ORDER BY id DESC LIMIT 1
            """,
            (property_id,),
        ).fetchone()
        if row is None:
            return None
        result = dict(row)
        result["attempted"] = _decode(result.pop("attempted_json"))
        result["succeeded"] = _decode(result.pop("succeeded_json"))
        result["unchanged"] = _decode(result.pop("unchanged_json", "[]"))
        result["failures"] = _decode(result.pop("failures_json"))
        return result

    def latest_refresh_attempts(self, property_id: int) -> Mapping[str, Mapping[str, Any]]:
        """Return the latest stored outcome for each independently refreshed category."""

        latest: Dict[str, Mapping[str, Any]] = {}
        rows = self.connection.execute(
            "SELECT * FROM refresh_runs WHERE property_id=? ORDER BY id DESC",
            (property_id,),
        )
        for row in rows:
            run = dict(row)
            attempted = _decode(run["attempted_json"])
            succeeded = set(_decode(run["succeeded_json"]))
            unchanged = set(_decode(run.get("unchanged_json", "[]")))
            failures = _decode(run["failures_json"])
            for category in attempted:
                if category in latest:
                    continue
                if category in failures:
                    outcome = "failed"
                elif category in unchanged:
                    outcome = "unchanged"
                elif category in succeeded:
                    outcome = "fresh"
                else:
                    outcome = "unknown"
                latest[category] = {
                    "category": category,
                    "outcome": outcome,
                    "failure_reason": failures.get(category, ""),
                    "finished_at": run["finished_at"],
                    "refresh_status": run["status"],
                }
        return latest

    def save_valuation_run(
        self,
        property_id: int,
        objective: str,
        recommendation: str,
        confidence: str,
        result: Mapping[str, Any],
    ) -> int:
        with self.connection:
            cursor = self.connection.execute(
                """
                INSERT INTO valuation_runs(
                    property_id, created_at, objective, recommendation,
                    confidence, result_json
                ) VALUES (?, ?, ?, ?, ?, ?)
                """,
                (
                    property_id,
                    datetime.now(timezone.utc).isoformat(),
                    objective,
                    recommendation,
                    confidence,
                    _encode(dict(result)),
                ),
            )
        return int(cursor.lastrowid)

    def latest_valuation(self, property_id: int) -> Optional[Mapping[str, Any]]:
        row = self.connection.execute(
            "SELECT * FROM valuation_runs WHERE property_id=? ORDER BY id DESC LIMIT 1",
            (property_id,),
        ).fetchone()
        if row is None:
            return None
        result = dict(row)
        result["result"] = _decode(result.pop("result_json"))
        return result

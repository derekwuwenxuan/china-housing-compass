PRAGMA foreign_keys = ON;

CREATE TABLE IF NOT EXISTS schema_version (
    version INTEGER PRIMARY KEY,
    applied_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS properties (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    city TEXT NOT NULL,
    district TEXT NOT NULL,
    project_name TEXT NOT NULL DEFAULT '',
    community_name TEXT NOT NULL DEFAULT '',
    submarket TEXT NOT NULL DEFAULT '',
    building TEXT NOT NULL DEFAULT '',
    unit_name TEXT NOT NULL DEFAULT '',
    developer_brand TEXT NOT NULL DEFAULT '',
    project_company TEXT NOT NULL DEFAULT '',
    official_project_id TEXT NOT NULL DEFAULT '',
    parcel_id TEXT NOT NULL DEFAULT '',
    created_at TEXT NOT NULL,
    UNIQUE(city, district, project_name, community_name, building, unit_name)
);

CREATE TABLE IF NOT EXISTS sources (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    source_key TEXT NOT NULL UNIQUE,
    url TEXT NOT NULL,
    title TEXT NOT NULL DEFAULT '',
    grade TEXT NOT NULL,
    retrieved_on TEXT NOT NULL,
    metadata_json TEXT NOT NULL DEFAULT '{}'
);

CREATE TABLE IF NOT EXISTS evidence (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    property_id INTEGER NOT NULL REFERENCES properties(id),
    evidence_type TEXT NOT NULL,
    value_json TEXT NOT NULL,
    unit TEXT NOT NULL,
    observed_on TEXT NOT NULL,
    retrieved_on TEXT NOT NULL,
    source TEXT NOT NULL,
    source_id TEXT NOT NULL DEFAULT '',
    grade TEXT NOT NULL,
    scope TEXT NOT NULL,
    metadata_json TEXT NOT NULL DEFAULT '{}',
    snapshot_id TEXT NOT NULL DEFAULT '',
    created_at TEXT NOT NULL
);

CREATE INDEX IF NOT EXISTS evidence_property_type_date
ON evidence(property_id, evidence_type, observed_on, id);

CREATE UNIQUE INDEX IF NOT EXISTS evidence_snapshot_identity
ON evidence(property_id, snapshot_id, evidence_type, source_id)
WHERE snapshot_id <> '';

CREATE TABLE IF NOT EXISTS infrastructure_items (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    property_id INTEGER NOT NULL REFERENCES properties(id),
    category TEXT NOT NULL,
    name TEXT NOT NULL,
    status TEXT NOT NULL,
    observed_on TEXT NOT NULL,
    source_id TEXT NOT NULL DEFAULT '',
    walking_minutes INTEGER,
    realization_factor TEXT NOT NULL,
    metadata_json TEXT NOT NULL DEFAULT '{}'
);

CREATE TABLE IF NOT EXISTS risk_events (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    property_id INTEGER NOT NULL REFERENCES properties(id),
    entity_name TEXT NOT NULL,
    event_type TEXT NOT NULL,
    severity TEXT NOT NULL,
    occurred_on TEXT,
    source_id TEXT NOT NULL,
    description TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS valuation_runs (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    property_id INTEGER NOT NULL REFERENCES properties(id),
    created_at TEXT NOT NULL,
    objective TEXT NOT NULL,
    recommendation TEXT NOT NULL,
    confidence TEXT NOT NULL,
    result_json TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS scenario_results (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    valuation_run_id INTEGER NOT NULL REFERENCES valuation_runs(id),
    scenario_name TEXT NOT NULL,
    delivery_value TEXT NOT NULL,
    maximum_purchase_price_today TEXT NOT NULL,
    result_json TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS refresh_runs (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    property_id INTEGER REFERENCES properties(id),
    status TEXT NOT NULL,
    attempted_json TEXT NOT NULL,
    succeeded_json TEXT NOT NULL,
    unchanged_json TEXT NOT NULL DEFAULT '[]',
    failures_json TEXT NOT NULL,
    started_at TEXT NOT NULL,
    finished_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS imported_snapshots (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    property_id INTEGER NOT NULL REFERENCES properties(id),
    snapshot_id TEXT NOT NULL,
    schema_version INTEGER NOT NULL,
    imported_at TEXT NOT NULL,
    UNIQUE(property_id, snapshot_id)
);

CREATE TABLE IF NOT EXISTS source_observations (
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
);

CREATE INDEX IF NOT EXISTS source_observations_snapshot
ON source_observations(property_id, snapshot_id, source_key);

CREATE TABLE IF NOT EXISTS social_research_runs (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    property_id INTEGER NOT NULL REFERENCES properties(id),
    snapshot_id TEXT NOT NULL,
    run_key TEXT NOT NULL,
    source_id TEXT NOT NULL REFERENCES sources(source_key),
    access_mode TEXT NOT NULL,
    platforms_json TEXT NOT NULL DEFAULT '[]',
    queries_json TEXT NOT NULL DEFAULT '[]',
    requested_count INTEGER,
    obtained_count INTEGER,
    failures_json TEXT NOT NULL DEFAULT '{}',
    observed_on TEXT NOT NULL,
    retrieved_on TEXT NOT NULL,
    grade TEXT NOT NULL,
    metadata_json TEXT NOT NULL DEFAULT '{}',
    created_at TEXT NOT NULL
);

CREATE UNIQUE INDEX IF NOT EXISTS social_research_runs_snapshot_identity
ON social_research_runs(property_id, snapshot_id, run_key);

CREATE TABLE IF NOT EXISTS social_items (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    property_id INTEGER NOT NULL REFERENCES properties(id),
    snapshot_id TEXT NOT NULL,
    item_key TEXT NOT NULL,
    source_id TEXT NOT NULL REFERENCES sources(source_key),
    platform TEXT NOT NULL,
    locator TEXT NOT NULL,
    access_mode TEXT NOT NULL,
    author_role TEXT NOT NULL,
    content_type TEXT NOT NULL,
    stance TEXT NOT NULL,
    summary TEXT NOT NULL,
    published_on TEXT,
    engagement_json TEXT NOT NULL DEFAULT '{}',
    commercial_json TEXT NOT NULL DEFAULT '{}',
    observed_on TEXT NOT NULL,
    retrieved_on TEXT NOT NULL,
    grade TEXT NOT NULL,
    metadata_json TEXT NOT NULL DEFAULT '{}',
    created_at TEXT NOT NULL
);

CREATE UNIQUE INDEX IF NOT EXISTS social_items_snapshot_identity
ON social_items(property_id, snapshot_id, item_key);

CREATE TABLE IF NOT EXISTS social_comments (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    property_id INTEGER NOT NULL REFERENCES properties(id),
    snapshot_id TEXT NOT NULL,
    comment_key TEXT NOT NULL,
    source_id TEXT NOT NULL REFERENCES sources(source_key),
    parent_item_key TEXT NOT NULL,
    stance TEXT NOT NULL,
    themes_json TEXT NOT NULL DEFAULT '[]',
    engagement_json TEXT NOT NULL DEFAULT '{}',
    summary TEXT NOT NULL DEFAULT '',
    privacy_json TEXT NOT NULL DEFAULT '{}',
    observed_on TEXT NOT NULL,
    retrieved_on TEXT NOT NULL,
    grade TEXT NOT NULL,
    metadata_json TEXT NOT NULL DEFAULT '{}',
    created_at TEXT NOT NULL
);

CREATE UNIQUE INDEX IF NOT EXISTS social_comments_snapshot_identity
ON social_comments(property_id, snapshot_id, comment_key);

CREATE TABLE IF NOT EXISTS parcel_history_findings (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    property_id INTEGER NOT NULL REFERENCES properties(id),
    snapshot_id TEXT NOT NULL,
    finding_key TEXT NOT NULL,
    source_id TEXT NOT NULL REFERENCES sources(source_key),
    geography_scope TEXT NOT NULL,
    historical_use TEXT NOT NULL,
    finding_state TEXT NOT NULL,
    start_on TEXT,
    end_on TEXT,
    distance_meters INTEGER,
    direction TEXT NOT NULL DEFAULT '',
    observed_on TEXT NOT NULL,
    retrieved_on TEXT NOT NULL,
    grade TEXT NOT NULL,
    metadata_json TEXT NOT NULL DEFAULT '{}',
    created_at TEXT NOT NULL
);

CREATE UNIQUE INDEX IF NOT EXISTS parcel_history_findings_snapshot_identity
ON parcel_history_findings(property_id, snapshot_id, finding_key);

CREATE TABLE IF NOT EXISTS environmental_findings (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    property_id INTEGER NOT NULL REFERENCES properties(id),
    snapshot_id TEXT NOT NULL,
    finding_key TEXT NOT NULL,
    source_id TEXT NOT NULL REFERENCES sources(source_key),
    geography_scope TEXT NOT NULL,
    hazard_type TEXT NOT NULL,
    finding_state TEXT NOT NULL,
    remediation_status TEXT NOT NULL DEFAULT '',
    acceptance_status TEXT NOT NULL DEFAULT '',
    residual_uncertainty TEXT NOT NULL DEFAULT '',
    valuation_treatment TEXT NOT NULL DEFAULT '',
    observed_on TEXT NOT NULL,
    retrieved_on TEXT NOT NULL,
    grade TEXT NOT NULL,
    metadata_json TEXT NOT NULL DEFAULT '{}',
    created_at TEXT NOT NULL
);

CREATE UNIQUE INDEX IF NOT EXISTS environmental_findings_snapshot_identity
ON environmental_findings(property_id, snapshot_id, finding_key);

CREATE TABLE IF NOT EXISTS cultural_factors (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    property_id INTEGER NOT NULL REFERENCES properties(id),
    snapshot_id TEXT NOT NULL,
    factor_key TEXT NOT NULL,
    source_id TEXT NOT NULL REFERENCES sources(source_key),
    geography_scope TEXT NOT NULL DEFAULT '',
    observable_feature TEXT NOT NULL,
    cultural_interpretation TEXT NOT NULL DEFAULT '',
    buyer_sensitivity TEXT NOT NULL,
    objective_counterpart TEXT NOT NULL DEFAULT '',
    liquidity_treatment TEXT NOT NULL DEFAULT '',
    observed_on TEXT NOT NULL,
    retrieved_on TEXT NOT NULL,
    grade TEXT NOT NULL,
    metadata_json TEXT NOT NULL DEFAULT '{}',
    created_at TEXT NOT NULL
);

CREATE UNIQUE INDEX IF NOT EXISTS cultural_factors_snapshot_identity
ON cultural_factors(property_id, snapshot_id, factor_key);

INSERT OR IGNORE INTO schema_version(version, applied_at)
VALUES (1, CURRENT_TIMESTAMP);

INSERT OR IGNORE INTO schema_version(version, applied_at)
VALUES (2, CURRENT_TIMESTAMP);

INSERT OR IGNORE INTO schema_version(version, applied_at)
VALUES (3, CURRENT_TIMESTAMP);

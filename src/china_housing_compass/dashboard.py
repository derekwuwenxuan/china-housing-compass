"""Generate self-contained, offline HTML research dashboards."""

from decimal import Decimal, InvalidOperation
from datetime import date
from html import escape
from pathlib import Path
import re
from typing import Any, Iterable, List, Mapping, Sequence

from .database import ResearchDatabase, _decode


TEMPLATE_PATH = Path(__file__).with_name("templates") / "dashboard.html"
KNOWN_SLUGS = {"澄江雅苑（合成示例）": "synthetic-river-garden"}


def _slug(project: Mapping[str, Any]) -> str:
    name = project.get("project_name") or project.get("community_name") or "property"
    if name in KNOWN_SLUGS:
        return KNOWN_SLUGS[name]
    ascii_slug = re.sub(r"[^a-z0-9]+", "-", str(name).lower()).strip("-")
    return ascii_slug or f"property-{project['id']}"


def _text(value: Any) -> str:
    if isinstance(value, Decimal):
        value = format(value, "f")
    return escape(str(value), quote=True)


def _evidence_table(records: Sequence[Any]) -> str:
    if not records:
        return '<p class="empty">No verified records yet / 暂无已核验数据。</p>'
    rows = []
    for item in records:
        rows.append(
            "<tr>"
            f"<td>{_text(item.evidence_type)}</td>"
            f"<td>{_text(item.value)} {_text(item.unit)}</td>"
            f"<td>{_text(item.observed_on.isoformat())}</td>"
            f"<td>Source grade {_text(item.grade.value)}</td>"
            f"<td>{_text(item.source)}</td>"
            "</tr>"
        )
    return (
        "<table><thead><tr><th>Metric / 指标</th><th>Value / 数值</th>"
        "<th>Observed / 观察日</th><th>Evidence / 证据</th><th>Source / 来源</th>"
        "</tr></thead><tbody>" + "".join(rows) + "</tbody></table>"
    )


def _result_value(result: Mapping[str, Any], key: str, default: str = "Not calculated") -> str:
    return _text(result.get(key, default))


def _scenario_table(result: Mapping[str, Any]) -> str:
    scenarios = result.get("scenarios", {})
    if not isinstance(scenarios, Mapping) or not scenarios:
        return '<p class="empty">No delivery scenarios stored / 暂无交付情景。</p>'
    rows = []
    values = []
    for name, data in scenarios.items():
        data = data if isinstance(data, Mapping) else {"delivery_value": data}
        delivery_value = data.get("delivery_value", "")
        maximum = data.get("maximum_purchase_price_today", "")
        rows.append(
            f"<tr><td>{_text(name)}</td><td>{_text(delivery_value)} RMB</td>"
            f"<td>{_text(maximum) if maximum != '' else '—'}</td></tr>"
        )
        try:
            values.append((str(name), Decimal(str(delivery_value))))
        except (InvalidOperation, ValueError):
            pass
    chart = _inline_bar_chart(values)
    return chart + (
        "<table><thead><tr><th>Scenario / 情景</th><th>Delivery value / 交付价值</th>"
        "<th>Maximum price today / 今日最高承受价</th></tr></thead><tbody>"
        + "".join(rows) + "</tbody></table>"
    )


def _inline_bar_chart(values: Sequence[Any]) -> str:
    if not values:
        return ""
    maximum = max(value for _, value in values)
    if maximum <= 0:
        return ""
    width, row_height = 720, 34
    height = max(130, 24 + len(values) * row_height)
    parts = [f'<svg class="chart" viewBox="0 0 {width} {height}" role="img" aria-label="Scenario value chart">']
    for index, (name, value) in enumerate(values):
        y = 14 + index * row_height
        bar_width = int((value / maximum) * Decimal("500"))
        parts.append(f'<text x="0" y="{y + 16}" font-size="13">{_text(name)}</text>')
        parts.append(f'<rect x="120" y="{y}" width="{bar_width}" height="20" rx="5" fill="#176b50"/>')
        parts.append(f'<text x="{130 + bar_width}" y="{y + 16}" font-size="12">{_text(value)}</text>')
    parts.append("</svg>")
    return "".join(parts)


def _section(title: str, body: str) -> str:
    return f"<section><h2>{title}</h2>{body}</section>"


def _label(value: Any, default: str = "unknown") -> str:
    """Format stored enum values for display without treating unknown as a fact."""

    if value in (None, ""):
        value = default
    return str(value).replace("_", " ")


def _details(value: Any, default: str = "none stored") -> str:
    """Flatten stored structured details for escaped, human-readable display."""

    if isinstance(value, Mapping):
        if not value:
            return default
        return "; ".join(
            f"{_label(key)}: {_details(item, default='none')}"
            for key, item in value.items()
        )
    if isinstance(value, Sequence) and not isinstance(value, (str, bytes, bytearray)):
        if not value:
            return default
        return ", ".join(_details(item, default="none") for item in value)
    if value in (None, ""):
        return default
    return str(value)


def _has_marker(value: Any) -> bool:
    """Treat explicit false/empty classifications as unmarked."""

    if isinstance(value, Mapping):
        return any(_has_marker(item) for item in value.values())
    if isinstance(value, Sequence) and not isinstance(value, (str, bytes, bytearray)):
        return any(_has_marker(item) for item in value)
    if isinstance(value, str):
        return value.strip().lower() not in {"", "false", "no", "none", "0"}
    return bool(value)


def _badge(label: str, value: Any, style: str = "") -> str:
    classes = "badge" + (f" {style}" if style else "")
    return f'<span class="{classes}">{_text(label)}: {_text(_label(value))}</span>'


def _is_stale(retrieved_on: Any) -> bool:
    try:
        return (date.today() - date.fromisoformat(str(retrieved_on))).days > 30
    except (TypeError, ValueError):
        return True


def _research_row_order(item: Mapping[str, Any]) -> tuple:
    """Order append-only rows by their observed/retrieved dates, then row ID."""

    try:
        row_id = int(item.get("id", 0))
    except (TypeError, ValueError):
        row_id = 0
    return (str(item.get("observed_on", "")), str(item.get("retrieved_on", "")), row_id)


def _latest_by_stable_key(records: Sequence[Mapping[str, Any]], key: str) -> List[Mapping[str, Any]]:
    """Keep the most recent row for each stable key without deleting history."""

    latest = {}
    for item in records:
        stable_key = item.get(key) or f"row-{item.get('id', '')}"
        prior = latest.get(stable_key)
        if prior is None or _research_row_order(item) >= _research_row_order(prior):
            latest[stable_key] = item
    return sorted(latest.values(), key=_research_row_order)


def _research_provenance(
    item: Mapping[str, Any], *, include_scope: bool = False, show_evidence_grade: bool = False
) -> str:
    """Show the safe, source-linked fields shared by research-layer records."""

    if show_evidence_grade:
        parts = [
            _badge("Evidence grade / 证据等级", item.get("grade"), "badge-grade"),
            _badge(
                "Source registry grade / 来源登记等级",
                item.get("source_grade", item.get("grade")),
                "badge-grade",
            ),
        ]
    else:
        parts = [
            _badge(
                "Source grade",
                item.get("source_grade", item.get("grade")),
                "badge-grade",
            ),
        ]
    if include_scope:
        parts.append(_badge("Scope", item.get("geography_scope"), "badge-scope"))
    if "finding_state" in item:
        parts.append(_badge("Finding", item.get("finding_state"), "badge-state"))
    access_mode = item.get("access_mode")
    if access_mode is not None:
        access_style = "badge-unavailable" if access_mode == "unavailable" else "badge-access"
        parts.append(_badge("Access", access_mode, access_style))
    if _is_stale(item.get("retrieved_on")):
        parts.append(_badge("Freshness", "stale", "badge-stale"))
    source_title = item.get("source_title") or item.get("source_id", "unknown")
    source_url = item.get("source_url") or "unknown"
    source_retrieved = item.get("source_retrieved_on") or "unknown"
    return (
        '<div class="badges">' + "".join(parts) + "</div>"
        f'<div class="evidence-meta">Observed: {_text(item.get("observed_on", "unknown"))}'
        f' · Retrieved: {_text(item.get("retrieved_on", "unknown"))}'
        f' · Source: {_text(source_title)}'
        f' · URL: {_text(source_url)}'
        f' · Source retrieved: {_text(source_retrieved)}</div>'
    )


def _social_section(db: ResearchDatabase, property_id: int) -> str:
    all_runs = db.list_research_layer(property_id, "social_research_runs")
    items = db.list_research_layer(property_id, "social_items")
    comments = db.list_research_layer(property_id, "social_comments")
    latest_social_row = max([*all_runs, *items, *comments], key=_research_row_order, default=None)
    current_snapshot = latest_social_row.get("snapshot_id") if latest_social_row else None
    runs = [run for run in all_runs if run.get("snapshot_id") == current_snapshot]
    if current_snapshot is not None:
        items = [item for item in items if item.get("snapshot_id") == current_snapshot]
        comments = [item for item in comments if item.get("snapshot_id") == current_snapshot]
    items = _latest_by_stable_key(items, "item_key")
    comments = _latest_by_stable_key(comments, "comment_key")
    platforms = sorted({platform for run in runs for platform in run.get("platforms_json", [])} | {
        item.get("platform") for item in items if item.get("platform")
    })
    access_modes = sorted({item.get("access_mode") for item in [*runs, *items] if item.get("access_mode")})
    stances = sorted({item.get("stance") for item in [*items, *comments] if item.get("stance")})
    social_records = [*runs, *items, *comments]
    sample_dates = [
        str(item.get("published_on") or item.get("observed_on"))
        for item in social_records
        if item.get("published_on") or item.get("observed_on")
    ]
    time_window = (
        f"{min(sample_dates)} – {max(str(item.get('observed_on')) for item in social_records)}"
        if sample_dates
        else "unknown"
    )
    themes = sorted({
        str(theme)
        for comment in comments
        for theme in comment.get("themes_json", [])
        if theme not in (None, "")
    })
    commercial_count = sum(
        1 for item in items
        if _has_marker(item.get("commercial_json", {}))
    )
    commercial_share = (commercial_count / len(items) * 100) if items else 0
    allegations = []
    for item in [*items, *comments]:
        metadata = item.get("metadata_json", {})
        if not isinstance(metadata, Mapping):
            continue
        stored = metadata.get("unverified_allegations", [])
        if isinstance(stored, Sequence) and not isinstance(stored, (str, bytes, bytearray)):
            allegations.extend(str(value) for value in stored if value not in (None, ""))
    run_summaries = []
    for run in runs:
        failures = run.get("failures_json", {})
        if isinstance(failures, Mapping) and failures:
            failed_sources = ", ".join(
                f"{source}: {reason}" for source, reason in failures.items()
            )
        else:
            failed_sources = "none reported"
        run_summaries.append(
            '<div class="sample-run">'
            f'<p><strong>Coverage:</strong> {_text(run.get("obtained_count", 0))} of '
            f'{_text(run.get("requested_count", 0))} requested sources; '
            f'<strong>Failed-source coverage:</strong> {_text(failed_sources)}.</p>'
            f'{_research_provenance(run)}'
            "</div>"
        )
    post_rows = []
    for item in items:
        engagement = _details(item.get("engagement_json"))
        commercial = _details(item.get("commercial_json"))
        post_rows.append(
            "<tr>"
            f'<td>{_text(item.get("platform", "unknown"))}</td>'
            f'<td>{_text(item.get("author_role", "unknown"))} · {_text(item.get("content_type", "unknown"))}</td>'
            f'<td>{_text(item.get("summary", ""))}'
            f'<div class="evidence-meta"><strong>Engagement:</strong> {_text(engagement)}<br>'
            f'<strong>Commercial markers:</strong> {_text(commercial)}</div></td>'
            f'<td>{_badge("Stance", item.get("stance"), "badge-state")}'
            f'{_research_provenance(item, show_evidence_grade=True)}</td>'
            "</tr>"
        )
    comment_rows = []
    for comment in comments:
        themes_text = _details(comment.get("themes_json"))
        engagement = _details(comment.get("engagement_json"))
        comment_rows.append(
            "<tr>"
            f'<td>{_text(comment.get("stance", "unknown"))}</td>'
            f'<td>{_text(comment.get("summary", ""))}'
            f'<div class="evidence-meta"><strong>Themes:</strong> {_text(themes_text)}<br>'
            f'<strong>Engagement:</strong> {_text(engagement)}</div></td>'
            f'<td>{_research_provenance(comment, show_evidence_grade=True)}</td>'
            "</tr>"
        )
    platform_text = ", ".join(_label(platform) for platform in platforms) or "none captured"
    access_text = ", ".join(_label(mode) for mode in access_modes) or "unavailable"
    disagreement = ", ".join(_label(stance) for stance in stances) or "unknown"
    social_attempts = [
        attempt
        for category, attempt in db.latest_refresh_attempts(property_id).items()
        if "social" in category.lower()
    ]
    latest_social_attempt = max(
        social_attempts,
        key=lambda attempt: str(attempt.get("finished_at", "")),
        default=None,
    )
    refresh_notice = ""
    if latest_social_attempt and latest_social_attempt.get("outcome") == "failed":
        refresh_notice = (
            '<p class="warning"><strong>Social refresh: stale</strong> · '
            f'{_text(latest_social_attempt.get("failure_reason", "unknown failure"))}</p>'
        )
    body = refresh_notice + (
        f'<p><strong>{_text(len(items))} posts / {_text(len(comments))} comments</strong> · '
        f'<strong>Platforms captured:</strong> {_text(platform_text)} · '
        f'<strong>Access:</strong> {_text(access_text)}.</p>'
        f'<p><strong>Sample time window: {_text(time_window)}</strong> · '
        f'<strong>Commercial-marked posts: {_text(commercial_count)}/{_text(len(items))} '
        f'({_text(f"{commercial_share:.1f}")}%)</strong>.</p>'
        f'<p><strong>Captured themes:</strong> {_text(", ".join(themes) or "none stored")}.</p>'
        f'<p class="warning">Commercial-content caveat: captured social samples can include promotional or selective content and are not representative of all buyers.</p>'
        f'<p><strong>Disagreement:</strong> {_text(disagreement)} stances appear in the captured sample.</p>'
        + (
            '<p class="warning"><strong>Unverified allegations awaiting verification:</strong> '
            + _text("; ".join(allegations)) + ".</p>"
            if allegations else
            '<p><strong>Unverified allegations awaiting verification:</strong> none stored.</p>'
        )
        + "".join(run_summaries)
        + ("<h3>Captured posts</h3><table><thead><tr><th>Platform</th><th>Context</th><th>Summary</th><th>Evidence</th></tr></thead><tbody>"
           + "".join(post_rows) + "</tbody></table>" if post_rows else '<p class="empty">No captured posts.</p>')
        + ("<h3>Captured comments</h3><table><thead><tr><th>Stance</th><th>Summary</th><th>Evidence</th></tr></thead><tbody>"
           + "".join(comment_rows) + "</tbody></table>" if comment_rows else '<p class="empty">No captured comments.</p>')
    )
    return _section("Social reputation and captured comments / 社交口碑与已采集评论", body)


def _parcel_history_section(db: ResearchDatabase, property_id: int) -> str:
    findings = db.list_research_layer(property_id, "parcel_history_findings")
    exact_findings = [item for item in findings if item.get("geography_scope") == "exact_parcel"]
    exact = max(exact_findings, key=_research_row_order, default=None)
    exact_use = exact.get("historical_use") if exact else "unknown"
    rows = []
    for item in findings:
        start_on = item.get("start_on") or "unknown"
        end_on = item.get("end_on") or "unknown"
        timeline = f"{start_on} – {end_on}"
        distance = item.get("distance_meters")
        proximity = f"{distance} m" if distance is not None else "distance unknown"
        if item.get("direction"):
            proximity += f" · {item['direction']}"
        rows.append(
            "<tr>"
            f'<td>{_text(_label(item.get("historical_use")))}</td>'
            f'<td>{_text(timeline)}</td>'
            f'<td>{_text(proximity)}</td>'
            f'<td>{_research_provenance(item, include_scope=True)}</td>'
            "</tr>"
        )
    body = (
        f'<p><strong>Exact parcel: {_text(_label(exact_use))}</strong>. Broader-area findings are shown separately and do not establish parcel history.</p>'
        + ("<table><thead><tr><th>Historical use</th><th>Active period</th><th>Distance and direction</th><th>Evidence</th></tr></thead><tbody>" + "".join(rows) + "</tbody></table>"
           if rows else '<p class="empty">No parcel-history findings captured.</p>')
    )
    return _section("Parcel history / 地块历史", body)


def _environment_section(db: ResearchDatabase, property_id: int) -> str:
    findings = db.list_research_layer(property_id, "environmental_findings")
    rows = []
    for item in findings:
        details = [
            _label(item.get("remediation_status")),
            _label(item.get("acceptance_status")),
            _label(item.get("residual_uncertainty")),
        ]
        details = [detail for detail in details if detail != "unknown"]
        rows.append(
            "<tr>"
            f'<td>{_text(_label(item.get("hazard_type")))}</td>'
            f'<td>{_text("; ".join(details) or "unknown")}</td>'
            f'<td>{_text(_label(item.get("valuation_treatment")))}</td>'
            f'<td>{_research_provenance(item, include_scope=True)}</td>'
            "</tr>"
        )
    body = (
        '<p class="warning">Environmental findings describe recorded evidence and any remaining uncertainty; they are not a substitute for project-specific due diligence.</p>'
        + ("<table><thead><tr><th>Hazard or legacy</th><th>Status</th><th>Valuation treatment</th><th>Evidence</th></tr></thead><tbody>" + "".join(rows) + "</tbody></table>"
           if rows else '<p class="empty">No environmental findings captured.</p>')
    )
    return _section("Environmental legacy / 环境遗留", body)


def _cultural_section(db: ResearchDatabase, property_id: int) -> str:
    factors = db.list_research_layer(property_id, "cultural_factors")
    rows = []
    for item in factors:
        rows.append(
            "<tr>"
            f'<td>{_text(item.get("observable_feature", "unknown"))}</td>'
            f'<td>{_text(item.get("cultural_interpretation", "unknown"))}</td>'
            f'<td>{_badge("Buyer sensitivity", item.get("buyer_sensitivity"), "badge-state")}</td>'
            f'<td>{_text(_label(item.get("objective_counterpart")))}</td>'
            f'<td>{_text(_label(item.get("liquidity_treatment")))}</td>'
            f'<td>{_research_provenance(item, include_scope=True)}</td>'
            "</tr>"
        )
    body = (
        '<p class="warning">Cultural interpretations reflect stated resale perception, not verified physical hazards or universal buyer preferences.</p>'
        + ("<table><thead><tr><th>Observable feature</th><th>Interpretation</th><th>Perception</th><th>Objective counterpart</th><th>Liquidity treatment</th><th>Evidence</th></tr></thead><tbody>" + "".join(rows) + "</tbody></table>"
           if rows else '<p class="empty">No cultural-acceptance factors captured.</p>')
    )
    return _section("Cultural acceptance and resale perception / 文化接受度与转售认知", body)


def _render(template: str, title: str, meta: str, content: str) -> str:
    return template.replace("{{TITLE}}", _text(title)).replace("{{META}}", meta).replace("{{CONTENT}}", content)


def _latest_success(db: ResearchDatabase, property_id: int) -> Any:
    return db.latest_successful_refresh(property_id)


def _refresh_attempts_table(db: ResearchDatabase, property_id: int) -> str:
    attempts = db.latest_refresh_attempts(property_id)
    if not attempts:
        return '<p class="empty">No category refresh attempts recorded.</p>'
    rows = []
    for category, attempt in sorted(attempts.items()):
        outcome = attempt.get("outcome", "unknown")
        style = "badge-stale" if outcome == "failed" else "badge-state"
        rows.append(
            "<tr>"
            f"<td>{_text(category)}</td>"
            f'<td>{_badge("Outcome", outcome, style)}</td>'
            f'<td>{_text(attempt.get("finished_at", "unknown"))}</td>'
            f'<td>{_text(attempt.get("failure_reason") or "none")}</td>'
            "</tr>"
        )
    return (
        "<h3>Latest source/category refresh attempts</h3>"
        "<table><thead><tr><th>Category</th><th>Freshness</th><th>Attempted</th>"
        "<th>Failure reason</th></tr></thead><tbody>"
        + "".join(rows) + "</tbody></table>"
    )


def _project_page(db: ResearchDatabase, project: Mapping[str, Any], template: str) -> str:
    property_id = int(project["id"])
    records = db.list_evidence(property_id)
    valuation = db.latest_valuation(property_id)
    result = valuation["result"] if valuation else {}
    recommendation = valuation["recommendation"] if valuation else "research incomplete"
    confidence = valuation["confidence"] if valuation else "low"
    refresh = db.latest_refresh(property_id)
    successful = _latest_success(db, property_id)
    successful_at = successful["finished_at"] if successful else "Never"
    current_status = refresh["status"] if refresh else "never refreshed"

    categories = {
        "history": [r for r in records if any(term in r.evidence_type for term in ("index", "transaction_volume", "historical"))],
        "price_rent": [r for r in records if "price" in r.evidence_type or "rent" in r.evidence_type],
        "inventory": [r for r in records if "units" in r.evidence_type or "inventory" in r.evidence_type or "supply" in r.evidence_type],
        "risk": [r for r in records if any(term in r.evidence_type for term in ("developer", "delivery", "model_home", "penalty", "claim"))],
        "infrastructure": [r for r in records if "infrastructure" in r.evidence_type or "facility" in r.evidence_type],
        "affordability": [r for r in records if any(term in r.evidence_type for term in ("income", "mortgage", "affordability"))],
    }

    fair_range = result.get("comparable_fair_range", "Not calculated")
    if isinstance(fair_range, (list, tuple)):
        fair_range = " – ".join(str(value) for value in fair_range) + " RMB"
    hero = (
        '<div class="hero"><div><h2>Recommendation / 购房建议</h2>'
        f'<div class="recommendation">{_text(recommendation)}</div>'
        f'<p>Confidence / 置信度：{_text(confidence)}</p></div>'
        '<div class="grid">'
        f'<div class="metric"><small>Comparable fair range / 可比合理区间</small><strong>{_text(fair_range)}</strong></div>'
        f'<div class="metric"><small>Risk-adjusted maximum / 风险调整最高价</small><strong>{_result_value(result, "risk_adjusted_max_price")} RMB</strong></div>'
        f'<div class="metric"><small>Rent-supported value / 租金支撑价</small><strong>{_result_value(result, "rent_supported_value")} RMB</strong></div>'
        f'<div class="metric"><small>Current refresh / 当前刷新</small><strong>{_text(current_status)}</strong></div>'
        "</div></div>"
    )

    content = [hero]
    content.append(_section("Valuation ranges / 估值区间", f"<p>Comparable: {_text(fair_range)}<br>Rent-supported: {_result_value(result, 'rent_supported_value')} RMB<br>Risk-adjusted maximum: {_result_value(result, 'risk_adjusted_max_price')} RMB</p>"))
    content.append(_section("Five-year context / 五年走势", _evidence_table(categories["history"])))
    content.append(_section("Price and rent comparables / 售价与租金可比", _evidence_table(categories["price_rent"])))
    content.append(_section("Inventory and supply / 库存与供应", _evidence_table(categories["inventory"])))
    content.append(_section("Developer and delivery risk / 开发商与交付风险", _evidence_table(categories["risk"])))
    content.append(_section("Infrastructure status / 基础设施兑现", _evidence_table(categories["infrastructure"])))
    content.append(_section("Affordability / 支付能力", _evidence_table(categories["affordability"])))
    content.append(_section("Delivery scenarios / 交付情景", _scenario_table(result)))
    content.append(_social_section(db, property_id))
    content.append(_parcel_history_section(db, property_id))
    content.append(_environment_section(db, property_id))
    content.append(_cultural_section(db, property_id))
    content.append(_section("Sources and evidence / 来源与证据", _evidence_table(records)))
    missing = result.get("missing_categories", [])
    if isinstance(missing, (list, tuple)):
        missing_text = ", ".join(_text(item) for item in missing) or "None recorded"
    else:
        missing_text = _text(missing)
    freshness = f"<p><strong>Last successful refresh:</strong> {_text(successful_at)}<br><strong>Missing:</strong> {missing_text}</p>"
    if current_status == "unchanged":
        freshness += '<p class="warning">Latest refresh found no new records; the prior successful-refresh timestamp remains authoritative.</p>'
    elif current_status != "success":
        freshness += '<p class="warning">Latest refresh was not fully successful; older evidence remains visible and must not be treated as freshly verified.</p>'
    freshness += _refresh_attempts_table(db, property_id)
    content.append(_section("Missing evidence and freshness / 缺失证据与时效", freshness))

    title = project.get("project_name") or project.get("community_name") or f"Property {property_id}"
    meta = f"{_text(project['city'])} · {_text(project['district'])} · {_text(project.get('submarket', ''))}<br>Local offline research dashboard"
    return _render(template, str(title), meta, "".join(content))


def build_dashboard(database_path: Any, output_dir: Any) -> List[Path]:
    """Build an index and one self-contained page per tracked property."""

    output = Path(output_dir)
    output.mkdir(parents=True, exist_ok=True)
    template = TEMPLATE_PATH.read_text(encoding="utf-8")
    db = ResearchDatabase(database_path)
    outputs: List[Path] = []
    try:
        projects = db.list_properties()
        links = []
        for project in projects:
            filename = _slug(project) + ".html"
            page = output / filename
            page.write_text(_project_page(db, project, template), encoding="utf-8")
            outputs.append(page)
            name = project.get("project_name") or project.get("community_name") or filename
            links.append(f'<section><h2><a href="{_text(filename)}">{_text(name)}</a></h2><p>{_text(project["city"])} · {_text(project["district"])} · {_text(project.get("submarket", ""))}</p></section>')
        index = output / "index.html"
        index.write_text(
            _render(template, "Tracked homes / 房源跟踪", "Offline, local-first, source-graded", "".join(links) or '<section><p class="empty">No tracked homes yet.</p></section>'),
            encoding="utf-8",
        )
        outputs.append(index)
    finally:
        db.close()
    return outputs

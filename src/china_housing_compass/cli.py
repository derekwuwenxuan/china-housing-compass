"""Command-line workflows for local China Housing Compass research workspaces."""

import argparse
from datetime import datetime, timezone
from decimal import Decimal
import json
from pathlib import Path
import sys
from typing import Any, Mapping, Optional, Sequence

from .dashboard import build_dashboard
from .database import ResearchDatabase
from .importers import import_snapshot, load_snapshot
from .models import ValidationError, decimal_value
from .providers.structured_import import StructuredImportProvider
from .refresh import RefreshRequest, run_refresh
from .risk import calculate_confidence, detect_red_flags, recommend
from .valuation import gross_rental_yield, listing_unit_price, price_to_income_ratio


WORKSPACE_DIRS = ("inputs", "snapshots", "reports", "dashboard")


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="china-housing-compass",
        description="Evidence-backed Chinese home valuation and local tracking",
    )
    commands = parser.add_subparsers(dest="command", required=True)

    init = commands.add_parser("init", help="create a local research workspace")
    init.add_argument("workspace")

    importer = commands.add_parser("import", help="import a normalized JSON snapshot")
    importer.add_argument("workspace")
    importer.add_argument("snapshot")

    valuate = commands.add_parser("valuate", help="save a reproducible valuation assessment")
    valuate.add_argument("workspace")
    valuate.add_argument("property_id", type=int)
    valuate.add_argument("--objective", default="owner_occupation")
    valuate.add_argument("--asking-price")
    valuate.add_argument("--area")
    valuate.add_argument("--monthly-rent")
    valuate.add_argument("--annual-income")
    valuate.add_argument("--risk-adjusted-max-price", required=True)

    dashboard = commands.add_parser("dashboard", help="build offline HTML dashboards")
    dashboard.add_argument("workspace")

    refresh = commands.add_parser("refresh", help="refresh selected categories from saved snapshots")
    refresh.add_argument("workspace")
    refresh.add_argument("property_id", type=int)
    refresh.add_argument(
        "--provider",
        action="append",
        default=[],
        metavar="CATEGORY=SNAPSHOT.json",
        help="repeat for each category to refresh",
    )

    status = commands.add_parser("status", help="show refresh status and stale categories")
    status.add_argument("workspace")
    status.add_argument("--property-id", type=int)
    return parser


def _workspace(value: str, *, require_database: bool = True) -> Path:
    root = Path(value).expanduser().resolve()
    if require_database and not (root / "housing.sqlite").is_file():
        raise ValidationError(f"workspace is not initialized: {root}")
    return root


def _cmd_init(args: argparse.Namespace) -> int:
    root = _workspace(args.workspace, require_database=False)
    root.mkdir(parents=True, exist_ok=True)
    for name in WORKSPACE_DIRS:
        (root / name).mkdir(exist_ok=True)
    db = ResearchDatabase(root / "housing.sqlite")
    try:
        db.initialize()
    finally:
        db.close()
    print(f"Initialized China Housing Compass workspace: {root / 'housing.sqlite'}")
    return 0


def _cmd_import(args: argparse.Namespace) -> int:
    root = _workspace(args.workspace)
    payload = load_snapshot(args.snapshot)
    db = ResearchDatabase(root / "housing.sqlite")
    try:
        result = import_snapshot(db, payload)
    finally:
        db.close()
    print(
        f"Imported {result['imported_evidence']} evidence records "
        f"for property {result['property_id']}"
    )
    layer_count = sum(result.get("imported_layers", {}).values())
    if result["schema_version"] == 2:
        print(f"Imported {layer_count} research-layer records")
    return 0


def _latest_number(latest: Mapping[str, Any], evidence_type: str) -> Optional[Decimal]:
    record = latest.get(evidence_type)
    if record is None:
        return None
    return decimal_value(record.value, evidence_type)


def _cmd_valuate(args: argparse.Namespace) -> int:
    root = _workspace(args.workspace)
    db = ResearchDatabase(root / "housing.sqlite")
    try:
        project = db.get_property(args.property_id)
        evidence = db.list_evidence(args.property_id)
        latest = db.latest_evidence(args.property_id)
        quote_record = latest.get("developer_quoted_total_price")
        asking = decimal_value(args.asking_price, "asking_price") if args.asking_price else _latest_number(latest, "developer_quoted_total_price")
        if asking is None:
            raise ValidationError("asking price is required or must exist in stored evidence")
        area = decimal_value(args.area, "area") if args.area else None
        if area is None and quote_record is not None:
            area_value = quote_record.metadata.get("area_sqm")
            if area_value is not None:
                area = decimal_value(area_value, "area_sqm")
        if area is None:
            raise ValidationError("area is required or must exist in quote metadata")
        maximum = decimal_value(args.risk_adjusted_max_price, "risk_adjusted_max_price")

        confidence, missing = calculate_confidence(
            evidence,
            ("price", "inventory", "product", "transactions", "rent"),
        )
        findings = detect_red_flags(evidence)
        values = {
            "asking_price": asking,
            "risk_adjusted_max_price": maximum,
            "asking_unit_price": listing_unit_price(asking, area),
        }
        if args.monthly_rent:
            rent = decimal_value(args.monthly_rent, "monthly_rent")
            values["gross_rental_yield"] = gross_rental_yield(rent, asking)
        if args.annual_income:
            income = decimal_value(args.annual_income, "annual_income")
            values["price_to_income_ratio"] = price_to_income_ratio(asking, income)
        assessment = recommend(
            values,
            findings,
            args.objective,
            confidence=confidence,
            missing_categories=missing,
        )
        result = {
            **values,
            "missing_categories": list(missing),
            "decisive_findings": [item.code for item in assessment.decisive_findings],
            "note": "Conditional valuation range; not a guaranteed market floor.",
        }
        run_id = db.save_valuation_run(
            args.property_id,
            args.objective,
            assessment.recommendation,
            assessment.confidence,
            result,
        )
    finally:
        db.close()

    timestamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    report = root / "reports" / f"valuation-{args.property_id}-{timestamp}.md"
    report.write_text(
        "# China Housing Compass valuation\n\n"
        f"- Project: {project.get('project_name') or project.get('community_name')}\n"
        f"- Recommendation: {assessment.recommendation}\n"
        f"- Confidence: {assessment.confidence}\n"
        f"- Asking price: RMB {asking}\n"
        f"- Asking unit price: RMB {values['asking_unit_price']}/㎡\n"
        f"- Risk-adjusted maximum: RMB {maximum}\n"
        f"- Missing evidence: {', '.join(missing) or 'none'}\n\n"
        "This is a conditional evidence-based range, not a guaranteed floor or investment promise.\n",
        encoding="utf-8",
    )
    print(f"Saved valuation run {run_id}: {report}")
    return 0


def _cmd_dashboard(args: argparse.Namespace) -> int:
    root = _workspace(args.workspace)
    outputs = build_dashboard(root / "housing.sqlite", root / "dashboard")
    print(f"Built {len(outputs)} dashboard files: {root / 'dashboard' / 'index.html'}")
    return 0


def _cmd_refresh(args: argparse.Namespace) -> int:
    root = _workspace(args.workspace)
    if not args.provider:
        raise ValidationError("at least one --provider CATEGORY=SNAPSHOT.json is required")
    providers = {}
    for item in args.provider:
        if "=" not in item:
            raise ValidationError("provider must use CATEGORY=SNAPSHOT.json")
        category, path = item.split("=", 1)
        if not category.strip() or not path.strip():
            raise ValidationError("provider must use CATEGORY=SNAPSHOT.json")
        providers[category] = StructuredImportProvider(path)
    db = ResearchDatabase(root / "housing.sqlite")
    try:
        result = run_refresh(
            db,
            providers,
            RefreshRequest(
                property_id=args.property_id,
                categories=tuple(providers),
                dashboard_dir=root / "dashboard",
            ),
        )
    finally:
        db.close()
    print(f"Refresh status: {result.status}; added {result.added_records} records")
    if result.unchanged:
        print("Unchanged categories: " + ", ".join(result.unchanged))
    if result.failures:
        for category, error in result.failures.items():
            print(f"Stale {category}: {error}")
    return 0 if result.status in {"success", "unchanged"} else 1


def _cmd_status(args: argparse.Namespace) -> int:
    root = _workspace(args.workspace)
    db = ResearchDatabase(root / "housing.sqlite")
    try:
        projects = db.list_properties()
        if args.property_id is not None:
            projects = [db.get_property(args.property_id)]
        if not projects:
            print("No tracked properties.")
            return 0
        for project in projects:
            property_id = int(project["id"])
            name = project.get("project_name") or project.get("community_name") or property_id
            refresh = db.latest_refresh(property_id)
            print(f"Property {property_id}: {name}")
            if refresh is None:
                print("Last refresh: never")
                print("Last successful refresh: never")
                print("Stale categories: unknown")
                print("Unchanged categories: none")
            else:
                print(f"Last refresh: {refresh['status']} at {refresh['finished_at']}")
                successful = db.latest_successful_refresh(property_id)
                print(
                    "Last successful refresh: "
                    + (successful["finished_at"] if successful else "never")
                )
                stale = tuple(refresh["failures"])
                print("Stale categories: " + (", ".join(stale) if stale else "none"))
                unchanged = tuple(refresh["unchanged"])
                print("Unchanged categories: " + (", ".join(unchanged) if unchanged else "none"))
    finally:
        db.close()
    return 0


COMMANDS = {
    "init": _cmd_init,
    "import": _cmd_import,
    "valuate": _cmd_valuate,
    "dashboard": _cmd_dashboard,
    "refresh": _cmd_refresh,
    "status": _cmd_status,
}


def main(argv: Optional[Sequence[str]] = None) -> int:
    parser = _parser()
    try:
        args = parser.parse_args(argv)
        return COMMANDS[args.command](args)
    except ValidationError as exc:
        print(f"Error: {exc}", file=sys.stderr)
        return 2
    except SystemExit as exc:
        return int(exc.code or 0)


if __name__ == "__main__":
    raise SystemExit(main())

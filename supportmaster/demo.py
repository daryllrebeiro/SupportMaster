"""Repeatable, offline golden-path demo for SupportMaster.

The demo intentionally uses the deterministic evaluation boundary. It proves
the product's safety story without requiring Gemini keys or external systems.
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Sequence

from .evaluation import load_scenarios, simulate_workflow
from .models.organization import OrganizationProfile
from .organization import OrganizationContextService
from .persistence import SQLiteRunStore


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_FIXTURE = ROOT / "fixtures" / "cases" / "saas_authentication.json"
DEFAULT_DB = ROOT / ".supportmaster" / "demo.db"
DEMO_TENANT = "demo-acme"


def seed(db_path: str | Path = DEFAULT_DB) -> Path:
    """Create the local demo store and safe demo organization."""
    path = Path(db_path)
    store = SQLiteRunStore(path)
    OrganizationContextService(store).save(
        OrganizationProfile(
            organization_id=DEMO_TENANT,
            display_name="Acme Demo Organization",
            products=["Identity Gateway", "AuthEngine", "APIGateway", "ExportEngine"],
            services=["Identity Gateway", "AuthEngine", "APIGateway", "ExportEngine"],
        )
    )
    return path


def run_demo(db_path: str | Path = DEFAULT_DB, fixture_path: str | Path = DEFAULT_FIXTURE) -> dict:
    """Run the golden-path scenario and return a JSON-serializable report."""
    path = seed(db_path)
    scenarios = load_scenarios(Path(fixture_path).parent)
    scenario_id = Path(fixture_path).stem
    scenario = next(item for item in scenarios if item.scenario_id == scenario_id)
    result = simulate_workflow(SQLiteRunStore(path), scenario, tenant_id=DEMO_TENANT)
    return result.model_dump(mode="json")


def reset(db_path: str | Path = DEFAULT_DB) -> None:
    """Remove only the explicitly selected demo database and SQLite sidecars."""
    path = Path(db_path)
    for candidate in (path, Path(f"{path}-wal"), Path(f"{path}-shm")):
        if candidate.exists():
            candidate.unlink()


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Run the offline SupportMaster golden-path demo.")
    parser.add_argument("command", choices=("seed", "run", "reset"), nargs="?", default="run")
    parser.add_argument("--db", type=Path, default=DEFAULT_DB)
    parser.add_argument("--fixture", type=Path, default=DEFAULT_FIXTURE)
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    args = _parser().parse_args(argv)
    if args.command == "seed":
        print(json.dumps({"status": "SEEDED", "db": str(seed(args.db))}, indent=2))
    elif args.command == "reset":
        reset(args.db)
        print(json.dumps({"status": "RESET", "db": str(args.db)}, indent=2))
    else:
        report = run_demo(args.db, args.fixture)
        print(json.dumps(report, indent=2, default=str))
        return 0 if report["status"] == "PASS" else 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

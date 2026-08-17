"""Production release-readiness checks for SupportMaster."""

from __future__ import annotations

import argparse
import json
import os
from pathlib import Path
from typing import Mapping, Sequence

from .evaluation.quality import run_fixture_quality_pack
from .integrations import IntegrationPolicy
from .models.evaluation import ReleaseCheck, ReleaseReadinessResult
from .operations import HealthReporter, load_operation_settings
from .persistence import SQLiteRunStore
from .security import load_security_settings


ROOT = Path(__file__).resolve().parents[1]


def run_release_readiness(
    store: SQLiteRunStore,
    scenarios_directory: str | Path,
    *,
    environ: Mapping[str, str] | None = None,
    require_auth: bool = True,
) -> ReleaseReadinessResult:
    """Validate runtime safety posture and deterministic product quality."""
    values = dict(environ or os.environ)
    checks: list[ReleaseCheck] = []
    try:
        load_operation_settings(values)
        checks.append(ReleaseCheck(name="operation_limits", status="PASS", detail="Operational limits are valid."))
    except Exception as error:
        checks.append(ReleaseCheck(name="operation_limits", status="FAIL", detail=str(error)))
    try:
        security = load_security_settings(values)
        secure = security.auth_mode != "DISABLED" if require_auth else True
        checks.append(ReleaseCheck(name="authentication", status="PASS" if secure else "FAIL", detail=f"Authentication mode: {security.auth_mode}."))
    except Exception as error:
        checks.append(ReleaseCheck(name="authentication", status="FAIL", detail=str(error)))
    integration = IntegrationPolicy()
    safe_defaults = integration.mode == "DRY_RUN" and not any(permission.startswith("WRITE_") or permission in {"TRIGGER_CI", "SEND_NOTIFICATIONS"} for permission in integration.allowed_permissions)
    checks.append(ReleaseCheck(name="integration_defaults", status="PASS" if safe_defaults else "FAIL", detail="Default integration policy is read-only dry-run."))
    health = HealthReporter(run_db=store.db_path).readiness()
    checks.append(ReleaseCheck(name="run_store", status="PASS" if health.status == "READY" else "FAIL", detail=str(health.checks)))
    quality = run_fixture_quality_pack(store, scenarios_directory)
    checks.append(ReleaseCheck(name="quality_pack", status=quality.status, detail=f"Functional {quality.functional.passed}/{len(quality.functional.scenarios)}; end-to-end {quality.end_to_end.passed}/{len(quality.end_to_end.simulations)}."))
    return ReleaseReadinessResult(status="PASS" if all(check.status == "PASS" for check in checks) else "FAIL", checks=checks, quality=quality)


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Run SupportMaster release-readiness checks.")
    parser.add_argument("--fixtures", type=Path, default=ROOT / "fixtures" / "cases")
    parser.add_argument("--db", type=Path, default=ROOT / ".supportmaster" / "release.db")
    parser.add_argument("--allow-anonymous", action="store_true", help="Do not require authentication for local-only checks.")
    args = parser.parse_args(argv)
    result = run_release_readiness(SQLiteRunStore(args.db), args.fixtures, require_auth=not args.allow_anonymous)
    print(json.dumps(result.model_dump(mode="json"), indent=2, default=str))
    return 0 if result.status == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())

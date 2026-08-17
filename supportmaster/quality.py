"""Command-line pre-demo quality validation."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Sequence

from .evaluation.quality import run_fixture_quality_pack
from .persistence import SQLiteRunStore


ROOT = Path(__file__).resolve().parents[1]


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Run SupportMaster's deterministic pre-demo quality pack.")
    parser.add_argument("--fixtures", type=Path, default=ROOT / "fixtures" / "cases")
    parser.add_argument("--db", type=Path, default=ROOT / ".supportmaster" / "quality.db")
    args = parser.parse_args(argv)
    result = run_fixture_quality_pack(SQLiteRunStore(args.db), args.fixtures)
    print(json.dumps(result.model_dump(mode="json"), indent=2, default=str))
    return 0 if result.status == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())

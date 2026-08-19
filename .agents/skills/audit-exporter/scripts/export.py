"""Exporter script to extract and redact tenant telemetry audit logs from SupportMaster runs database."""

import argparse
import json
import re
import sqlite3
from pathlib import Path


def redact_secrets(val):
    if isinstance(val, dict):
        return {k: redact_secrets(v) for k, v in val.items()}
    elif isinstance(val, list):
        return [redact_secrets(v) for v in val]
    elif isinstance(val, str):
        if "secret" in val.lower():
            return "[REDACTED_SECRET]"
        if re.search(r"^[a-zA-Z0-9_\-\|\,]+$", val) and ("secret" in val or "|" in val):
            return "[REDACTED_AUTH_INFO]"
        return val
    return val


def main():
    parser = argparse.ArgumentParser(description="SupportMaster Telemetry Audit Exporter")
    parser.add_argument("--db", required=True, help="Path to SQLite runs database")
    parser.add_argument("--tenant", required=True, help="Tenant ID to filter by")
    parser.add_argument("--output", required=True, help="Path to output JSON file")
    args = parser.parse_args()

    db_path = Path(args.db)
    if not db_path.exists():
        print(f"Error: Database file {args.db} does not exist.")
        return

    connection = sqlite3.connect(str(db_path))
    connection.row_factory = sqlite3.Row
    cursor = connection.cursor()

    try:
        cursor.execute("SELECT run_id, state_json FROM runs")
        rows = cursor.fetchall()
        
        tenant_runs = []
        for row in rows:
            try:
                state = json.loads(row["state_json"])
                if state.get("tenant_id") == args.tenant:
                    tenant_runs.append(row["run_id"])
            except Exception:
                pass

        if not tenant_runs:
            print(f"No runs found for tenant {args.tenant}.")
            with open(args.output, "w", encoding="utf-8") as f:
                json.dump([], f, indent=2)
            return

        placeholders = ",".join("?" for _ in tenant_runs)
        cursor.execute(
            f"SELECT run_id, event_type, payload_json, recorded_at FROM run_events WHERE run_id IN ({placeholders}) ORDER BY sequence ASC",
            tenant_runs
        )
        events = cursor.fetchall()

        audit_log = []
        for event in events:
            try:
                payload = json.loads(event["payload_json"])
                redacted_payload = redact_secrets(payload)
                audit_log.append({
                    "run_id": event["run_id"],
                    "event_type": event["event_type"],
                    "payload": redacted_payload,
                    "recorded_at": event["recorded_at"]
                })
            except Exception:
                pass

        with open(args.output, "w", encoding="utf-8") as f:
            json.dump(audit_log, f, indent=2)
        print(f"Successfully exported {len(audit_log)} audit events for tenant {args.tenant} to {args.output}")

    finally:
        connection.close()


if __name__ == "__main__":
    main()

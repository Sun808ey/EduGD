"""Compare frozen inventories; equality is necessary, not cutover approval."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

from alembic.config import Config
from alembic.script import ScriptDirectory


def compare(source: dict[str, Any], target: dict[str, Any], head: str) -> list[str]:
    if not isinstance(source, dict) or not isinstance(target, dict):
        return ["Invalid inventory: expected JSON objects"]
    failures = []
    for label, report in (("source", source), ("target", target)):
        for field in (
            "sequences",
            "sequence_definitions",
            "triggers",
            "functions",
            "row_security",
        ):
            if not isinstance(report.get(field), list):
                failures.append(f"{label}: missing or invalid {field}")
        if report.get("format_version") != 1:
            failures.append(f"{label}: unsupported inventory version")
        for flag in ("tls_verified", "writers_stopped"):
            if report.get(flag) is not True:
                failures.append(f"{label}: {flag} is not verified")
        if (
            not isinstance(report.get("audit"), dict)
            or not report.get("audit")
            or report.get("missing_application_tables") != []
        ):
            failures.append(f"{label}: incomplete application/audit verification")
        if report.get("migration_heads") != [head]:
            failures.append(f"{label}: migration head mismatch")
        tables = report.get("tables")
        if (
            not isinstance(tables, dict)
            or not tables
            or any(
                not isinstance(table, dict)
                or not isinstance(table.get("sha256"), str)
                or len(table["sha256"]) != 64
                or any(char not in "0123456789abcdef" for char in table["sha256"])
                or type(table.get("row_count")) is not int
                or table["row_count"] < 0
                for table in tables.values()
            )
        ):
            failures.append(f"{label}: missing data fingerprints")
    for key in (
        "tables",
        "sequences",
        "sequence_definitions",
        "triggers",
        "functions",
        "row_security",
        "audit",
    ):
        if source.get(key) != target.get(key):
            failures.append(f"Source/target differ: {key}")
    return failures


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("source", type=Path)
    parser.add_argument("target", type=Path)
    arguments = parser.parse_args()
    try:
        config = Config()
        config.set_main_option(
            "script_location", str(Path(__file__).resolve().parents[1] / "migrations")
        )
        head = ScriptDirectory.from_config(config).get_current_head()
        if head is None:
            raise ValueError("Missing migration head")
        failures = compare(
            json.loads(arguments.source.read_text()),
            json.loads(arguments.target.read_text()),
            head,
        )
    except (OSError, ValueError, TypeError, KeyError):
        print("FAIL: inventories could not be validated")
        return 1
    if failures:
        print("\n".join(failures))
        return 1
    print(
        "PASS: captured application schema/data/evidence match. Operator must still review extensions, roles/grants, other schemas, backups and deployment gates. This is NOT cutover approval."
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

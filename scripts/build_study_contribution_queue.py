"""Freeze the remaining contribution-account queue from the generated study register."""
from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
INDEX = ROOT / "site/public/data/v1/study/index.json"
LEDGER = ROOT / "reports/private-sector-study/orchestration-ledger.json"


def read(path: Path):
    return json.loads(path.read_text(encoding="utf-8"))


def write(path: Path, value):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2) + "\n", encoding="utf-8", newline="\n")


def ranked_projects(index):
    remaining = [
        project for project in index["projects"]
        if project["model_completeness"]["status"] != "full_modeled_account"
    ]
    return sorted(
        remaining,
        key=lambda project: (
            -len(project["model_completeness"]["covered_categories"]),
            -project["economic_record_count"],
            project["project_id"],
        ),
    )


def build_ledger(index, generated_at):
    queue = []
    for position, project in enumerate(ranked_projects(index), 1):
        queue.append({
            "queue_position": position,
            "project_id": project["project_id"],
            "project_name": project["name"],
            "county_fips": project["county_fips"],
            "county_name": project["county_name"],
            "state_abbr": project["state_abbr"],
            "baseline_evidence": {
                "covered_category_count": len(project["model_completeness"]["covered_categories"]),
                "covered_categories": project["model_completeness"]["covered_categories"],
                "source_records": project["economic_record_count"],
                "reported_observations": project["reported_actual_count"],
                "source_forecasts": project["projection_count"],
                "modeled_syntheses": project["modeled_synthesis_count"],
                "missing_categories": project["model_completeness"]["missing_categories"],
                "missing_county_outcomes": project["model_completeness"]["missing_county_outcomes"],
            },
            "worker_task_id": None,
            "worker_branch": None,
            "worker_commit_sha": None,
            "status": "queued",
            "source_record_additions": 0,
            "forecast_additions": 0,
            "modeled_record_additions": 0,
            "validation_result": None,
            "integration_commit": None,
            "remaining_unresolved_analytical_limits": [],
        })
    return {
        "schema_version": "1.0.0",
        "study_release": index["release_id"],
        "generated_at": generated_at,
        "queue_status": "frozen",
        "ranking_method": "Descending covered contribution-account category count, then descending sourced economic-record count, then ascending project_id.",
        "baseline": {
            "projects": index["counts"]["projects"],
            "counties": index["counts"]["counties"],
            "states": index["counts"]["states"],
            "source_records": index["counts"]["economic_records"],
            "reported_observations": index["counts"]["reported_actual_records"],
            "source_forecasts": index["counts"]["projection_records"],
            "modeled_syntheses": index["counts"]["modeled_synthesis_records"],
            "completed_accounts": index["full_modeled_county_accounts"],
            "remaining_accounts": len(queue),
        },
        "queue": queue,
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--check", action="store_true", help="Fail if the frozen ledger differs from the generated register.")
    args = parser.parse_args()
    index = read(INDEX)
    stamp = datetime.now(timezone.utc).isoformat(timespec="seconds")
    expected = build_ledger(index, stamp)
    if args.check:
        current = read(LEDGER)
        expected["generated_at"] = current.get("generated_at")
        immutable_keys = ("schema_version", "study_release", "generated_at", "queue_status", "ranking_method", "baseline")
        immutable_matches = all(current.get(key) == expected[key] for key in immutable_keys)
        queue_matches = len(current.get("queue", [])) == len(expected["queue"]) and all(
            all(actual.get(key) == frozen[key] for key in (
                "queue_position", "project_id", "project_name", "county_fips",
                "county_name", "state_abbr", "baseline_evidence",
            ))
            for actual, frozen in zip(current.get("queue", []), expected["queue"])
        )
        if not immutable_matches or not queue_matches:
            raise SystemExit("Frozen orchestration ledger differs from the generated study register")
        print(f"Queue verified: {len(expected['queue'])} remaining projects")
        return
    write(LEDGER, expected)
    print(f"Queue frozen: {len(expected['queue'])} remaining projects")


if __name__ == "__main__":
    main()

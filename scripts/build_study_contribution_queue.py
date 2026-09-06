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
    parser.add_argument("--check", action="store_true", help="Validate the frozen queue and its project identities without re-ranking the evolving register.")
    args = parser.parse_args()
    index = read(INDEX)
    stamp = datetime.now(timezone.utc).isoformat(timespec="seconds")
    expected = build_ledger(index, stamp)
    if args.check:
        current = read(LEDGER)
        queue = current.get("queue", [])
        projects = {project["project_id"]: project for project in index["projects"]}
        identities_match = all(
            row.get("project_id") in projects
            and row.get("project_name") == projects[row["project_id"]]["name"]
            and row.get("county_fips") == projects[row["project_id"]]["county_fips"]
            and row.get("county_name") == projects[row["project_id"]]["county_name"]
            and row.get("state_abbr") == projects[row["project_id"]]["state_abbr"]
            for row in queue
        )
        positions = [row.get("queue_position") for row in queue]
        project_ids = [row.get("project_id") for row in queue]
        structure_matches = (
            current.get("schema_version") == "1.0.0"
            and current.get("queue_status") == "frozen"
            and bool(current.get("study_release"))
            and bool(current.get("generated_at"))
            and bool(current.get("ranking_method"))
            and current.get("baseline", {}).get("remaining_accounts") == len(queue)
            and positions == list(range(1, len(queue) + 1))
            and len(project_ids) == len(set(project_ids))
        )
        if not structure_matches or not identities_match:
            raise SystemExit("Frozen orchestration ledger is invalid or no longer matches project identities")
        completed = sum(row.get("status") == "integrated" for row in queue)
        print(f"Queue verified: {len(queue)} frozen projects; {completed} integrated")
        return
    write(LEDGER, expected)
    print(f"Queue frozen: {len(expected['queue'])} remaining projects")


if __name__ == "__main__":
    main()

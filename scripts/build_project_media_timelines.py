"""Validate and publish the standalone project-media timeline dataset."""
from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
from validate_data_contract import ContractValidator

SOURCE = ROOT / "config/v1/project-media-timelines.json"
SCHEMA = ROOT / "schemas/v1/project-media-timeline.schema.json"
SCHEMA_ROOT = ROOT / "schemas/v1"
STUDY_INDEX = ROOT / "site/public/data/v1/study/index.json"
OUTPUT = ROOT / "site/public/data/v1/study/project-media-timelines.json"


def read(path: Path):
    return json.loads(path.read_text(encoding="utf-8"))


def validate(data, index):
    errors = ContractValidator(SCHEMA_ROOT).validate_record(data, SCHEMA)
    if errors:
        formatted = "\n".join(f"- {error}" for error in errors)
        raise ValueError(f"Project media timeline schema validation failed:\n{formatted}")

    project_ids = {project["project_id"] for project in index["projects"]}
    timeline_ids = [timeline["project_id"] for timeline in data["timelines"]]
    if len(timeline_ids) != len(set(timeline_ids)):
        raise ValueError("Project media timeline contains duplicate project_id values")
    unknown = sorted(set(timeline_ids) - project_ids)
    if unknown:
        raise ValueError(f"Project media timeline references unknown study projects: {', '.join(unknown)}")

    event_ids = []
    for timeline in data["timelines"]:
        events = timeline["events"]
        sort_dates = [event["sort_date"] for event in events]
        if sort_dates != sorted(sort_dates):
            raise ValueError(f"Events are not chronological for {timeline['project_id']}")
        event_ids.extend(event["event_id"] for event in events)
    if len(event_ids) != len(set(event_ids)):
        raise ValueError("Project media timeline contains duplicate event_id values")


def write(path: Path, value):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2) + "\n", encoding="utf-8", newline="\n")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--check", action="store_true", help="Fail when the published dataset is absent or stale.")
    args = parser.parse_args()
    data = read(SOURCE)
    validate(data, read(STUDY_INDEX))
    if args.check:
        if not OUTPUT.exists() or read(OUTPUT) != data:
            raise SystemExit("Published project media timeline differs from its governed source")
        print(f"Project media timeline verified: {len(data['timelines'])} projects")
        return
    write(OUTPUT, data)
    print(f"Project media timeline published: {len(data['timelines'])} projects")


if __name__ == "__main__":
    main()

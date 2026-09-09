"""Build the rejected/private-proposal comparison registry and public projections."""

from __future__ import annotations

import argparse
import copy
import json
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
CONFIG = ROOT / "config" / "v1" / "rejected-project-study.json"
SILVER = ROOT / "data" / "silver" / "study" / "rejected-projects"
PUBLIC = ROOT / "site" / "public" / "data" / "v1" / "study" / "rejected-projects"


def read(path: Path):
    return json.loads(path.read_text(encoding="utf-8"))


def write(path: Path, value) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")


def build_products(config: dict, generated_at: str) -> tuple[dict, list[dict], list[dict], list[dict]]:
    rows = copy.deepcopy(config["projects"])
    project_ids: set[str] = set()
    site_ids: set[str] = set()
    details: list[dict] = []
    projects: list[dict] = []
    sites: list[dict] = []

    detail_only = {
        "proposal_description", "proposed_scale", "site_afterlife", "evidence_note", "timeline", "sources"
    }
    for row in rows:
        project_id = row["project_id"]
        site_id = row["site_id"]
        if project_id in project_ids or site_id in site_ids:
            raise ValueError(f"Duplicate project or proposed-site identifier: {project_id} / {site_id}")
        project_ids.add(project_id)
        site_ids.add(site_id)
        if not row["sources"] or not row["timeline"]:
            raise ValueError(f"{project_id} requires sources and timeline events")
        source_ids = {source["source_id"] for source in row["sources"]}
        if len(source_ids) != len(row["sources"]):
            raise ValueError(f"{project_id} has duplicate source identifiers")
        if not any(source["source_role"] == "primary" for source in row["sources"]):
            raise ValueError(f"{project_id} requires at least one primary source")
        if any(not source["url"].startswith("https://") for source in row["sources"]):
            raise ValueError(f"{project_id} has a non-HTTPS source")
        if row["coordinate_source_id"] not in source_ids:
            raise ValueError(f"{project_id} coordinate source is missing")
        for event in row["timeline"]:
            missing = set(event["source_ids"]) - source_ids
            if missing:
                raise ValueError(f"{project_id} event {event['event_id']} references missing sources: {sorted(missing)}")
        scale_missing = {item["source_id"] for item in row["proposed_scale"]} - source_ids
        if scale_missing:
            raise ValueError(f"{project_id} proposed scale references missing sources: {sorted(scale_missing)}")
        row["timeline"] = sorted(row["timeline"], key=lambda event: (event["date"], event["event_id"]))
        row["detail_path"] = f"rejected-projects/projects/{project_id}.json"
        row["source_count"] = len(row["sources"])
        row["timeline_event_count"] = len(row["timeline"])
        details.append(row)
        projects.append({
            "schema_version": "1.0.0",
            "project_id": project_id,
            "canonical_name": row["name"],
            "project_type": "new_facility",
            "current_status": row["disposition"],
            "target_refs": [{"entity_type": "proposed_site", "entity_id": site_id}],
            "geography_assignments": [{
                "geography_type": "county", "geography_id": row["county_fips"],
                "assignment_method": "source_reported", "confidence": 1.0,
            }],
            "created_at": generated_at,
            "updated_at": generated_at,
            "record_status": "provisional",
        })
        site_status = {
            "rejected": "approval_denied", "withdrawn": "application_withdrawn", "cancelled": "cancelled"
        }[row["disposition"]]
        if row["finality"] == "litigated":
            site_status = "litigated"
        elif row["finality"] in {"redesigned", "relocated"}:
            site_status = "alternative_use"
        sites.append({
            "schema_version": "1.0.0",
            "site_id": site_id,
            "canonical_name": f"Proposed site — {row['name']}",
            "coordinates": {
                "latitude": row["latitude"], "longitude": row["longitude"],
                "precision": row["coordinate_precision"],
            },
            "coordinate_source_id": row["coordinate_source_id"],
            "geography_assignments": [{
                "geography_type": "county", "geography_id": row["county_fips"],
                "assignment_method": "source_reported", "confidence": 1.0,
            }],
            "site_status": site_status,
            "created_at": generated_at,
            "updated_at": generated_at,
            "record_status": "provisional",
        })
    summaries = []
    for detail in details:
        summary = {key: value for key, value in detail.items() if key not in detail_only}
        summaries.append(summary)
    disposition_counts = Counter(row["disposition"] for row in summaries)
    readiness_counts = Counter(row["outcome_readiness"] for row in summaries)
    index = {
        "schema_version": "1.0.0",
        "release_id": config["dataset_version"],
        "generated_at": generated_at,
        "reviewed_on": config["reviewed_on"],
        "scope": config["scope"],
        "selection_basis": config["selection_basis"],
        "counts": {
            "projects": len(summaries),
            "counties": len({row["county_fips"] for row in summaries}),
            "states": len({row["state_abbr"] for row in summaries}),
            "by_disposition": dict(sorted(disposition_counts.items())),
            "by_readiness": dict(sorted(readiness_counts.items())),
        },
        "projects": sorted(summaries, key=lambda row: (row["state_abbr"], row["county_name"], row["name"])),
    }
    return index, details, projects, sites


def publish(index: dict, details: list[dict], projects: list[dict], sites: list[dict]) -> None:
    for root in (SILVER, PUBLIC):
        write(root / "index.json", index)
        for detail in details:
            write(root / "projects" / f"{detail['project_id']}.json", detail)
    write(SILVER / "project-entities.json", projects)
    write(SILVER / "proposed-sites.json", sites)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--generated-at")
    args = parser.parse_args()
    generated_at = args.generated_at or datetime.now(timezone.utc).replace(microsecond=0).isoformat()
    products = build_products(read(CONFIG), generated_at)
    publish(*products)
    print(f"Published {products[0]['counts']['projects']} rejected/private proposal records")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

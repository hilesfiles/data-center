"""Build the unresolved county first-material-exposure adjudication queue."""

from __future__ import annotations

import json
from collections import defaultdict
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
STUDY_DIR = ROOT / "site" / "public" / "data" / "v1" / "study"
TIMELINES_PATH = ROOT / "config" / "v1" / "project-media-timelines.json"
EXPOSURE_POLICY_PATH = ROOT / "config" / "v1" / "county-data-center-exposure-policy.json"
ADJUDICATIONS_PATH = ROOT / "config" / "v1" / "county-treatment-anchor-adjudications.json"
EXPOSURE_POLICY_PUBLIC_PATH = ROOT / "site" / "public" / "data" / "v1" / "methodology" / "county-data-center-exposure-policy.json"
PUBLIC_PATH = ROOT / "site" / "public" / "data" / "v1" / "analysis" / "county-treatment-anchor-review" / "index.json"
SILVER_PATH = ROOT / "data" / "silver" / "analysis" / "county-treatment-anchor-review.json"
GENERATED_AT = "2026-09-09T00:00:00+00:00"

REQUIRED_REVIEW_DOMAINS = [
    {"code": "preexisting_facilities", "label": "Earlier operating, construction, colocation, institutional and enterprise facilities in the county"},
    {"code": "planning_permits", "label": "Planning, zoning, building-permit and land-development records"},
    {"code": "incentives_financing", "label": "Incentive agreements, bonds, abatements and economic-development records"},
    {"code": "utility_service", "label": "Electric, transmission, water, wastewater and generator-service milestones"},
    {"code": "operator_operations", "label": "Operator evidence distinguishing announcement, construction, energization and customer service"},
    {"code": "local_reporting", "label": "Contemporaneous local reporting and public-meeting records"},
    {"code": "phase_scope", "label": "Campus, building and phase boundaries needed to identify the first economically material exposure"},
]


def read(path: Path):
    return json.loads(path.read_text(encoding="utf-8"))


def write(path: Path, value) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def normalized_anchor(history: dict) -> dict:
    anchor = history.get("anchor") or {}
    date_value = anchor.get("date")
    year_value = int(date_value[:4]) if date_value else anchor.get("year")
    return {
        "anchor_date": date_value,
        "anchor_year": year_value,
        "precision": anchor.get("precision"),
        "history_description": history.get("description"),
        "date_note": history.get("date_note"),
        "status": "candidate_project_anchor_only",
    }


def candidate_timeline_events(timeline: dict | None) -> list[dict]:
    if not timeline:
        return []
    useful = []
    for event in timeline["events"]:
        category = event["presentation_category"]
        if category not in {"announcement", "milestone", "expansion"}:
            continue
        useful.append({
            "event_id": event["event_id"],
            "sort_date": event["sort_date"],
            "date_label": event["date_label"],
            "event_type": event["event_type"],
            "title": event["title"],
            "sources": [{"title": source["title"], "publisher": source["publisher"], "url": source["url"]} for source in event["sources"]],
        })
    useful.sort(key=lambda event: (event["sort_date"], event["event_id"]))
    return useful[:6]


def build_product(generated_at: str = GENERATED_AT) -> dict:
    study = read(STUDY_DIR / "index.json")
    timelines = {timeline["project_id"]: timeline for timeline in read(TIMELINES_PATH)["timelines"]}
    exposure_policy = read(EXPOSURE_POLICY_PATH)
    adjudication_source = read(ADJUDICATIONS_PATH)
    adjudications = {record["county_fips"]: record for record in adjudication_source["adjudications"]}
    if len(adjudications) != len(adjudication_source["adjudications"]):
        raise ValueError("treatment-anchor adjudications must have unique county FIPS values")
    grouped: dict[str, list[dict]] = defaultdict(list)
    for project in study["projects"]:
        detail = read(STUDY_DIR / project["detail_path"])
        grouped[project["county_fips"]].append({
            "project_id": project["project_id"],
            "project_name": project["name"],
            "stored_history_anchor": normalized_anchor(detail["history"]),
            "candidate_timeline_events": candidate_timeline_events(timelines.get(project["project_id"])),
        })
    counties = []
    for fips in sorted(grouped):
        projects = sorted(grouped[fips], key=lambda project: project["project_id"])
        summary = next(project for project in study["projects"] if project["county_fips"] == fips)
        adjudication = adjudications.get(fips)
        counties.append({
            "county_fips": fips,
            "county_name": summary["county_name"],
            "state_abbr": summary["state_abbr"],
            "projects": projects,
            "exposure_tier_target": "E3",
            "county_first_material_exposure_status": adjudication["county_first_material_exposure_status"] if adjudication else "unresolved",
            "adjudicated_date": adjudication["adjudicated_date"] if adjudication else None,
            "anticipation_date": adjudication["anticipation_date"] if adjudication else None,
            "known_exposure_no_later_than": adjudication["known_exposure_no_later_than"] if adjudication else None,
            "date_precision": adjudication["date_precision"] if adjudication else None,
            "causal_use_status": adjudication["causal_use_status"] if adjudication else "not_ready",
            "adjudication_rationale": adjudication["rationale"] if adjudication else None,
            "adjudication_sources": adjudication["sources"] if adjudication else [],
            "unresolved_questions": adjudication["unresolved_questions"] if adjudication else [],
            "review_domains": [{**domain, "status": "not_reviewed", "sources": []} for domain in REQUIRED_REVIEW_DOMAINS],
            "required_next_step": "Resolve the documented adjudication questions and complete every review domain before causal use." if adjudication else "Determine whether an earlier economically material county exposure exists, then distinguish announcement, construction, energization and operating dates with cited evidence.",
        })
    unknown_adjudications = sorted(set(adjudications) - set(grouped))
    if unknown_adjudications:
        raise ValueError(f"treatment-anchor adjudications reference non-host counties: {unknown_adjudications}")
    return {
        "schema_version": "1.0.0",
        "release_id": "county-treatment-anchor-review-1.0.0",
        "generated_at": generated_at,
        "as_of": exposure_policy["as_of"],
        "exposure_policy_id": exposure_policy["policy_id"],
        "scope": "Adjudication queue for the first economically material E3 data-center exposure in each active-project host county.",
        "counts": {
            "host_counties": len(counties),
            "host_projects": sum(len(county["projects"]) for county in counties),
            "adjudicated_counties": len(adjudications),
            "causal_ready_counties": 0,
            "unresolved_counties": len(counties) - len(adjudications),
        },
        "warning": "Stored project-history anchors and media-timeline events are candidate evidence only. A governed adjudication may reject a selected-project anchor, establish only an exposure upper bound, or identify an unusable pre-period; none of the current decisions is causal-ready.",
        "required_review_domains": REQUIRED_REVIEW_DOMAINS,
        "counties": counties,
    }


def main() -> int:
    product = build_product()
    write(PUBLIC_PATH, product)
    write(SILVER_PATH, product)
    write(EXPOSURE_POLICY_PUBLIC_PATH, read(EXPOSURE_POLICY_PATH))
    print(json.dumps(product["counts"], indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

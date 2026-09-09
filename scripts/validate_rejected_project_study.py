"""Validate rejected-project source records, public projections, and canonical entities."""

from __future__ import annotations

from pathlib import Path

if __package__:
    from .build_rejected_project_study import CONFIG, PUBLIC, SILVER, build_products, read
else:
    from build_rejected_project_study import CONFIG, PUBLIC, SILVER, build_products, read


ROOT = Path(__file__).resolve().parents[1]
SCHEMAS = ROOT / "schemas" / "v1"


def validate_rejected_study(validator) -> list[str]:
    issues: list[str] = []
    try:
        config = read(CONFIG)
        index, details, projects, sites = build_products(config, "2026-09-09T00:00:00+00:00")
    except (KeyError, TypeError, ValueError) as error:
        return [f"rejected-project configuration: {error}"]

    for record, schema_name, label in [
        (index, "public-rejected-project-index.schema.json", "generated index"),
        *[(detail, "public-rejected-project.schema.json", detail["project_id"]) for detail in details],
        *[(project, "project.schema.json", project["project_id"]) for project in projects],
        *[(site, "proposed-site.schema.json", site["site_id"]) for site in sites],
    ]:
        for issue in validator.validate_record(record, SCHEMAS / schema_name):
            issues.append(f"{label}{issue.path}: {issue.message}")

    published_index = PUBLIC / "index.json"
    if not published_index.is_file() or read(published_index) != index:
        issues.append("published rejected-project index is missing or stale; run build_rejected_project_study.py")
    for detail in details:
        path = PUBLIC / "projects" / f"{detail['project_id']}.json"
        if not path.is_file() or read(path) != detail:
            issues.append(f"published rejected-project detail is missing or stale: {detail['project_id']}")
    if not (SILVER / "project-entities.json").is_file() or read(SILVER / "project-entities.json") != projects:
        issues.append("rejected-project canonical project entities are missing or stale")
    if not (SILVER / "proposed-sites.json").is_file() or read(SILVER / "proposed-sites.json") != sites:
        issues.append("proposed-site entities are missing or stale")
    return issues

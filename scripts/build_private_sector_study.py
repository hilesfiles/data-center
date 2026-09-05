"""Publish the provisional private-sector study register without changing adjudications.

The one-time --import-screen option freezes the advisory screen as a versioned input.
Subsequent builds read that input, retaining source wording and date precision.
"""
from __future__ import annotations

import argparse
import hashlib
import json
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path

if __package__:
    from .study_economic_evidence import EVIDENCE, category_coverage, economic_products
    from .study_modeled_synthesis import MODELING_POLICY, SYNTHESIS, modeled_products
else:
    from study_economic_evidence import EVIDENCE, category_coverage, economic_products
    from study_modeled_synthesis import MODELING_POLICY, SYNTHESIS, modeled_products

ROOT = Path(__file__).resolve().parents[1]
CONFIG = ROOT / "config/v1/private-sector-study-candidates.json"
PUBLIC = ROOT / "site/public/data/v1"
OUT = PUBLIC / "study"
SILVER = ROOT / "data/silver/study"
VERSION = "private-sector-study-1.41.0"
GAPS = [
    ("investment", "Capital investment", "Annual actual spending, local share, and phase allocation."),
    ("construction", "Construction jobs and payroll", "Workers, job-years, payroll, duration, and local participation."),
    ("suppliers", "Local suppliers and household spending", "Documented purchases and separately identified spending estimates."),
    ("operations", "Permanent jobs and compensation", "Realized direct and contractor employment, wages, and operating purchases."),
    ("fiscal", "Tax base and public revenue", "Taxable values and actual receipts by year and recipient jurisdiction."),
    ("public_costs", "Incentives and public costs", "Agreements, abatements, infrastructure, financing, and service costs."),
    ("resources", "Electricity, water, and cooling", "Measured use, source, cooling design, and attributable system costs."),
    ("community", "Community institutions and direct funding", "Annual grants, recipients, program purposes, realized spending, and overlap with other transfers."),
]


def read(path):
    return json.loads(path.read_text(encoding="utf-8"))


def write(path, value):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def import_screen():
    if CONFIG.exists():
        raise ValueError("Study input exists; update reviewed candidates explicitly rather than reimporting.")
    screen = ROOT / "reports/2026-09-03-study-candidates/candidate-screen.json"
    payload = read(screen)
    rows = payload["recommendations"]
    for row in rows:
        row["project_id"] = "prj_study_" + row["inventory_entity_id"].removeprefix("fac_").removeprefix("cam_")
        row["operator_label"] = next((name for name in [
            "Meta", "Apple", "Google", "Microsoft", "Switch", "Digital Crossroad", "TierPoint",
            "Flexential / Stream", "Quicken Loans", "Markley", "EdgeConneX", "NTT", "Expedient",
            "Stream", "Equinix", "State Farm", "NYSE",
        ] if row["study_label"].startswith(name)), "Needs classification")
    write(CONFIG, {
        "schema_version": "1.0.0", "release_id": VERSION,
        "screen_date": payload["screen_date"], "selection_basis": payload["selection_basis"],
        "scope": payload["scope"], "input_screen_path": str(screen.relative_to(ROOT)).replace("\\", "/"),
        "input_screen_sha256": digest(screen),
        "classification_status": "provisional_research_scope", "candidates": rows,
    })


def build_products(config, inventory, panels, generated_at, evidence=None, synthesis=None, modeling_policy=None):
    candidates = config["candidates"]
    evidence = read(EVIDENCE) if evidence is None else evidence
    synthesis = read(SYNTHESIS) if synthesis is None else synthesis
    modeling_policy = read(MODELING_POLICY) if modeling_policy is None else modeling_policy
    if modeling_policy["effective_release"] != VERSION:
        raise ValueError("Modeling policy release mismatch")
    economic_by_project, _, _ = economic_products(evidence, candidates, generated_at)
    modeled_by_project, modeled_sources = modeled_products(synthesis, candidates, evidence, modeling_policy)
    ids = [r["project_id"] for r in candidates]
    targets = [r["inventory_entity_id"] for r in candidates]
    if len(set(ids)) != len(ids) or len(set(targets)) != len(targets):
        raise ValueError("Duplicate study project or inventory target")
    summaries, details, entities = [], [], []
    for row in candidates:
        target = inventory[row["inventory_entity_id"]]
        if row["county_fips"] not in target["county_fipses"]:
            raise ValueError(f"County does not match inventory target: {row['project_id']}")
        panel = panels[row["county_fips"]]
        group = row["proposed_study_group"]
        records = economic_by_project[row["project_id"]]
        modeled = modeled_by_project[row["project_id"]]
        summary = {
            "project_id": row["project_id"], "name": row["study_label"],
            "inventory_entity_id": target["entity_id"], "inventory_entity_type": target["entity_type"],
            "county_fips": row["county_fips"], "county_name": row["county_name"], "state_abbr": row["state_abbr"],
            "operator_label": row["operator_label"],
            "study_group": "Colocation" if group.startswith("Colocation") else group,
            "membership_status": "research_candidate", "sector_status": "provisional_private_sector",
            "history_status": "needs_research" if "chronology needs reconstruction" in row["documented_timing"] else "evidence_available",
            "documented_timing": row["documented_timing"],
            "panel_years": panel["complete_year_count"],
            "detail_path": f"projects/{row['project_id']}.json",
            "latitude": target["latitude"], "longitude": target["longitude"],
            "economic_record_count": len(records),
            "reported_actual_count": sum(r["basis"] == "reported_actual" for r in records),
            "projection_count": sum(r["basis"] == "source_projection" for r in records),
            "modeled_synthesis_count": len(modeled),
        }
        sources = []
        for source in row["evidence_sources"]:
            if not source.get("url") or not source["url"].startswith("https://"):
                raise ValueError(f"Missing or unsafe evidence URL for {row['project_id']}")
            sources.append({
                "source_id": source.get("source_id") or "src_study_" + hashlib.sha256(source["url"].encode()).hexdigest()[:16],
                "title": source.get("title") or f"{row['study_label']} development source", "url": source["url"],
            })
        detail = {
            **summary, "schema_version": "1.0.0", "release_id": VERSION, "generated_at": generated_at,
            "inventory_name": row["inventory_name"], "research_value": row["research_value"],
            "history": {
                "description": row["documented_timing"], "anchor": row.get("original_anchor"),
                "date_note": "This is a stored historical observation. Completion, grand opening, lease and operating-by dates are not automatically commissioning dates. Campus timing does not date every building.",
            },
            "sources": sources,
            "research_updates": [{**u, "source": next(s for s in evidence["sources"] if s["source_id"] == u["source_id"])}
                                 for u in evidence.get("project_updates", []) if u["project_id"] == row["project_id"]],
            "evidence_gaps": [{"code": code, "label": label, "status": category_coverage(records, code), "needed": needed} for code, label, needed in GAPS],
            "economic_records": records,
            "economic_sources": [s for s in evidence["sources"] if s["source_id"] in {r["source_id"] for r in records}],
            "economic_scope_note": evidence["scope_note"], "evidence_version": evidence["evidence_version"],
            "modeled_syntheses": modeled,
            "modeled_sources": [s for s in [*evidence["sources"], *modeled_sources]
                                if s["source_id"] in {source_id for estimate in modeled for source_id in estimate["derivation"]["input_source_ids"]}],
            "modeled_scope_note": synthesis["scope_note"], "synthesis_version": synthesis["synthesis_version"],
            "modeling_policy_version": modeling_policy["policy_version"],
            "analysis_readiness": {"construction": "not_assessed", "operations": "not_assessed", "fiscal": "not_assessed", "causal": "not_assessed"},
            "legacy_first_entry_note": row.get("existing_first_entry_rationale"),
            "scope_note": "Provisional private-sector research candidate. Owner/operator history, project boundaries and lifecycle require review. Membership does not verify current operation or establish economic impact.",
        }
        entities.append({
            "schema_version": "1.0.0", "project_id": row["project_id"], "canonical_name": row["study_label"],
            "project_type": "unknown", "current_status": "unknown",
            "target_refs": [{"entity_type": target["entity_type"], "entity_id": target["entity_id"]}],
            "created_at": generated_at, "updated_at": generated_at, "record_status": "provisional",
        })
        summaries.append(summary)
        details.append(detail)
    index = {
        "schema_version": "1.0.0", "release_id": VERSION, "generated_at": generated_at,
        "screen_date": config["screen_date"], "selection_basis": config["selection_basis"], "scope": config["scope"],
        "counts": {
            "projects": len(summaries), "counties": len({r["county_fips"] for r in summaries}),
            "states": len({r["state_abbr"] for r in summaries}),
            "campus_targets": sum(r["inventory_entity_type"] == "campus" for r in summaries),
            "history_evidence_available": sum(r["history_status"] == "evidence_available" for r in summaries),
            "groups": dict(sorted(Counter(r["study_group"] for r in summaries).items())),
            "projects_with_economic_evidence": sum(r["economic_record_count"] > 0 for r in summaries),
            "economic_records": sum(r["economic_record_count"] for r in summaries),
            "reported_actual_records": sum(r["reported_actual_count"] for r in summaries),
            "projection_records": sum(r["projection_count"] for r in summaries),
            "modeled_synthesis_records": sum(r["modeled_synthesis_count"] for r in summaries),
        },
        "economic_evidence_status": "partial" if evidence["records"] else "not_yet_collected",
        "modeling_policy_version": modeling_policy["policy_version"], "projects": summaries,
    }
    return index, details, entities


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--import-screen", action="store_true")
    args = parser.parse_args()
    if args.import_screen:
        import_screen()
    config = read(CONFIG)
    evidence = read(EVIDENCE)
    synthesis = read(SYNTHESIS)
    modeling_policy = read(MODELING_POLICY)
    inventory_path = PUBLIC / "facilities/index.json"
    inventory = {r["entity_id"]: r for r in read(inventory_path)}
    panel_paths = sorted((PUBLIC / "panels/county-economic-history/by-state").glob("*.json"))
    panels = {r["county_fips"]: r for p in panel_paths for r in read(p)}
    stamp = datetime.now(timezone.utc).isoformat(timespec="seconds")
    index, details, entities = build_products(config, inventory, panels, stamp, evidence, synthesis, modeling_policy)
    _, claims, sources = economic_products(evidence, config["candidates"], stamp)
    write(SILVER / "projects.json", entities)
    write(OUT / "index.json", index)
    paths = [(OUT / "index.json", len(index["projects"])), (SILVER / "projects.json", len(entities))]
    for name, payload in [("economic-claims.json", claims), ("economic-sources.json", sources)]:
        write(SILVER / name, payload)
        paths.append((SILVER / name, len(payload)))
    write(SILVER / "modeled-syntheses.json", synthesis)
    paths.append((SILVER / "modeled-syntheses.json", len(synthesis["estimates"])))
    for detail in details:
        path = OUT / detail["detail_path"]
        write(path, detail)
        paths.append((path, 1))
    manifest = {
        "schema_version": "1.0.0", "release_id": VERSION, "generated_at": stamp,
        "inputs": [{"path": str(p.relative_to(ROOT)).replace("\\", "/"), "sha256": digest(p)} for p in [CONFIG, EVIDENCE, SYNTHESIS, MODELING_POLICY, inventory_path, *panel_paths, Path(__file__), Path(__file__).with_name("build_hammond_modeled_synthesis.py"), Path(__file__).with_name("study_economic_evidence.py"), Path(__file__).with_name("study_modeled_synthesis.py")]],
        "parts": [{"path": str(p.relative_to(ROOT)).replace("\\", "/"), "record_count": count, "byte_size": p.stat().st_size, "sha256": digest(p)} for p, count in paths],
    }
    write(OUT / "manifest.json", manifest)
    print(json.dumps(index["counts"]))


if __name__ == "__main__":
    main()

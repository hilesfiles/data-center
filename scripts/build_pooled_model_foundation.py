"""Build the non-estimating foundation for the pooled county-impact model.

This builder inventories every existing project synthesis, identifies reported-data
families that may support later cross-project calibration, and constructs project-year
and county-year component spines.  It deliberately does not aggregate incompatible
values, impute missing observations, or fit a pooled/statistical model.
"""
from __future__ import annotations

import hashlib
import hashlib
import json
from collections import Counter, defaultdict
from pathlib import Path

try:
    from .study_project_fragments import load_evidence, load_synthesis
except ImportError:
    from study_project_fragments import load_evidence, load_synthesis


ROOT = Path(__file__).resolve().parents[1]
STUDY_INDEX = ROOT / "site/public/data/v1/study/index.json"
STUDY_MANIFEST = ROOT / "site/public/data/v1/study/manifest.json"
PANEL_REPORT = ROOT / "data/silver/panels/county-economic-core-2001-2024.processing-report.json"
TREATMENT_INDEX = ROOT / "site/public/data/v1/treatments/county-first-entry-resolution/index.json"
OUTPUT_DIR = ROOT / "data/silver/study/pooled"
REASSESSMENT = OUTPUT_DIR / "synthesis-reassessment.json"
FACILITY_YEAR = OUTPUT_DIR / "facility-year-exposures.json"
COUNTY_YEAR = OUTPUT_DIR / "county-year-exposures.json"
FOUNDATION_MANIFEST = OUTPUT_DIR / "manifest.json"
FOUNDATION_MANIFEST = OUTPUT_DIR / "manifest.json"
START_YEAR = 2001
END_YEAR = 2024


def read(path: Path):
    return json.loads(path.read_text(encoding="utf-8"))


def write(path: Path, payload) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
        newline="\n",
    )


def file_record(path: Path, record_count: int | None = None) -> dict:
    payload = path.read_bytes()
    record = {
        "path": path.relative_to(ROOT).as_posix(),
        "sha256": hashlib.sha256(payload).hexdigest(),
        "byte_size": len(payload),
    }
    if record_count is not None:
        record["record_count"] = record_count
    return record


def file_record(path: Path, record_count: int | None = None) -> dict:
    payload = path.read_bytes()
    record = {
        "path": path.relative_to(ROOT).as_posix(),
        "sha256": hashlib.sha256(payload).hexdigest(),
        "byte_size": len(payload),
    }
    if record_count is not None:
        record["record_count"] = record_count
    return record


def model_disposition(estimate: dict) -> tuple[str, str]:
    method = estimate["derivation"]["method"]
    if estimate["category"] == "county_outcome":
        return (
            "migrate_to_pooled_outcome_framework",
            "Project-scoped county comparisons share county outcomes and must be replaced by a registered county-year analysis.",
        )
    if method in {"benchmark_application", "input_output_multiplier", "contribution_analysis"}:
        return (
            "cross_project_calibration_required",
            "Transferred benchmark or contribution coefficients require comparison with compatible reported observations across the 36-project set.",
        )
    if method in {"allocation", "engineering_estimate", "sensitivity_analysis"}:
        return (
            "cross_project_calibration_candidate",
            "Assumption-sensitive derivation may be recalibrated only if compatible reported observations support an empirical distribution.",
        )
    if method == "statutory_counterfactual":
        return (
            "retain_scope_audit_required",
            "The governing arithmetic may remain exact, but legal scope, counterfactual basis, and non-additivity require substantive review.",
        )
    return (
        "manual_reassessment_required",
        "The estimate requires substantive review before it can be retained in or excluded from pooled exposure construction.",
    )


def build_reassessment(evidence: dict, synthesis: dict, projects: list[dict], release_id: str, generated_at: str) -> dict:
    project_ids = {project["project_id"] for project in projects}
    records = []
    for estimate in sorted(synthesis["estimates"], key=lambda row: row["estimate_id"]):
        disposition, reason = model_disposition(estimate)
        provenance_counts = Counter(
            parameter["provenance"]["kind"] for parameter in estimate["parameters"]
        )
        records.append(
            {
                "estimate_id": estimate["estimate_id"],
                "project_id": estimate["project_id"],
                "metric_code": estimate["metric_code"],
                "category": estimate["category"],
                "method": estimate["derivation"]["method"],
                "interval_kind": estimate["interval"]["kind"],
                "confidence": estimate["confidence"],
                "parameter_provenance_counts": {
                    kind: provenance_counts.get(kind, 0)
                    for kind in ("claim", "source", "model", "assumption")
                },
                "screening_disposition": disposition,
                "screening_reason": reason,
                "review_status": "machine_triaged_pending_substantive_review",
                "final_recommendation": False,
            }
        )

    metric_catalog = {metric["metric_code"]: metric for metric in evidence["metrics"]}
    annual_reported = defaultdict(list)
    for row in evidence["records"]:
        year = row["period"].get("year")
        if row["basis"] != "reported_actual" or year is None:
            continue
        if not START_YEAR <= year <= END_YEAR:
            continue
        annual_reported[row["metric_code"]].append(row)

    empirical_candidates = []
    for metric_code, rows in sorted(annual_reported.items()):
        metric = metric_catalog[metric_code]
        observed_projects = sorted({row["project_id"] for row in rows})
        if len(observed_projects) < 3:
            continue
        scope_levels = sorted({row["scope"]["level"] for row in rows})
        empirical_candidates.append(
            {
                "metric_code": metric_code,
                "label": metric["label"],
                "category": metric["category"],
                "unit": metric["unit"],
                "measure_type": metric["measure_type"],
                "reported_observation_count": len(rows),
                "project_count": len(observed_projects),
                "project_ids": observed_projects,
                "first_year": min(row["period"]["year"] for row in rows),
                "last_year": max(row["period"]["year"] for row in rows),
                "scope_levels": scope_levels,
                "calibration_status": "candidate_requires_scope_period_and_definition_harmonization",
                "input_policy": "reported_actual_only_leave_one_project_out",
            }
        )

    disposition_counts = Counter(record["screening_disposition"] for record in records)
    return {
        "schema_version": "1.0.0",
        "artifact_version": "pooled-synthesis-reassessment-0.1.0",
        "generated_at": generated_at,
        "source_release": release_id,
        "status": "machine_inventory_complete_substantive_reassessment_pending",
        "policy": {
            "observations_first": True,
            "source_projections_excluded_from_empirical_calibration": True,
            "modeled_outputs_excluded_from_empirical_calibration": True,
            "leave_one_project_out_required": True,
            "no_automatic_model_replacement": True,
        },
        "counts": {
            "registered_projects": len(project_ids),
            "modeled_projects": len({record["project_id"] for record in records}),
            "modeled_syntheses": len(records),
            "empirical_metric_candidates": len(empirical_candidates),
            "screening_dispositions": dict(sorted(disposition_counts.items())),
        },
        "empirical_metric_candidates": empirical_candidates,
        "records": records,
    }


def annual_component(row: dict, metric: dict, origin_kind: str, origin_id: str) -> dict:
    if origin_kind == "modeled_synthesis":
        interval = row["interval"]
        contribution_channel = row["contribution_channel"]
        if row["category"] == "county_outcome":
            eligibility = "excluded_existing_project_county_comparison"
        else:
            eligibility = "modeled_input_requires_repeated_draw_and_overlap_review"
        aggregation_id = row["aggregation"]["aggregation_id"]
    else:
        interval = {
            "kind": "point_observation",
            "low": row["value"],
            "central": row["value"],
            "high": row["value"],
        }
        contribution_channel = "not_specified"
        eligibility = (
            "projection_scenario_only"
            if origin_kind == "source_projection"
            else "reported_component_requires_overlap_review"
        )
        aggregation_id = row.get("annual_series_key", origin_id)
    return {
        "origin_kind": origin_kind,
        "origin_id": origin_id,
        "metric_code": row["metric_code"],
        "category": metric["category"] if origin_kind != "modeled_synthesis" else row["category"],
        "unit": row["unit"] if origin_kind == "modeled_synthesis" else metric["unit"],
        "measure_type": row["measure_type"] if origin_kind == "modeled_synthesis" else metric["measure_type"],
        "period_kind": row["period"]["kind"],
        "value": row["value"],
        "interval": interval,
        "scope_level": row["scope"]["level"],
        "inventory_allocation": row["scope"]["inventory_allocation"],
        "contribution_channel": contribution_channel,
        "aggregation_identity": aggregation_id,
        "analysis_eligibility": eligibility,
    }


def build_facility_year(evidence: dict, synthesis: dict, projects: list[dict], release_id: str, generated_at: str) -> dict:
    metrics = {metric["metric_code"]: metric for metric in evidence["metrics"]}
    by_project_year: dict[tuple[str, int], list[dict]] = defaultdict(list)
    excluded_period_kinds = Counter()

    for row in evidence["records"]:
        year = row["period"].get("year")
        if year is None or not START_YEAR <= year <= END_YEAR:
            excluded_period_kinds[row["period"]["kind"]] += 1
            continue
        by_project_year[(row["project_id"], year)].append(
            annual_component(row, metrics[row["metric_code"]], row["basis"], row["claim_id"])
        )

    for row in synthesis["estimates"]:
        year = row["period"].get("year")
        if year is None or not START_YEAR <= year <= END_YEAR:
            excluded_period_kinds[row["period"]["kind"]] += 1
            continue
        metric = metrics.get(
            row["metric_code"],
            {
                "category": row["category"],
                "unit": row["unit"],
                "measure_type": row["measure_type"],
            },
        )
        by_project_year[(row["project_id"], year)].append(
            annual_component(row, metric, "modeled_synthesis", row["estimate_id"])
        )

    years = []
    project_summaries = []
    for project in projects:
        project_id = project["project_id"]
        project_component_count = 0
        observed_count = 0
        projection_count = 0
        modeled_count = 0
        years_with_components = 0
        for year in range(START_YEAR, END_YEAR + 1):
            components = sorted(
                by_project_year.get((project_id, year), []),
                key=lambda item: (item["metric_code"], item["origin_kind"], item["origin_id"]),
            )
            counts = Counter(component["origin_kind"] for component in components)
            if components:
                years_with_components += 1
            project_component_count += len(components)
            observed_count += counts.get("reported_actual", 0)
            projection_count += counts.get("source_projection", 0)
            modeled_count += counts.get("modeled_synthesis", 0)
            years.append(
                {
                    "project_id": project_id,
                    "project_name": project["name"],
                    "county_fips": project["county_fips"],
                    "year": year,
                    "component_counts": {
                        "reported_actual": counts.get("reported_actual", 0),
                        "source_projection": counts.get("source_projection", 0),
                        "modeled_synthesis": counts.get("modeled_synthesis", 0),
                    },
                    "components": components,
                    "exposure_status": "component_inventory_only_no_aggregation",
                }
            )
        project_summaries.append(
            {
                "project_id": project_id,
                "project_name": project["name"],
                "county_fips": project["county_fips"],
                "history_status": project["history_status"],
                "documented_timing": project["documented_timing"],
                "years_with_components": years_with_components,
                "annual_component_count": project_component_count,
                "reported_actual_component_count": observed_count,
                "source_projection_component_count": projection_count,
                "modeled_component_count": modeled_count,
                "chronology_gate": (
                    "requires_commissioning_reconstruction"
                    if project["history_status"] == "needs_research"
                    else "documented_anchor_requires_event_contract_review"
                ),
            }
        )

    return {
        "schema_version": "1.0.0",
        "artifact_version": "facility-year-exposures-0.1.0",
        "generated_at": generated_at,
        "source_release": release_id,
        "analysis_years": {"start": START_YEAR, "end": END_YEAR},
        "status": "component_inventory_only_no_imputation_or_aggregation",
        "counts": {
            "projects": len(projects),
            "project_years": len(years),
            "projects_with_annual_components": sum(item["years_with_components"] > 0 for item in project_summaries),
            "reported_actual_components": sum(item["reported_actual_component_count"] for item in project_summaries),
            "source_projection_components": sum(item["source_projection_component_count"] for item in project_summaries),
            "modeled_components": sum(item["modeled_component_count"] for item in project_summaries),
            "excluded_nonannual_or_out_of_range_records": sum(excluded_period_kinds.values()),
            "excluded_period_kinds": dict(sorted(excluded_period_kinds.items())),
        },
        "project_summaries": project_summaries,
        "project_years": years,
    }


def load_county_outcomes(projects: list[dict]) -> dict[tuple[str, int], dict]:
    wanted_counties = {project["county_fips"] for project in projects}
    states = sorted({project["state_abbr"].lower() for project in projects})
    outcomes = {}
    for state in states:
        path = ROOT / f"site/public/data/v1/panels/county-economic-history/by-state/{state}.json"
        for county in read(path):
            if county["county_fips"] not in wanted_counties:
                continue
            for row in county["years"]:
                outcomes[(county["county_fips"], row["year"])] = {
                    "real_gdp_usd": row.get("real_gdp_usd"),
                    "population": row.get("population"),
                    "annual_avg_covered_employment": row.get("annual_avg_covered_employment"),
                    "annual_avg_weekly_wage_nominal_usd": row.get("annual_avg_weekly_wage_nominal_usd"),
                    "coverage_status": row["coverage_status"],
                }
    return outcomes


def build_county_year(facility_year: dict, projects: list[dict], panel_report: dict, treatment_index: dict, release_id: str, generated_at: str) -> dict:
    projects_by_county = defaultdict(list)
    for project in projects:
        projects_by_county[project["county_fips"]].append(project["project_id"])
    outcomes = load_county_outcomes(projects)

    project_year_lookup = {
        (row["project_id"], row["year"]): row for row in facility_year["project_years"]
    }
    county_years = []
    for county_fips in sorted(projects_by_county):
        registered_projects = sorted(projects_by_county[county_fips])
        for year in range(START_YEAR, END_YEAR + 1):
            rows = [project_year_lookup[(project_id, year)] for project_id in registered_projects]
            counts = {
                basis: sum(row["component_counts"][basis] for row in rows)
                for basis in ("reported_actual", "source_projection", "modeled_synthesis")
            }
            evidence_projects = sorted(
                row["project_id"] for row in rows if sum(row["component_counts"].values()) > 0
            )
            county_years.append(
                {
                    "county_fips": county_fips,
                    "year": year,
                    "registered_project_ids": registered_projects,
                    "evidence_project_ids": evidence_projects,
                    "component_counts": counts,
                    "observed_county_outcomes": outcomes[(county_fips, year)],
                    "aggregation_status": "component_inventory_only_no_compatible_totals_computed",
                    "pooled_estimation_eligible": False,
                    "ineligibility_reasons": [
                        "metric-specific aggregation and overlap rules are not yet registered",
                        "project treatment and phase histories are not yet complete",
                        "national comparison-pool exposure screening is not yet complete",
                    ],
                }
            )

    duplicate_counties = {
        county_fips: sorted(project_ids)
        for county_fips, project_ids in sorted(projects_by_county.items())
        if len(project_ids) > 1
    }
    return {
        "schema_version": "1.0.0",
        "artifact_version": "county-year-exposures-0.1.0",
        "generated_at": generated_at,
        "source_release": release_id,
        "analysis_years": {"start": START_YEAR, "end": END_YEAR},
        "status": "level_0_foundation_only_no_pooled_estimates",
        "counts": {
            "project_count": len(projects),
            "county_count": len(projects_by_county),
            "county_year_count": len(county_years),
            "national_panel_counties": panel_report["county_count"],
            "national_panel_years": panel_report["year_count"],
            "national_panel_observations": panel_report["observation_count"],
            "comparison_resolution_records": treatment_index["record_count"],
            "comparison_resolution_evidence_collected": treatment_index["resolution_status_counts"].get("evidence_collected", 0),
            "comparison_resolution_queued": treatment_index["resolution_status_counts"].get("queued", 0),
            "pooled_estimation_eligible_county_years": 0,
        },
        "shared_counties": duplicate_counties,
        "publication_gate": {
            "level_0_component_coverage": "ready",
            "numeric_county_year_aggregation": "blocked_pending_metric_rules",
            "pooled_association": "blocked_pending_exposure_and_comparison_registration",
            "causal_estimation": "blocked_pending_treatment_comparison_and_diagnostics",
        },
        "county_years": county_years,
    }


def main() -> None:
    study_index = read(STUDY_INDEX)
    manifest = read(STUDY_MANIFEST)
    panel_report = read(PANEL_REPORT)
    treatment_index = read(TREATMENT_INDEX)
    evidence = load_evidence()
    synthesis = load_synthesis()
    projects = sorted(study_index["projects"], key=lambda row: row["project_id"])
    release_id = manifest["release_id"]
    generated_at = manifest["generated_at"]

    reassessment = build_reassessment(evidence, synthesis, projects, release_id, generated_at)
    facility_year = build_facility_year(evidence, synthesis, projects, release_id, generated_at)
    county_year = build_county_year(
        facility_year, projects, panel_report, treatment_index, release_id, generated_at
    )
    write(REASSESSMENT, reassessment)
    write(FACILITY_YEAR, facility_year)
    write(COUNTY_YEAR, county_year)
    input_paths = [
        ROOT / "config/v1/study-economic-evidence.json",
        *sorted((ROOT / "config/v1/study-economic-evidence.projects").glob("*.json")),
        ROOT / "config/v1/study-modeled-synthesis.json",
        *sorted((ROOT / "config/v1/study-modeled-synthesis.projects").glob("*.json")),
        STUDY_INDEX,
        STUDY_MANIFEST,
        PANEL_REPORT,
        TREATMENT_INDEX,
        ROOT / "site/public/data/v1/panels/county-economic-history/index.json",
        *[
            ROOT / f"site/public/data/v1/panels/county-economic-history/by-state/{state}.json"
            for state in sorted({project["state_abbr"].lower() for project in projects})
        ],
        Path(__file__).resolve(),
    ]
    foundation_manifest = {
        "schema_version": "1.0.0",
        "artifact_version": "pooled-model-foundation-0.1.0",
        "generated_at": generated_at,
        "source_release": release_id,
        "builder": file_record(Path(__file__).resolve()),
        "inputs": [file_record(path) for path in sorted(input_paths)],
        "outputs": [
            file_record(REASSESSMENT, len(reassessment["records"])),
            file_record(FACILITY_YEAR, len(facility_year["project_years"])),
            file_record(COUNTY_YEAR, len(county_year["county_years"])),
        ],
        "publication_status": "foundation_only_no_pooled_estimates",
    }
    write(FOUNDATION_MANIFEST, foundation_manifest)
    print(
        json.dumps(
            {
                "syntheses_triaged": reassessment["counts"]["modeled_syntheses"],
                "empirical_metric_candidates": reassessment["counts"]["empirical_metric_candidates"],
                "project_years": facility_year["counts"]["project_years"],
                "county_years": county_year["counts"]["county_year_count"],
                "pooled_estimates": 0,
            }
        )
    )


if __name__ == "__main__":
    main()

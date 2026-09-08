"""Build the 36-project Level 0 portfolio synthesis.

The output is deliberately descriptive. It inventories project evidence, constructs
same-year reported-observation cohorts, and keeps retained modeled identities in a
separate section. It does not impute gaps, calculate a cross-project benefit total,
fit a pooled model, or use counties outside the 35 study hosts.
"""
from __future__ import annotations

import hashlib
import json
import statistics
from collections import Counter, defaultdict
from pathlib import Path

try:
    from .study_project_fragments import fragment_input_paths, load_evidence, load_synthesis
except ImportError:
    from study_project_fragments import fragment_input_paths, load_evidence, load_synthesis


ROOT = Path(__file__).resolve().parents[1]
STUDY_INDEX = ROOT / "site/public/data/v1/study/index.json"
STUDY_MANIFEST = ROOT / "site/public/data/v1/study/manifest.json"
REASSESSMENT = ROOT / "data/silver/study/pooled/synthesis-reassessment.json"
DERIVED_SCREEN = ROOT / "data/silver/study/pooled/derived-parameter-screen.json"
AGGREGATION_RULES = ROOT / "data/silver/study/pooled/metric-aggregation-rules.json"
COUNTY_YEAR = ROOT / "data/silver/study/pooled/county-year-exposures.json"
SILVER_OUTPUT = ROOT / "data/silver/study/pooled/portfolio-level-0-synthesis.json"
PUBLIC_OUTPUT = ROOT / "site/public/data/v1/study/pooled/portfolio-level-0-synthesis.json"
MANIFEST_OUTPUT = ROOT / "data/silver/study/pooled/portfolio-level-0-manifest.json"

CATEGORIES = (
    ("investment", "Capital investment", "Annual actual spending, local share, and phase allocation."),
    ("construction", "Construction jobs and payroll", "Workers, job-years, payroll, duration, and local participation."),
    ("suppliers", "Local suppliers and household spending", "Documented purchases and separately identified spending estimates."),
    ("operations", "Permanent jobs and compensation", "Realized direct and contractor employment, wages, and operating purchases."),
    ("fiscal", "Tax base and public revenue", "Taxable values and actual receipts by year and recipient jurisdiction."),
    ("public_costs", "Incentives and public costs", "Agreements, abatements, infrastructure, financing, and service costs."),
    ("resources", "Electricity, water, and cooling", "Measured use, source, cooling design, and attributable system costs."),
    ("community", "Community institutions and direct funding", "Annual grants, recipients, program purposes, realized spending, and overlap with other transfers."),
)
CATEGORY_CODES = tuple(row[0] for row in CATEGORIES)


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
    result = {
        "path": str(path.relative_to(ROOT)).replace("\\", "/"),
        "sha256": hashlib.sha256(payload).hexdigest(),
        "byte_size": len(payload),
    }
    if record_count is not None:
        result["record_count"] = record_count
    return result


def percentile(values: list[float], probability: float) -> float:
    ordered = sorted(values)
    if len(ordered) == 1:
        return ordered[0]
    position = (len(ordered) - 1) * probability
    lower = int(position)
    upper = min(lower + 1, len(ordered) - 1)
    fraction = position - lower
    return ordered[lower] + (ordered[upper] - ordered[lower]) * fraction


def distribution(values: list[float]) -> dict:
    return {
        "minimum": min(values),
        "p25": percentile(values, 0.25),
        "median": statistics.median(values),
        "p75": percentile(values, 0.75),
        "maximum": max(values),
    }


def gap_status(records: list[dict], category: str) -> str:
    matching = [row for row in records if row["category"] == category]
    if not matching:
        return "not_yet_collected"
    if any(row["basis"] == "reported_actual" for row in matching):
        return "partial"
    return "projections_only"


def build_project_matrix(
    projects: list[dict], evidence: dict, synthesis: dict, reassessment: dict
) -> tuple[list[dict], list[dict], list[dict]]:
    evidence_by_project: dict[str, list[dict]] = defaultdict(list)
    synthesis_by_project: dict[str, list[dict]] = defaultdict(list)
    for row in evidence["records"]:
        evidence_by_project[row["project_id"]].append(row)
    for row in synthesis["estimates"]:
        synthesis_by_project[row["project_id"]].append(row)
    disposition_by_estimate = {
        row["estimate_id"]: row["substantive_disposition"]
        for row in reassessment["records"]
    }

    rows = []
    gaps = []
    for project in projects:
        project_id = project["project_id"]
        reported = [row for row in evidence_by_project[project_id] if row["basis"] == "reported_actual"]
        projected = [row for row in evidence_by_project[project_id] if row["basis"] == "source_projection"]
        modeled = synthesis_by_project[project_id]
        category_rows = []
        for code, label, needed in CATEGORIES:
            actual_rows = [row for row in reported if row["category"] == code]
            projection_rows = [row for row in projected if row["category"] == code]
            modeled_rows = [row for row in modeled if row["category"] == code]
            status = gap_status([*actual_rows, *projection_rows], code)
            gap = {
                "project_id": project_id,
                "project_name": project["name"],
                "county_fips": project["county_fips"],
                "category": code,
                "label": label,
                "status": status,
                "needed": needed,
            }
            gaps.append(gap)
            category_rows.append(
                {
                    "category": code,
                    "reported_actual_count": len(actual_rows),
                    "source_projection_count": len(projection_rows),
                    "modeled_synthesis_count": len(modeled_rows),
                    "direct_evidence_status": status,
                    "reported_metric_codes": sorted({row["metric_code"] for row in actual_rows}),
                    "projection_metric_codes": sorted({row["metric_code"] for row in projection_rows}),
                    "modeled_metric_codes": sorted({row["metric_code"] for row in modeled_rows}),
                }
            )

        metric_rows = []
        metric_codes = sorted({row["metric_code"] for row in [*reported, *projected, *modeled]})
        for metric_code in metric_codes:
            actual_rows = [row for row in reported if row["metric_code"] == metric_code]
            projection_rows = [row for row in projected if row["metric_code"] == metric_code]
            modeled_rows = [row for row in modeled if row["metric_code"] == metric_code]
            metric_rows.append(
                {
                    "metric_code": metric_code,
                    "category": ([*actual_rows, *projection_rows, *modeled_rows][0])["category"],
                    "reported_actual_count": len(actual_rows),
                    "source_projection_count": len(projection_rows),
                    "modeled_synthesis_count": len(modeled_rows),
                    "modeled_dispositions": dict(
                        sorted(
                            Counter(
                                disposition_by_estimate[row["estimate_id"]]
                                for row in modeled_rows
                            ).items()
                        )
                    ),
                }
            )
        rows.append(
            {
                "project_id": project_id,
                "project_name": project["name"],
                "operator_label": project["operator_label"],
                "study_group": project["study_group"],
                "county_fips": project["county_fips"],
                "county_name": project["county_name"],
                "state_abbr": project["state_abbr"],
                "reported_actual_count": len(reported),
                "source_projection_count": len(projected),
                "modeled_synthesis_count": len(modeled),
                "categories": category_rows,
                "metrics": metric_rows,
            }
        )

    category_coverage = []
    for code, label, _ in CATEGORIES:
        project_categories = [
            category
            for row in rows
            for category in row["categories"]
            if category["category"] == code
        ]
        actual_projects = sum(row["reported_actual_count"] > 0 for row in project_categories)
        projection_projects = sum(row["source_projection_count"] > 0 for row in project_categories)
        modeled_projects = sum(row["modeled_synthesis_count"] > 0 for row in project_categories)
        category_coverage.append(
            {
                "category": code,
                "label": label,
                "project_count": len(projects),
                "projects_with_reported_actual": actual_projects,
                "reported_actual_coverage_rate": actual_projects / len(projects),
                "projects_with_source_projection": projection_projects,
                "projects_with_modeled_synthesis": modeled_projects,
                "reported_actual_record_count": sum(row["reported_actual_count"] for row in project_categories),
                "source_projection_record_count": sum(row["source_projection_count"] for row in project_categories),
                "modeled_synthesis_count": sum(row["modeled_synthesis_count"] for row in project_categories),
                "direct_evidence_status_counts": dict(
                    sorted(Counter(row["direct_evidence_status"] for row in project_categories).items())
                ),
            }
        )
    return rows, category_coverage, gaps


def build_metric_profiles(projects: list[dict], evidence: dict) -> list[dict]:
    project_by_id = {row["project_id"]: row for row in projects}
    groups: dict[tuple, list[dict]] = defaultdict(list)
    for row in evidence["records"]:
        if row["basis"] != "reported_actual":
            continue
        key = (row["metric_code"], row["category"], row["unit"], row["measure_type"])
        groups[key].append(row)
    profiles = []
    for (metric_code, category, unit, measure_type), records in sorted(groups.items()):
        years = sorted({row["period"].get("year") for row in records if row["period"].get("year") is not None})
        project_ids = sorted({row["project_id"] for row in records})
        profiles.append(
            {
                "metric_code": metric_code,
                "category": category,
                "unit": unit,
                "measure_type": measure_type,
                "reported_actual_record_count": len(records),
                "project_count": len(project_ids),
                "county_count": len({project_by_id[project_id]["county_fips"] for project_id in project_ids}),
                "explicit_year_count": len(years),
                "earliest_year": years[0] if years else None,
                "latest_year": years[-1] if years else None,
                "period_kinds": sorted({row["period"]["kind"] for row in records}),
                "scope_levels": sorted({row["scope"]["level"] for row in records}),
                "project_ids": project_ids,
            }
        )
    return profiles


def build_timing_aligned_cohorts(projects: list[dict], evidence: dict) -> tuple[list[dict], int]:
    project_by_id = {row["project_id"]: row for row in projects}
    groups: dict[tuple, list[dict]] = defaultdict(list)
    for row in evidence["records"]:
        year = row["period"].get("year")
        qualifier = row.get("value_qualifier", "exact")
        if (
            row["basis"] != "reported_actual"
            or year is None
            or row["scope"]["level"] == "county_context"
            or qualifier not in {"exact", None}
        ):
            continue
        key = (
            row["metric_code"],
            row["category"],
            row["unit"],
            row["measure_type"],
            row["period"]["kind"],
            year,
            row["scope"]["level"],
            row["scope"]["inventory_allocation"],
        )
        groups[key].append(row)

    cohorts = []
    ambiguous_project_groups = 0
    for key, records in sorted(groups.items()):
        by_project: dict[str, list[dict]] = defaultdict(list)
        for row in records:
            by_project[row["project_id"]].append(row)
        project_values = []
        for project_id, project_records in sorted(by_project.items()):
            values = sorted({row["value"] for row in project_records})
            if len(values) != 1:
                ambiguous_project_groups += 1
                continue
            project_values.append(
                {
                    "project_id": project_id,
                    "project_name": project_by_id[project_id]["name"],
                    "county_fips": project_by_id[project_id]["county_fips"],
                    "value": values[0],
                    "claim_ids": sorted(row["claim_id"] for row in project_records),
                    "scope_labels": sorted({row["scope"]["label"] for row in project_records}),
                }
            )
        county_count = len({row["county_fips"] for row in project_values})
        if len(project_values) < 3 or county_count < 3:
            continue
        metric_code, category, unit, measure_type, period_kind, year, scope_level, allocation = key
        signature = "|".join(str(value) for value in key)
        values = [row["value"] for row in project_values]
        cohorts.append(
            {
                "cohort_id": "cohort_" + hashlib.sha256(signature.encode("utf-8")).hexdigest()[:16],
                "metric_code": metric_code,
                "category": category,
                "unit": unit,
                "measure_type": measure_type,
                "period_kind": period_kind,
                "year": year,
                "scope_level": scope_level,
                "inventory_allocation": allocation,
                "project_count": len(project_values),
                "county_count": county_count,
                "observation_count": sum(len(row["claim_ids"]) for row in project_values),
                "project_values": project_values,
                "distribution": distribution(values),
                "interpretation": "Same-year distribution of reported project observations; descriptive only and not a portfolio total.",
                "limitations": [
                    "No missing project value is treated as zero.",
                    "The distribution is unweighted and does not establish a representative national benchmark.",
                    "Matching metric, unit, measure type, period kind, year, scope level, and allocation status does not erase differences documented in each source scope label.",
                    "No modeled synthesis or source projection enters this distribution.",
                ],
            }
        )
    cohorts.sort(key=lambda row: (-row["project_count"], row["metric_code"], row["year"], row["cohort_id"]))
    return cohorts, ambiguous_project_groups


def build_modeled_identity_summary(county_year: dict) -> list[dict]:
    grouped: dict[tuple, list[dict]] = defaultdict(list)
    for row in county_year["county_years"]:
        for exposure in row["metric_exposures"]:
            grouped[(exposure["metric_code"], exposure["category"], exposure["unit"], exposure["measure_type"])].append(
                {"county_fips": row["county_fips"], "year": row["year"], **exposure}
            )
    summaries = []
    for (metric_code, category, unit, measure_type), rows in sorted(grouped.items()):
        summaries.append(
            {
                "metric_code": metric_code,
                "category": category,
                "unit": unit,
                "measure_type": measure_type,
                "exposure_count": len(rows),
                "project_count": len({project_id for row in rows for project_id in row["contributing_project_ids"]}),
                "county_count": len({row["county_fips"] for row in rows}),
                "earliest_year": min(row["year"] for row in rows),
                "latest_year": max(row["year"] for row in rows),
                "project_ids": sorted({project_id for row in rows for project_id in row["contributing_project_ids"]}),
                "estimate_ids": sorted({estimate_id for row in rows for estimate_id in row["contributing_estimate_ids"]}),
                "aggregation_status": "identity_only_not_summed_or_used_in_reported_distributions",
            }
        )
    return summaries


def build_portfolio_level0(
    study_index: dict,
    study_manifest: dict,
    evidence: dict,
    synthesis: dict,
    reassessment: dict,
    derived_screen: dict,
    aggregation_rules: dict,
    county_year: dict,
) -> dict:
    metric_by_code = {row["metric_code"]: row for row in evidence["metrics"]}
    evidence = {
        **evidence,
        "records": [
            {
                **row,
                "label": metric_by_code[row["metric_code"]]["label"],
                "category": metric_by_code[row["metric_code"]]["category"],
                "unit": metric_by_code[row["metric_code"]]["unit"],
                "measure_type": metric_by_code[row["metric_code"]]["measure_type"],
            }
            for row in evidence["records"]
        ],
    }
    projects = sorted(study_index["projects"], key=lambda row: row["project_id"])
    project_ids = {row["project_id"] for row in projects}
    if len(projects) != 36 or len({row["county_fips"] for row in projects}) != 35:
        raise ValueError("Level 0 portfolio synthesis is fixed to 36 projects and 35 host counties")
    if {row["project_id"] for row in evidence["records"]} - project_ids:
        raise ValueError("Economic evidence contains a project outside the selected portfolio")
    if {row["project_id"] for row in synthesis["estimates"]} - project_ids:
        raise ValueError("Modeled synthesis contains a project outside the selected portfolio")

    project_matrix, category_coverage, gaps = build_project_matrix(
        projects, evidence, synthesis, reassessment
    )
    metric_profiles = build_metric_profiles(projects, evidence)
    cohorts, ambiguous_groups = build_timing_aligned_cohorts(projects, evidence)
    modeled_identities = build_modeled_identity_summary(county_year)
    gap_counts = dict(sorted(Counter(row["status"] for row in gaps).items()))
    retained_exposure_count = sum(row["exposure_count"] for row in modeled_identities)

    return {
        "schema_version": "1.0.0",
        "artifact_version": "portfolio-level-0-synthesis-1.0.0",
        "generated_at": study_manifest["generated_at"],
        "source_release": study_manifest["release_id"],
        "status": "level_0_descriptive_portfolio_synthesis",
        "scope": {
            "project_count": len(projects),
            "county_count": len({row["county_fips"] for row in projects}),
            "state_count": len({row["state_abbr"] for row in projects}),
            "project_ids": sorted(project_ids),
            "county_fips": sorted({row["county_fips"] for row in projects}),
            "boundary": "Only the 36 selected projects and their 35 host counties; no national comparison counties are included.",
        },
        "methodology": {
            "reported_actual_only_for_distributions": True,
            "source_projections_kept_separate": True,
            "modeled_syntheses_kept_separate": True,
            "missing_is_not_zero": True,
            "same_year_exact_signature_required": True,
            "minimum_projects_per_distribution": 3,
            "minimum_counties_per_distribution": 3,
            "cross_project_totals_authorized": False,
            "new_modeled_values_created": False,
            "causal_or_attributable_claims": False,
        },
        "counts": {
            "reported_actual_records": sum(row["basis"] == "reported_actual" for row in evidence["records"]),
            "source_projection_records": sum(row["basis"] == "source_projection" for row in evidence["records"]),
            "modeled_syntheses": len(synthesis["estimates"]),
            "project_metric_cells": sum(len(row["metrics"]) for row in project_matrix),
            "reported_metric_profiles": len(metric_profiles),
            "timing_aligned_reported_cohorts": len(cohorts),
            "ambiguous_project_cohort_groups_excluded": ambiguous_groups,
            "direct_evidence_gap_entries": len(gaps),
            "direct_evidence_gap_status_counts": gap_counts,
            "retained_modeled_level_0_identities": retained_exposure_count,
            "authorized_portfolio_totals": 0,
            "authorized_transferable_calibration_parameters": derived_screen["counts"]["calibration_authorized_parameters"],
        },
        "synthesis_policy": {
            "reassessment_count": reassessment["counts"]["modeled_syntheses"],
            "substantive_dispositions": reassessment["counts"]["substantive_dispositions"],
            "retained_metric_rules": aggregation_rules["counts"]["metric_rules"],
            "rule_status_counts": aggregation_rules["counts"]["status_counts"],
            "modeled_use": "Retained transparent syntheses appear only as separately labeled Level 0 identities; sensitivity and county-outcome records are excluded from portfolio distributions.",
        },
        "publication_gate": {
            "project_coverage": "ready_36_projects_35_host_counties",
            "reported_timing_aligned_distributions": "ready_descriptive_only",
            "modeled_identity_inventory": "ready_separate_from_reported_distributions",
            "portfolio_totals": "blocked_no_overlap_adjudicated_cross_project_sum",
            "empirical_transfer_model": "blocked_zero_authorized_transferable_parameters",
            "pooled_association": "outside_current_level_0_scope",
            "causal_estimation": "outside_current_level_0_scope",
        },
        "category_coverage": category_coverage,
        "metric_profiles": metric_profiles,
        "timing_aligned_reported_cohorts": cohorts,
        "modeled_level_0_identities": modeled_identities,
        "project_matrix": project_matrix,
        "gap_register": gaps,
    }


def main() -> None:
    study_index = read(STUDY_INDEX)
    study_manifest = read(STUDY_MANIFEST)
    evidence = load_evidence()
    synthesis = load_synthesis()
    reassessment = read(REASSESSMENT)
    derived_screen = read(DERIVED_SCREEN)
    aggregation_rules = read(AGGREGATION_RULES)
    county_year = read(COUNTY_YEAR)
    artifact = build_portfolio_level0(
        study_index,
        study_manifest,
        evidence,
        synthesis,
        reassessment,
        derived_screen,
        aggregation_rules,
        county_year,
    )
    write(SILVER_OUTPUT, artifact)
    write(PUBLIC_OUTPUT, artifact)
    input_paths = [
        ROOT / "config/v1/study-economic-evidence.json",
        ROOT / "config/v1/study-modeled-synthesis.json",
        *fragment_input_paths(),
        STUDY_INDEX,
        STUDY_MANIFEST,
        REASSESSMENT,
        DERIVED_SCREEN,
        AGGREGATION_RULES,
        COUNTY_YEAR,
    ]
    manifest = {
        "schema_version": "1.0.0",
        "artifact_version": "portfolio-level-0-manifest-1.0.0",
        "generated_at": study_manifest["generated_at"],
        "source_release": study_manifest["release_id"],
        "builder": file_record(Path(__file__).resolve()),
        "inputs": [file_record(path) for path in sorted(set(input_paths))],
        "outputs": [
            file_record(SILVER_OUTPUT, len(artifact["project_matrix"])),
            file_record(PUBLIC_OUTPUT, len(artifact["project_matrix"])),
        ],
        "publication_status": "level_0_descriptive_only_no_portfolio_total_or_pooled_estimate",
    }
    write(MANIFEST_OUTPUT, manifest)
    print(json.dumps(artifact["counts"], sort_keys=True))


if __name__ == "__main__":
    main()

"""Build the non-estimating foundation for the pooled county-impact model.

This builder inventories every existing project synthesis, identifies reported-data
families that may support later cross-project calibration, and constructs project-year
and county-year component spines.  It deliberately does not aggregate incompatible
values, impute missing observations, or fit a pooled/statistical model.
"""
from __future__ import annotations

import hashlib
import json
import statistics
from collections import Counter, defaultdict
from pathlib import Path

try:
    from .study_project_fragments import load_evidence, load_synthesis
except ImportError:
    from study_project_fragments import load_evidence, load_synthesis


ROOT = Path(__file__).resolve().parents[1]
CANDIDATE_CONFIG = ROOT / "config/v1/private-sector-study-candidates.json"
STUDY_INDEX = ROOT / "site/public/data/v1/study/index.json"
STUDY_MANIFEST = ROOT / "site/public/data/v1/study/manifest.json"
PANEL_REPORT = ROOT / "data/silver/panels/county-economic-core-2001-2024.processing-report.json"
PANEL_INDEX = ROOT / "site/public/data/v1/panels/county-economic-history/index.json"
TREATMENT_INDEX = ROOT / "site/public/data/v1/treatments/county-first-entry-resolution/index.json"
TREATMENT_DIR = ROOT / "site/public/data/v1/treatments"
OUTPUT_DIR = ROOT / "data/silver/study/pooled"
REASSESSMENT = OUTPUT_DIR / "synthesis-reassessment.json"
DERIVED_SCREEN = OUTPUT_DIR / "derived-parameter-screen.json"
AGGREGATION_RULES = OUTPUT_DIR / "metric-aggregation-rules.json"
CHRONOLOGY_SCREEN = OUTPUT_DIR / "project-chronology-screen.json"
COMPARISON_SCREEN = OUTPUT_DIR / "comparison-pool-readiness.json"
FACILITY_YEAR = OUTPUT_DIR / "facility-year-exposures.json"
COUNTY_YEAR = OUTPUT_DIR / "county-year-exposures.json"
FOUNDATION_MANIFEST = OUTPUT_DIR / "manifest.json"
START_YEAR = 2001
END_YEAR = 2024

DERIVED_RATIO_DEFINITIONS = (
    {
        "parameter_code": "effective_tax_paid_per_account_assessed_value",
        "label": "Property taxes paid per dollar of account assessed value",
        "numerator_metric_code": "study.property_taxes_paid",
        "denominator_metric_code": "study.account_assessed_value",
        "unit": "ratio",
        "transferability": "jurisdiction_specific",
    },
    {
        "parameter_code": "effective_tax_billed_per_account_assessed_value",
        "label": "Property taxes billed per dollar of account assessed value",
        "numerator_metric_code": "study.property_taxes_billed",
        "denominator_metric_code": "study.account_assessed_value",
        "unit": "ratio",
        "transferability": "jurisdiction_specific",
    },
    {
        "parameter_code": "effective_tax_paid_per_taxable_assessed_value",
        "label": "Property taxes paid per dollar of taxable assessed value",
        "numerator_metric_code": "study.property_taxes_paid",
        "denominator_metric_code": "study.taxable_assessed_value",
        "unit": "ratio",
        "transferability": "jurisdiction_specific",
    },
    {
        "parameter_code": "effective_tax_billed_per_taxable_assessed_value",
        "label": "Property taxes billed per dollar of taxable assessed value",
        "numerator_metric_code": "study.property_taxes_billed",
        "denominator_metric_code": "study.taxable_assessed_value",
        "unit": "ratio",
        "transferability": "jurisdiction_specific",
    },
    {
        "parameter_code": "effective_tax_paid_per_appraised_value",
        "label": "Property taxes paid per dollar of appraised value",
        "numerator_metric_code": "study.property_taxes_paid",
        "denominator_metric_code": "study.appraised_property_value",
        "unit": "ratio",
        "transferability": "jurisdiction_specific",
    },
    {
        "parameter_code": "effective_tax_billed_per_appraised_value",
        "label": "Property taxes billed per dollar of appraised value",
        "numerator_metric_code": "study.property_taxes_billed",
        "denominator_metric_code": "study.appraised_property_value",
        "unit": "ratio",
        "transferability": "jurisdiction_specific",
    },
    {
        "parameter_code": "effective_tax_paid_per_taxable_property_value",
        "label": "Property taxes paid per dollar of taxable property value",
        "numerator_metric_code": "study.property_taxes_paid",
        "denominator_metric_code": "study.taxable_property_value",
        "unit": "ratio",
        "transferability": "jurisdiction_specific",
    },
    {
        "parameter_code": "electricity_use_per_operating_mw",
        "label": "Annual electricity use per operating MW",
        "numerator_metric_code": "study.annual_electricity_use",
        "denominator_metric_code": "study.operating_power_capacity",
        "unit": "kWh_per_year_per_MW",
        "transferability": "operational_intensity",
    },
    {
        "parameter_code": "water_withdrawal_per_kwh",
        "label": "Annual water withdrawal per kWh of annual electricity use",
        "numerator_metric_code": "study.annual_water_withdrawal",
        "denominator_metric_code": "study.annual_electricity_use",
        "unit": "gallons_per_kWh",
        "transferability": "operational_intensity",
    },
    {
        "parameter_code": "water_consumption_per_kwh",
        "label": "Annual water consumption per kWh of annual electricity use",
        "numerator_metric_code": "study.annual_water_consumption",
        "denominator_metric_code": "study.annual_electricity_use",
        "unit": "gallons_per_kWh",
        "transferability": "operational_intensity",
    },
    {
        "parameter_code": "operating_employees_per_mw",
        "label": "Operating employees per operating MW",
        "numerator_metric_code": "study.operating_employees",
        "denominator_metric_code": "study.operating_power_capacity",
        "unit": "employees_per_MW",
        "transferability": "operational_intensity",
    },
    {
        "parameter_code": "operating_employees_per_100k_square_feet",
        "label": "Operating employees per 100,000 square feet",
        "numerator_metric_code": "study.operating_employees",
        "denominator_metric_code": "study.operating_property_floor_area",
        "unit": "employees_per_100000_square_feet",
        "scale": 100000,
        "transferability": "operational_intensity",
    },
)

TRANSPARENT_ROLLUP_METRICS = {
    "study.modeled_annual_project_linked_property_taxes_paid",
    "study.modeled_combined_assessed_value",
    "study.modeled_combined_property_tax_paid",
    "study.modeled_cumulative_incentive_payments",
    "study.modeled_current_taxable_assessed_value_total",
    "study.modeled_latest_project_linked_local_tax_contribution",
    "study.modeled_real_property_city_levy_allocation",
    "study.modeled_real_property_county_levy_allocation",
    "study.modeled_real_property_school_levy_allocation",
    "study.modeled_aggregate_billable_air_emissions",
    "study.modeled_assessor_listed_emergency_generator_total_nameplate_capacity",
    "study.modeled_identified_lvl_infrastructure_fund_expenditure",
}

CHRONOLOGY_OVERRIDES = {
    "prj_study_im3_campus_00019988712": {
        "documented_timing": "Opened on 2011-04-07 (day precision; operator announcement)",
        "anchor": {"date": "2011-04-07", "precision": "day"},
        "event_class": "opening",
        "chronology_status": "registered_from_existing_documented_timing",
        "source_id": "src_meta_prineville_open_compute_20110407",
        "source_title": "Facebook Launches Open Compute Project",
        "source_url": "https://www.prnewswire.com/news-releases/facebook-launches-open-compute-project-to-share-custom-engineered-highly-efficient-server-and-data-center-technology-with-the-world-119415214.html",
        "source_basis": "operator announcement",
    },
    "prj_study_im3_campus_00675108684": {
        "documented_timing": "Operating since 2010 (year precision; operator ten-year retrospective published in 2020)",
        "anchor": {"year": 2010, "precision": "year"},
        "event_class": "operational_no_later_than",
        "chronology_status": "registered_from_existing_documented_timing",
        "source_id": "src_microsoft_boydton_ten_years_2020",
        "source_title": "Celebrating 10 years in Boydton",
        "source_url": "https://local.microsoft.com/blog/celebrating-10-years-in-boydton/",
        "source_basis": "operator retrospective",
    },
    "prj_study_im3_campus_00009474864": {
        "documented_timing": "Opened in 2008 (year precision; Google-supplied campus history)",
        "anchor": {"year": 2008, "precision": "year"},
        "event_class": "opening",
        "source_id": "src_pooled_google_us_datacenter_history_2018",
        "source_title": "The Economic Impact of Google Data Centers in the United States",
        "source_url": "https://oeservices.oxfordeconomics.com/publication/open/297800",
        "source_basis": "Google LLC campus history reproduced by Oxford Economics",
    },
    "prj_study_im3_campus_00231769626": {
        "documented_timing": "Opened in 2006 (year precision; operator location history)",
        "anchor": {"year": 2006, "precision": "year"},
        "event_class": "opening",
        "source_id": "src_pooled_google_dalles_location_history",
        "source_title": "The Dalles, Oregon — Google Data Center Location",
        "source_url": "https://www.datacenters.google/locations/oregon/",
        "source_basis": "Google operator location history",
    },
    "prj_study_im3_campus_00578435601": {
        "documented_timing": "Opened in 2006 (year precision; Google-supplied campus history)",
        "anchor": {"year": 2006, "precision": "year"},
        "event_class": "opening",
        "source_id": "src_pooled_google_us_datacenter_history_2018",
        "source_title": "The Economic Impact of Google Data Centers in the United States",
        "source_url": "https://oeservices.oxfordeconomics.com/publication/open/297800",
        "source_basis": "Google LLC campus history reproduced by Oxford Economics",
    },
}


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


def substantive_disposition(estimate: dict) -> tuple[str, str, str, str]:
    """Apply the registered portfolio policy after method and metric review."""
    method = estimate["derivation"]["method"]
    metric_code = estimate["metric_code"]
    provenance = Counter(parameter["provenance"]["kind"] for parameter in estimate["parameters"])
    if estimate["category"] == "county_outcome":
        return (
            "migrate_to_pooled_outcome_framework",
            "pooled_county_outcome_replacement",
            "excluded_shared_county_outcome",
            "A project-level county comparison cannot be treated as an independent project effect; replace it only through a registered county-year design.",
        )
    if method == "statutory_counterfactual":
        return (
            "restrict_to_sensitivity",
            "project_counterfactual_scenario",
            "excluded_counterfactual_not_observed_exposure",
            "Statutory arithmetic is a project scenario, not an observed payment, receipt, cost, or transferable exposure.",
        )
    if metric_code == "study.modeled_annual_local_service_cost_break_even":
        return (
            "restrict_to_sensitivity",
            "project_break_even_scenario",
            "excluded_threshold_not_observed_cost",
            "A break-even threshold is not an observation of public-service cost and cannot be netted into a county-year exposure.",
        )
    if (
        metric_code in TRANSPARENT_ROLLUP_METRICS
        and method in {"allocation", "benchmark_application"}
        and provenance.get("assumption", 0) == 0
        and provenance.get("model", 0) == 0
    ):
        return (
            "retain",
            "project_descriptive_aggregation",
            "candidate_pending_metric_aggregation_contract",
            "The record is transparent arithmetic over cited project evidence; retain it as a derived project fact while overlap and county-year aggregation remain gated.",
        )
    return (
        "restrict_to_sensitivity",
        "project_sensitivity_scenario",
        "excluded_from_pooled_exposure",
        "The result depends on transferred benchmarks, engineering assumptions, contribution coefficients, or sensitivity choices that reported cross-project evidence does not currently calibrate.",
    )


def empirical_metric_screen(metric: dict) -> tuple[str, str, str]:
    if metric["measure_type"] == "rate":
        return (
            "descriptive_distribution_only",
            "descriptive_reported_rate",
            "Reported rates can be summarized, but their measurement and geographic definitions are not sufficiently harmonized for imputation.",
        )
    return (
        "reported_exposure_not_calibration_parameter",
        "candidate_facility_year_exposure",
        "Reported levels belong in the exposure inventory after scope and overlap review; a cross-project level distribution is not a transferable project parameter.",
    )


def build_reassessment(evidence: dict, synthesis: dict, projects: list[dict], release_id: str, generated_at: str) -> dict:
    project_ids = {project["project_id"] for project in projects}
    records = []
    for estimate in sorted(synthesis["estimates"], key=lambda row: row["estimate_id"]):
        disposition, reason = model_disposition(estimate)
        provenance_counts = Counter(
            parameter["provenance"]["kind"] for parameter in estimate["parameters"]
        )
        substantive, analytical_role, pooled_input_eligibility, substantive_reason = substantive_disposition(estimate)
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
                "substantive_disposition": substantive,
                "analytical_role": analytical_role,
                "pooled_input_eligibility": pooled_input_eligibility,
                "substantive_reason": substantive_reason,
                "review_status": "portfolio_policy_adjudicated",
                "final_recommendation": True,
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
        calibration_status, analytical_use, screening_reason = empirical_metric_screen(metric)
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
                "calibration_status": calibration_status,
                "analytical_use": analytical_use,
                "screening_reason": screening_reason,
                "input_policy": "reported_actual_only_leave_one_project_out",
            }
        )

    disposition_counts = Counter(record["screening_disposition"] for record in records)
    substantive_counts = Counter(record["substantive_disposition"] for record in records)
    return {
        "schema_version": "1.0.0",
        "artifact_version": "pooled-synthesis-reassessment-0.2.0",
        "generated_at": generated_at,
        "source_release": release_id,
        "status": "portfolio_policy_adjudication_complete_calibration_blocked",
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
            "substantive_dispositions": dict(sorted(substantive_counts.items())),
            "pooled_input_candidates": sum(
                record["pooled_input_eligibility"] == "candidate_pending_metric_aggregation_contract"
                for record in records
            ),
        },
        "empirical_metric_candidates": empirical_candidates,
        "records": records,
    }


def percentile(values: list[float], probability: float) -> float | None:
    if not values:
        return None
    ordered = sorted(values)
    if len(ordered) == 1:
        return ordered[0]
    position = (len(ordered) - 1) * probability
    lower = int(position)
    upper = min(lower + 1, len(ordered) - 1)
    weight = position - lower
    return ordered[lower] * (1 - weight) + ordered[upper] * weight


def distribution(values: list[float]) -> dict | None:
    if not values:
        return None
    return {
        "minimum": round(min(values), 12),
        "p25": round(percentile(values, 0.25), 12),
        "median": round(statistics.median(values), 12),
        "p75": round(percentile(values, 0.75), 12),
        "maximum": round(max(values), 12),
    }


def build_derived_parameter_screen(evidence: dict, release_id: str, generated_at: str) -> dict:
    grouped: dict[tuple, dict[str, list[dict]]] = defaultdict(lambda: defaultdict(list))
    for row in evidence["records"]:
        year = row["period"].get("year")
        if row["basis"] != "reported_actual" or year is None or not START_YEAR <= year <= END_YEAR:
            continue
        scope = row["scope"]
        scope_key = (
            row["project_id"],
            year,
            scope["level"],
            scope["label"],
            scope.get("county_fips"),
            scope["inventory_allocation"],
        )
        grouped[scope_key][row["metric_code"]].append(row)

    parameters = []
    all_observations = []
    for definition in DERIVED_RATIO_DEFINITIONS:
        numerator_code = definition["numerator_metric_code"]
        denominator_code = definition["denominator_metric_code"]
        observations = []
        ambiguous_match_count = 0
        for scope_key, metrics in sorted(grouped.items()):
            if numerator_code not in metrics or denominator_code not in metrics:
                continue
            numerator_values = {float(row["value"]) for row in metrics[numerator_code]}
            denominator_values = {float(row["value"]) for row in metrics[denominator_code]}
            if len(numerator_values) != 1 or len(denominator_values) != 1:
                ambiguous_match_count += 1
                continue
            numerator = next(iter(numerator_values))
            denominator = next(iter(denominator_values))
            if denominator <= 0:
                ambiguous_match_count += 1
                continue
            scale = definition.get("scale", 1)
            value = numerator / denominator * scale
            project_id, year, level, label, county_fips, allocation = scope_key
            observation = {
                "parameter_code": definition["parameter_code"],
                "project_id": project_id,
                "year": year,
                "scope_level": level,
                "scope_label": label,
                "county_fips": county_fips,
                "inventory_allocation": allocation,
                "value": round(value, 12),
                "unit": definition["unit"],
                "numerator_value": numerator,
                "denominator_value": denominator,
                "numerator_claim_ids": sorted(row["claim_id"] for row in metrics[numerator_code]),
                "denominator_claim_ids": sorted(row["claim_id"] for row in metrics[denominator_code]),
            }
            observations.append(observation)
            all_observations.append(observation)
        by_project = defaultdict(list)
        for observation in observations:
            by_project[observation["project_id"]].append(observation["value"])
        project_medians = [round(statistics.median(values), 12) for values in by_project.values()]
        project_count = len(by_project)
        if project_count < 3:
            calibration_status = "blocked_insufficient_independent_projects"
            reason = "Fewer than three independent projects have an unambiguous same-year, exact-scope numerator and denominator."
        elif definition["transferability"] == "jurisdiction_specific":
            calibration_status = "descriptive_only_jurisdiction_specific"
            reason = "The ratio is derived reproducibly, but tax rates and assessment bases are jurisdiction-specific and cannot be transferred across projects as a national parameter."
        else:
            calibration_status = "blocked_pending_definition_and_scope_harmonization"
            reason = "The ratio meets the project-count floor but still requires definition and scope harmonization before empirical calibration."
        parameters.append(
            {
                **{key: value for key, value in definition.items() if key != "scale"},
                "match_policy": "same_project_year_exact_scope_label_level_county_and_inventory_allocation",
                "observation_count": len(observations),
                "project_count": project_count,
                "project_ids": sorted(by_project),
                "ambiguous_match_count": ambiguous_match_count,
                "project_median_distribution": distribution(project_medians),
                "calibration_status": calibration_status,
                "calibration_authorized": False,
                "screening_reason": reason,
            }
        )

    status_counts = Counter(parameter["calibration_status"] for parameter in parameters)
    return {
        "schema_version": "1.0.0",
        "artifact_version": "derived-parameter-screen-0.1.0",
        "generated_at": generated_at,
        "source_release": release_id,
        "status": "descriptive_derived_data_complete_no_calibration_authorized",
        "policy": {
            "reported_actual_only": True,
            "same_project_year_required": True,
            "exact_scope_identity_required": True,
            "independent_project_minimum": 3,
            "repeated_years_collapsed_to_project_medians": True,
            "leave_one_project_out_required_for_future_estimation": True,
        },
        "counts": {
            "parameter_definitions": len(parameters),
            "derived_observations": len(all_observations),
            "calibration_authorized_parameters": 0,
            "status_counts": dict(sorted(status_counts.items())),
        },
        "parameters": parameters,
        "observations": sorted(
            all_observations,
            key=lambda row: (row["parameter_code"], row["project_id"], row["year"], row["scope_label"]),
        ),
    }


def build_metric_aggregation_rules(reassessment: dict, synthesis: dict, release_id: str, generated_at: str) -> dict:
    retained_ids = {
        row["estimate_id"]
        for row in reassessment["records"]
        if row["substantive_disposition"] == "retain"
    }
    retained = [row for row in synthesis["estimates"] if row["estimate_id"] in retained_ids]
    by_metric = defaultdict(list)
    for row in retained:
        by_metric[row["metric_code"]].append(row)

    rules = []
    for metric_code, rows in sorted(by_metric.items()):
        period_kinds = sorted({row["period"]["kind"] for row in rows})
        scope_levels = sorted({row["scope"]["level"] for row in rows})
        annual_rows = [
            row for row in rows
            if row["period"].get("year") is not None
            and START_YEAR <= row["period"]["year"] <= END_YEAR
        ]
        if period_kinds == ["cumulative"]:
            status = "excluded_nonannual_cumulative"
            operator = "exclude_from_annual_panel"
            reason = "A cumulative total cannot be allocated across years without a sourced annual schedule."
        elif not annual_rows:
            status = "blocked_missing_explicit_panel_year"
            operator = "exclude_until_period_is_resolved"
            reason = "The retained stock has a report date but no registered panel year; no year is inferred."
        else:
            status = "registered_level_0_single_component_only"
            operator = "identity_if_single_component"
            reason = "One retained component may be carried into a county-year Level 0 record; multiple same-metric components block aggregation pending record-level overlap adjudication."
        rules.append(
            {
                "metric_code": metric_code,
                "category": rows[0]["category"],
                "unit": rows[0]["unit"],
                "measure_type": rows[0]["measure_type"],
                "retained_estimate_count": len(rows),
                "panel_range_estimate_count": len(annual_rows),
                "allowed_period_kinds": period_kinds,
                "allowed_scope_levels": scope_levels,
                "aggregation_operator": operator,
                "within_project_overlap_policy": "honor_declared_total_and_do_not_sum_inputs_or_nested_components",
                "cross_project_overlap_policy": "block_if_more_than_one_component_for_same_county_year_metric",
                "evidence_precedence": ["reported_actual", "retained_transparent_synthesis"],
                "status": status,
                "rule_reason": reason,
                "eligible_estimate_ids": sorted(row["estimate_id"] for row in annual_rows),
            }
        )
    status_counts = Counter(rule["status"] for rule in rules)
    return {
        "schema_version": "1.0.0",
        "artifact_version": "metric-aggregation-rules-0.1.0",
        "generated_at": generated_at,
        "source_release": release_id,
        "status": "level_0_single_component_rules_registered",
        "policy": {
            "reported_actual_precedence": True,
            "nested_components_not_additive": True,
            "cross_project_sums_require_overlap_adjudication": True,
            "cumulative_values_not_annualized": True,
            "snapshots_without_panel_year_not_aligned": True,
        },
        "counts": {
            "retained_syntheses": len(retained),
            "metric_rules": len(rules),
            "panel_range_single_component_candidates": sum(rule["panel_range_estimate_count"] for rule in rules),
            "status_counts": dict(sorted(status_counts.items())),
        },
        "rules": rules,
    }


def classify_chronology_event(documented_timing: str) -> str:
    timing = documented_timing.lower()
    if "opening" in timing or "opened" in timing:
        return "opening"
    if "operational" in timing or "operation" in timing:
        return "operational_no_later_than"
    if "completion" in timing or "completed" in timing:
        return "completion"
    if "lease" in timing:
        return "lease"
    if "announcement" in timing or "announced" in timing:
        return "announcement"
    return "documented_project_anchor"


def build_chronology_screen(candidate_config: dict, projects: list[dict], release_id: str, generated_at: str) -> dict:
    candidates = {row["project_id"]: row for row in candidate_config["candidates"]}
    records = []
    override_sources = []
    for project in projects:
        project_id = project["project_id"]
        candidate = candidates[project_id]
        override = CHRONOLOGY_OVERRIDES.get(project_id)
        if override:
            anchor = override["anchor"]
            event_class = override["event_class"]
            chronology_status = override.get(
                "chronology_status", "reconstructed_from_operator_supplied_campus_history"
            )
            source_ids = [override["source_id"]]
            source_urls = [override["source_url"]]
            override_sources.append(
                {
                    "source_id": override["source_id"],
                    "title": override["source_title"],
                    "url": override["source_url"],
                    "source_role": override["source_basis"],
                }
            )
            chronology_note = override["documented_timing"]
        else:
            anchor = candidate["original_anchor"]
            event_class = classify_chronology_event(candidate["documented_timing"])
            chronology_status = "registered_existing_project_anchor"
            source_ids = [
                row.get("source_id")
                or f"src_candidate_{hashlib.sha1(row['url'].encode('utf-8')).hexdigest()[:16]}"
                for row in candidate.get("evidence_sources", [])
            ]
            source_urls = [row["url"] for row in candidate.get("evidence_sources", [])]
            chronology_note = candidate["documented_timing"]
        records.append(
            {
                "project_id": project_id,
                "project_name": project["name"],
                "county_fips": project["county_fips"],
                "anchor": anchor,
                "event_class": event_class,
                "chronology_status": chronology_status,
                "chronology_note": chronology_note,
                "source_ids": sorted(set(source_ids)),
                "source_urls": sorted(set(source_urls)),
                "project_anchor_registered": True,
                "county_treatment_status": "blocked_county_first_entry_unverified",
                "county_first_entry_verified": False,
            }
        )
    status_counts = Counter(row["chronology_status"] for row in records)
    return {
        "schema_version": "1.0.0",
        "artifact_version": "project-chronology-screen-0.1.0",
        "generated_at": generated_at,
        "source_release": release_id,
        "status": "project_chronology_complete_county_treatment_unverified",
        "policy": {
            "project_anchor_is_not_county_first_entry": True,
            "county_treatment_requires_separate_inventory_closure": True,
            "no_anchor_date_imputation": True,
        },
        "counts": {
            "projects": len(records),
            "project_anchors_registered": sum(row["project_anchor_registered"] for row in records),
            "reconstructed_project_anchors": status_counts.get("reconstructed_from_operator_supplied_campus_history", 0),
            "county_first_entry_verified": 0,
            "chronology_status_counts": dict(sorted(status_counts.items())),
        },
        "override_sources": sorted(
            {row["source_id"]: row for row in override_sources}.values(),
            key=lambda row: row["source_id"],
        ),
        "records": records,
    }


def load_partition_records(index: dict, base_dir: Path) -> tuple[list[dict], list[Path]]:
    records = []
    paths = []
    for part in index["partitions"]:
        path = base_dir / part["path"]
        paths.append(path)
        records.extend(read(path))
    return records, paths


def build_comparison_readiness(
    panel_counties: list[dict],
    projects: list[dict],
    resolution_candidates: list[dict],
    adjudications: dict,
    release_id: str,
    generated_at: str,
) -> dict:
    study_counties = {row["county_fips"] for row in projects}
    resolution_by_county = {row["county_fips"]: row for row in resolution_candidates}
    adjudication_by_county = {row["county_fips"]: row for row in adjudications["records"]}
    records = []
    for county in sorted(panel_counties, key=lambda row: row["county_fips"]):
        county_fips = county["county_fips"]
        candidate = resolution_by_county.get(county_fips)
        adjudication = adjudication_by_county.get(county_fips)
        if county_fips in study_counties:
            readiness_status = "excluded_study_host_county"
            reason = "Selected-project host counties cannot serve as untreated comparisons."
        elif adjudication is not None:
            readiness_status = "blocked_reviewed_but_unresolved"
            reason = "Completed review did not verify a county first-entry history or untreated status."
        elif candidate is not None:
            readiness_status = "blocked_resolution_queued"
            reason = "County is in the first-entry resolution queue but research is not complete."
        else:
            readiness_status = "blocked_national_exposure_unscreened"
            reason = "County has not been screened for qualifying historical data-center exposure."
        records.append(
            {
                "county_fips": county_fips,
                "county_name": county["county_name"],
                "state_abbr": county["state_abbr"],
                "panel_coverage_status": county["coverage_status"],
                "study_host_county": county_fips in study_counties,
                "resolution_candidate_id": candidate.get("resolution_candidate_id") if candidate else None,
                "resolution_status": candidate.get("resolution_status") if candidate else None,
                "adjudication_id": adjudication.get("resolution_adjudication_id") if adjudication else None,
                "county_first_entry_verified": bool(adjudication and adjudication.get("county_first_entry_verified")),
                "readiness_status": readiness_status,
                "comparison_eligible": False,
                "ineligibility_reason": reason,
            }
        )
    counts = Counter(row["readiness_status"] for row in records)
    return {
        "schema_version": "1.0.0",
        "artifact_version": "comparison-pool-readiness-0.1.0",
        "generated_at": generated_at,
        "source_release": release_id,
        "status": "national_register_complete_zero_verified_comparisons",
        "policy": {
            "study_host_counties_excluded": True,
            "untreated_status_requires_exposure_screening": True,
            "unresolved_or_queued_counties_ineligible": True,
            "no_absence_inference_from_missing_inventory": True,
        },
        "counts": {
            "national_panel_counties": len(records),
            "study_host_counties": len(study_counties),
            "resolution_candidates": len(resolution_candidates),
            "reviewed_adjudications": len(adjudications["records"]),
            "county_first_entry_verified": sum(row["county_first_entry_verified"] for row in records),
            "comparison_eligible_counties": 0,
            "readiness_status_counts": dict(sorted(counts.items())),
        },
        "records": records,
    }


def annual_component(row: dict, metric: dict, origin_kind: str, origin_id: str) -> dict:
    if origin_kind == "modeled_synthesis":
        interval = row["interval"]
        contribution_channel = row["contribution_channel"]
        _, _, eligibility, _ = substantive_disposition(row)
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


def build_facility_year(
    evidence: dict,
    synthesis: dict,
    projects: list[dict],
    chronology_screen: dict,
    release_id: str,
    generated_at: str,
) -> dict:
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
    chronology_by_project = {row["project_id"]: row for row in chronology_screen["records"]}
    if set(chronology_by_project) != {row["project_id"] for row in projects}:
        raise ValueError("chronology screen must cover every selected project exactly once")
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
                "chronology_gate": "project_anchor_registered_county_first_entry_unverified",
            }
        )

    return {
        "schema_version": "1.0.0",
        "artifact_version": "facility-year-exposures-0.2.0",
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


def build_county_year(
    facility_year: dict,
    projects: list[dict],
    panel_report: dict,
    treatment_index: dict,
    aggregation_rules: dict,
    comparison_readiness: dict,
    release_id: str,
    generated_at: str,
) -> dict:
    projects_by_county = defaultdict(list)
    for project in projects:
        projects_by_county[project["county_fips"]].append(project["project_id"])
    outcomes = load_county_outcomes(projects)

    project_year_lookup = {
        (row["project_id"], row["year"]): row for row in facility_year["project_years"]
    }
    rules_by_metric = {row["metric_code"]: row for row in aggregation_rules["rules"]}
    county_years = []
    metric_exposure_count = 0
    overlap_block_count = 0
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
            candidates_by_metric = defaultdict(list)
            for row in rows:
                for component in row["components"]:
                    rule = rules_by_metric.get(component["metric_code"])
                    if (
                        component["origin_kind"] == "modeled_synthesis"
                        and rule is not None
                        and rule["status"] == "registered_level_0_single_component_only"
                        and component["origin_id"] in rule["eligible_estimate_ids"]
                    ):
                        candidates_by_metric[component["metric_code"]].append((row["project_id"], component))
            metric_exposures = []
            for metric_code, candidate_components in sorted(candidates_by_metric.items()):
                if len(candidate_components) != 1:
                    overlap_block_count += 1
                    continue
                project_id, component = candidate_components[0]
                metric_exposures.append(
                    {
                        "metric_code": metric_code,
                        "category": component["category"],
                        "unit": component["unit"],
                        "measure_type": component["measure_type"],
                        "value": component["value"],
                        "interval": component["interval"],
                        "contributing_project_ids": [project_id],
                        "contributing_estimate_ids": [component["origin_id"]],
                        "aggregation_identities": [component["aggregation_identity"]],
                        "aggregation_method": "identity_single_component",
                        "evidence_basis": "retained_transparent_synthesis",
                        "rule_status": "registered_level_0_single_component_only",
                        "pooled_model_eligible": False,
                        "limitations": [
                            "Level 0 descriptive exposure only; no cross-project summation was performed.",
                            "Modeled interval is retained and must be propagated in any future model.",
                            "No comparison counties have passed the national exposure screen.",
                        ],
                    }
                )
            metric_exposure_count += len(metric_exposures)
            county_years.append(
                {
                    "county_fips": county_fips,
                    "year": year,
                    "registered_project_ids": registered_projects,
                    "evidence_project_ids": evidence_projects,
                    "component_counts": counts,
                    "metric_exposures": metric_exposures,
                    "observed_county_outcomes": outcomes[(county_fips, year)],
                    "aggregation_status": (
                        "level_0_single_component_exposure_registered"
                        if metric_exposures
                        else "no_level_0_metric_exposure"
                    ),
                    "pooled_estimation_eligible": False,
                    "ineligibility_reasons": [
                        "project anchors do not establish county first-entry treatment histories",
                        "national comparison-pool screen contains no eligible comparison counties",
                        "Level 1 association and causal estimation are not authorized",
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
        "artifact_version": "county-year-exposures-0.2.0",
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
            "level_0_metric_exposures": metric_exposure_count,
            "blocked_same_county_year_metric_overlaps": overlap_block_count,
            "comparison_eligible_counties": comparison_readiness["counts"]["comparison_eligible_counties"],
            "pooled_estimation_eligible_county_years": 0,
        },
        "shared_counties": duplicate_counties,
        "publication_gate": {
            "level_0_component_coverage": "ready",
            "numeric_county_year_aggregation": "partial_level_0_single_component_only",
            "pooled_association": "blocked_zero_verified_comparison_counties",
            "causal_estimation": "blocked_pending_treatment_comparison_and_diagnostics",
        },
        "county_years": county_years,
    }


def main() -> None:
    candidate_config = read(CANDIDATE_CONFIG)
    study_index = read(STUDY_INDEX)
    manifest = read(STUDY_MANIFEST)
    panel_report = read(PANEL_REPORT)
    panel_index = read(PANEL_INDEX)
    treatment_index = read(TREATMENT_INDEX)
    adjudications_path = TREATMENT_DIR / treatment_index["adjudications_path"]
    adjudications = read(adjudications_path)
    panel_counties, panel_partition_paths = load_partition_records(
        panel_index, ROOT / "site/public/data/v1/panels"
    )
    resolution_candidates, treatment_partition_paths = load_partition_records(
        treatment_index, TREATMENT_DIR
    )
    evidence = load_evidence()
    synthesis = load_synthesis()
    projects = sorted(study_index["projects"], key=lambda row: row["project_id"])
    release_id = manifest["release_id"]
    generated_at = manifest["generated_at"]

    reassessment = build_reassessment(evidence, synthesis, projects, release_id, generated_at)
    derived_screen = build_derived_parameter_screen(evidence, release_id, generated_at)
    aggregation_rules = build_metric_aggregation_rules(
        reassessment, synthesis, release_id, generated_at
    )
    chronology_screen = build_chronology_screen(
        candidate_config, projects, release_id, generated_at
    )
    comparison_screen = build_comparison_readiness(
        panel_counties,
        projects,
        resolution_candidates,
        adjudications,
        release_id,
        generated_at,
    )
    facility_year = build_facility_year(
        evidence, synthesis, projects, chronology_screen, release_id, generated_at
    )
    county_year = build_county_year(
        facility_year,
        projects,
        panel_report,
        treatment_index,
        aggregation_rules,
        comparison_screen,
        release_id,
        generated_at,
    )
    write(REASSESSMENT, reassessment)
    write(DERIVED_SCREEN, derived_screen)
    write(AGGREGATION_RULES, aggregation_rules)
    write(CHRONOLOGY_SCREEN, chronology_screen)
    write(COMPARISON_SCREEN, comparison_screen)
    write(FACILITY_YEAR, facility_year)
    write(COUNTY_YEAR, county_year)
    input_paths = [
        ROOT / "config/v1/study-economic-evidence.json",
        *sorted((ROOT / "config/v1/study-economic-evidence.projects").glob("*.json")),
        ROOT / "config/v1/study-modeled-synthesis.json",
        *sorted((ROOT / "config/v1/study-modeled-synthesis.projects").glob("*.json")),
        CANDIDATE_CONFIG,
        STUDY_INDEX,
        STUDY_MANIFEST,
        PANEL_REPORT,
        PANEL_INDEX,
        *panel_partition_paths,
        TREATMENT_INDEX,
        *treatment_partition_paths,
        adjudications_path,
        Path(__file__).resolve(),
    ]
    foundation_manifest = {
        "schema_version": "1.0.0",
        "artifact_version": "pooled-model-foundation-0.2.0",
        "generated_at": generated_at,
        "source_release": release_id,
        "builder": file_record(Path(__file__).resolve()),
        "inputs": [file_record(path) for path in sorted(set(input_paths))],
        "outputs": [
            file_record(REASSESSMENT, len(reassessment["records"])),
            file_record(DERIVED_SCREEN, len(derived_screen["observations"])),
            file_record(AGGREGATION_RULES, len(aggregation_rules["rules"])),
            file_record(CHRONOLOGY_SCREEN, len(chronology_screen["records"])),
            file_record(COMPARISON_SCREEN, len(comparison_screen["records"])),
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
                "derived_parameter_observations": derived_screen["counts"]["derived_observations"],
                "calibration_authorized_parameters": 0,
                "aggregation_rules": aggregation_rules["counts"]["metric_rules"],
                "project_anchors_registered": chronology_screen["counts"]["project_anchors_registered"],
                "comparison_eligible_counties": comparison_screen["counts"]["comparison_eligible_counties"],
                "level_0_metric_exposures": county_year["counts"]["level_0_metric_exposures"],
                "project_years": facility_year["counts"]["project_years"],
                "county_years": county_year["counts"]["county_year_count"],
                "pooled_estimates": 0,
            }
        )
    )


if __name__ == "__main__":
    main()

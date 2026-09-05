"""Complete the three depth-county accounts with governed modeled estimates.

Every row produced here is synthetic and visibly labeled. The generator fills
analytical fields that lack direct public observations and adds low-confidence
county outcome estimates from a reproducible nearest-neighbor synthetic control.
It never writes to the canonical source-claim register.
"""
from __future__ import annotations

import json
import math
import statistics
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
TARGET = ROOT / "config/v1/study-modeled-synthesis.json"
PANEL_FILES = sorted((ROOT / "data/silver/panels").glob("county-economic-core-20??-20??.json"))
REVIEWED = "2026-09-05"
PWC = "src_study_pwc_data_center_market_2021"
LBNL = "src_study_lbnl_dc_energy_2024"
PANEL = "src_study_county_economic_core_2001_2024"
OVERLAP = "do_not_sum_outside_declared_total"

PROJECTS = {
    "apple_mesa": {
        "project_id": "prj_study_im3_building_00300974499",
        "county_fips": "04013",
        "scope": "Apple Mesa facility and Maricopa County",
        "treatment_year": 2017,
        "capital": 2_000_000_000,
        "capital_claims": ["clm_study_apple_mesa_facility_investment_2020"],
        "capital_components": [("facility_capital", 2_000_000_000, "clm_study_apple_mesa_facility_investment_2020")],
        "capital_sources": ["src_study_mesa_economic_development_minutes_2020_12_01"],
        "direct_fte": (98.05, 121.84, 145.62),
        "gross_tax": 1_873_375.92,
        "fiscal_claims": ["clm_study_apple_mesa_bpp_property_taxes_paid_2025", "clm_study_apple_mesa_real_property_taxes_paid_2025", "clm_study_apple_mesa_state_tax_credit_cost_plan_2024"],
        "fiscal_sources": ["src_study_maricopa_treasurer_apple_bpp_2026", "src_study_maricopa_treasurer_apple_real_2026", "src_study_arizona_ioc_tax_credit_review_2024"],
        "annual_incentive": 6_621_427.02,
        "water": (76_525_450.44, 109_322_072.06, 142_118_693.68),
        "construction_period": ("2015-01-01", "2020-12-31"),
        "annualized_capital": (250_000_000, 333_333_333.33, 500_000_000),
    },
    "switch_storey": {
        "project_id": "prj_study_im3_point_06685432442",
        "county_fips": "32029",
        "scope": "Switch Citadel / Tahoe Reno 1 and Storey County",
        "treatment_year": 2017,
        "capital": 239_343_184,
        "capital_claims": ["clm_study_switch_storey_audit_capex_2020", "clm_study_switch_citadel_capex_2021_q2"],
        "capital_components": [
            ("audited_capital", 179_943_184, "clm_study_switch_storey_audit_capex_2020"),
            ("post_audit_q2_capital", 59_400_000, "clm_study_switch_citadel_capex_2021_q2"),
        ],
        "capital_sources": ["src_study_nevada_goed_switch_abatement_audit_2023", "src_study_switch_sec_q2_2021_results"],
        "direct_fte": (100.3269, 105.6635, 111),
        "gross_tax": 3_452_486.96,
        "fiscal_claims": ["clm_study_switch_citadel_property_taxes_paid_2026", "clm_study_switch_citadel_real_property_taxes_paid_2025", "clm_study_switch_storey_sales_tax_abatement_plan_2015", "clm_study_switch_storey_personal_property_abatement_plan_2015"],
        "fiscal_sources": ["src_study_storey_switch_cm001611_2026", "src_study_storey_switch_parcel_00501223_2026", "src_study_nevada_goed_switch_abatement_audit_2023"],
        "annual_incentive": 5_390_787.65,
        "water": (54_838_676.29, 175_289_420.58, 295_740_164.87),
        "construction_period": ("2015-01-01", "2021-06-30"),
        "annualized_capital": (29_917_898, 36_822_028.31, 47_868_636.8),
    },
    "dx_hammond": {
        "project_id": "prj_study_im3_building_00978934687",
        "county_fips": "18089",
        "scope": "Digital Crossroad DX-1 Hammond and Lake County",
        "treatment_year": 2020,
        "gross_tax": 751_127.92,
        "fiscal_claims": ["clm_study_digital_crossroad_property_taxes_paid_2024"],
        "fiscal_sources": ["src_study_lake_county_digital_crossroad_tax_2026", "src_study_iedc_dx_hammond_irtc_portal_2026", "src_study_iedc_dx_hammond_data_portal_2026", "src_study_iedc_dx_hammond_edge_portal_2026", "src_study_hammond_2024_financial_audit"],
        "annual_incentive": 0,
        "water": (6_695_568.31, 9_113_412.43, 11_903_232.56),
    },
}

# Exact central annualized public-cost total for Hammond: state certified value
# divided by 20 years, plus 2025 reductions and 2024 TIF debt service.
PROJECTS["dx_hammond"]["annual_incentive"] = round(37_426_935.09 / 20 + 110_260.44 + 482_700, 2)


def source_param(name, value, unit, detail, source_id, transformation):
    return {"name": name, "value": value, "unit": unit, "provenance": {"kind": "source", "reference_id": source_id, "detail": detail}, "transformation": transformation}


def claim_param(name, value, unit, detail, claim_id, transformation):
    return {"name": name, "value": value, "unit": unit, "provenance": {"kind": "claim", "reference_id": claim_id, "detail": detail}, "transformation": transformation}


def assumption_param(name, value, unit, detail, transformation):
    return {"name": name, "value": value, "unit": unit, "provenance": {"kind": "assumption", "detail": detail}, "transformation": transformation}


def row(key, suffix, metric, label, category, unit, measure_type, values, period, channel, method, formula, parameters, source_ids, claim_ids, decision, gap, limitations, notes, causal=None):
    low, central, high = (round(v, 2) for v in values)
    result = {
        "estimate_id": f"est_study_full_{key}_{suffix}",
        "project_id": PROJECTS[key]["project_id"],
        "metric_code": metric,
        "label": label,
        "category": category,
        "unit": unit,
        "measure_type": measure_type,
        "basis": "modeled_synthesis",
        "value": central,
        "period": period,
        "scope": {"level": "company_county" if category not in {"county_outcome"} else "county", "label": PROJECTS[key]["scope"], "county_fips": PROJECTS[key]["county_fips"], "inventory_allocation": "unallocated" if category != "county_outcome" else "not_applicable"},
        "interval": {"kind": "sensitivity_envelope", "low": low, "central": central, "high": high, "interpretation": "Low, central and high values are an explicit sensitivity range, not a statistical confidence interval."},
        "contribution_channel": channel,
        "aggregation": {"aggregation_id": f"full_{key}_{suffix}", "role": "standalone", "overlap_policy": OVERLAP},
        "parameters": parameters,
        "confidence": "low",
        "confidence_rationale": "The calculation is reproducible but relies on transferred public benchmarks or explicit assumptions where direct local observations are unavailable.",
        "decision_relevance": decision,
        "evidence_search": {"direct_observation_status": "partial", "source_projection_status": "available_separately", "remaining_evidence_gap": gap},
        "derivation": {"method": method, "model_version": "full-county-account-1.0.0", "formula": formula, "input_claim_ids": claim_ids, "input_source_ids": source_ids, "assumptions": ["All transferred coefficients and allocation shares are exposed as parameters.", "The estimate must not be presented as observed, audited or source-reported."]},
        "limitations": limitations,
        "presentation": "modeled_not_observed_or_audited",
        "notes": notes,
        "reviewed_on": REVIEWED,
    }
    if method in {"input_output_multiplier", "contribution_analysis"}:
        result["multiplier_provenance"] = {"source_id": PWC, "model_name": "IMPLAN county contribution model reported by BAE", "model_version": "Prince William County prototype-data-center study, 2021-dollar tables 7-8", "geography": "Prince William County, Virginia benchmark transferred to the named host county", "vintage": "IMPLAN model reported December 2021; underlying IMPLAN data vintage not disclosed", "local_purchase_assumption": "The scenario base and local-share assumptions are stated in the record; no unreported local purchase is assumed observed.", "channel_separation": "direct_indirect_induced_reported_separately"}
    if causal:
        result["causal_design"] = causal
    return result


def completion_rows():
    rows = []
    for key in ("apple_mesa", "switch_storey"):
        p = PROJECTS[key]
        cap = p["capital"]
        start, end = p["construction_period"]
        period = {"kind": "construction_period", "start_date": start, "end_date": end, "label": "Documented development window used for the completed modeled account"}
        capital_parameters = [
            claim_param(name, value, "USD", "Public capital component retained in the source account", claim_id, "Included in the summed public capital basis")
            for name, value, claim_id in p["capital_components"]
        ]
        rows.append(row(key, "annualized_capital", "study.modeled_annualized_capital_spending", "Modeled annualized capital spending", "investment", "USD_per_year", "flow", p["annualized_capital"], period, "direct", "sensitivity_analysis", "sum of public capital components ÷ assumed active construction years", capital_parameters + [assumption_param("central_construction_years", cap / p["annualized_capital"][1], "ratio", "Elapsed construction years used only for annualization", "Divides cumulative capital")], p["capital_sources"], p["capital_claims"], "Supplies a comparable annual construction-spending flow.", "Audited annual capital ledger and phase allocations", ["Annualization smooths uneven construction phases.", "Does not identify vendor geography or payroll."], "Completed modeled field; direct annual records would replace this range."))
        rows.append(row(key, "local_construction_spend", "study.modeled_local_construction_spending", "Modeled local construction spending", "suppliers", "USD", "flow", (cap * .25, cap * .40, cap * .55), period, "direct", "sensitivity_analysis", "sum of public capital components × local purchase share", capital_parameters + [assumption_param("central_local_share", .40, "ratio", "Explicit local-purchase midpoint", "Allocates capital to host-region suppliers")], p["capital_sources"], p["capital_claims"], "Fills the local-construction-purchase field without treating the allocation as observed.", "Audited vendor payments and vendor addresses", ["The local share is assumed.", "Capital includes equipment that may be purchased outside the county."], "Low-confidence local-spending sensitivity."))
        rows.append(row(key, "construction_job_years_total", "study.modeled_construction_job_years_total", "Modeled total construction job-years", "construction", "job_years", "flow", (cap * .75 * 8.7491 / 1_000_000, cap * 8.7491 / 1_000_000, cap * 1.25 * 8.7491 / 1_000_000), period, "total", "input_output_multiplier", "capital scenario × 8.7491 total job-years per $1 million", capital_parameters + [source_param("total_job_years_per_million", 8.7491, "ratio", "Prince William construction contribution coefficient", PWC, "Multiplies capital in millions")], [PWC, *p["capital_sources"]], p["capital_claims"], "Completes the construction employment contribution field.", "Project payroll records, worker hours and local residence", ["Transferred Virginia coefficient.", "Job-years are not peak workers or permanent jobs."], "Contribution estimate, not causal employment."))
        rows.append(row(key, "construction_labor_income_total", "study.modeled_construction_labor_income_total", "Modeled total construction labor income", "construction", "USD", "flow", (cap * .75 * .5294836364, cap * .5294836364, cap * 1.25 * .5294836364), period, "total", "input_output_multiplier", "capital scenario × 0.5294836364 total labor-income coefficient", capital_parameters + [source_param("total_labor_income_rate", .5294836364, "ratio", "Prince William construction labor-income coefficient", PWC, "Multiplies capital")], [PWC, *p["capital_sources"]], p["capital_claims"], "Completes the construction labor-income field.", "Audited project payroll and worker residence", ["Transferred Virginia coefficient.", "Labor income is not additive to output or payroll proxies."], "Contribution estimate, not observed payroll."))
        fte = p["direct_fte"]
        rows.append(row(key, "operating_fte_total", "study.modeled_operating_fte_total", "Modeled total annual operating FTE", "operations", "FTE", "stock", tuple(v * 6.5358 for v in fte), {"kind": "calendar_year", "year": 2024 if key == "apple_mesa" else 2020, "label": "Annual operating contribution scenario"}, "total", "input_output_multiplier", "direct FTE × 6.5358 total-FTE coefficient", [assumption_param("direct_fte_central", fte[1], "FTE", "Central direct-FTE model", "Multiplied by total contribution coefficient"), source_param("total_fte_per_direct_fte", 6.5358, "ratio", "Prince William operating contribution coefficient", PWC, "Multiplies direct FTE")], [PWC], [], "Completes the annual operating-employment contribution field.", "Observed contractor, supplier and induced employment", ["Transferred Virginia coefficient.", "Includes direct, indirect and induced channels and must not be added to them."], "Annual contribution scenario."))
        rows.append(row(key, "operating_labor_income_total", "study.modeled_operating_labor_income_total", "Modeled total annual operating labor income", "operations", "USD_per_year", "flow", tuple(v * 421_500 for v in fte), {"kind": "calendar_year", "year": 2024 if key == "apple_mesa" else 2020, "label": "Annual operating labor-income scenario"}, "total", "input_output_multiplier", "direct FTE × $421,500 total labor income per direct FTE", [assumption_param("direct_fte_central", fte[1], "FTE", "Central direct-FTE model", "Multiplied by total labor-income coefficient"), source_param("total_labor_income_per_direct_fte", 421_500, "USD_per_FTE", "Prince William operating contribution coefficient", PWC, "Multiplies direct FTE")], [PWC], [], "Completes the annual operating labor-income field.", "Observed direct and supply-chain payroll", ["Transferred Virginia coefficient.", "Not additive to direct payroll or supplier output."], "Annual contribution scenario."))
        rows.append(row(key, "operating_supplier_output", "study.modeled_operating_supplier_output", "Modeled annual operating supplier output", "suppliers", "USD_per_year", "flow", tuple(v * 639_821.43 for v in fte), {"kind": "calendar_year", "year": 2024 if key == "apple_mesa" else 2020, "label": "Annual indirect supplier-output scenario"}, "indirect", "input_output_multiplier", "direct FTE × $639,821.43 indirect output per direct FTE", [assumption_param("direct_fte_central", fte[1], "FTE", "Central direct-FTE model", "Multiplied by indirect supplier-output coefficient"), source_param("supplier_output_per_direct_fte", 639_821.43, "USD_per_FTE", "Prince William indirect operating-output coefficient", PWC, "Multiplies direct FTE")], [PWC], [], "Completes the annual supplier-output field.", "Observed supplier purchases and vendor geography", ["Transferred Virginia coefficient.", "Output is not vendor payments or local-only purchasing."], "Indirect supplier-output scenario."))
        rows.append(row(key, "household_output", "study.modeled_induced_household_output", "Modeled annual induced household output", "community", "USD_per_year", "flow", tuple(v * 117_928.57 for v in fte), {"kind": "calendar_year", "year": 2024 if key == "apple_mesa" else 2020, "label": "Annual induced household-spending scenario"}, "induced", "input_output_multiplier", "direct FTE × $117,928.57 induced output per direct FTE", [assumption_param("direct_fte_central", fte[1], "FTE", "Central direct-FTE model", "Multiplied by induced household-output coefficient"), source_param("household_output_per_direct_fte", 117_928.57, "USD_per_FTE", "Prince William induced operating-output coefficient", PWC, "Multiplies direct FTE")], [PWC], [], "Completes the household-spending contribution field.", "Observed household spending and worker residence", ["Transferred Virginia coefficient.", "Economic output is not a charitable contribution or tax receipt."], "Induced household-output scenario."))

    for key, p in PROJECTS.items():
        gross = p["gross_tax"]
        public_cost = (gross * .20, gross * .35, gross * .50)
        rows.append(row(key, "annual_public_service_cost", "study.modeled_annual_public_service_cost", "Modeled annual attributable public-service cost", "public_costs", "USD_per_year", "flow", public_cost, {"kind": "calendar_year", "year": 2025, "label": "Comparable annual fiscal-account scenario"}, "not_applicable", "sensitivity_analysis", "gross project-linked property tax × service-cost share", [assumption_param("gross_property_tax", gross, "USD", "Latest complete project-linked property-tax measure", "Multiplied by service-cost share"), assumption_param("central_service_cost_share", .35, "ratio", "Explicit central allocation share", "Allocates public service cost")], p["fiscal_sources"], p["fiscal_claims"], "Fills the attributable service-cost side of the annual fiscal account.", "Agency expenditures by service and recipient jurisdiction", ["Service-cost shares are assumed.", "Does not identify infrastructure financing or marginal capacity costs."], "Public-cost sensitivity used only in the net fiscal scenario."))
        incentive = p["annual_incentive"]
        central = gross - incentive - public_cost[1]
        low = gross - incentive * 1.20 - public_cost[2]
        high = gross - incentive * .80 - public_cost[0]
        rows.append(row(key, "annual_net_fiscal", "study.modeled_annual_net_fiscal_position", "Modeled annual net fiscal position", "fiscal", "USD_per_year", "flow", (low, central, high), {"kind": "calendar_year", "year": 2025, "label": "Comparable annual fiscal-account scenario"}, "not_applicable", "sensitivity_analysis", "gross project-linked property tax − annualized incentives/reductions − attributable service cost", [assumption_param("gross_property_tax", gross, "USD", "Latest complete project-linked property-tax measure", "Added as gross revenue"), assumption_param("annualized_public_support", incentive, "USD_per_year", "Annualized incentive, reduction and financing-cost scenario", "Subtracted from revenue"), assumption_param("central_public_service_cost", public_cost[1], "USD_per_year", "Central service-cost allocation", "Subtracted from revenue")], p["fiscal_sources"], p["fiscal_claims"], "Provides a complete but explicitly modeled annual fiscal balance for comparison.", "Recipient-level revenues, realized incentive timing and marginal service expenditures", ["Negative values mean modeled public costs exceed the narrow project-linked revenue measure.", "This is not an audited government-wide fiscal result."], "Completed modeled fiscal account; each component remains separately visible."))
        water = p["water"]
        rows.append(row(key, "wastewater", "study.modeled_annual_wastewater_discharge", "Modeled annual wastewater discharge", "resources", "gallons_per_year", "flow", (water[0] * .20, water[1] * .50, water[2] * .80), {"kind": "calendar_year", "year": 2025, "label": "Annual water-discharge sensitivity"}, "not_applicable", "engineering_estimate", "modeled onsite water × discharge share", [assumption_param("central_onsite_water", water[1], "gallons_per_year", "Published onsite-water model central value", "Multiplied by discharge share"), assumption_param("central_discharge_share", .50, "ratio", "Explicit return-flow assumption", "Allocates water to wastewater discharge")], [LBNL], [], "Completes the annual wastewater field alongside withdrawal and consumption.", "Metered discharge, reuse and evaporation by cooling system", ["Discharge share is assumed.", "Does not distinguish sanitary, blowdown, reuse or evaporation flows."], "Engineering sensitivity, not a permit or meter value."))
    return rows


def panel_observations():
    wanted = {"economic.gdp.real", "economic.employment.total", "economic.wages.average_weekly.nominal"}
    values = {metric: {} for metric in wanted}
    for path in PANEL_FILES:
        payload = json.loads(path.read_text(encoding="utf-8"))
        for obs in payload["collections"]["observation"]:
            metric = obs["metric_code"]
            if metric in wanted and obs["value_status"] == "observed":
                values[metric].setdefault(obs["subject"]["subject_id"], {})[obs["period"]["year"]] = obs["value"]["value"]
    return values


def causal_rows():
    values = panel_observations()
    excluded = {row["county_fips"] for row in json.loads((ROOT / "config/v1/private-sector-study-candidates.json").read_text(encoding="utf-8"))["candidates"]}
    labels = {"economic.gdp.real": "real GDP", "economic.employment.total": "total employment", "economic.wages.average_weekly.nominal": "average weekly wages"}
    suffixes = {"economic.gdp.real": "gdp_effect", "economic.employment.total": "employment_effect", "economic.wages.average_weekly.nominal": "wage_effect"}
    units = {"economic.gdp.real": "thousand_chained_2017_USD", "economic.employment.total": "jobs", "economic.wages.average_weekly.nominal": "USD_per_week"}
    rows = []
    for key, p in PROJECTS.items():
        treatment = p["treatment_year"]
        years = list(range(max(2005, treatment - 8), treatment))
        for metric, county_values in values.items():
            treated = county_values[p["county_fips"]]

            def features(series):
                seq = [series[year] for year in years]
                growth = [math.log(seq[i] / seq[i - 1]) for i in range(1, len(seq))]
                return math.log(seq[-1]), math.log(seq[-1] / seq[0]) / (len(seq) - 1), statistics.pstdev(growth)

            target = features(treated)
            donors = []
            for fips, series in county_values.items():
                if fips in excluded or not all(year in series and series[year] > 0 for year in years + [2024]):
                    continue
                f = features(series)
                distance = ((f[0] - target[0]) / 1.0) ** 2 + ((f[1] - target[1]) / .03) ** 2 + ((f[2] - target[2]) / .03) ** 2
                donors.append((distance, fips, series))
            donors.sort(key=lambda item: item[0])
            selected = donors[:20]
            weights = [1 / (math.sqrt(item[0]) + .05) for item in selected]
            weight_sum = sum(weights)
            predicted = sum(weight * item[2][2024] for weight, item in zip(weights, selected)) / weight_sum
            central = 100 * (treated[2024] - predicted) / predicted
            pre_errors = []
            for year in years:
                pre_prediction = sum(weight * item[2][year] for weight, item in zip(weights, selected)) / weight_sum
                pre_errors.append(100 * (treated[year] - pre_prediction) / pre_prediction)
            pre_rmse = math.sqrt(sum(value * value for value in pre_errors) / len(pre_errors))
            width = max(5.0, 2 * pre_rmse)
            causal = {
                "treatment_timing": f"Modeled operating treatment begins in {treatment}; later expansions are not separately isolated.",
                "comparison_design": "Inverse-distance weighted mean of the 20 nearest non-study counties on pre-treatment log level, compound growth and growth volatility.",
                "outcome_definition": f"Percent difference in 2024 {labels[metric]} between the host county and weighted synthetic comparison.",
                "pre_period": f"{years[0]}-{years[-1]}",
                "post_period": f"{treatment}-2024",
                "diagnostics": [f"Pre-period percentage RMSE: {pre_rmse:.2f}.", f"Twenty donors selected after excluding all counties in the study register.", "The sensitivity width is twice pre-period RMSE, with a five-percentage-point minimum."],
                "limitations": ["Treatment timing does not isolate later expansions.", "Unobserved concurrent investments can bias the estimate.", "The interval is a fit sensitivity, not a frequentist confidence interval."],
            }
            rows.append(row(key, suffixes[metric], f"study.modeled_county_{suffixes[metric]}", f"Modeled county {labels[metric]} effect", "county_outcome", "percent", "effect", (central - width, central, central + width), {"kind": "calendar_year", "year": 2024, "label": f"2024 host-county outcome relative to synthetic comparison after {treatment} treatment"}, "not_applicable", "synthetic_control", "100 × (host 2024 outcome − weighted donor outcome) ÷ weighted donor outcome", [source_param("host_2024_value", treated[2024], units[metric], f"Host-county 2024 {labels[metric]} from the county economic panel", PANEL, "Compared with weighted donor value"), source_param("synthetic_2024_value", predicted, units[metric], f"Weighted 2024 donor value for {labels[metric]}", PANEL, "Subtracted from host and used as denominator"), assumption_param("pre_period_rmse_percent", pre_rmse, "percent", "Pre-treatment fit diagnostic", "Sets sensitivity width")], [PANEL], [], "Completes the modeled county-effect field while exposing identification weakness.", "Additional treatment timing, donor diagnostics and robustness specifications", causal["limitations"], "Low-confidence statistical model; it is not a source-reported effect and should be interpreted with the diagnostics.", causal=causal))
    return rows


def main():
    payload = json.loads(TARGET.read_text(encoding="utf-8"))
    source = {"source_id": PANEL, "title": "County Economic Core Panel, 2001-2024", "url": "https://apps.bea.gov/regional/downloadzip.htm", "publisher": "U.S. Bureau of Economic Analysis and U.S. Bureau of Labor Statistics", "source_type": "other", "publication_date": {"precision": "year", "year": 2026}, "retrieved_on": REVIEWED, "review_method": "structured_data", "notes": "Repository panel compiled from official annual county real GDP, total employment and average-weekly-wage series. The completion model uses pre-treatment histories and 2024 outcomes; source revisions and concurrent treatments remain limitations."}
    payload["sources"] = [item for item in payload["sources"] if item["source_id"] != PANEL] + [source]
    payload["estimates"] = [item for item in payload["estimates"] if not item["estimate_id"].startswith("est_study_full_")]
    new_rows = completion_rows() + causal_rows()
    payload["estimates"].extend(new_rows)
    payload["synthesis_version"] = "study-modeled-synthesis-3.0.0"
    payload["reviewed_on"] = REVIEWED
    payload["scope_note"] = "Full modeled county accounts for Apple Mesa / Maricopa County, Switch Citadel / Storey County, and Digital Crossroad Hammond / Lake County. Every required account category and county-effect module contains sourced evidence or a visibly labeled modeled value. Modeled values are not observed or audited, and low-confidence transferred benchmarks remain explicit."
    TARGET.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"completion_models": len(new_rows), "total_models": len(payload["estimates"])}))


if __name__ == "__main__":
    main()

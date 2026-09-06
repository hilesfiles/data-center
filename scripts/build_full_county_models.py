"""Complete the three depth-county accounts with governed modeled estimates.

Every row produced here is synthetic and visibly labeled. The generator fills
analytical fields that lack direct public observations and adds low-confidence
county outcome comparisons from a reproducible nearest-neighbor benchmark.
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
        "local_tax": 1_873_375.92,
        "tax_claims": ["clm_study_apple_mesa_bpp_property_taxes_paid_2025", "clm_study_apple_mesa_real_property_taxes_paid_2025"],
        "tax_components": [("business_personal_property_tax_paid", 966_899.82, "clm_study_apple_mesa_bpp_property_taxes_paid_2025"), ("real_property_tax_paid", 906_476.10, "clm_study_apple_mesa_real_property_taxes_paid_2025")],
        "tax_sources": ["src_study_maricopa_treasurer_apple_bpp_2026", "src_study_maricopa_treasurer_apple_real_2026"],
        "tax_period": {"kind": "tax_year", "year": 2025, "label": "Tax year 2025 project-linked local property taxes paid"},
        "tax_scope": "Local taxing jurisdictions receiving Apple Mesa property taxes in Maricopa County",
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
        "local_tax": 3_452_486.96,
        "tax_claims": ["clm_study_switch_citadel_property_taxes_paid_2026", "clm_study_switch_citadel_real_property_taxes_paid_2025"],
        "tax_components": [("personal_property_tax_paid", 1_083_187.19, "clm_study_switch_citadel_property_taxes_paid_2026"), ("real_property_tax_paid", 2_369_299.77, "clm_study_switch_citadel_real_property_taxes_paid_2025")],
        "tax_sources": ["src_study_storey_switch_cm001611_2026", "src_study_storey_switch_parcel_00501223_2026"],
        "tax_period": {"kind": "fiscal_year", "year": 2026, "label": "Fiscal year 2025-2026 personal- and real-property taxes paid"},
        "tax_scope": "Local taxing jurisdictions receiving Switch Citadel property taxes in Storey County",
        "water": (54_838_676.29, 175_289_420.58, 295_740_164.87),
        "construction_period": ("2015-01-01", "2021-06-30"),
        "annualized_capital": (29_917_898, 36_822_028.31, 47_868_636.8),
    },
    "dx_hammond": {
        "project_id": "prj_study_im3_building_00978934687",
        "county_fips": "18089",
        "scope": "Digital Crossroad DX-1 Hammond and Lake County",
        "treatment_year": 2020,
        "local_tax": 641_685.14,
        "tax_claims": ["clm_study_digital_crossroad_property_taxes_paid_2024"],
        "tax_components": [("net_property_tax_paid", 641_685.14, "clm_study_digital_crossroad_property_taxes_paid_2024")],
        "tax_sources": ["src_study_lake_county_digital_crossroad_tax_2026"],
        "tax_period": {"kind": "tax_year", "year": 2024, "label": "Assessment year 2024, payable 2025; both installments paid"},
        "tax_scope": "Digital Crossroad property-tax account spanning local taxing authorities in Lake County",
        "water": (6_695_568.31, 9_113_412.43, 11_903_232.56),
    },
}

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
        "derivation": {"method": method, "model_version": "full-county-account-1.2.0", "formula": formula, "input_claim_ids": claim_ids, "input_source_ids": source_ids, "assumptions": ["All transferred coefficients and allocation shares are exposed as parameters.", "The estimate must not be presented as observed, audited or source-reported."]},
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
        construction_shares = [
            assumption_param("low_construction_cost_share", .25, "ratio", "Lower share of broad capital treated as building construction", "Excludes equipment before applying the benchmark"),
            assumption_param("central_construction_cost_share", .50, "ratio", "Central share of broad capital treated as building construction", "Excludes equipment before applying the benchmark"),
            assumption_param("high_construction_cost_share", .75, "ratio", "Upper share of broad capital treated as building construction", "Excludes equipment before applying the benchmark"),
        ]
        rows.append(row(key, "local_construction_spend", "study.modeled_local_construction_spending", "Modeled construction-eligible spending retained locally", "suppliers", "USD", "flow", (cap * .25 * .25, cap * .50 * .40, cap * .75 * .55), period, "direct", "sensitivity_analysis", "sum of public capital components × construction-cost share × local purchase share", capital_parameters + construction_shares + [assumption_param("low_local_share", .25, "ratio", "Lower local-purchase share", "Allocates construction cost to host-region suppliers"), assumption_param("central_local_share", .40, "ratio", "Central local-purchase share", "Allocates construction cost to host-region suppliers"), assumption_param("high_local_share", .55, "ratio", "Upper local-purchase share", "Allocates construction cost to host-region suppliers")], p["capital_sources"], p["capital_claims"], "Bounds local construction purchasing without treating equipment purchases as construction activity.", "Audited construction-only vendor payments and vendor addresses", ["Construction-cost and local-purchase shares are assumptions.", "The broad capital source does not isolate building construction from IT equipment."], "Low-confidence local-spending sensitivity."))
        rows.append(row(key, "construction_job_years_total", "study.modeled_construction_job_years_total", "Modeled Prince William benchmark-equivalent construction job-years", "construction", "job_years", "flow", (cap * .25 * 8.7491 / 1_000_000, cap * .50 * 8.7491 / 1_000_000, cap * .75 * 8.7491 / 1_000_000), period, "total", "input_output_multiplier", "broad capital × construction-cost share × 8.7491 total job-years per $1 million", capital_parameters + construction_shares + [source_param("total_job_years_per_million", 8.7491, "ratio", "Prince William construction contribution coefficient for construction cost excluding IT equipment", PWC, "Multiplies construction-eligible capital in millions")], [PWC, *p["capital_sources"]], p["capital_claims"], "Provides a benchmark-equivalent construction employment range without applying a construction coefficient to all equipment capital.", "Construction-only spending, project payroll, worker hours and local residence", ["Transferred Prince William County coefficient, not a host-county input-output model.", "Construction-cost share is assumed because the broad capital source does not isolate IT equipment.", "Job-years are not peak workers or permanent jobs."], "Benchmark-equivalent contribution range, not observed or causal employment."))
        rows.append(row(key, "construction_labor_income_total", "study.modeled_construction_labor_income_total", "Modeled Prince William benchmark-equivalent construction labor income", "construction", "USD", "flow", (cap * .25 * .5294836364, cap * .50 * .5294836364, cap * .75 * .5294836364), period, "total", "input_output_multiplier", "broad capital × construction-cost share × 0.5294836364 total labor-income coefficient", capital_parameters + construction_shares + [source_param("total_labor_income_rate", .5294836364, "ratio", "Prince William construction labor-income coefficient for construction cost excluding IT equipment", PWC, "Multiplies construction-eligible capital")], [PWC, *p["capital_sources"]], p["capital_claims"], "Provides a benchmark-equivalent construction labor-income range without applying a construction coefficient to all equipment capital.", "Construction-only spending, audited project payroll and worker residence", ["Transferred Prince William County coefficient, not a host-county input-output model.", "Construction-cost share is assumed because the broad capital source does not isolate IT equipment.", "Labor income is not additive to output or payroll proxies."], "Benchmark-equivalent contribution range, not observed payroll."))
        fte = p["direct_fte"]
        rows.append(row(key, "operating_fte_total", "study.modeled_operating_fte_total", "Modeled total annual operating FTE", "operations", "FTE", "stock", tuple(v * 6.5358 for v in fte), {"kind": "calendar_year", "year": 2024 if key == "apple_mesa" else 2020, "label": "Annual operating contribution scenario"}, "total", "input_output_multiplier", "direct FTE × 6.5358 total-FTE coefficient", [assumption_param("direct_fte_central", fte[1], "FTE", "Central direct-FTE model", "Multiplied by total contribution coefficient"), source_param("total_fte_per_direct_fte", 6.5358, "ratio", "Prince William operating contribution coefficient", PWC, "Multiplies direct FTE")], [PWC], [], "Completes the annual operating-employment contribution field.", "Observed contractor, supplier and induced employment", ["Transferred Virginia coefficient.", "Includes direct, indirect and induced channels and must not be added to them."], "Annual contribution scenario."))
        rows.append(row(key, "operating_labor_income_total", "study.modeled_operating_labor_income_total", "Modeled total annual operating labor income", "operations", "USD_per_year", "flow", tuple(v * 421_500 for v in fte), {"kind": "calendar_year", "year": 2024 if key == "apple_mesa" else 2020, "label": "Annual operating labor-income scenario"}, "total", "input_output_multiplier", "direct FTE × $421,500 total labor income per direct FTE", [assumption_param("direct_fte_central", fte[1], "FTE", "Central direct-FTE model", "Multiplied by total labor-income coefficient"), source_param("total_labor_income_per_direct_fte", 421_500, "USD_per_FTE", "Prince William operating contribution coefficient", PWC, "Multiplies direct FTE")], [PWC], [], "Completes the annual operating labor-income field.", "Observed direct and supply-chain payroll", ["Transferred Virginia coefficient.", "Not additive to direct payroll or supplier output."], "Annual contribution scenario."))
        rows.append(row(key, "operating_supplier_output", "study.modeled_operating_supplier_output", "Modeled annual operating supplier output", "suppliers", "USD_per_year", "flow", tuple(v * 639_821.43 for v in fte), {"kind": "calendar_year", "year": 2024 if key == "apple_mesa" else 2020, "label": "Annual indirect supplier-output scenario"}, "indirect", "input_output_multiplier", "direct FTE × $639,821.43 indirect output per direct FTE", [assumption_param("direct_fte_central", fte[1], "FTE", "Central direct-FTE model", "Multiplied by indirect supplier-output coefficient"), source_param("supplier_output_per_direct_fte", 639_821.43, "USD_per_FTE", "Prince William indirect operating-output coefficient", PWC, "Multiplies direct FTE")], [PWC], [], "Completes the annual supplier-output field.", "Observed supplier purchases and vendor geography", ["Transferred Virginia coefficient.", "Output is not vendor payments or local-only purchasing."], "Indirect supplier-output scenario."))
        rows.append(row(key, "household_output", "study.modeled_induced_household_output", "Modeled annual induced household output", "community", "USD_per_year", "flow", tuple(v * 117_928.57 for v in fte), {"kind": "calendar_year", "year": 2024 if key == "apple_mesa" else 2020, "label": "Annual induced household-spending scenario"}, "induced", "input_output_multiplier", "direct FTE × $117,928.57 induced output per direct FTE", [assumption_param("direct_fte_central", fte[1], "FTE", "Central direct-FTE model", "Multiplied by induced household-output coefficient"), source_param("household_output_per_direct_fte", 117_928.57, "USD_per_FTE", "Prince William induced operating-output coefficient", PWC, "Multiplies direct FTE")], [PWC], [], "Completes the household-spending contribution field.", "Observed household spending and worker residence", ["Transferred Virginia coefficient.", "Economic output is not a charitable contribution or tax receipt."], "Induced household-output scenario."))

    for key, p in PROJECTS.items():
        local_tax = p["local_tax"]
        tax_parameters = [claim_param(name, value, "USD", "Component of the latest complete project-linked local property-tax measure", claim_id, "Included in recurring local revenue") for name, value, claim_id in p["tax_components"]]
        tax_total = row(key, "latest_local_tax_contribution", "study.modeled_latest_project_linked_local_tax_contribution", "Aggregated project-linked local property-tax contribution", "fiscal", "USD_per_year", "flow", (local_tax, local_tax, local_tax), p["tax_period"], "not_applicable", "allocation", "sum(latest same-period project-linked local property-tax components)", tax_parameters, p["tax_sources"], p["tax_claims"], "Presents recurring local revenue documented in the underlying tax records without subtracting unmatched incentives or invented service costs.", "Audited recipient-level reconciliation and any omitted project-linked tax accounts", ["This is an aggregation of source claims, not a government-wide net benefit estimate.", "It does not include indirect sales, income or household tax effects.", "Recipient scope differs by project and is stated explicitly."], "Deterministic aggregation of accepted tax claims; inspect the source ledger for each component.")
        tax_total["scope"]["label"] = p["tax_scope"]
        tax_total["interval"] = {"kind": "point_estimate", "low": local_tax, "central": local_tax, "high": local_tax, "interpretation": "The point is the arithmetic sum of accepted source claims for the stated period; it is not a statistical estimate."}
        tax_total["confidence"] = "medium"
        tax_total["confidence_rationale"] = "The arithmetic is exact for the cited claims, while project and recipient completeness has not been independently audited."
        rows.append(tax_total)

        break_even = row(key, "annual_local_service_cost_break_even", "study.modeled_annual_local_service_cost_break_even", "Annual local service-cost break-even threshold", "public_costs", "USD_per_year", "flow", (local_tax, local_tax, local_tax), p["tax_period"], "not_applicable", "allocation", "annual marginal local public-service cost at break-even = aggregated project-linked local property-tax contribution", tax_parameters, p["tax_sources"], p["tax_claims"], "Shows the annual cost threshold at which the recurring local property-tax contribution would be fully offset.", "Observed marginal service expenditures and infrastructure obligations for the same recipient jurisdictions and period", ["This is a break-even threshold, not an estimate of actual public cost.", "A positive recurring fiscal margin exists only if same-scope annual marginal costs are below this threshold; the margin is negative if costs are above it.", "State incentives, counterfactual tax reductions, financing flows and multi-period support remain separate because their jurisdictions or periods do not match this annual local account."], "No net fiscal result is asserted without same-scope cost evidence.")
        break_even["scope"]["label"] = p["tax_scope"]
        break_even["interval"] = {"kind": "point_estimate", "low": local_tax, "central": local_tax, "high": local_tax, "interpretation": "The break-even threshold equals the cited recurring local property-tax contribution by definition; it is not an estimate of actual cost."}
        break_even["confidence"] = "medium"
        break_even["confidence_rationale"] = "The threshold identity is exact for the cited tax aggregation, while actual same-scope public cost remains unobserved."
        rows.append(break_even)
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


def comparison_rows():
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
            suffix = suffixes[metric].replace("_effect", "_comparison_gap")
            rows.append(row(key, suffix, f"study.modeled_county_{suffix}", f"Modeled county {labels[metric]} comparison gap", "county_outcome", "percent", "change", (central - width, central, central + width), {"kind": "calendar_year", "year": 2024, "label": f"2024 host-county outcome relative to a mechanically matched benchmark; opening year {treatment}"}, "not_applicable", "benchmark_application", "100 × (host 2024 outcome − weighted comparison outcome) ÷ weighted comparison outcome", [source_param("host_2024_value", treated[2024], units[metric], f"Host-county 2024 {labels[metric]} from the county economic panel", PANEL, "Compared with weighted benchmark value"), source_param("comparison_2024_value", predicted, units[metric], f"Inverse-distance weighted 2024 value from 20 comparison counties", PANEL, "Subtracted from host and used as denominator"), assumption_param("pre_period_rmse_percent", pre_rmse, "percent", f"Fit diagnostic over {years[0]}-{years[-1]}", "Sets sensitivity width")], [PANEL], [], "Shows the host county's 2024 divergence from a reproducible comparison benchmark without assigning that divergence to the facility.", "A defensible causal design with treatment isolation, uncontaminated controls, placebo tests and robustness diagnostics", ["This comparison is descriptive and must not be interpreted as a data-center effect.", "Opening timing does not isolate later expansions or concurrent investments.", "The donor screen excludes study counties but cannot exclude every unobserved data-center or economic treatment.", "The interval is a fit sensitivity, not a statistical confidence interval."], "Low-confidence county comparison gap; no causal attribution is made."))
    return rows


def main():
    payload = json.loads(TARGET.read_text(encoding="utf-8"))
    source = {"source_id": PANEL, "title": "County Economic Core Panel, 2001-2024", "url": "https://apps.bea.gov/regional/downloadzip.htm", "publisher": "U.S. Bureau of Economic Analysis and U.S. Bureau of Labor Statistics", "source_type": "other", "publication_date": {"precision": "year", "year": 2026}, "retrieved_on": REVIEWED, "review_method": "structured_data", "notes": "Repository panel compiled from official annual county real GDP, total employment and average-weekly-wage series. The completion model uses pre-treatment histories and 2024 outcomes; source revisions and concurrent treatments remain limitations."}
    payload["sources"] = [item for item in payload["sources"] if item["source_id"] != PANEL] + [source]
    payload["estimates"] = [item for item in payload["estimates"] if not item["estimate_id"].startswith("est_study_full_")]
    new_rows = completion_rows() + comparison_rows()
    payload["estimates"].extend(new_rows)
    payload["synthesis_version"] = "study-modeled-synthesis-3.2.0"
    payload["modeling_policy_version"] = "study-modeling-policy-1.3.0"
    payload["reviewed_on"] = REVIEWED
    payload["scope_note"] = "Modeled contribution accounts for Apple Mesa / Maricopa County, Switch Citadel / Storey County, and Digital Crossroad Hammond / Lake County. Every required account category and county-comparison module contains sourced evidence or a visibly labeled modeled value. Public support is not netted against unmatched local revenues, unavailable public-service cost is represented by a break-even threshold rather than an invented net margin, county comparisons are descriptive rather than causal, and low-confidence transferred benchmarks remain explicit."
    TARGET.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8", newline="\n")
    print(json.dumps({"completion_models": len(new_rows), "total_models": len(payload["estimates"])}))


if __name__ == "__main__":
    main()

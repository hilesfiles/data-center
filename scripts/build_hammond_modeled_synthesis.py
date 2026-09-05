"""Build the Hammond modeled-synthesis increment without changing source evidence.

The generated rows are scenarios and arithmetic reconciliations, not observations.
Running this script is idempotent: it replaces only ``est_study_dx_hammond_*``
rows and the four Hammond benchmark sources in the governed synthesis register.
"""
from __future__ import annotations

import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
TARGET = ROOT / "config/v1/study-modeled-synthesis.json"
PROJECT = "prj_study_im3_building_00978934687"
COUNTY = "18089"
REVIEWED = "2026-09-05"
OVERLAP = "do_not_sum_outside_declared_total"

PWC = "src_study_pwc_data_center_market_2021"
NIRPC = "src_study_nirpc_recovery_plan_2022"
LBNL = "src_study_lbnl_dc_energy_2024"
EGRID = "src_study_epa_egrid_2023_rev2"


def provenance(kind, detail, reference_id=None):
    row = {"kind": kind, "detail": detail}
    if reference_id:
        row["reference_id"] = reference_id
    return row


def parameter(name, value, unit, kind, detail, transformation, reference_id=None):
    return {
        "name": name,
        "value": value,
        "unit": unit,
        "provenance": provenance(kind, detail, reference_id),
        "transformation": transformation,
    }


def interval(kind, low, central, high, interpretation):
    return {"kind": kind, "low": low, "central": central, "high": high, "interpretation": interpretation}


def scope(label, level="campus"):
    return {"level": level, "label": label, "county_fips": COUNTY, "inventory_allocation": "unallocated"}


def estimate(
    suffix,
    metric,
    label,
    category,
    unit,
    measure_type,
    period,
    scope_value,
    interval_value,
    channel,
    aggregation_id,
    role,
    parameters,
    method,
    model_version,
    formula,
    claim_ids,
    source_ids,
    assumptions,
    confidence,
    confidence_rationale,
    decision_relevance,
    remaining_gap,
    limitations,
    notes,
    component_ids=None,
    multiplier=None,
):
    aggregation = {"aggregation_id": aggregation_id, "role": role, "overlap_policy": OVERLAP}
    if component_ids:
        aggregation["component_estimate_ids"] = component_ids
    row = {
        "estimate_id": f"est_study_dx_hammond_{suffix}",
        "project_id": PROJECT,
        "metric_code": metric,
        "label": label,
        "category": category,
        "unit": unit,
        "measure_type": measure_type,
        "basis": "modeled_synthesis",
        "value": interval_value["central"],
        "period": period,
        "scope": scope_value,
        "interval": interval_value,
        "contribution_channel": channel,
        "aggregation": aggregation,
        "parameters": parameters,
        "confidence": confidence,
        "confidence_rationale": confidence_rationale,
        "decision_relevance": decision_relevance,
        "evidence_search": {
            "direct_observation_status": "partial",
            "source_projection_status": "available_separately",
            "remaining_evidence_gap": remaining_gap,
        },
        "derivation": {
            "method": method,
            "model_version": model_version,
            "formula": formula,
            "input_claim_ids": claim_ids,
            "input_source_ids": source_ids,
            "assumptions": assumptions,
        },
        "limitations": limitations,
        "presentation": "modeled_not_observed_or_audited",
        "notes": notes,
        "reviewed_on": REVIEWED,
    }
    if multiplier:
        row["multiplier_provenance"] = multiplier
    return row


def multiplier(local_purchase_assumption):
    return {
        "source_id": PWC,
        "model_name": "IMPLAN county contribution model reported by BAE",
        "model_version": "Prince William County prototype-data-center study, 2021-dollar tables 7-8",
        "geography": "Prince William County, Virginia benchmark transferred to Hammond/Lake County, Indiana",
        "vintage": "IMPLAN model reported December 2021; underlying IMPLAN data vintage not disclosed",
        "local_purchase_assumption": local_purchase_assumption,
        "channel_separation": "direct_indirect_induced_reported_separately",
    }


def contribution_rows(prefix, metric_prefix, category, unit, period, scope_value, base_values, benchmark_values, benchmark_denominator, benchmark_unit, confidence_rationale, remaining_gap, notes, local_purchase_assumption):
    """Create direct/indirect/induced/total rows scaled by a three-point base."""
    channels = ["direct", "indirect", "induced", "total"]
    rows = []
    component_ids = [f"est_study_dx_hammond_{prefix}_{name}" for name in channels[:3]]
    for index, channel in enumerate(channels):
        rate = benchmark_values[index] / benchmark_denominator
        values = [round(value * rate, 2) for value in base_values]
        role = "total" if channel == "total" else "component"
        params = [
            parameter("scenario_base_low", base_values[0], benchmark_unit, "assumption", "Low endpoint of the disclosed Hammond scenario base", "Multiplied by the channel benchmark rate"),
            parameter("scenario_base_central", base_values[1], benchmark_unit, "assumption", "Central endpoint of the disclosed Hammond scenario base", "Multiplied by the channel benchmark rate"),
            parameter("scenario_base_high", base_values[2], benchmark_unit, "assumption", "High endpoint of the disclosed Hammond scenario base", "Multiplied by the channel benchmark rate"),
            parameter(f"{channel}_benchmark_numerator", benchmark_values[index], unit, "source", f"Prince William County prototype {channel} contribution", "Divided by the benchmark denominator", PWC),
            parameter("benchmark_denominator", benchmark_denominator, benchmark_unit, "source", "Prince William County prototype model denominator", "Divides the channel benchmark numerator", PWC),
        ]
        rows.append(estimate(
            f"{prefix}_{channel}", f"{metric_prefix}_{channel}", f"Modeled {label_channel(channel, prefix)}", category, unit,
            "flow" if unit != "FTE" else "stock", period, scope_value,
            interval("sensitivity_envelope", values[0], values[1], values[2], f"Low, central and high scenario bases multiplied by the public {channel}-channel benchmark rate."),
            channel, f"dx_hammond_{prefix}", role, params, "input_output_multiplier", f"dx-hammond-{prefix}-1.0.0",
            f"scenario_base × ({channel}_benchmark_numerator ÷ benchmark_denominator)",
            ["clm_study_digital_crossroad_local_contractor_spend_2025"] if benchmark_unit == "USD" else ["clm_study_digital_crossroad_operating_employees_2020", "clm_study_digital_crossroad_edge_jobs_2018"],
            [PWC, "src_study_hammond_council_minutes_2025_06_09"] if benchmark_unit == "USD" else [PWC, "src_study_dcd_hammond_completion_2020", "src_study_iedc_2018_annual_report_active_contracts"],
            ["The transferred county benchmark is a sensitivity device, not a Lake County coefficient.", "Dollar benchmarks remain in reported 2021 dollars because the Hammond spending accumulation dates are incomplete." if benchmark_unit == "USD" else "The modeled FTE envelope is not a current headcount."],
            "low", confidence_rationale, "Separates contribution channels without treating a source fact or forecast as a modeled total.", remaining_gap,
            ["Geographic structure and local purchasing differ between Prince William and Lake counties.", "The public benchmark's underlying IMPLAN data vintage is not disclosed.", "Contribution is not causation."],
            notes, component_ids if channel == "total" else None, multiplier(local_purchase_assumption)
        ))
    return rows


def label_channel(channel, prefix):
    descriptor = {
        "construction_job_years": "construction job-years",
        "construction_labor_income": "construction labor income",
        "operating_fte": "annual operating FTE",
        "operating_labor_income": "annual operating labor income",
    }[prefix]
    return {
        "direct": f"direct {descriptor}",
        "indirect": f"indirect supplier {descriptor}",
        "induced": f"induced household-spending {descriptor}",
        "total": f"total {descriptor}",
    }[channel]


def build_rows():
    rows = []
    construction_period = {"kind": "construction_period", "start_date": "2018-08-14", "end_date": "2025-06-09", "label": "Observed first-groundbreaking through latest cumulative local-contractor statement"}
    construction_scope = scope("Digital Crossroad Hammond Building 1 construction and later documented buildout activity")
    spend_claim = "clm_study_digital_crossroad_local_contractor_spend_2025"
    spend_values = [80000000, 100000000, 120000000]
    rows.append(estimate(
        "construction_spend_direct", "study.modeled_construction_supplier_spending_direct", "Modeled direct local-contractor spending envelope", "suppliers", "USD", "flow",
        construction_period, construction_scope,
        interval("sensitivity_envelope", *spend_values, "The observed greater-than-$80 million lower bound is paired with 1.25× and 1.50× sensitivity factors; endpoints are not audited totals."),
        "direct", "dx_hammond_construction_spend", "standalone",
        [parameter("reported_local_spend_lower_bound", 80000000, "USD", "claim", "Developer-reported cumulative lower bound", "Multiplied by the scenario factor", spend_claim), parameter("central_factor", 1.25, "ratio", "assumption", "Sensitivity factor above the strict lower bound", "Produces the central endpoint"), parameter("high_factor", 1.5, "ratio", "assumption", "Sensitivity factor above the strict lower bound", "Produces the high endpoint")],
        "sensitivity_analysis", "dx-hammond-local-spend-1.0.0", "reported_lower_bound × scenario_factor (1.00, 1.25, 1.50)", [spend_claim], ["src_study_hammond_council_minutes_2025_06_09"],
        ["The source phrase 'well over' is represented only by disclosed sensitivity factors.", "Local retains the source's undefined geography and does not mean Lake County payroll or worker residence."],
        "low", "The lower bound is a public statement, but the upper endpoints and local geography are assumptions.", "Carries supplier spending above the observed lower bound without converting it into capital expenditure.", "Audited vendor payments by date, trade, vendor address, project phase and local-geography definition", ["Not audited spending.", "Accumulation start is unknown.", "May include labor, materials and subcontractor margins."], "Direct construction supplier-output scenario; do not add it to source-reported spending."
    ))
    rows += contribution_rows("construction_job_years", "study.modeled_construction_job_years", "construction", "job_years", construction_period, construction_scope, spend_values, [1697, 407, 301, 2406], 275000000, "USD", "The Hammond spending amount is bounded only below and the Virginia county coefficients may not transfer.", "Certified Hammond worker-hours, payroll records, worker residence and phase dates", "Temporary job-years over the full construction window; not peak workers or permanent jobs.", "The source-described local-contractor base is treated as eligible direct output, while the benchmark's county capture is transferred only as a sensitivity.")
    rows += contribution_rows("construction_labor_income", "study.modeled_construction_labor_income", "construction", "USD", construction_period, construction_scope, spend_values, [110695000, 23166000, 11747000, 145608000], 275000000, "USD", "The wage-and-benefit coefficients are a cross-county 2021-dollar transfer applied to a cumulative amount with incomplete dates.", "Certified Hammond payroll, benefits, proprietor income, worker residence and annual phase allocation", "Labor income includes compensation and proprietor income under the source model; it is not payroll paid by DX Hammond.", "The source-described local-contractor base is treated as eligible direct output, while the benchmark's county capture is transferred only as a sensitivity.")
    rows.append(estimate(
        "construction_local_resident_job_years", "study.modeled_construction_local_resident_job_years", "Modeled Lake County-resident construction job-years", "construction", "job_years", "flow", construction_period, construction_scope,
        interval("sensitivity_envelope", 197.47, 339.40, 518.36, "Direct job-year endpoints multiplied by 40%, 55% and 70% residence-share sensitivities; 55% is a regional workforce proxy."), "direct", "dx_hammond_construction_local_resident", "standalone",
        [parameter("direct_job_years_low", 493.67, "job_years", "assumption", "Low direct job-year scenario from the Hammond contribution model", "Multiplied by low residence share"), parameter("direct_job_years_central", 617.09, "job_years", "assumption", "Central direct job-year scenario from the Hammond contribution model", "Multiplied by central residence share"), parameter("direct_job_years_high", 740.51, "job_years", "assumption", "High direct job-year scenario from the Hammond contribution model", "Multiplied by high residence share"), parameter("regional_resident_worker_proxy", 0.55, "ratio", "source", "NIRPC reports about 55% of resident workers also work in Lake County", "Used as the central residence-share proxy", NIRPC), parameter("low_residence_share", 0.4, "ratio", "assumption", "Sensitivity below the regional proxy", "Multiplies low job-years"), parameter("high_residence_share", 0.7, "ratio", "assumption", "Sensitivity above the regional proxy", "Multiplies high job-years")],
        "benchmark_application", "dx-hammond-local-labor-1.0.0", "direct_job_years × assumed_Lake_County_resident_share", [spend_claim], [PWC, NIRPC, "src_study_hammond_council_minutes_2025_06_09"], ["The regional resident-worker statistic is only a proxy for construction-worker residence.", "The development-agreement preference is not treated as realized participation."], "low", "No project worker-residence record is public and the regional proxy measures a different population.", "Makes the local-worker assumption visible instead of relabeling local-contractor spending as local labor.", "Quarterly certified worker residence, hours, trades and employer records", ["Proxy population differs from project workers.", "Local-contractor location does not establish worker residence.", "Not a compliance finding."], "A residence sensitivity only; the 2018 local-labor requirement remains a separate source fact."
    ))

    operating_period = {"kind": "calendar_year", "year": 2025, "label": "2025 operating scenario anchored by public 2020 employment and 2025 occupancy evidence"}
    operating_scope = scope("Digital Crossroad Hammond operating facility")
    fte_values = [17, 31, 45]
    rows.append(estimate(
        "operating_fte_direct", "study.modeled_operating_fte_direct", "Modeled direct annual operating FTE", "operations", "FTE", "stock", operating_period, operating_scope,
        interval("sensitivity_envelope", *fte_values, "Low retains the 17-employee 2020 snapshot, high retains the separate 45-job EDGE expectation, and central is their midpoint."), "direct", "dx_hammond_operating_fte", "component",
        [parameter("reported_employee_snapshot", 17, "employees", "claim", "Contemporaneous 2020 facility employee count", "Used as low endpoint", "clm_study_digital_crossroad_operating_employees_2020"), parameter("source_job_projection", 45, "jobs", "claim", "Separate EDGE job expectation", "Used only as high scenario endpoint", "clm_study_digital_crossroad_edge_jobs_2018"), parameter("midpoint_fte", 31, "FTE", "assumption", "Arithmetic midpoint of the two anchors", "Used as central scenario")],
        "sensitivity_analysis", "dx-hammond-operating-fte-1.0.0", "scenario endpoints = 17 observed employees, midpoint 31, and 45 source-projected jobs", ["clm_study_digital_crossroad_operating_employees_2020", "clm_study_digital_crossroad_edge_jobs_2018"], ["src_study_dcd_hammond_completion_2020", "src_study_iedc_2018_annual_report_active_contracts"], ["Employees and jobs are treated as FTE sensitivity anchors only.", "Neither anchor is asserted to equal 2025 annual-average FTE."], "low", "The anchors differ in date and definition; current annual-average direct and contractor FTE are not public.", "Bounds direct operating labor without converting the source forecast into an observation.", "Current annual-average direct and contractor FTE, occupation, hours and work-location definitions", ["Not a current headcount.", "Source forecast remains separately displayed.", "Customer staff are excluded."], "The high endpoint is not forecast realization."
    ))
    operating_jobs = contribution_rows("operating_fte", "study.modeled_operating_fte", "operations", "FTE", operating_period, operating_scope, fte_values, [28, 133, 22, 183], 28, "FTE", "The direct FTE base is a scenario and the Virginia county operating coefficients may not transfer to Lake County.", "Current annual-average direct, contractor and supplier employment by work location", "Operating contribution jobs, not jobs caused or guaranteed by the facility.", "No Hammond supplier-purchase matrix is public; the full Prince William local-capture structure is transferred as a low-confidence sensitivity.")
    # Use the purpose-built direct FTE row as the direct component and omit the generated duplicate.
    operating_jobs = [row for row in operating_jobs if row["contribution_channel"] != "direct"]
    for row in operating_jobs:
        if row["aggregation"]["role"] == "total":
            row["aggregation"]["component_estimate_ids"][0] = "est_study_dx_hammond_operating_fte_direct"
    rows += operating_jobs
    rows += contribution_rows("operating_labor_income", "study.modeled_operating_labor_income", "operations", "USD", operating_period, operating_scope, fte_values, [5040000, 5889000, 873000, 11802000], 28, "FTE", "Compensation includes benefits and proprietor income and relies on a cross-county benchmark.", "Current Hammond payroll, benefits, contractor compensation, supplier labor income and worker residence", "Annual labor-income contribution; not audited payroll and not additive to the separate payroll benchmark.", "No Hammond supplier-purchase matrix is public; the full Prince William local-capture structure is transferred as a low-confidence sensitivity.")
    rows.append(estimate(
        "operating_payroll_direct", "study.modeled_operating_payroll_direct", "Modeled direct annual payroll", "operations", "USD", "flow", operating_period, operating_scope,
        interval("sensitivity_envelope", 1563613.64, 2851295.45, 4138977.27, "FTE scenario endpoints multiplied by 2023 Lake County NAICS 518210 payroll per March employee."), "direct", "dx_hammond_operating_payroll", "standalone",
        [parameter("county_industry_payroll", 4047000, "USD", "claim", "Lake County NAICS 518210 annual payroll in 2023", "Divided by county-industry employment", "clm_study_lake_county_cbp_518210_annual_payroll_2023"), parameter("county_industry_employment", 44, "employees", "claim", "Lake County NAICS 518210 March employment in 2023", "Denominator for payroll per employee", "clm_study_lake_county_cbp_518210_employment_2023"), parameter("payroll_per_employee", 91977.27, "USD_per_FTE", "assumption", "Quotient of the two source claims", "Multiplied by FTE endpoints")],
        "benchmark_application", "dx-hammond-operating-payroll-1.0.0", "operating_FTE × ($4,047,000 county-industry payroll ÷ 44 March employees)", ["clm_study_lake_county_cbp_518210_annual_payroll_2023", "clm_study_lake_county_cbp_518210_employment_2023", "clm_study_digital_crossroad_operating_employees_2020", "clm_study_digital_crossroad_edge_jobs_2018"], ["src_study_census_cbp_2023_lake_county_naics_518210", "src_study_dcd_hammond_completion_2020", "src_study_iedc_2018_annual_report_active_contracts"], ["County NAICS payroll per March employee approximates facility payroll per FTE.", "No inflation adjustment is applied."], "low", "Both county inputs carry Census noise and cover the entire industry; the FTE base is a scenario.", "Provides a local compensation benchmark distinct from the broader labor-income contribution model.", "Facility wages, bonuses, benefits, hours, occupations, contractor compensation and residency", ["County-industry rather than facility payroll.", "March employment is not annual-average FTE.", "Do not add to modeled labor income."], "Payroll excludes an explicit benefits estimate; the contribution-model labor-income rows use a different definition."
    ))
    rows.append(estimate(
        "operating_local_resident_fte", "study.modeled_operating_local_resident_fte", "Modeled Lake County-resident operating FTE", "operations", "FTE", "stock", operating_period, operating_scope,
        interval("sensitivity_envelope", 6.8, 17.05, 31.5, "Operating FTE endpoints multiplied by 40%, 55% and 70% residence-share sensitivities."), "direct", "dx_hammond_operating_local_resident", "standalone",
        [parameter("operating_fte_low", 17, "FTE", "assumption", "Low direct operating-FTE scenario", "Multiplied by low residence share"), parameter("operating_fte_central", 31, "FTE", "assumption", "Central direct operating-FTE scenario", "Multiplied by central residence share"), parameter("operating_fte_high", 45, "FTE", "assumption", "High direct operating-FTE scenario", "Multiplied by high residence share"), parameter("regional_resident_worker_proxy", 0.55, "ratio", "source", "NIRPC regional proxy", "Used as central residence share", NIRPC), parameter("low_residence_share", 0.4, "ratio", "assumption", "Sensitivity below proxy", "Multiplies low FTE"), parameter("high_residence_share", 0.7, "ratio", "assumption", "Sensitivity above proxy", "Multiplies high FTE")],
        "benchmark_application", "dx-hammond-operating-residence-1.0.0", "operating_FTE × assumed_Lake_County_resident_share", ["clm_study_digital_crossroad_operating_employees_2020", "clm_study_digital_crossroad_edge_jobs_2018"], [NIRPC, "src_study_dcd_hammond_completion_2020", "src_study_iedc_2018_annual_report_active_contracts"], ["The regional workforce statistic is only a residence-share proxy.", "Customer employees are outside scope."], "low", "No facility employee-residence distribution is public.", "Makes resident-share uncertainty explicit.", "Current employee and contractor residence by annual-average FTE", ["Proxy population differs from facility workers.", "Not a local-hiring compliance finding."], "Residence scenario only."
    ))
    for suffix, metric, label, benchmark, channel, category in [
        ("operating_supplier_output_indirect", "study.modeled_operating_supplier_output_indirect", "Modeled indirect supplier output", 17915000, "indirect", "suppliers"),
        ("operating_household_output_induced", "study.modeled_operating_household_output_induced", "Modeled induced household-spending output", 3302000, "induced", "community"),
    ]:
        vals = [round(x * benchmark / 28, 2) for x in fte_values]
        rows.append(estimate(
            suffix, metric, label, category, "USD_per_year", "flow", operating_period, operating_scope,
            interval("sensitivity_envelope", *vals, "Operating FTE endpoints multiplied by the corresponding Prince William County output-per-direct-FTE coefficient."), channel, f"dx_hammond_{suffix}", "standalone",
            [parameter("operating_fte_central", 31, "FTE", "assumption", "Central operating-FTE scenario", "Multiplied by benchmark output per FTE"), parameter(f"{channel}_benchmark_output", benchmark, "USD_per_year", "source", f"Prototype {channel} annual output", "Divided by 28 direct FTE", PWC), parameter("benchmark_direct_fte", 28, "FTE", "source", "Prototype direct operating FTE", "Divides benchmark output", PWC)],
            "input_output_multiplier", f"dx-hammond-{suffix}-1.0.0", f"operating_FTE × (${benchmark:,} benchmark_output ÷ 28 benchmark_direct_FTE)", ["clm_study_digital_crossroad_operating_employees_2020", "clm_study_digital_crossroad_edge_jobs_2018"], [PWC, "src_study_dcd_hammond_completion_2020", "src_study_iedc_2018_annual_report_active_contracts"], ["Prince William County output-per-FTE transfers to Lake County.", "Reported 2021 dollars are not inflation-adjusted."], "low", "Supplier structure, commuting and local purchase shares can differ materially between counties.", "Separates supplier and household-spending channels.", "Hammond annual operating purchases by vendor location and household expenditure capture", ["Economic output is not vendor purchases or household income.", "Contribution is not causation.", "Cross-county 2021-dollar transfer."], "A channel-specific output scenario, not project revenue.", multiplier=multiplier("No Hammond purchase matrix is public; the Prince William county-capture coefficient is transferred without asserting identical leakages.")))

    rows.append(estimate(
        "cost_basis_change_2025", "study.modeled_real_estate_cost_basis_change", "Modeled change in audited real-estate cost basis", "investment", "USD", "change", {"kind": "calendar_year", "year": 2025, "label": "Change between audited year-end 2024 and 2025 cost-basis stocks"}, scope("PDREF Aggregator interest in Digital Crossroad Hammond real estate"),
        interval("point_estimate", 9702347, 9702347, 9702347, "Exact arithmetic difference between two audited accounting stocks."), "not_applicable", "dx_hammond_cost_basis_change", "standalone",
        [parameter("cost_basis_2025", 220812911, "USD", "claim", "Audited 2025 year-end cost basis", "Less 2024 cost basis", "clm_study_digital_crossroad_cost_basis_2025"), parameter("cost_basis_2024", 211110564, "USD", "claim", "Audited 2024 year-end cost basis", "Subtracted from 2025 cost basis", "clm_study_digital_crossroad_cost_basis_2024")],
        "benchmark_application", "dx-hammond-cost-basis-change-1.0.0", "$220,812,911 - $211,110,564", ["clm_study_digital_crossroad_cost_basis_2025", "clm_study_digital_crossroad_cost_basis_2024"], ["src_study_principal_digital_real_estate_2025"], ["The subtraction is an accounting-stock reconciliation only."], "high", "The arithmetic is exact for the reported stocks, but its economic interpretation is deliberately limited.", "Shows why a year-to-year accounting change must not be labeled construction spending.", "Property-level cost-basis roll-forward separating acquisitions, improvements, depreciation, transfers and dispositions", ["Not capital expenditure.", "Not timed construction spending.", "May reflect accounting changes unrelated to physical work."], "A stock change presented specifically to prevent expenditure misclassification."
    ))

    fiscal_scope = scope("Digital Crossroad Hammond fiscal account across named taxing units", "company_county")
    distribution_claims = ["clm_study_digital_crossroad_gross_tax_distribution_county_2025", "clm_study_digital_crossroad_gross_tax_distribution_township_2025", "clm_study_digital_crossroad_gross_tax_distribution_school_2025", "clm_study_digital_crossroad_gross_tax_distribution_city_2025", "clm_study_digital_crossroad_gross_tax_distribution_library_2025", "clm_study_dx_gross_tax_special_2025"]
    distribution_values = [116985.32, 14630.67, 203548.49, 336545.51, 31102.69, 48315.24]
    rows.append(estimate(
        "gross_tax_distribution_2025", "study.modeled_gross_property_tax_distribution_total", "Modeled gross property-tax distribution total", "fiscal", "USD", "flow", {"kind": "tax_year", "year": 2025, "label": "Tax year 2025 gross distribution reconciliation"}, fiscal_scope,
        interval("point_estimate", 751127.92, 751127.92, 751127.92, "Exact sum of six separately reported taxing-unit gross distributions."), "not_applicable", "dx_hammond_fiscal_gross_2025", "standalone",
        [parameter(f"distribution_{index+1}", value, "USD", "claim", "Separately reported gross taxing-unit distribution", "Included once in gross total", claim) for index, (value, claim) in enumerate(zip(distribution_values, distribution_claims))],
        "benchmark_application", "dx-hammond-tax-reconciliation-1.0.0", "sum(six named gross taxing-unit distributions)", distribution_claims, ["src_study_lake_county_digital_crossroad_tax_2026"], ["Each source line is mutually exclusive within the published gross distribution table."], "high", "The arithmetic and source rows are exact, but gross distribution is not cash received by one government.", "Exposes gross fiscal benefit before credits and cap savings.", "Cash receipt timing and reconciliation by recipient government", ["Gross rather than net of credits.", "Multi-jurisdiction total.", "Not a complete benefit-cost account."], "Do not add the source distribution rows again."
    ))
    rows.append(estimate(
        "property_tax_reductions_2025", "study.modeled_property_tax_reductions_total", "Modeled property-tax credits and cap savings", "public_costs", "USD", "flow", {"kind": "tax_year", "year": 2025, "label": "Tax year 2025 reductions from gross distribution"}, fiscal_scope,
        interval("point_estimate", 110260.44, 110260.44, 110260.44, "Exact sum of local property-tax credits and circuit-breaker cap savings."), "not_applicable", "dx_hammond_fiscal_reductions_2025", "standalone",
        [parameter("local_property_tax_credits", 95115.62, "USD", "claim", "Source-reported local credits", "Added once", "clm_study_digital_crossroad_local_property_tax_credits_2025"), parameter("property_tax_cap_savings", 15144.82, "USD", "claim", "Source-reported cap savings", "Added once", "clm_study_digital_crossroad_property_tax_cap_savings_2025")],
        "benchmark_application", "dx-hammond-tax-reconciliation-1.0.0", "$95,115.62 + $15,144.82", ["clm_study_digital_crossroad_local_property_tax_credits_2025", "clm_study_digital_crossroad_property_tax_cap_savings_2025"], ["src_study_lake_county_digital_crossroad_tax_2026"], ["The source fields represent distinct reductions on the same account."], "high", "Exact source arithmetic, though incidence across governments and taxpayers is not modeled.", "Keeps a public-cost component separate from gross property-tax distribution.", "Government-by-government incidence and any reimbursement of credits", ["Not a cash grant.", "Does not include state incentives or service costs."], "Gross less this amount reconciles to the separately sourced tax bill; that bill is not duplicated as a modeled record."
    ))
    rows.append(estimate(
        "tif_debt_service_2024", "study.modeled_tif_debt_service", "Modeled annual TIF bond debt service", "public_costs", "USD", "flow", {"kind": "calendar_year", "year": 2024, "label": "City fiscal year ended December 31, 2024"}, scope("City of Hammond Series 2019 Data Center bond", "company_county"),
        interval("point_estimate", 482700, 482700, 482700, "Exact sum of audited principal retired and interest/fees for 2024."), "not_applicable", "dx_hammond_tif_debt_service_2024", "standalone",
        [parameter("principal_retired", 165000, "USD", "claim", "Audited 2024 principal retired", "Added once", "clm_study_dx_principal_2024"), parameter("interest_and_fees", 317700, "USD", "claim", "Audited 2024 interest and fees", "Added once", "clm_study_dx_interest_2024")],
        "benchmark_application", "dx-hammond-tif-debt-service-1.0.0", "$165,000 + $317,700", ["clm_study_dx_principal_2024", "clm_study_dx_interest_2024"], ["src_study_hammond_2024_financial_audit"], ["Audited components are nonoverlapping within the bond note."], "high", "Audited components and arithmetic are exact.", "Separates annual financing cost from bond balances, draws and future commitments.", "Administrative costs, reserve changes and government service costs attributable to the project", ["Not the outstanding principal stock.", "Not a subsidy total.", "Does not identify ultimate tax incidence."], "Annual debt-service flow only."
    ))
    rows.append(estimate(
        "tif_project_flow_2024", "study.modeled_tif_project_revenue_flow_reconciliation", "Modeled TIF project-revenue flow reconciliation", "fiscal", "USD", "flow", {"kind": "calendar_year", "year": 2024, "label": "Alternative 2024 audited and fund-accounting measures"}, scope("Digital Crossroad Hammond TIF repayment flow", "company_county"),
        interval("reported_band", 258200, 289593.5, 320987, "Low is the private fund's project-tax repayment measure, high is the City's debt-service-fund transfer, and central is their midpoint; the measures are alternatives, not additive."), "not_applicable", "dx_hammond_tif_flow_2024", "standalone",
        [parameter("private_fund_project_tax_repayment", 258200, "USD", "claim", "Private audited fund statement", "Used as low endpoint", "clm_study_digital_crossroad_tif_revenue_repayment_2024"), parameter("city_debt_service_fund_transfer", 320987, "USD", "claim", "City audited statement", "Used as high endpoint", "clm_study_dx_transfer_2024")],
        "band_midpoint", "dx-hammond-tif-flow-reconciliation-1.0.0", "midpoint($258,200 private-fund measure, $320,987 City transfer)", ["clm_study_digital_crossroad_tif_revenue_repayment_2024", "clm_study_dx_transfer_2024"], ["src_study_principal_digital_real_estate_2025", "src_study_hammond_2024_financial_audit"], ["The two public accounts measure related but not proven-identical flows.", "No amount is added across accounts."], "medium", "Both endpoints are audited, but their definitions and reconciliation differ.", "Prevents double counting while showing the documented range of project-linked TIF flows.", "Transaction-level reconciliation among pledged revenue, City transfers and private loan repayment", ["Not a statistical interval.", "Not evidence that both amounts accrued as separate benefits.", "Does not establish a full TIF cash-flow account."], "Alternative accounting measures only."
    ))
    rows.append(estimate(
        "state_incentives_certified_2026", "study.modeled_state_incentives_certified_total", "Modeled cumulative state-incentive certified total", "public_costs", "USD", "flow", {"kind": "cumulative", "report_date": "2026-09-04", "label": "Current IEDC portal snapshot across three separately governed agreements"}, scope("DX Hammond/Indiana NAP state incentive agreements", "company_county"),
        interval("point_estimate", 37426935.09, 37426935.09, 37426935.09, "Exact arithmetic sum of portal-reported IRTC, DATA exemption and EDGE paid-or-certified fields."), "not_applicable", "dx_hammond_state_incentives_2026", "standalone",
        [parameter("irtc_certified", 9045773.82, "USD", "claim", "Current IRTC paid-or-certified field", "Added once", "clm_study_digital_crossroad_irtc_certified_2026"), parameter("data_exemption_certified", 28369398.27, "USD", "claim", "Current DATA exemption certified field", "Added once", "clm_study_digital_crossroad_data_exemption_certified_2026"), parameter("edge_paid_certified", 11763, "USD", "claim", "Current EDGE paid-or-certified field", "Added once", "clm_study_digital_crossroad_edge_paid_certified_2026")],
        "benchmark_application", "dx-hammond-state-incentive-total-1.0.0", "$9,045,773.82 + $28,369,398.27 + $11,763", ["clm_study_digital_crossroad_irtc_certified_2026", "clm_study_digital_crossroad_data_exemption_certified_2026", "clm_study_digital_crossroad_edge_paid_certified_2026"], ["src_study_iedc_dx_hammond_irtc_portal_2026", "src_study_iedc_dx_hammond_data_portal_2026", "src_study_iedc_dx_hammond_edge_portal_2026"], ["The portal fields are added as certified program value, not as cash disbursement.", "Different tax mechanisms remain named and visible."], "medium", "Portal values are current and exact, but paid-versus-certified timing and fiscal incidence differ across programs.", "Provides a bounded public-cost total without combining contract ceilings or local credits.", "Tax-year realization, cash timing, recapture, carryforward and government incidence for each program", ["Not a cash-grant total.", "Does not include contract ceilings, local tax credits or EV award.", "Cumulative rather than annual."], "A certified-value reconciliation, outside sourced-record and realized-benefit totals."
    ))

    resource_period = {"kind": "calendar_year", "year": 2025, "label": "Year-end 2025 operating-scale engineering scenario"}
    resource_scope = scope("Digital Crossroad Hammond commissioned and occupied critical-power envelope")
    rows.append(estimate(
        "occupied_critical_capacity_2025", "study.modeled_occupied_critical_power_capacity", "Modeled occupied commissioned critical capacity", "resources", "MW", "stock", resource_period, resource_scope,
        interval("point_estimate", 13.395, 13.395, 13.395, "Exact product of 15 MW commissioned critical power and 89.3% leased-and-occupied share."), "not_applicable", "dx_hammond_occupied_capacity_2025", "standalone",
        [parameter("commissioned_critical_capacity", 15, "MW", "claim", "Fund-reported commissioned critical power", "Multiplied by occupied share", "clm_study_digital_crossroad_commissioned_capacity_2025"), parameter("occupied_share", 0.893, "ratio", "claim", "Fund-reported occupied share converted from percent", "Multiplied by commissioned critical power", "clm_study_digital_crossroad_occupied_share_2025")],
        "benchmark_application", "dx-hammond-occupied-capacity-1.0.0", "15 MW × 89.3%", ["clm_study_digital_crossroad_commissioned_capacity_2025", "clm_study_digital_crossroad_occupied_share_2025"], ["src_study_principal_digital_real_estate_2025"], ["Leased and occupied critical capacity is not measured instantaneous IT load."], "high", "Source inputs and arithmetic are exact, but occupancy is not electrical utilization.", "Defines the IT-capacity basis without confusing it with the separate 20 MW utility-feed descriptor.", "Metered IT load and coincident peak by interval", ["Not measured load.", "Not utility-feed capacity.", "Not annual energy."], "A capacity-stock calculation only."
    ))
    rows.append(estimate(
        "it_electricity_2025", "study.modeled_it_electricity_consumption", "Modeled annual IT electricity consumption", "resources", "kWh_per_year", "flow", resource_period, resource_scope,
        interval("sensitivity_envelope", 70404120, 82138140, 93872160, "Occupied critical capacity operated at 60%, 70% and 80% annual load factors."), "not_applicable", "dx_hammond_it_energy_2025", "standalone",
        [parameter("occupied_critical_capacity", 13.395, "MW", "assumption", "Product of public commissioned capacity and occupancy", "Multiplied by hours and load factor"), parameter("hours_per_year", 8760, "hours", "assumption", "Non-leap-year conversion", "Multiplies MW"), parameter("central_it_load_factor", 0.7, "ratio", "assumption", "Engineering sensitivity", "Produces central energy"), parameter("low_it_load_factor", 0.6, "ratio", "assumption", "Engineering sensitivity", "Produces low energy"), parameter("high_it_load_factor", 0.8, "ratio", "source", "Upper operational-power share used in LBNL server scenarios", "Produces high energy", LBNL)],
        "engineering_estimate", "dx-hammond-it-energy-1.0.0", "15 MW × 89.3% × 8,760 hours × IT_load_factor × 1,000 kW/MW", ["clm_study_digital_crossroad_commissioned_capacity_2025", "clm_study_digital_crossroad_occupied_share_2025"], ["src_study_principal_digital_real_estate_2025", LBNL], ["Occupied capacity is available to IT equipment throughout the year.", "Annual IT load factor ranges from 60% to 80%."], "low", "No facility meter or IT load series is public; occupancy is not utilization.", "Bounds annual IT energy while preserving the difference between capacity and measured use.", "Interval electricity meter data, IT load, curtailment and downtime", ["Not a utility meter reading.", "Does not include cooling or electrical overhead.", "Load factors are assumptions."], "Engineering scenario only."
    ))
    rows.append(estimate(
        "facility_electricity_2025", "study.modeled_facility_electricity_consumption", "Modeled annual facility electricity consumption", "resources", "kWh_per_year", "flow", resource_period, resource_scope,
        interval("sensitivity_envelope", 80964738, 114993396, 150195456, "IT-energy endpoints multiplied by PUE values 1.15, 1.40 and 1.60."), "not_applicable", "dx_hammond_facility_energy_2025", "standalone",
        [parameter("it_energy_low", 70404120, "kWh_per_year", "assumption", "Low IT-energy scenario", "Multiplied by low PUE"), parameter("it_energy_central", 82138140, "kWh_per_year", "assumption", "Central IT-energy scenario", "Multiplied by central PUE"), parameter("it_energy_high", 93872160, "kWh_per_year", "assumption", "High IT-energy scenario", "Multiplied by high PUE"), parameter("low_pue", 1.15, "PUE_ratio", "source", "Lower endpoint of LBNL 2028 all-data-center PUE range", "Multiplies low IT energy", LBNL), parameter("central_pue", 1.4, "PUE_ratio", "source", "LBNL 2023 annual-average PUE", "Multiplies central IT energy", LBNL), parameter("high_pue", 1.6, "PUE_ratio", "source", "LBNL 2014 annual-average PUE used as conservative sensitivity", "Multiplies high IT energy", LBNL)],
        "engineering_estimate", "dx-hammond-facility-energy-1.0.0", "IT_electricity × PUE", ["clm_study_digital_crossroad_commissioned_capacity_2025", "clm_study_digital_crossroad_occupied_share_2025"], ["src_study_principal_digital_real_estate_2025", LBNL], ["National PUE benchmarks transfer to Hammond only as a broad envelope.", "No renewable procurement or hourly grid matching is assumed."], "low", "Facility PUE and metered electricity are not public.", "Provides an electricity envelope for water and emissions calculations.", "Metered facility electricity, PUE, losses and renewable procurement by year", ["Not measured use.", "National benchmark transfer.", "Does not imply peak demand."], "Whole-facility electricity scenario."
    ))
    rows.append(estimate(
        "peak_demand_2025", "study.modeled_peak_electric_demand", "Modeled facility peak-demand envelope", "resources", "MW", "peak", resource_period, resource_scope,
        interval("sensitivity_envelope", 15.40425, 18.753, 20, "Occupied critical power multiplied by PUE, with the high endpoint capped at the separate 20 MW utility-feed/operating-capacity descriptor."), "not_applicable", "dx_hammond_peak_demand_2025", "standalone",
        [parameter("occupied_critical_capacity", 13.395, "MW", "assumption", "Derived occupied commissioned critical capacity", "Multiplied by PUE"), parameter("low_pue", 1.15, "PUE_ratio", "source", "LBNL lower PUE sensitivity", "Produces low peak", LBNL), parameter("central_pue", 1.4, "PUE_ratio", "source", "LBNL 2023 average", "Produces central peak", LBNL), parameter("utility_feed_descriptor", 20, "MW", "claim", "Company witness operating-capacity descriptor", "Caps high scenario", "clm_study_digital_crossroad_operating_capacity_2025")],
        "engineering_estimate", "dx-hammond-peak-demand-1.0.0", "min(20 MW utility-feed descriptor, 13.395 MW occupied critical capacity × PUE)", ["clm_study_digital_crossroad_commissioned_capacity_2025", "clm_study_digital_crossroad_occupied_share_2025", "clm_study_digital_crossroad_operating_capacity_2025"], ["src_study_principal_digital_real_estate_2025", "src_study_dx_hammond_iurc_testimony_2025", LBNL], ["Critical capacity and PUE approximate coincident facility demand.", "The 20 MW descriptor is treated as a cap, not measured peak."], "low", "No interval meter or utility coincident-peak record is public.", "Keeps commissioned critical power, occupancy, PUE and feed capacity distinct.", "Utility meter coincident peak, demand ratchets, redundancy and losses", ["Not measured peak demand.", "Feed descriptor may not be a contractual limit.", "PUE transfer uncertainty."], "Engineering peak envelope only."
    ))
    rows.append(estimate(
        "onsite_water_2025", "study.modeled_onsite_water_use", "Modeled annual onsite water use", "resources", "gallons_per_year", "flow", resource_period, resource_scope,
        interval("sensitivity_envelope", 6695568.31, 9113412.43, 11903232.56, "IT-energy endpoints multiplied by 0.36, 0.42 and 0.48 L/kWh WUE and converted to U.S. gallons."), "not_applicable", "dx_hammond_water_2025", "standalone",
        [parameter("it_energy_low", 70404120, "kWh_per_year", "assumption", "Low IT-energy scenario", "Multiplied by low WUE"), parameter("it_energy_central", 82138140, "kWh_per_year", "assumption", "Central IT-energy scenario", "Multiplied by central WUE"), parameter("it_energy_high", 93872160, "kWh_per_year", "assumption", "High IT-energy scenario", "Multiplied by high WUE"), parameter("low_wue", 0.36, "WUE_liters_per_kWh", "source", "LBNL 2023 annual average just over 0.36 L/kWh", "Multiplies low IT energy", LBNL), parameter("central_wue", 0.42, "WUE_liters_per_kWh", "assumption", "Midpoint sensitivity", "Multiplies central IT energy"), parameter("high_wue", 0.48, "WUE_liters_per_kWh", "source", "Upper LBNL post-2023 range", "Multiplies high IT energy", LBNL), parameter("liters_per_gallon", 3.785411784, "liters_per_gallon", "assumption", "Exact unit conversion", "Divides modeled liters")],
        "engineering_estimate", "dx-hammond-water-1.0.0", "IT_electricity × WUE ÷ 3.785411784", ["clm_study_digital_crossroad_commissioned_capacity_2025", "clm_study_digital_crossroad_occupied_share_2025", "clm_study_dx_permitted_water_withdrawal_capacity_2018", "clm_study_dx_permitted_water_consumptive_capacity_2018"], ["src_study_principal_digital_real_estate_2025", "src_study_hammond_dx_development_agreement_2018", LBNL], ["National WUE benchmarks transfer to Hammond.", "The permit capacities are comparison ceilings only and do not enter the use formula."], "low", "No water meter, cooling design, WUE, reuse or discharge series is public.", "Bounds onsite use without treating the 910.85/18.202 MGD permit limits as consumption.", "Potable/process/reclaimed intake, cooling cycles, blowdown, wastewater, reuse and meter records", ["Not measured water use.", "Permit capacities are not modeled consumption.", "Excludes indirect grid water."], "Wastewater and reuse remain unmodeled because no public mass-balance inputs were found."
    ))
    rows.append(estimate(
        "grid_emissions_2025", "study.modeled_location_based_grid_emissions", "Modeled location-based grid emissions", "resources", "metric_tons_co2e_per_year", "flow", resource_period, resource_scope,
        interval("sensitivity_envelope", 33643.76, 62112.28, 99840.87, "Facility-electricity endpoints multiplied by RFC West, midpoint and Indiana eGRID CO2e output rates."), "not_applicable", "dx_hammond_grid_emissions_2025", "standalone",
        [parameter("facility_energy_low", 80964738, "kWh_per_year", "assumption", "Low facility-energy scenario", "Converted to MWh and multiplied by low emission rate"), parameter("facility_energy_central", 114993396, "kWh_per_year", "assumption", "Central facility-energy scenario", "Converted to MWh and multiplied by midpoint rate"), parameter("facility_energy_high", 150195456, "kWh_per_year", "assumption", "High facility-energy scenario", "Converted to MWh and multiplied by high rate"), parameter("rfcw_co2e_rate", 916.1, "lb_CO2e_per_MWh", "source", "eGRID2023 RFC West total output rate", "Low emission factor", EGRID), parameter("indiana_co2e_rate", 1465.5, "lb_CO2e_per_MWh", "source", "eGRID2023 Indiana total output rate", "High emission factor", EGRID), parameter("pounds_per_metric_ton", 2204.62262185, "lb_per_metric_ton", "assumption", "Exact mass conversion", "Divides pounds")],
        "engineering_estimate", "dx-hammond-grid-emissions-1.0.0", "facility_kWh ÷ 1,000 × eGRID_lb_CO2e_per_MWh ÷ 2,204.62262185", ["clm_study_digital_crossroad_commissioned_capacity_2025", "clm_study_digital_crossroad_occupied_share_2025", "clm_study_digital_crossroad_operating_capacity_2025", "clm_study_digital_crossroad_permitted_generators_2022"], ["src_study_principal_digital_real_estate_2025", "src_study_dx_hammond_iurc_testimony_2025", "src_study_idem_dx_hammond_permit_2022", LBNL, EGRID], ["Location-based annual output rates approximate delivered-electricity emissions.", "No market-based renewable claim or marginal-emissions effect is assumed.", "Backup generators are excluded because ratings, fuel and runtime are not public."], "low", "Electricity is modeled and the applicable grid rate is uncertain; backup operation is unmeasured.", "Provides an operational emissions envelope with explicit grid-factor provenance.", "Metered electricity, supplier-specific mix, hourly matching, losses, backup-generator ratings, fuel and runtime", ["Not a measured emissions inventory.", "Excludes embodied emissions and backup generation.", "Output-rate choice is a sensitivity, not a marginal causal effect."], "Permit-listed eight generators remain a stock; no backup-generation effect is quantified."
    ))

    cbp_specs = [
        ("cbp_employment_pre_post", "study.modeled_county_industry_employment_pre_post_change", "Modeled descriptive county-industry employment pre/post change", "employees", [67, 323, 378, 398], [429, 131, 44], -30.93, "employment", "clm_study_lake_county_cbp_518210_employment_"),
        ("cbp_payroll_pre_post", "study.modeled_county_industry_payroll_pre_post_change", "Modeled descriptive county-industry payroll pre/post change", "USD", [7295000, 13434000, 14110000, 14548000], [18443000, 5840000, 4047000], -23.52, "annual payroll", "clm_study_lake_county_cbp_518210_annual_payroll_"),
        ("cbp_establishments_pre_post", "study.modeled_county_industry_establishments_pre_post_change", "Modeled descriptive county-industry establishment pre/post change", "establishments", [7, 13, 15, 15], [11, 12, 11], -9.33, "establishments", "clm_study_lake_county_cbp_518210_establishments_"),
    ]
    for suffix, metric, label, input_unit, pre, post, change, noun, claim_prefix in cbp_specs:
        years = [2016, 2017, 2018, 2019, 2021, 2022, 2023]
        claim_ids = [f"{claim_prefix}{year}" for year in years]
        source_ids = [f"src_study_census_cbp_{year}_lake_county_naics_518210" for year in years]
        pre_mean = sum(pre) / len(pre)
        post_mean = sum(post) / len(post)
        rows.append(estimate(
            suffix, metric, label, "county_outcome", "percent", "change", {"kind": "cumulative", "report_date": "2023-12-31", "label": "Descriptive pre/post window around October 2020 operation; 2020 omitted"}, scope("Lake County NAICS 518210 public CBP context", "county"),
            interval("point_estimate", change, change, change, "Deterministic percentage difference between 2016-2019 and 2021-2023 arithmetic means; not a statistical or causal interval."), "not_applicable", f"dx_hammond_{suffix}", "standalone",
            [parameter("pre_period_mean", round(pre_mean, 2), input_unit, "assumption", f"Arithmetic mean of public 2016-2019 county-industry {noun}", "Denominator for percentage change"), parameter("post_period_mean", round(post_mean, 2), input_unit, "assumption", f"Arithmetic mean of public 2021-2023 county-industry {noun}", "Numerator for percentage change"), parameter("operating_event_year", 2020, "year", "claim", "October 2020 operating event anchors the excluded transition year", "Defines pre/post split", "clm_study_digital_crossroad_operating_employees_2020")],
            "benchmark_application", "dx-hammond-cbp-pre-post-1.0.0", "((mean(2021..2023) ÷ mean(2016..2019)) - 1) × 100", claim_ids + ["clm_study_digital_crossroad_operating_employees_2020"], source_ids + ["src_study_dcd_hammond_completion_2020"], ["The 2020 transition year is excluded.", "No facility attribution is made.", "Published CBP noise and classification changes remain in the inputs."], "low", "The series is noisy, industry-wide and lacks a comparison group, pre-trend diagnostics and treatment-isolation design.", "Provides longitudinal context while refusing a causal event-study claim.", "Comparison counties, facility exposure inventory, harmonized industry definitions, diagnostics and longer post period", ["Not difference-in-differences, event study or synthetic control.", "COVID-19 and classification changes confound the split.", "County industry includes employers unrelated to DX-1."], "A descriptive transformation only; no causal_design is attached because causal requirements are not met."
        ))
    return rows


def main():
    payload = json.loads(TARGET.read_text(encoding="utf-8"))
    new_sources = [
        {"source_id": PWC, "title": "Prince William County Data Center Market Study", "url": "https://www.pwcva.gov/assets/2021-12/Final%20Report%20-%20Prince%20William%20County%20Data%20Center%20Market%20Study%20120121%20.pdf", "publisher": "Prince William County, Virginia", "source_type": "local_government_record", "publication_date": {"precision": "year", "year": 2021}, "retrieved_on": REVIEWED, "review_method": "pdf_text_and_page_image", "notes": "Tables 7 and 8 report direct, indirect, induced and total construction and operating employment, labor income and output for a county prototype using IMPLAN. Dollar values are 2021 dollars; the underlying IMPLAN data vintage is not disclosed."},
        {"source_id": NIRPC, "title": "Northwest Indiana Economic Recovery and Resilience Plan", "url": "https://www.in.gov/nirpc/files/2022-09-14-NIRPC-Economic-Recovery-and-Resilience-Plan-1.pdf", "publisher": "Northwestern Indiana Regional Planning Commission", "source_type": "local_government_record", "publication_date": {"date": "2022-09-14", "precision": "day"}, "retrieved_on": REVIEWED, "review_method": "pdf_text_and_page_image", "notes": "Reports that roughly 117,000, or about 55 percent, of resident workers also work in Lake County. This is a regional workforce benchmark, not project worker-residence evidence."},
        {"source_id": LBNL, "title": "2024 United States Data Center Energy Usage Report", "url": "https://eta-publications.lbl.gov/sites/default/files/2024-12/lbnl-2024-united-states-data-center-energy-usage-report.pdf", "publisher": "U.S. Department of Energy and Lawrence Berkeley National Laboratory", "source_type": "other", "publication_date": {"date": "2024-12-19", "precision": "day"}, "retrieved_on": REVIEWED, "review_method": "pdf_text_and_page_image", "notes": "Public national engineering benchmark: 2014 and 2023 average PUE values of 1.6 and 1.4; projected 2028 PUE range 1.15-1.35; WUE just over 0.36 L/kWh through 2023 and 0.45-0.48 thereafter; AI server operational power scenarios span 60-80 percent. These values are not Hammond measurements."},
        {"source_id": EGRID, "title": "eGRID2023 Summary Tables, Revision 2", "url": "https://www.epa.gov/system/files/documents/2025-06/summary_tables_rev2.pdf", "publisher": "U.S. Environmental Protection Agency", "source_type": "other", "publication_date": {"date": "2025-06-12", "precision": "day"}, "retrieved_on": REVIEWED, "review_method": "pdf_text_and_page_image", "notes": "Reports 2023 total output CO2e rates of 916.1 lb/MWh for RFC West and 1,465.5 lb/MWh for Indiana. The Hammond model treats these as a location-based sensitivity rather than a marginal or supplier-specific factor."},
    ]
    source_ids = {source["source_id"] for source in new_sources}
    payload["sources"] = [source for source in payload["sources"] if source["source_id"] not in source_ids] + new_sources
    payload["estimates"] = [row for row in payload["estimates"] if not row["estimate_id"].startswith("est_study_dx_hammond_")] + build_rows()
    payload["reviewed_on"] = REVIEWED
    TARGET.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8", newline="\n")
    print(json.dumps({"hammond_modeled_records": len(build_rows()), "total_modeled_records": len(payload["estimates"])}))


if __name__ == "__main__":
    main()

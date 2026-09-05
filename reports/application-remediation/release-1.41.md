# Study release 1.41 - Digital Crossroad Hammond modeled synthesis

Release `private-sector-study-1.41.0` integrates the completed Lake County depth account for Digital Crossroad DX-1 Hammond under `study-modeled-synthesis-2.4.0` and `study-modeling-policy-1.2.0`. The study publishes 585 source records—533 reported observations and 52 forecasts. Hammond remains 113 sourced records—103 reported and ten forecasts—with 30 research updates. Thirty-seven Hammond models join 13 Apple Mesa and 20 Switch Citadel / Tahoe Reno 1 models for a study-wide total of 70.

## Public evidence and model set

The Hammond models use only the existing source register plus four already-public benchmarks: the Prince William County 2021 IMPLAN market study, NIRPC's Lake County resident-worker share, LBNL's 2024 national data-center energy report and EPA eGRID2023 Revision 2. No public-records request, private-data request, survey, questionnaire or solicitation was sent or recommended.

The 37 records comprise:

- ten construction models: a direct local-contractor spending envelope, direct/indirect/induced/total job-years, direct/indirect/induced/total labor income and Lake County-resident job-years;
- twelve annual operations models: direct/indirect/induced/total FTE, direct/indirect/induced/total labor income, direct payroll, resident FTE, indirect supplier output and induced household-spending output;
- six investment and fiscal reconciliations: 2025 audited cost-basis change, gross property-tax distribution, tax reductions, 2024 TIF debt service, alternative TIF project revenue flows and cumulative state incentives certified;
- six resource-engineering models: occupied critical capacity, IT and facility electricity, peak demand, onsite water and location-based grid emissions; and
- three descriptive county-industry pre/post changes for employment, payroll and establishments.

Construction uses the public greater-than-$80 million local-contractor amount as a lower scenario and $100 million/$120 million sensitivity values. Transferred Prince William coefficients yield a central 874.91 construction job-years and $52.95 million labor-income contribution; they do not claim Hammond causation. Annual operations use 17 reported employees and 45 forecast jobs as bounds with a 31-FTE midpoint. The transferred contribution structure yields a central 202.61 total FTE and $13.07 million labor income. County payroll per March employee supplies a separate $2.85 million direct-payroll benchmark that is not additive to labor income.

Deterministic arithmetic reports a $9,702,347 year-over-year audited real-estate cost-basis change, $751,127.92 gross 2025 property-tax distribution, $110,260.44 in separately reported credits and cap savings, $482,700 in 2024 TIF principal and interest/fees, a $258,200-$320,987 alternative-flow range, and $37,426,935.09 of program-level certified incentives. These are reconciliations, not complete net fiscal benefits: recipient incidence, service costs, incentive tax expenditure and time alignment remain unresolved.

Capacity and public engineering benchmarks produce central scenarios of 13.395 occupied critical MW, 82,138,140 kWh IT electricity, 114,993,396 kWh facility electricity, 18.753 MW peak demand, 9,113,412.43 gallons annual onsite water and 62,112.28 metric tons annual location-based CO2e. None is metered Hammond use. Withdrawal permits and generator counts are retained as contextual source records and are not converted into consumption or backup-runtime claims.

Lake County NAICS 518210 arithmetic means before the October 2020 operating event (2016-2019) and after it (2021-2023) change by -30.93% for employment, -23.52% for payroll and -9.33% for establishments. These transformations are explicitly descriptive. COVID-19, Census noise, industry-classification scope and the absence of a comparison group, pre-trend diagnostics and treatment isolation make a causal design ineligible.

## Publication and validation boundary

Every model declares scope, period, unit, interval type, contribution channel, aggregation identity, named parameters and provenance, method/version, formula, assumptions, limitations, evidence search, unresolved gap, confidence and presentation status. Multiplier rows also declare model, geography, vintage, local-purchase assumption and channel separation. Models remain outside canonical claims, source-record counts and realized-benefit totals.

The release is regenerated from versioned inputs. Validation passes 65 schemas, one valid fixture and three expected-invalid fixtures. All 49 repository tests pass. TypeScript compilation and the Vite production build pass. All 37 browser checks pass with no runtime errors. Focused 390-pixel mobile captures of the Hammond forecast, modeled-synthesis, annual-account coverage, analysis-readiness and public-evidence-gap states were visually inspected; the modeled cards are readable and have no horizontal overflow.

## Parallel county reconciliation

This main-worktree release includes the Maricopa 1.39, Storey 1.40 and Lake County 1.41 increments together. The Hammond generator replaces only `est_study_dx_hammond_*` records and its four public benchmark sources, so rerunning it preserves all Apple and Storey model IDs. Public and silver JSON are regenerated from the combined versioned inputs rather than copied from an isolated county worktree.

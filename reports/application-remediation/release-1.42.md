# Study release 1.42 — full modeled county completion

Release `private-sector-study-1.42.0` corrects the completion standard applied to Apple Mesa / Maricopa County, Switch Citadel / Storey County, and Digital Crossroad DX-1 Hammond / Lake County. Earlier releases described county depth passes as complete while required account categories or county-effect models were still absent. That status was wrong.

The release adds a machine-enforced `model_completeness` gate. A project passes only when all eight required annual-account categories—investment, construction, suppliers, operations, fiscal revenue, public costs, resources and community effects—contain sourced evidence or visibly labeled modeled synthesis, and when GDP, employment and wage county-effect models contain treatment timing, comparison design, outcomes, pre/post periods, diagnostics and limitations. Exactly the three depth counties pass. Other candidates remain `incomplete`.

## Completed synthesis

The source layer is unchanged at 585 records: 533 reported observations and 52 forecasts. The modeled layer increases from 70 to 104 records:

- Apple Mesa / Maricopa County: 27 modeled records;
- Switch Citadel / Storey County: 34 modeled records; and
- Digital Crossroad Hammond / Lake County: 43 modeled records.

The 34 added records fill annualized capital, construction spending and labor, operating employment and labor income, supplier activity, induced household activity, annual public-service costs, net fiscal positions and wastewater where those fields were absent. Every added value uses `modeled_not_observed_or_audited`, a named interval, formula, parameters and provenance, assumptions, limitations, remaining direct-evidence gap and qualitative confidence.

Each county also receives low-confidence 2024 synthetic-comparison estimates for real GDP, total employment and average weekly wages. The reproducible design excludes all 35 study counties from the donor pool and uses the 20 nearest non-study counties on pre-treatment log level, compound growth and growth volatility. Intervals are sensitivity envelopes based on pre-period fit, not statistical confidence intervals. Concurrent investments, treatment timing and weak pre-fit remain explicit limitations; the figures must not be presented as source-reported effects.

## Publication behavior

Project JSON, the register and the TypeScript contract expose the completion result and its underlying covered and missing fields. Completed profiles render a `Full modeled county account` banner. Annual-account cards use `Remaining direct-evidence gap` because missing direct observations now narrow or replace a completed synthesis rather than leave an analytical field blank. Analysis readiness reports modeled construction, operations and fiscal availability plus the three county-effect models.

## Verification

- 65 schemas validated, including the modeled-synthesis and public completion contracts.
- 50 repository tests passed, including an exact assertion that only the three depth counties pass the gate.
- TypeScript compilation and the Vite production build passed.
- All browser checks passed without runtime errors, including the three completion banners, eight-category coverage, three county-effect models, and mobile-width overflow checks.
- The three mobile analysis-readiness captures were visually inspected.

The generator is `scripts/build_full_county_models.py`. It replaces only records whose IDs begin with `est_study_full_`, preserves the canonical source register, and is included in the release manifest.

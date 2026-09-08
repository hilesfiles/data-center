# Modeling and synthesis current-state checkpoint

Recorded 8 September 2026 after publication of the 36-project Level 0 portfolio synthesis. The analytical state is reproducible at commit `98ca7bd5c0807f86daa3bb082588c3d1cd4d5de4` on `codex/pooled-model-foundation`. This checkpoint is the restart boundary for any later workstream; it does not authorize a new workstream.

## Scope and publication state

- Current analytical population: exactly 36 selected projects, 35 host counties, and 23 states.
- Project research release: `private-sector-study-1.60.0`.
- Current cross-project publication: Level 0 descriptive synthesis only.
- National comparison counties used by the current synthesis: zero.
- Pending publication: none.
- Portfolio totals, pooled associations, attributable effects, and causal estimates: none.

The national 3,144-county economic panel remains durable background infrastructure, but it is not the current analytical population. Reopening a national comparison-pool program requires a separate explicit scope decision.

## Governed evidence state

The project accounts contain 1,818 reported observations, 162 source projections, and 304 separately governed modeled syntheses. The project matrix contains 659 populated project/metric cells and one explicit status for each of the 288 project/category combinations: 184 partial, 16 projections-only, and 88 not yet collected. Missing evidence is not encoded as zero.

Reported category coverage is:

| Category | Projects with reported evidence | Coverage |
|---|---:|---:|
| Investment | 24 of 36 | 66.7% |
| Construction | 25 of 36 | 69.4% |
| Suppliers | 2 of 36 | 5.6% |
| Operations | 36 of 36 | 100.0% |
| Fiscal | 36 of 36 | 100.0% |
| Public costs | 11 of 36 | 30.6% |
| Resources | 29 of 36 | 80.6% |
| Community | 21 of 36 | 58.3% |

Coverage means that at least one reported observation exists. It does not mean that a category is complete, annualized, locally allocated, or comparable across projects.

## Host-county baseline

The baseline outcome data are complete for the present 35-county scope. All 840 county-year rows from 2001 through 2024 contain all four governed measures, producing 3,360 observed values with no missing host-county observation:

- real GDP;
- population;
- total employment; and
- nominal average weekly wage.

The county baseline can support descriptive trajectories and configured pre/post windows. Completeness of the outcome history does not itself identify a project effect. Project chronology anchors are registered, but a project opening is not proof of county first entry, and the current scope contains no governed comparison design.

## Derived and exposure state

The facility-year spine represents all 36 projects in 864 project-years. Its annual-range inventory contains 1,245 reported components and 225 modeled components. Another 814 records are excluded from the annual spine because they are cumulative, snapshots, tax or fiscal periods, historical peaks, construction periods, projection horizons, or otherwise outside the 2001–2024 annual panel. They remain in the project accounts rather than being silently allocated.

The observed-data calibration screen evaluates 12 candidate ratios from same-project, same-year, exact-scope numerator and denominator matches. It contains 235 derived observations but authorizes zero transferable parameters:

- Five tax/value ratios have enough contributing projects for descriptive summaries, but tax rates and assessment bases are jurisdiction-specific.
- Two additional tax/value ratios have fewer than three compatible projects.
- Electricity per operating MW, water withdrawal per kWh, water consumption per kWh, employees per MW, and employees per 100,000 square feet have no exact compatible observations.

The strict reported-observation screen produces 55 same-year cohorts across at least three projects and three counties. Forty-three are fiscal, nine concern annual electricity use, and three concern incentive payments. The largest compatible cohort contains seven projects. No investment, construction, supplier, operating-employment, or community metric clears the full timing-and-definition screen.

## Modeled-synthesis disposition

Every one of the 304 modeled syntheses has a portfolio-policy disposition:

- 66 transparent project-level arithmetic records are retained for metric-rule review;
- 194 assumption-dependent records are restricted to sensitivity or counterfactual use; and
- 44 project-scoped county comparisons are directed to a future governed county-outcome framework.

The aggregation rules carry forward 48 modeled annual identities where exactly one eligible component exists for a county, year, and metric. These identities are not cross-project sums and do not enter the reported-observation distributions. No new gap-filling model was created for Level 0.

## What the evidence presently establishes

The strongest common evidence concerns project-linked fiscal accounts. Compatible assessed values and tax payments vary widely across projects and jurisdictions, which argues against a universal tax or fiscal multiplier. Electricity records demonstrate large annual loads for a small compatible subset, but there is no exact empirical electricity-per-MW calibration. Operations and fiscal categories have broad project coverage, while supplier payments and observed public costs remain particularly sparse.

Accordingly, the evidence supports project-level findings, host-county histories, explicit coverage and gap reporting, and narrow same-definition descriptive distributions. It does not currently support a portfolio benefit total, a transferable operating or resource multiplier, a pooled association, or a causal project-impact estimate. This is an identification and comparability limit, not evidence that project effects are zero.

## Validation state

At the analytical-state commit:

- the complete data contract passed across 75 schemas and all public JSON;
- all 274 repository tests passed;
- the seven focused Level 0 tests passed;
- the TypeScript production build passed;
- the automated browser regression passed, including the Level 0 desktop and mobile route;
- all 36 project descriptions rendered above the study rationale;
- all 36 map markers and direct county-detail links passed; and
- the preview process was stopped.

## Restart contract

Future work must preserve all evidence, projections, models, project descriptions, release metadata, manifests, counts, and orchestration history through the analytical-state commit. Modeled synthesis remains a last resort after direct-source avenues and exact derived matches are exhausted. Any change in population, comparison design, outcome definition, or modeling level must begin as an explicit new workstream rather than silently extending this checkpoint.

Canonical artifacts:

- `data/silver/study/pooled/portfolio-level-0-synthesis.json`
- `data/silver/study/pooled/portfolio-level-0-manifest.json`
- `data/silver/study/pooled/derived-parameter-screen.json`
- `data/silver/study/pooled/synthesis-reassessment.json`
- `data/silver/study/pooled/facility-year-exposures.json`
- `data/silver/study/pooled/county-year-exposures.json`
- `reports/private-sector-study/portfolio-level-0-synthesis-1.0.md`
- `reports/private-sector-study/orchestration-ledger.json`

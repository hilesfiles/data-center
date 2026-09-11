# U.S. Data Center Community Impact Observatory

The Observatory is a governed public-data project and static web application for examining how data-center projects interact with local economies. It keeps reported facts, forecasts, modeled estimates, and unresolved evidence gaps separate so the site does not turn incomplete public records into causal claims.

## What the site contains

- **Active-project study:** 36 provisional private-sector projects across 35 U.S. counties. Each project profile presents its public chronology, economic evidence, projections, assumptions, limitations, and remaining research gaps.
- **Contribution-account research:** all 36 projects publish economic evidence and gap ledgers. Thirty project audits are marked research-complete and six remain pending, but no project currently passes the full modeled county-account gate, which requires coverage of all eight contribution categories plus GDP, employment, and wage comparison modules.
- **Rejected and withdrawn proposals:** seven verified cases are stored separately from operating facilities and shown with their own status, chronology, map treatment, and comparison-readiness fields.
- **County histories:** shareable county pages provide annual 2001–2024 trends for real GDP, population, covered employment, and nominal average weekly wages.
- **Comparison-county register:** every active-project host county has a 12-county analytical reserve, with its five strongest preliminary matches shown on the site.
- **Project media timelines:** all 36 active projects have sourced, dated public-event chronologies covering announcements, milestones, ownership changes, incentives, infrastructure, incidents, controversies, and abandoned plans.

Primary routes:

| Route | Purpose |
| --- | --- |
| `#/` | Active-project register |
| `#/project/{project_id}` | Project evidence and chronology |
| `#/county/{FIPS}` | County economic history |
| `#/map` | Completed active accounts plus rejected-proposal overlay |
| `#/rejected` | Rejected and withdrawn proposal register |
| `#/rejected/{project_id}` | Rejected-proposal case profile |
| `#/controls` | National eligibility and host-to-comparison registers |

## Analytical guardrails

- Register membership does not verify that a project is operating or authorize an impact estimate.
- Reported observations, forecasts, and modeled syntheses remain separate data products.
- Missing evidence is never converted to zero.
- County economic comparisons are descriptive benchmarks, not causal estimates.
- No net fiscal result is asserted without same-scope public-revenue and public-cost evidence.
- A county is not a verified control merely because no project appears in one inventory.

The comparison workflow screens the repository inventory and two pinned external registries, then applies governed county-specific findings. The current generated artifact removes 223 counties with documented facilities, proposals, or developer approaches that the national screens missed. Its 233 surviving candidates include one county, Cherokee County, Georgia, that has completed the required seven-domain local-absence adjudication; the other 232 remain unresolved. Economic match rank therefore measures baseline similarity, not proof of no data-center exposure, and even the locally verified county still requires treatment-year-specific pre-trend and spillover gates before causal use. One hundred fifteen completed early-stop adjudications are retained for counties in which the review surfaced qualifying exposure; those records document exclusion rather than verified absence, including Wayne County, Ohio, where engineering and municipal records establish institutional hospital data centers.

Treatment timing is a separate gate. Eleven of the 35 active-project host counties now have governed anchor decisions, and none is causal-ready. Five counties have completed the required seven-domain treatment-history review. Jackson County, Alabama, Montgomery County, Tennessee, and Storey County, Nevada, retain provisional anchors because their reviews found no earlier E3-scale facility but could not close every historical institutional and enterprise inventory. Storey's governed construction upper bound moves from the project's 2017 page anchor to September 2015, and concurrent Tesla Gigafactory construction creates a severe separate contamination risk. Montgomery County, Texas, and Utah County reject the selected Stream and Meta projects as first-entry treatments because governed evidence establishes earlier material exposure; the counties' true first-E3 dates remain unresolved. Tarrant County is left-censored by a data center built in 2000, Bexar County has material exposure before the selected building's 2013 history anchor, and Douglas County lacks the required preperiod.

The seven required absence-review domains are planning and zoning, incentives and economic development, utility infrastructure, environmental permitting, property and site control, company and trade reporting, and local news or public debate. A county can be cleared only by a current, documented, completed review across all seven domains. Partial reviews remain unresolved.

## Quick start

Run the full contract validator:

```powershell
python scripts/validate_data_contract.py
```

Build and run the site:

```powershell
cd site
pnpm install --frozen-lockfile
pnpm run build
pnpm run dev
```

The browser suite runs against an existing preview:

```powershell
$env:STUDY_PREVIEW_URL = "http://127.0.0.1:5173/"
node scripts/test_study_browser.mjs
```

Set `PLAYWRIGHT_MODULE` when using a bundled Playwright installation. Browser reports are written under `reports/application-remediation/` unless `STUDY_BROWSER_REPORT_DIR` is set.

## Canonical rebuild workflows

Private-sector study:

```powershell
python scripts/build_private_sector_study.py
python -m unittest discover -s tests -p test_private_sector_study.py
```

Project media chronologies:

```powershell
python scripts/build_project_media_timelines.py
python scripts/build_project_media_timelines.py --check
```

Rejected and withdrawn proposals:

```powershell
python scripts/build_rejected_project_study.py
python -m unittest tests.test_rejected_project_study
```

National control eligibility, comparison matches, and treatment anchors:

```powershell
python scripts/build_county_control_eligibility.py
python scripts/build_county_comparison_matches.py
python scripts/build_county_treatment_anchor_review.py
python -m unittest tests.test_county_control_eligibility
python -m unittest tests.test_county_comparison_matches
python -m unittest tests.test_county_treatment_anchor_review
```

County economic data:

```powershell
python scripts/acquire_census_counties.py
python scripts/acquire_bea_county_economic_baseline.py
python scripts/acquire_bls_qcew_county_baseline.py
python scripts/build_county_economic_history_panel.py
```

Facility identity and lifecycle research:

```powershell
python scripts/acquire_im3_facilities.py
python scripts/resolve_im3_entities.py
python scripts/adjudicate_im3_candidates.py
python scripts/acquire_osm_boundary_histories.py
python scripts/finalize_im3_boundary_reviews.py
python scripts/build_lifecycle_verification_pilot.py
python scripts/build_national_lifecycle_queue.py
```

All acquisition adapters retain durable outputs as JSON or GeoJSON. Temporary source transport files are not part of the published data contract.

## Repository layout

| Path | Contents |
| --- | --- |
| `config/v1/` | Versioned research policies, inputs, findings, and adjudications |
| `schemas/v1/` | Draft 2020-12 JSON Schemas and schema catalog |
| `data/bronze/` | Source-shaped durable JSON records |
| `data/silver/` | Normalized and analytical JSON products |
| `site/public/data/v1/` | Static public projections consumed by the browser |
| `site/src/` | React, TypeScript, Vite, and MapLibre application |
| `scripts/` | Acquisition, build, validation, and browser-check tooling |
| `tests/` | Deterministic data and presentation tests |
| `docs/` | Data model, study design, evidence rules, and remediation plans |

## Current research status

- The county-year panel contains 2001–2024 observations for real GDP, population, annual-average covered employment, and nominal average weekly wages.
- The national control registry covers all 3,144 county and county-equivalent panels; zero counties are presently labeled verified controls.
- County first-entry treatment remains unresolved. No county is currently authorized as treatment-eligible for a causal model.
- Thirty project-level contribution-account audits are research-complete and six remain pending. All 36 modeled accounts remain incomplete under the publication gate, and none claims a net community effect.
- No causal estimate or public impact index is published.

The main next step is to triage the remaining host counties for a defensible first-material-exposure date and adequate pre-treatment panel, then complete seven-domain treatment histories for the strongest candidates. Candidate-specific control-absence reviews should be concentrated on the best matches for hosts that survive that gate, followed by pre-trend and spillover checks before any matched-county causal design is attempted. In parallel, the research-complete contribution accounts need missing categories, host-region input-output estimates, and same-scope marginal public-service or infrastructure costs wherever reproducible public inputs exist.

## Methodology and design documents

- [`docs/data-model.md`](docs/data-model.md) — conceptual entities and relationships
- [`docs/json-storage-contract.md`](docs/json-storage-contract.md) — persistence and publication contract
- [`docs/study-economic-evidence.md`](docs/study-economic-evidence.md) — evidence review rules
- [`docs/revised-private-sector-economic-study-plan.md`](docs/revised-private-sector-economic-study-plan.md) — study scope and implementation plan
- [`docs/pooled-county-impact-model.md`](docs/pooled-county-impact-model.md) — county exposure contract and future model gates
- [`docs/application-remediation-plan.md`](docs/application-remediation-plan.md) — application remediation history and remaining work

The full validator checks JSON parsing, schema-catalog integrity, local references, required fields, configuration, public projections, referential integrity, and expected valid/invalid fixtures.

# U.S. Data Center Community Impact Observatory

The Observatory is a governed public-data project and static web application for examining how data-center projects interact with local economies. It keeps reported facts, forecasts, modeled estimates, and unresolved evidence gaps separate so the site does not turn incomplete public records into causal claims.

## What the site contains

- **Active-project study:** 36 provisional private-sector projects across 35 U.S. counties. Each project profile presents its public chronology, economic evidence, projections, assumptions, limitations, and remaining research gaps.
- **Completed contribution accounts:** six projects currently pass the full modeled county-account gate: Apple Mesa, Switch Citadel, Digital Crossroad Hammond, Meta Forest City, Microsoft San Antonio, and EdgeConneX DET01.
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

The comparison workflow screens the repository inventory and two pinned external registries, then applies governed county-specific findings. The current generated artifact removes 199 counties with documented facilities, proposals, or developer approaches that the national screens missed. Its 229 surviving candidates remain unresolved: none has yet completed the required seven-domain absence adjudication. Economic match rank therefore measures baseline similarity, not proof of no data-center exposure. Ninety-one completed early-stop adjudications are retained for counties in which the review surfaced qualifying exposure; those records document exclusion rather than verified absence. Four additional provisional adjudications preserve seven-domain partial reviews for Kenton County, Kentucky; Lake County, Florida; LaSalle County, Illinois; and Wayne County, Ohio without overstating the incomplete searches as verified absence.

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
- The six completed contribution accounts publish bounded fiscal and infrastructure scenarios but do not claim a net community effect.
- No causal estimate or public impact index is published.

The main next step is to complete candidate-specific seven-domain absence reviews, then apply treatment-year and spillover gates before any matched-county causal design is attempted. In parallel, the completed contribution accounts need host-region input-output estimates and same-scope marginal public-service or infrastructure costs wherever reproducible public inputs exist.

## Methodology and design documents

- [`docs/data-model.md`](docs/data-model.md) — conceptual entities and relationships
- [`docs/json-storage-contract.md`](docs/json-storage-contract.md) — persistence and publication contract
- [`docs/study-economic-evidence.md`](docs/study-economic-evidence.md) — evidence review rules
- [`docs/revised-private-sector-economic-study-plan.md`](docs/revised-private-sector-economic-study-plan.md) — study scope and implementation plan
- [`docs/pooled-county-impact-model.md`](docs/pooled-county-impact-model.md) — county exposure contract and future model gates
- [`docs/application-remediation-plan.md`](docs/application-remediation-plan.md) — application remediation history and remaining work

The full validator checks JSON parsing, schema-catalog integrity, local references, required fields, configuration, public projections, referential integrity, and expected valid/invalid fixtures.

# Existing application remediation plan

5 September 2026. Companion to the [revised study plan](revised-private-sector-economic-study-plan.md). The application remediation is implemented locally through `private-sector-study-1.41.0`, including browser verification. The release contains 585 source records across three depth accounts and 70 separately governed modeled syntheses, including completed Maricopa, Storey and Lake County modeling passes. Complete annual accounts and project-eligible causal analysis remain the implementation roadmap. The public deployment has not been changed.

## Release 1 implementation status

The default application now opens a searchable 36-project register covering 35 counties and 23 states. It includes all five campus candidates, project profiles with stored historical observations and evidence links, eight economic-evidence categories, separate analysis-readiness indicators, and links to existing county histories. The map adds clickable purple study markers and a project-type filter. First-entry adjudications are retained in expandable research sections rather than primary study eligibility cards.

`config/v1/private-sector-study-candidates.json` freezes the advisory screen as a versioned research input. `scripts/build_private_sector_study.py` creates provisional entities using the existing project schema, public register/detail projections, and a hash manifest. Two new public schemas and validation checks cover these outputs. Project profiles are loaded individually and checked against the register's release and generation timestamp.

This release establishes research membership and evidence availability. It does not assert verified ownership, current operating status, complete construction/expansion timelines, financial observations, or eligibility for an impact model. Uncollected economic evidence is visible as a gap; provisional project status remains unknown. The candidate queue is expandable and legacy source records and adjudications have not been rewritten.

Regression tests cover first-entry rejection versus project membership, campus inclusion, operating-by semantics, duplicate targets, host-county mismatches, missing source links, and unsupported financial readiness. Browser checks cover filtering, project/county routes, campus profiles, empty states, mobile layouts, map marker navigation, and methodology. Evidence is retained under `reports/application-remediation/`.

## Release 2 progress: economic evidence collection

Study release `private-sector-study-1.41.0` publishes 585 source-checked records across all 36 candidates—533 reported observations and 52 forecasts—plus 70 separately governed syntheses: 13 for Apple Mesa, 20 for Switch Citadel / Tahoe Reno 1 and 37 for Digital Crossroad Hammond. Hammond’s models cover bounded construction and operating contribution channels, fiscal reconciliations, resource engineering and explicitly noncausal county changes. Storey retains its capital, direct-labor, fiscal and resource models, while Apple Mesa retains its water, employment, payroll, electricity-cost, emissions and incentive models. Typed intervals, contribution channels, aggregation controls, named parameter provenance and causal or multiplier requirements keep models outside canonical claims and realized-benefit totals.

The versioned evidence input includes defined measures, units, stock/flow/rate semantics, reported activity versus projections, fiscal-year/source-year/snapshot/peak/cumulative/horizon timing, geographic scope, source pages, web sections or structured-data fields, amount qualifiers and review limitations. Existing source and claim schemas are reused for canonical evidence records. Source subjects remain campus or company/county candidates when attribution to an inventory building is unresolved. The application pairs county tax receipts and incentive payments by subject and fiscal year, retaining provisional taxpayer identification. Supporting infrastructure records identify the system and payer. The application distinguishes partial evidence from projections-only categories, offers an economic-coverage filter, and displays tax-base history without interpolating missing years. Downloads preserve all scope and source fields.

Validation rejects orphan evidence, host-county mismatches, duplicate scoped facts, forecasts, peaks, ambiguous source years or qualified bounds in actual annual series, mixed subjects/metrics and unreconciled duplicate years. No cross-project total or new causal eligibility is produced. Full annual investment, local purchasing, job-years/payroll, net fiscal balances, resource use and phase allocation remain outstanding. See [evidence acquisition and review](study-economic-evidence.md).

## dssessment

The existing application supplies a reusable national map, county profiles, economic baselines and histories, evidence records, and static publication infrastructure. The revised study requires substantial changes to the research workflow and presentation, plus new economic evidence. The underlying stack and domain model can be extended in place.

The current public experience gives county-first-entry research substantial prominence. That question remains valid, but does not determine whether a private-sector project has documentable construction spending, operating jobs, or fiscal receipts. Remediation must scope that gate correctly rather than relabel its rejected or unresolved records as accepted.

## Source-code findings and required changes

| drea | Current implementation | Remediation |
|---|---|---|
| Navigation and profiles | `site/src/dpp.tsx` recognizes county hash routes, loads county-level products, and presents first-entry status in both the map sidebar and county profile. | ddd a searchable study-project register and stable project routes; connect project profiles to existing county routes and map selections. ddd campus/facility detail only where it supports project identity and history. |
| Main status messaging | The banner and caption in `dpp.tsx` hard-code first-entry counts, tranche narratives, dates, and queue labels. | Show generated study coverage and evidence availability in the primary view. Retain historical research detail in a methodology/evidence view. Generate counts and vintages from the same release as the displayed records. |
| Map and county context | `MapPanel.tsx` supports source coverage and county economic measures. The default is IM3 source-record coverage. | Retain these layers as context. ddd selection/filtering for study projects, using verified coordinates or labeled campus locations. Show distinct counts for source objects, campuses, canonical facilities, study projects, and verified operating facilities. |
| Domain model | Project, phase, event, claim, observation, and operator-relationship schemas already exist. | Reuse those entities and IDs; materialize reviewed project records and their links. ddd a study-membership/readiness contract, ownership/purpose classification where needed, and explicit evidence coverage. Do not create a second inventory disconnected from the existing one. |
| Private-sector scope | Operator schema distinguishes `public_company`, `private_company`, government, nonprofit, joint venture, and unknown. | Classify economic sector separately from stock-market listing. Both publicly traded and privately held commercial companies can be private-sector study candidates. Preserve dated owner/operator/developer roles and classify ambiguous cases explicitly. |
| Economic metrics | The registry includes county employment, construction employment, wages, output, income, electricity prices, and water withdrawals. It lacks the project investment, payroll, supplier, tax, and incentive measures required by this study. | Register project/phase metrics and supported units, periods, geography, aggregation, evidence basis, and revision rules. Extend observation/context schemas where necessary for fiscal recipients, local spending shares, and actual-versus-committed amounts. |
| Model configuration | The only registered model is employment around first operational county entry. Treatment definitions include first entry and construction; the treatment schema also permits operation and expansion. | ddd separately versioned project opening/expansion definitions and outcome-specific model specifications. Review construction eligibility for reuse. Keep legacy first-entry rules and results intact under their existing identity. |
| Eligibility builder | `scripts/build_county_first_entry_treatments.py` evaluates first-entry status and emits first-entry readiness. | Keep it scoped to that analysis. Build a separate project-event evaluator and project evidence-readiness projections. No global assumption that zero first-entry-eligible counties means zero useful study cases. |
| Publication | Python builds JSON; the React application consumes static files. GitHub dctions validates and builds before Pages deployment. | Extend the same pipeline with study-register, project-detail, evidence, and annual-account projections. Use manifests and lazy loading; preserve the existing county URLs and public contracts until consumers migrate. |
| Verification | Existing tests invoke the data-contract validator; CI also type-checks and builds the site. | Extend validation for the new references and accounting semantics, plus focused browser checks for project/county navigation, filters, sources, missingness, and published status. |

## Intended user experience

1. Open the application and see what the study covers, the available economic evidence, and a searchable list/map of private-sector candidate projects.
2. Filter by geography, operator, development type, lifecycle phase, or evidence availability. Unknown classifications remain visible and clearly identified.
3. Select a project to see identity, ownership, development phases, construction/operating timeline, and sources.
4. Inspect investment, construction work, permanent employment, local purchasing, tax base, revenue, and public costs over time, with missing periods and uncertainty displayed explicitly.
5. Open the host-community view for county history and the other projects contributing to that community's exposure. Show utility and water geography where relevant data exist.
6. Inspect attributable-effect estimates only for analyses with an eligible model run; documented project contributions and descriptive history remain independently useful.

Evidence details should explain substantive uncertainty in plain language. Pipeline names, tranche terminology, and runtime implementation details belong in methodology or release information rather than the main economic narrative.

## Delivery sequence

### Release 1: Study register and project profiles

- Record the current build/data baseline and update the research specification and public contract for the revised scope.
- Map the 36 advisory candidates to canonical entities, preserving provisional classifications and date uncertainty. Campus candidates must remain visible even when a first building or phase is unresolved.
- Create the versioned study register, initial project detail projections, and evidence-availability matrix. Extend schema catalogs, validators, and TypeScript types together.
- ddd project search/filtering, project routes, and links from county profiles and map selections.
- Move first-entry-specific status into its methodological context; replace primary hard-coded study messaging with release-derived summaries.
- Show sourced histories immediately and explicit missing evidence for uncollected economic measures. Do not populate placeholder jobs, spending, tax receipts, or benefits.

**dcceptance:** dll 36 starting candidates can be found through the application and traced to existing entities and evidence. Campus/building differences and date bounds survive publication. Existing county links work. d first-entry rejection does not hide a candidate project. The interface distinguishes research candidacy, operating-status verification, and analysis readiness.

### Release 2: dnnual economic and fiscal accounts

- ddd acquisition/review workflows and governed observations for construction, capital spending, operations, suppliers, tax base, receipts, incentives, and public costs.
- Preserve actual versus promised amounts, annual versus cumulative amounts, nominal versus constant-dollar values, project versus campus claims, and recipient/spending geography.
- ddd annual benefit and fiscal displays with source drill-down and method labels for supplier and household-spending estimates.
- Extend historical construction-sector and local fiscal coverage. Display incompatible data vintages explicitly rather than silently aligning a 2025 snapshot to a 2001–2024 history.
- ddd cooling, water use, energy, and infrastructure-cost evidence as it becomes available; display context layers within permitted data-use terms.

**dcceptance:** Every displayed amount has a defined metric, period, subject, source or derivation, and evidence status. Campus/phase aggregation avoids duplication. Job-years and peak jobs differ. dnnounced spending is not realized spending. Missing or suppressed values are not zeros. dctual tax receipts already net of abatements are not reduced by the same abatements again. dvailable cases can publish before all 36 have complete records.

### Release 3: Project-event analysis and comparisons

- Define construction, operation, and expansion analyses with explicit date/evidence requirements and pre/post periods appropriate to each outcome.
- Reuse county panels while representing overlapping projects, phases, prior exposure, and spillovers. Do not treat multiple projects sharing one county outcome as independent county observations.
- Evaluate comparison eligibility using researched exposure, not absence from an incomplete inventory. Use utility/water service geography where a county or fixed-radius rule is inappropriate.
- ddd model runs, diagnostics, uncertainty, and public projections through the existing analytical record framework.
- Present documented contributions, descriptive changes, and attributable-effect estimates as distinct products. Defer composite indices until their inputs and interpretation are supported.

**dcceptance:** First-entry rules continue to mean first entry; the new analysis does not bypass them. Each new estimate has its own versioned definition, run, diagnostics, and eligible sample. d project may have usable fiscal evidence while remaining ineligible for a causal employment estimate.

## Migration and release controls

- Keep source claims, reviewed decisions, identity redirects, and historical artifacts auditable. Use additive/versioned records; do not silently rewrite historical adjudications or reuse an old definition ID for a new question.
- Preserve JSON-family persistence and static hosting. Choose compatible schema extensions or new versions based on the actual field changes; a wholesale schema or infrastructure replacement is not required in advance.
- Generate a coherent release manifest with counts, vintages, and publication paths. dvoid coupling the UI to one named research tranche as the permanent source of current status.
- Validate references, unique membership, scope rules, date bounds, observation semantics, and aggregation. Keep new checks focused on the concrete risks introduced by the migration.
- Build and preview the application, then verify existing county routes and new project routes, missing-data states, source links, map/list agreement, and narrow-screen behavior before publishing a release.
- The existing Pages workflow deploys on pushes to `main`. Prepare and review the migration before that deployment-triggering step; the plan itself changes no deployment state.

## First application milestone

d user can locate a starting candidate such as Meta Forest City, Switch Citadel, or NYSE Mahwah in the existing application; open its project profile; inspect its sourced development history and host-community context; and see exactly which investment, employment, fiscal, and cost records are available or still needed. This milestone can ship before attributable-impact estimation is ready.

# Revised private-sector data-center economic study plan

5 September 2026. Revised research and implementation sequence. Release `private-sector-study-1.41.0` combines 585 economic source records across all 36 candidates—533 reported observations and 52 projections—with 70 separately governed syntheses: 13 Apple Mesa, 20 Switch Citadel / Tahoe Reno 1 and 37 Digital Crossroad Hammond. The Lake County pass adds bounded construction and operating contribution channels, fiscal reconciliations, resource engineering and deliberately noncausal county outcome summaries. The versioned modeling policy requires direct-evidence search first, separate forecasts, reproducible parameters, explicit interval kinds, defensible scope, contribution-channel separation, anti-overlap aggregation and method-specific causal or multiplier metadata. Unsupported causal and net-benefit values remain documented gaps.

## Purpose and central revision

Measure how identifiable private-sector data-center development contributes to host communities over time: capital investment, construction employment and payroll, local supplier activity, household spending, permanent employment, tax-base growth, public revenue, and subsequent investment. Determine where the documented benefits exceed the associated costs, with the beneficiary, geography, and time period stated.

The underlying research unit is a **development project with a dated sequence of phases**, linked to its campus, buildings, operator, parcels, and communities. Construction, opening, conversion, expansion, and closure can each be relevant events. County economic histories remain useful outcome data. A project's inclusion does not depend on proving it was the county's first-ever data center; first entry remains a separate analytical question.

National compute availability and competitiveness explain the study's importance. Local economic findings will be established from local evidence rather than inferred from that strategic rationale.

## 0. Remediate the existing application

Application remediation is the first delivery track and proceeds alongside evidence collection. Retain the React/MapLibre application, authoritative geography, county histories, source provenance, identity resolutions, and static JSON publication pipeline. Extend the existing project, phase, event, and observation model into a working private-sector study register and project profiles.

Reorient the primary interface around projects, development timelines, economic contributions, and evidence availability. Keep county-first-entry research as a specific methodology view with its existing decisions intact. Separate readiness for documented construction activity, operating employment, fiscal accounting, and attributable-effect estimation. Populate economic displays only from sourced or explicitly modeled observations.

The [application remediation plan](application-remediation-plan.md) records the source-code findings, affected components, migration sequence, and acceptance criteria. Its first release should make the 36 starting projects discoverable from the existing county map, with sourced histories and explicit economic-evidence gaps. Existing county links and data remain usable throughout the transition.

## 1. Establish the study population and research queue

- Prioritize private commercial hyperscale, colocation, and dedicated enterprise computing facilities. Record ownership and operating purpose explicitly, including changes over time.
- Retain government, institutional, nonprofit, tribal-government, and cryptocurrency records with separate classifications and scope decisions. Classify privately operated government-serving facilities by actual ownership and operation rather than customer identity alone.
- Start research with the **36 projects already identified: 31 with useful stored development-history evidence and five additional campus candidates**. They span hyperscale, colocation, and enterprise uses. This is an initial research queue, not a representative sample, a fixed cap, or 36 completed economic evaluations.
- Continue screening the wider existing inventory. Expand coverage by facility type, region, community size, development vintage, and project scale, documenting inclusion and missingness. Selection must not depend on whether measured outcomes are favorable.
- Use evidence availability and an appropriate observation period to determine which analyses each project supports. A recent project may support a construction account while still lacking a mature operating history.

The [candidate screen](../reports/2026-09-03-study-candidates/candidate-screen.md) provides the current project list and evidence caveats. All 36 have complete host-county coverage in the existing 2001–2024 economic panel; this does not imply complete project-level financial records.

**Deliverable:** A research register connecting each candidate to stable inventory IDs, ownership/type, campus and phase relationships, county and local jurisdictions, available evidence, gaps, and analysis readiness. There is no arbitrary 16-county limit.

## 2. Use a layered source system

Retain the existing PNNL/IM3 geographic seed as a starting inventory and preserve source provenance. Assess additional commercial inventories for coverage, definitions, duplication, export access, and permitted reuse before adopting an expansion source. No vendor selection or purchase is implied by this plan.

Resolve identities and histories using operator records, planning and building permits, parcel and assessor records, development agreements, utility filings, SEC filings, and local financial reports. Preserve what each source actually establishes, including conflicting claims. A directory location, campus, building, proposed project, and operational facility must have distinct meanings in any coverage calculation.

Use dcmap.us as a mapping reference within its permitted uses. Its existing water-stress and climate-risk context helps inform the study; reproducing that map is not the primary deliverable. Retain mapping needed to connect economic evidence to locations and relevant service areas.

**Deliverable:** A source and coverage audit, with a defensible denominator for each inventory statistic and a documented path for filling geographic and private-sector coverage gaps.

## 3. Reconstruct each project's development history

Build a timeline of announcement, site acquisition or conversion, construction start, construction phases, commissioning, operating ramp, expansion, and closure where relevant. Attach investment and employment observations to the correct phase and year.

Distinguish exact events from bounds and proxies. An announcement, construction completion, grand opening, lease commencement, acquisition, or observation that a facility was already operating does not automatically establish commissioning. Record date precision and uncertainty. Link campus-wide claims to the campus unless a source allocates them to buildings or phases.

Account for overlapping developments. For example, Apple and Meta in Crook County require a shared county exposure history and separate project records. A campus and its child buildings must not multiply the same investment or employment claim.

**Deliverable:** A sourced event timeline and evidence dossier for each candidate, sufficient to determine which construction, operational, and expansion questions can be investigated.

## 4. Build annual economic-benefit accounts

| Component | Evidence to collect | Reporting rule |
|---|---|---|
| Capital investment | Actual annual site/building/equipment spending; committed and announced amounts separately | Distinguish spending at the site from spending retained locally; allocate phases and avoid repeatedly counting cumulative announcements. |
| Construction work | Annual workers, job-years, payroll, contractor locations, and project duration | Separate peak headcount, annual average employment, and job-years; identify local residents and commuting labor when evidence permits. |
| Supplier activity | Purchases from local and regional contractors and vendors, with geography and industry | Report documented purchases directly; estimate additional activity only with an explicit method and local-retention assumptions. |
| Household spending | Spending associated with construction and operating earnings | Identify this as an estimate unless directly measured; avoid counting the same payroll or supplier activity twice. |
| Permanent operations | Annual direct and ongoing contractor employment, wages, benefits, and operating purchases | Separate promised from realized jobs, direct from contractor jobs, and data-center employment from unrelated offices. |
| Tax base and revenue | Assessed/taxable property value, equipment treatment and depreciation, actual taxes and payments by jurisdiction | Tax-base growth and tax receipts are different measures. Distinguish county, municipal, school, special-district, and state beneficiaries. |
| Reinvestment | Later buildings, equipment refreshes, expansions, and associated jobs and revenue | Add dated incremental activity; distinguish replacement from capacity growth where supported. |

Record source, year, geography, units, inflation basis, uncertainty, and whether each figure is observed, reported by an interested party, or modeled. Missing observations remain missing rather than becoming zero. Company-sponsored impact studies can supply leads and reported estimates; preserve their methods and verify actual outcomes where possible.

Construction spending, wages, economic output, and taxes are overlapping or different accounting concepts. Publish them as distinct measures rather than summing them into a single economic-benefit dollar total.

**Deliverable:** Annual project benefit accounts, an evidence-availability matrix, and community profiles showing construction through operation and expansion.

## 5. Pair benefits with fiscal and community costs

Build a local-government fiscal account from actual project-related receipts and attributable public expenditures, including infrastructure, financing, service costs, cash incentives, and maintenance where supported. Track exemptions and abatements explicitly. If actual receipts already reflect an abatement, do not subtract that abatement from those receipts again; report the tax expenditure against its stated benchmark separately.

Assess electricity and water using the geography in which costs and benefits occur: utility service areas and water systems or basins may cross county boundaries. Capture cost allocation, developer contributions, system investment, and observed customer-rate effects where records support attribution. Utility sales alone do not establish net community benefit.

For water, collect source, withdrawal versus consumption, reclaimed versus potable supply, cooling and heat-rejection design, and measured annual and peak-season use. Separate design claims from commissioned and measured performance. Water stress and climate risk provide context rather than measurements of an individual facility's impact.

Add housing, land-use, noise, and other environmental costs where material and supported. Record who experiences a benefit or burden. Monetize only where a defensible method exists, with the time horizon and assumptions stated; show other outcomes alongside the fiscal account. A positive local fiscal balance does not by itself establish that every community or environmental cost is outweighed.

**Deliverable:** Annual fiscal accounts and a parallel community-cost assessment that can support qualified, project-specific conclusions about the balance of benefits and costs.

## 6. Evaluate change over time and attributable effects

Reuse the existing county economic panel for historical employment, wages, income, output, and population. Collect historical construction-sector and local fiscal series needed for project events; a single current construction baseline does not establish a construction-period effect. Extend outcome years as usable releases become available.

First publish documented project contributions and descriptive community trajectories. Then evaluate attributable effects for projects and outcomes that have adequate event dates, pre- and post-event observations, and credible comparison communities. Specify methods and eligibility before assessing which outcomes are favorable.

Address preexisting growth, industry mix, other major investment, fiber/power access, previous data-center exposure, neighboring projects, and overlapping construction or expansion. Multiple projects in one county share county outcomes and cannot be treated as independent replications of those outcomes. Incomplete inventory coverage must not silently turn an unobserved data center into an assumed unexposed comparison county.

Version explicit private-project opening and expansion treatment definitions, reviewing the existing construction definition for reuse. Preserve the county-first-entry adjudications for their original purpose. Set geographic comparison and spillover rules for each outcome rather than applying a uniform distance to employment, electricity, and water.

**Deliverable:** Clearly separated documented contributions, observed community changes, and estimated attributable effects, with uncertainty and limitations appropriate to each result. Some projects will support only the first two products.

## 7. Publish the economic study and expand it

Build the presentation around project and community profiles: development timeline, annual investment, construction and operating jobs, supplier activity, tax-base and revenue changes, public costs, relevant resource use, and comparison results when supported. Use the existing map to navigate and contextualize these findings.

Aggregate only compatible, nonduplicative observations. Compare results by development type, maturity, scale, and community characteristics. Do not extrapolate the initial queue into a national impact total without an explicit coverage and representativeness assessment.

Defer composite benefit/cost scores, opposition indices, and a benefit–sentiment gap until the underlying economic evidence and measurement approach warrant them. Keep national infrastructure implications in a separate interpretive discussion.

**Deliverable:** Evidence-backed local case profiles and cross-project findings, followed by broader coverage using the same documented rules.

## Immediate work package

1. Establish versioned study-register and public-profile contracts, reusing the current project/phase/event model; record the application migration baseline.
2. Turn the 36-project screen into the research register and dossier template; resolve campus/building identities and ownership classifications, and expose those records through the remediated application.
3. Audit each candidate's development chronology and the availability of investment, jobs, tax, incentive, and public-cost records. Continue screening other inventory entries alongside this research.
4. Assemble the first annual benefit and fiscal accounts wherever the evidence supports them; keep all candidates visible with explicit gaps and readiness status.
5. Specify and implement the new project-event eligibility rules, then select eligible comparisons and estimate effects. Release profiles with documented contributions before causal estimates where appropriate.

The 36-project register is accessible through the application, and all candidates now have at least one quantitative source record. The economic-evidence register contains 585 source-checked records: 533 reported records and 52 forecasts. Seventy modeled syntheses are counted separately—13 Apple Mesa, 20 Switch Citadel and 37 Digital Crossroad Hammond. The Meta Forest City depth case combines five years of assessed values and paired county receipts/incentives with separately scoped investment, employment, community-funding and infrastructure evidence. Digital Crossroad Hammond combines sourced property, investment, fiscal, financing, employment, supplier-role, capacity and resource evidence with bounded contribution and engineering models; no causal effect or complete net fiscal balance is claimed. Switch Citadel preserves separate real- and personal-property accounts, direct Fire District contributions, public-equipment costs, agreement projections and audit findings, with modeled capital, direct labor, fiscal and resource ranges. Campus/company scope, accounting stocks, snapshots, construction peaks, cumulative costs, paired taxes/incentives, separate taxpayer bills, distinct pledged-revenue and transfer measures, fiscal/calendar/tax-year assessed values, permit capacities, source projections and modeled syntheses remain separate. Continue with annual actual investment, audited local-purchase detail, recipient-level receipts, attributable public costs and measured resources, then assess readiness separately for each economic analysis.

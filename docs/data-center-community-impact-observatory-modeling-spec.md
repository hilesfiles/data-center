# Data Center Community Impact Observatory
## Full Statistical Modeling, Econometric, Indexing, and National Mapping Specification

**Document purpose:** This document is the modeling and analytical-methodology companion to the project bootstrap specification. It instructs a local Codex agent how to construct, validate, model, score, and publish a national public-data system that measures the economic benefits, fiscal effects, community costs, and opposition dynamics associated with U.S. data-center development.

**Primary deployment target:** Static interactive application published through GitHub Pages, with all computationally intensive ingestion, data engineering, statistical estimation, uncertainty analysis, and model generation performed offline/local or in GitHub Actions. The deployed site must consume precomputed static artifacts rather than run econometric models in-browser.

**Geographic focus:** United States.

**Historical target:** 2000-present for the canonical data-center project/facility/event history where feasible, with longer historical baselines used for economic variables when public sources support them.

**Primary unit of causal analysis:** County-year, with county-quarter used for outcomes that support reliable quarterly frequency. Facility/project/event records are the underlying treatment-generating data model.

**Core requirement:** Never equate correlation with causal impact. Every map layer, score, chart, statistic, and narrative must clearly distinguish:

1. observed conditions,
2. observed changes,
3. modeled counterfactual differences,
4. quasi-causal estimates,
5. perception/opposition indicators, and
6. data-quality/confidence measures.

---

# 1. Mission

Build a reproducible national research system that answers five separate questions:

1. **Where and when were data centers proposed, approved, constructed, opened, expanded, cancelled, or closed?**
2. **What measurable economic and fiscal changes followed data-center development relative to plausible counterfactuals?**
3. **What measurable community costs or burdens followed development?**
4. **How has local, regional, state, and national opposition changed over time?**
5. **Where do measurable benefits, measurable costs, and public sentiment diverge?**

The system must support both national overview and local drill-down.

The final application should function as a **U.S. Data Center Community Impact Observatory** rather than merely an anti-data-center sentiment tracker.

---

# 2. Core Analytical Products

The system should ultimately publish at least the following independent products.

## 2.1 Canonical Data Center Historical Panel

A provenance-tracked database of facilities, projects, phases, events, operators, source claims, and locations.

## 2.2 Observed Economic Momentum

A descriptive layer measuring how county economic indicators are actually changing. This layer is not causal.

Suggested label:

**OEM — Observed Economic Momentum**

## 2.3 Data Center Economic Dividend

A quasi-causal layer estimating how economic outcomes differ from an appropriate counterfactual.

Suggested label:

**DCEDI — Data Center Economic Dividend Index**

## 2.4 Data Center Fiscal Dividend

A separate fiscal-effect layer focused on tax base, local public revenue, effective residential tax pressure, and net local-government fiscal effects.

Suggested label:

**DCFDi — Data Center Fiscal Dividend Index**

## 2.5 Data Center Community Cost

A burden/cost layer covering energy, water, housing affordability, land/infrastructure pressure, environmental burden where measurable, and related community effects.

Suggested label:

**DCCCI — Data Center Community Cost Index**

## 2.6 Data Center Opposition

A sentiment/mobilization/political-resistance layer measuring public opposition independently from actual economic outcomes.

Suggested label:

**DCOI — Data Center Opposition Index**

## 2.7 Benefit–Sentiment Gap

A derived measure comparing modeled economic dividend with public opposition.

\[
BSG_i = DCEDI_i - DCOI_i
\]

A positive value means modeled economic benefits are high relative to opposition. A negative value means opposition exceeds the measured economic dividend.

## 2.8 Net Community Balance

A derived measure comparing modeled economic benefit with modeled community cost.

\[
NCB_i = DCEDI_i - DCCCI_i
\]

Do **not** include opposition in this welfare-style balance. Opposition is perception/political behavior, not itself a direct economic cost.

---

# 3. Modeling Principles

Codex must implement the following principles as hard constraints.

## 3.1 Treatment is not a single binary variable

Data-center development occurs in phases:

- project announced,
- land acquired,
- zoning filed,
- zoning approved,
- permit issued,
- construction started,
- facility energized,
- facility operational,
- expansion announced,
- expansion constructed,
- expansion operational,
- project cancelled or withdrawn,
- facility closed.

Economic effects may differ sharply by phase.

## 3.2 Construction and operations must be modeled separately

Construction can create a strong temporary employment and spending shock. Operations can create a smaller permanent employment footprint but a large persistent tax-base, utility-load, and capital-stock effect.

The model must therefore estimate at least:

- construction-phase effect,
- post-operational effect,
- expansion effect.

## 3.3 Use denominators

Raw counts are often misleading.

Examples:

\[
OppositionIncidence_{c,t} = \frac{ProjectsFacingOrganizedOpposition_{c,t}}{ProjectsProposed_{c,t}}
\]

\[
ProjectResistanceRate_{c,t} = \frac{Blocked + Delayed + Withdrawn}{ProjectsFacingOpposition}
\]

\[
OppositionPerMW_{c,t} = \frac{OppositionEvents_{c,t}}{ProposedMW_{c,t}}
\]

Where MW is unavailable, use project count or square footage and expose the denominator used.

## 3.4 Preserve raw and modeled values separately

Never overwrite raw public data with modeled estimates.

For every modeled output preserve:

- source value,
- transformed value,
- model specification,
- estimate,
- standard error,
- confidence interval,
- sample size,
- data-quality score,
- model version.

## 3.5 Every material fact must be traceable

The facility/event dataset must be claim-based and provenance-preserving.

The system should be able to answer:

> Why does the database say this project became operational in 2017?

and return the supporting primary/secondary source claims.

## 3.6 Avoid post-treatment control bias

Do not control for variables that may themselves be caused by the data center when estimating the data center's effect.

Example: if employment composition changes after treatment, post-treatment employment composition should not be used as a contemporaneous matching/control variable for the causal effect.

Use pre-treatment covariates for matching and baseline adjustment.

## 3.7 Avoid naive two-way fixed-effects estimates under staggered treatment

Because counties receive treatment in different years and effects may vary by cohort/time, do not rely on a plain TWFE event-study as the headline causal estimate.

Implement a staggered-treatment estimator robust to heterogeneous treatment effects, such as a Callaway–Sant'Anna-style group-time ATT or Sun–Abraham-style interaction-weighted event study.

A conventional TWFE result may be shown only as a robustness comparison.

---

# 4. Canonical Data Model

The raw analytical spine should be relational, even if public releases include flattened Parquet/CSV views.

## 4.1 `facility`

One canonical physical location/campus/building asset.

Minimum fields:

```text
facility_id
canonical_name
campus_id
latitude
longitude
address
city
county_fips
county_name
state_fips
state_abbr
parcel_id
current_status
first_known_date
last_known_date
geometry_source
location_confidence
```

Do not use operator as the facility primary key.

## 4.2 `project`

A project or development phase attached to a facility/campus.

```text
project_id
facility_id
project_name
project_alias
project_type
announced_capex_usd
announced_mw
announced_sqft
announced_jobs
status
```

## 4.3 `event`

Historical lifecycle events.

```text
event_id
project_id
facility_id
event_type
event_date
event_year
event_date_precision
source_resolution_status
```

Allow event types including:

```text
PROPOSED
LAND_ACQUIRED
ANNOUNCED
ZONING_FILED
ZONING_APPROVED
PERMIT_ISSUED
CONSTRUCTION_STARTED
ENERGIZED
OPERATIONAL
EXPANSION_ANNOUNCED
EXPANSION_CONSTRUCTION_STARTED
EXPANSION_OPERATIONAL
SOLD
ACQUIRED
OPERATOR_CHANGED
MORATORIUM
LEGAL_CHALLENGE
DELAYED
WITHDRAWN
REJECTED
CANCELLED
CLOSED
```

## 4.4 `operator`

```text
operator_id
canonical_name
parent_company
public_private
former_names
```

## 4.5 `facility_operator_history`

```text
facility_id
operator_id
start_date
end_date
relationship_type
source_id
```

## 4.6 `source`

```text
source_id
source_type
publisher
title
url
archive_url
publication_date
retrieved_at
document_hash
license_class
redistribution_notes
```

## 4.7 `claim`

Every extracted assertion.

```text
claim_id
entity_type
entity_id
attribute
value_numeric
value_text
unit
source_id
source_excerpt_reference
extraction_method
extraction_model_version
confidence_score
review_status
created_at
```

The LLM/extractor is not the authority. It identifies what a source claims.

## 4.8 `claim_resolution`

```text
entity_type
entity_id
attribute
resolved_value
resolved_unit
resolution_method
resolution_confidence
winning_claim_id
supporting_claim_count
conflicting_claim_count
resolved_at
model_version
```

## 4.9 `county_year`

This is the principal national analytical panel.

```text
county_fips
year
population
employment_total
wage_total
avg_weekly_wage
gdp_real
gdp_nominal
personal_income
agi
business_establishments
business_births
business_deaths
in_migrants
out_migrants
house_price_index
local_revenue
local_property_tax_revenue
residential_tax_rate
industrial_electricity_price
commercial_electricity_price
industrial_mwh
commercial_mwh
...controls...
...treatment variables...
...modeled outputs...
```

Maintain quarterly equivalents in a separate `county_quarter` table where source data support them.

---

# 5. Historical Facility Reconstruction

The data-center panel is the hardest part of the project. Construct it in two complementary passes.

## 5.1 Reverse reconstruction

Start from a current public facility inventory, such as the DOE/PNNL open-source atlas, and reconstruct each existing facility backward.

For every facility search for:

- opening date,
- first announcement,
- construction start,
- zoning action,
- permits,
- prior operator,
- prior facility name,
- expansions,
- capex,
- MW,
- square footage,
- tax agreements,
- incentive agreements.

## 5.2 Forward discovery

Beginning approximately in 2000, discover projects prospectively from historical public sources.

This pass is required to capture survivorship failures:

- rejected projects,
- withdrawn projects,
- abandoned projects,
- cancelled projects,
- closed facilities,
- facilities that changed names/operators,
- developments that never became operational.

These records are especially important for opposition analysis.

---

# 6. Public Evidence Acquisition

Use multiple sources because no single public archive is complete.

## 6.1 News archives

Use public or publicly searchable sources such as:

- GDELT,
- Common Crawl News,
- local newspaper archives where accessible,
- trade publication archives,
- business-journal archives where legally accessible,
- archived search results and operator-news pages.

Search terms should include both industry and event vocabulary.

### Industry terms

```text
"data center"
"data centre"
datacenter
"server farm"
"cloud campus"
"hyperscale"
"colocation facility"
"computing campus"
"server facility"
```

### Event terms

```text
announced
proposed
approved
rezoning
permit
construction
groundbreaking
opened
operational
energized
expanded
megawatt
MW
million
billion
investment
campus
acre
square feet
```

## 6.2 Wayback/archival reconstruction

Use the Internet Archive for:

- deleted operator announcements,
- old municipal pages,
- old project websites,
- historic economic-development pages,
- retired facility pages.

Retain canonical URL and archival URL separately.

## 6.3 Municipal planning and zoning records

Search:

- Legistar instances,
- planning commission agendas,
- county board minutes,
- zoning applications,
- conditional-use permits,
- special-use permits,
- land-development filings,
- attached staff reports.

These records can provide parcel-level location, building footprint, phase count, generator count, substation plans, requested uses, acreage, zoning dates, votes, and opposition testimony.

## 6.4 Assessor/property records

Where publicly accessible, retrieve:

- parcel owner,
- acquisition date,
- purchase price,
- year built,
- assessed land value,
- assessed improvement value,
- taxable value,
- property taxes,
- building square footage.

## 6.5 Utility/regulatory filings

Search:

- state public utility commissions,
- utility integrated resource plans,
- transmission filings,
- rate cases,
- interconnection proceedings,
- large-load tariffs,
- public service commission dockets.

Use these to validate:

- expected load,
- service territory,
- substation/transmission investment,
- special tariff treatment,
- cost allocation,
- electricity-price effects.

## 6.6 Company disclosures

Use:

- operator press releases,
- hyperscaler announcements,
- SEC filings,
- investor materials,
- sustainability reports,
- earnings materials.

## 6.7 State/local incentive records

Capture:

- sales-tax exemptions,
- property-tax abatements,
- PILOT agreements,
- minimum investment requirements,
- job commitments,
- wage commitments,
- clawbacks,
- incentive expiration dates.

---

# 7. Claim Resolution and Confidence

Every resolved facility/project attribute must be supported by claims.

## 7.1 Suggested source reliability priors

Use configurable priors, not immutable truths.

Example starting values:

| Source class | Prior |
|---|---:|
| Permit / official land-use record | 1.00 |
| Assessor/property record | 1.00 |
| Utility/regulatory filing | 0.98 |
| SEC filing | 0.98 |
| Signed incentive agreement | 0.98 |
| Operator announcement | 0.95 |
| Local-government release | 0.95 |
| Local newspaper | 0.85 |
| National newspaper | 0.80 |
| Trade publication | 0.80 |
| Business journal | 0.80 |
| General industry site | 0.65 |
| Unverified aggregator | 0.40 |

## 7.2 Attribute-specific confidence

Reliability must be attribute-aware.

Example:

- A county permit may be excellent for square footage and permit date.
- An operator announcement may be stronger for announced capex.
- An assessor may be stronger for year built and assessed value.
- A utility filing may be stronger for load.

## 7.3 Multiple-source reinforcement

Increase confidence when independent high-quality sources agree.

A simple configurable approach:

\[
C = 1 - \prod_{j=1}^{n}(1-c_j)
\]

where \(c_j\) are independent source-confidence priors.

Do not mechanically apply this when sources merely copy one another.

## 7.4 Conflict handling

If two high-quality sources materially disagree:

- preserve both claims,
- flag conflict,
- select a provisional resolved value only if a documented resolution rule applies,
- otherwise leave unresolved.

## 7.5 Date precision

Represent uncertainty explicitly.

Possible values:

```text
DAY
MONTH
QUARTER
YEAR
APPROXIMATE_YEAR
UNKNOWN
```

Do not fabricate exact dates from year-only reporting.

---

# 8. Data Quality Score

Create a facility/project-level Data Quality Score, but keep it separate from statistical confidence intervals.

Example configurable structure:

\[
DQS = 25L + 20T + 15C + 15P + 15S + 10R
\]

where normalized 0–1 components are:

- \(L\): location certainty,
- \(T\): timeline certainty,
- \(C\): capacity/size certainty,
- \(P\): project/capex certainty,
- \(S\): source-quality score,
- \(R\): source redundancy.

Example grades:

```text
90–100 A
80–89  B
70–79  C
50–69  D
<50    Provisional
```

Do not discard provisional records automatically. They can still be useful for discovery, but causal treatment definitions should use stricter thresholds.

---

# 9. Geospatial Resolution

All facilities/projects must resolve to a stable geographic identifier.

Primary analytical geography:

- Census county FIPS.

Also retain:

- state FIPS,
- municipality,
- ZIP where reliable,
- census tract where reliable,
- coordinates,
- utility service territory where possible.

## 9.1 County assignment

Use point-in-polygon against authoritative Census county geometry.

Do not rely only on human-readable county names.

## 9.2 Historical county changes

Where county boundaries/FIPS change over the historical period, normalize to a consistent analytical geography and document crosswalks.

## 9.3 Campus spanning counties

If a campus crosses county boundaries:

- preserve exact geometry,
- allocate exposure by facility/phase footprint when feasible,
- otherwise flag the primary county and secondary affected county.

---

# 10. Treatment Variable Construction

Do not use a single treatment measure. Construct several nested treatment variables.

## 10.1 First entry

\[
FirstDC_{c,t} = 1[t \ge T_c]
\]

where \(T_c\) is the first operational year of a qualifying data center in county \(c\).

Use this for first-entry event studies.

## 10.2 Construction exposure

\[
ConstructionExposure_{c,t} = \sum_p 1[ConstructionStart_p \le t < Operational_p]
\]

Optionally weight by announced capex, square footage, or MW.

## 10.3 Operating facility count

\[
FacilityCount_{c,t} = \sum_f 1[Operational_f \le t < Closed_f]
\]

## 10.4 Capacity exposure

Where reliable:

\[
MWExposure_{c,t} = \sum_f MW_{f,t}
\]

## 10.5 Square-foot exposure

\[
SqFtExposure_{c,t} = \sum_f SqFt_{f,t}
\]

## 10.6 Capex exposure

Prefer realized or assessed capital where available.

Maintain separate variables:

```text
capex_announced
capex_committed
capex_realized_proxy
assessed_improvements
```

Do not collapse these into one number.

## 10.7 Expansion shock

\[
ExpansionShock_{c,t} = \sum_p ExpansionSize_{p,t}
\]

## 10.8 Proposed-project pressure

Needed for opposition normalization:

\[
ProposedProjectCount_{c,t}
\]

and, where possible:

\[
ProposedMW_{c,t}
\]

---

# 11. Treatment Eligibility Rules

Establish at least three treatment-quality tiers.

## High-confidence treatment

Require:

- county certainty high,
- operational or construction date known to year or better,
- at least one authoritative/first-party source,
- DQS above configurable threshold.

Use this sample for headline causal estimates.

## Expanded treatment

Allows lower source redundancy and year-only date precision.

Use for sensitivity analysis.

## Discovery treatment

Includes provisional records.

Never use as the sole sample for headline causal inference.

---

# 12. Economic Outcome Data

Build public historical outcome panels from sources such as BLS, Census, BEA, IRS, FHFA, EIA, and government finance data.

## 12.1 Employment and wages

At minimum:

- total employment,
- total wages,
- average weekly wage,
- construction employment,
- construction wages,
- information-sector employment,
- NAICS 518210 where disclosable,
- utilities employment,
- relevant professional-service employment.

Use BLS QCEW when available.

## 12.2 Business dynamics

Measure:

- establishment count,
- establishment births,
- establishment deaths,
- firm births,
- job creation,
- job destruction.

## 12.3 GDP and personal income

Measure:

- real county GDP,
- nominal GDP,
- GDP per capita,
- personal income,
- personal income per capita.

## 12.4 IRS household-income measures

Measure:

- returns,
- AGI,
- AGI per return,
- wages/salaries,
- dividend income,
- interest income.

## 12.5 Migration

Measure:

- in-migrants,
- out-migrants,
- net migration,
- inbound AGI,
- outbound AGI,
- net AGI migration.

## 12.6 Housing

Measure separately from economic dividend:

- FHFA HPI,
- home-price growth,
- rent where reliable,
- price-to-income ratio,
- rent-to-income ratio.

House-price appreciation can be an asset-value benefit and an affordability cost. Do not automatically classify it as a net benefit.

---

# 13. Fiscal Outcome Data

Build a distinct fiscal panel.

At minimum:

```text
local_general_revenue
property_tax_revenue
sales_tax_revenue
intergovernmental_revenue
capital_outlay
debt_outstanding
public_safety_spending
education_spending
infrastructure_spending
residential_property_tax_rate
commercial_or_industrial_rate_where_available
DC_specific_tax_revenue_where_available
DC_specific_PILOT_revenue_where_available
```

Derive:

\[
DCSpecificRevenuePerCapita = \frac{DCSpecificRevenue}{Population}
\]

\[
DCRevenueShare = \frac{DCSpecificRevenue}{TotalLocalRevenue}
\]

\[
NetFiscalEffect = IncrementalRevenue - IncrementalPublicCost
\]

Do not estimate net fiscal effect when public costs cannot be reasonably measured; instead publish gross revenue and an incompleteness flag.

---

# 14. Community Cost Outcome Data

Construct independent burden variables.

## 14.1 Electricity

Measure:

- retail price,
- industrial/commercial price,
- utility sales/load,
- rate cases tied to large-load infrastructure,
- special tariffs,
- transmission investment where available.

Model both local utility territory and broader state/regional effects when county attribution is impossible.

## 14.2 Water

Where public data permit:

- permitted withdrawal,
- actual reported withdrawal,
- local water-stress classification,
- drought exposure,
- utility water-rate changes,
- wastewater demand.

Do not impute facility water consumption from generic industry averages as if observed. If scenario estimates are used, label them as modeled scenarios.

## 14.3 Housing affordability

Use:

\[
PriceIncomeRatio_{c,t} = \frac{HousePriceIndexOrMedianValue}{HouseholdIncome}
\]

and analogous rent burden measures.

## 14.4 Land-use intensity

Where footprints are available:

\[
DCLandShare = \frac{DataCenterLandArea}{DevelopableOrCountyLandArea}
\]

Prefer developable/urbanized denominator when defensible.

## 14.5 Noise/environmental concerns

Use only if public measured/administrative data exist.

Separate:

- documented violations,
- modeled exposure,
- public complaints,
- sentiment claims.

Public complaints belong primarily in the opposition/civic-activity model unless independently verified as measured environmental burden.

---

# 15. Pre-Treatment Covariates

Construct a rich pre-treatment covariate set for matching and adjustment.

Potential variables:

- population,
- population growth,
- population density,
- urban/rural classification,
- baseline GDP,
- GDP growth,
- employment,
- employment growth,
- unemployment,
- wage level,
- income level,
- industry composition,
- business establishments,
- house prices,
- migration,
- educational attainment,
- broadband/fiber availability where historical data permit,
- proximity to major fiber backbone,
- proximity to major metro,
- electricity price,
- utility generation mix,
- climate/cooling-degree metrics,
- land values,
- state tax/incentive regime,
- interstate/highway access,
- baseline property-tax burden.

Use covariates measured strictly before treatment for matching.

---

# 16. Data Transformation Rules

## 16.1 Inflation adjustment

Convert monetary time series to a common real-dollar base year.

Store both nominal and real values where possible.

## 16.2 Population normalization

Create per-capita versions where appropriate.

## 16.3 Log transforms

For highly skewed positive variables, use:

\[
y^* = \ln(1+y)
\]

when zeros exist.

Document transform choice per variable.

## 16.4 Winsorization

Do not silently winsorize headline outcome variables.

If outlier treatment is necessary:

- publish raw result,
- publish robust result,
- disclose threshold.

## 16.5 Disclosure suppression

Respect source suppression flags.

Never interpret missing confidential/suppressed employment cells as zero.

---

# 17. Descriptive Baseline Analysis

Before causal modeling, publish descriptive diagnostics.

For treated vs untreated counties show:

- number of counties,
- treatment cohorts,
- facility counts,
- baseline means,
- baseline medians,
- standardized mean differences,
- treatment timing distribution,
- geographic distribution.

For each outcome calculate:

\[
Growth_{c,t} = \frac{Y_{c,t} - Y_{c,t-k}}{Y_{c,t-k}}
\]

Use one-, three-, five-, and ten-year growth windows when appropriate.

These are descriptive only.

---

# 18. Observed Economic Momentum (OEM)

OEM is a descriptive index and must never be presented as attributable to data-center development.

Possible components:

- real GDP growth,
- employment growth,
- real wage growth,
- business-establishment growth,
- real personal-income growth,
- net migration rate.

For component \(j\):

\[
z_{i,j} = \frac{x_{i,j} - \mu_j}{\sigma_j}
\]

Winsorize only if analytically justified and documented.

Combine configurable weighted z-scores:

\[
OEMRaw_i = \sum_j w_j z_{i,j}
\]

Map to 0–100 using an empirical percentile transformation or a logistic/CDF transform.

Preferred public interpretation:

- 50 = national median observed momentum,
- >50 = above-median observed momentum,
- <50 = below-median observed momentum.

Do not call 70 “70% growth.”

---

# 19. Causal Identification Hierarchy

The project should use a hierarchy of methods rather than one model.

## Tier 1 — Staggered Difference-in-Differences

Headline national average treatment effects when assumptions are credible.

## Tier 2 — Event Study

Visualize dynamic effects before and after treatment.

## Tier 3 — Matched Controls

Improve comparability and provide intuitive treated-vs-peer estimates.

## Tier 4 — Synthetic Control

Use for major counties/clusters with rich history.

## Tier 5 — Exposure/Intensity Models

Estimate response to MW, facility count, square footage, or capex.

## Tier 6 — Spatial Spillover Models

Estimate neighboring-county effects.

## Tier 7 — Instrumental Variable / natural experiment

Advanced research layer only where a defensible instrument is available. Do not force an IV for the sake of sophistication.

---

# 20. Staggered Difference-in-Differences

Let county \(i\) first receive qualifying treatment in year \(G_i=g\).

Estimate group-time average treatment effects:

\[
ATT(g,t)=E[Y_t(1)-Y_t(0)\mid G=g]
\]

Use not-yet-treated counties as controls where possible.

Aggregate to:

- overall ATT,
- cohort-specific ATT,
- calendar-time ATT,
- event-time ATT.

Event time:

\[
k=t-g
\]

Estimate:

\[
ATT_k
\]

for a window such as \(k=-10,...,+15\), subject to sample coverage.

## 20.1 Pre-trend requirement

Headline causal interpretation requires no material evidence of differential pre-trends.

Do not treat failure to reject individual pre-period coefficients as proof of parallel trends. Assess:

- joint pre-trend test,
- visual pattern,
- economic magnitude,
- covariate balance.

## 20.2 Standard errors

Cluster at county level at minimum.

If state-level shocks are material, test state-clustered or two-way clustered alternatives where statistically feasible.

## 20.3 Never-treated vs not-yet-treated

Run both when sample size permits.

Report sensitivity.

---

# 21. Event-Study Modeling

Create separate event studies centered on:

1. construction start,
2. operational start,
3. major expansion.

General specification conceptually:

\[
Y_{it}=\alpha_i+\lambda_t+\sum_{k\neq -1}\beta_k D_{it}^{k}+\epsilon_{it}
\]

but implement with a staggered-treatment-safe estimator for headline results.

Normalize \(k=-1\) as the reference period unless another baseline is justified.

Plot:

- estimate,
- 95% CI,
- observation count by event time,
- treated cohort count.

Do not plot very thin tails without a visible sample-size warning.

---

# 22. Matched-Control Construction

Create intuitive peer sets based on pre-treatment characteristics.

Possible methods:

- Mahalanobis distance,
- propensity score matching,
- coarsened exact matching,
- nearest-neighbor matching on standardized covariates.

Do not present propensity scores as causal proof.

## 22.1 Matching window

Use several years of pre-treatment trajectory, not only one baseline year.

Include both levels and trends.

Example matching vector:

```text
population level
population 5y CAGR
real GDP level
real GDP 5y CAGR
employment level
employment 5y CAGR
real wages
industry shares
house price growth
net migration
urbanization
electricity price
state/region indicator where appropriate
```

## 22.2 Balance diagnostics

For each matched sample publish standardized mean differences.

Target:

\[
|SMD| < 0.1
\]

as a useful heuristic, not a universal guarantee.

---

# 23. Synthetic Control

Use synthetic control for high-interest case studies such as major clusters.

For treated county \(1\), choose donor weights \(w_j\) such that:

\[
\sum_j w_j X_j \approx X_1
\]

subject to:

\[
w_j \ge 0,\quad \sum_j w_j = 1
\]

Estimate:

\[
\tau_t=Y_{1t}-\sum_j w_jY_{jt}
\]

## 23.1 Donor-pool rules

Exclude:

- counties treated before or near the focal county,
- counties with known major contemporaneous shocks when those shocks would invalidate comparison,
- counties with insufficient baseline history.

## 23.2 Placebo tests

Reassign treatment across donor counties and calculate placebo gaps.

Compare treated post/pre RMSPE ratio with placebo distribution.

## 23.3 Public display

Show:

- actual series,
- synthetic series,
- treatment date,
- gap,
- donor weights,
- pre-treatment fit metric,
- placebo ranking.

---

# 24. Exposure/Intensity Models

Binary entry understates large clusters.

Estimate continuous-dose relationships using:

- facility count,
- cumulative MW,
- MW per 1,000 residents,
- square footage,
- capex,
- assessed capital value.

Example fixed-effects model:

\[
Y_{it}=\alpha_i+\lambda_t+\beta Exposure_{it}+\gamma X_{it}+\epsilon_{it}
\]

Interpret cautiously because capacity is endogenous.

Use lag structures:

\[
Y_{it}=\alpha_i+\lambda_t+\sum_{l=0}^{L}\beta_l Exposure_{i,t-l}+\epsilon_{it}
\]

Separate construction and operational exposure.

---

# 25. Construction vs Operations Decomposition

Define:

\[
Build_{it}=1[ConstructionPhase]
\]

\[
Operate_{it}=1[OperationalPhase]
\]

Model:

\[
Y_{it}=\alpha_i+\lambda_t+\beta_B Build_{it}+\beta_O Operate_{it}+\epsilon_{it}
\]

For multiple facilities, use counts or weighted exposures.

This decomposition is required for employment, wages, business activity, and tax outcomes.

---

# 26. Spatial Spillovers

A data center in one county can affect neighboring counties through:

- construction labor,
- commuting,
- housing demand,
- utility infrastructure,
- tax competition,
- supplier activity.

Create distance bands around facilities or treated counties.

Example:

```text
0 km / host county
adjacent county
0–25 miles
25–50 miles
50–100 miles
```

Construct spillover treatment:

\[
Spillover_{it}=\sum_f w(d_{if})Exposure_{ft}
\]

where \(w(d)\) declines with distance.

Headline host-county models should test robustness to excluding neighboring counties from the control group.

---

# 27. Heterogeneous Treatment Effects

Estimate effects by:

- development era,
- region,
- urban/rural status,
- baseline income,
- baseline electricity price,
- facility scale,
- hyperscaler vs colocation,
- first facility vs cluster expansion,
- state incentive regime,
- water stress,
- utility structure.

Suggested development cohorts:

```text
2000–2004 Internet/telecom
2005–2014 cloud emergence
2015–2022 hyperscale cloud
2023–present AI infrastructure
```

Do not assume cohort labels imply structural breaks; test them empirically.

---

# 28. Economic Effect Metrics

For every treated geography and outcome, calculate where feasible:

- point estimate,
- percent effect,
- absolute effect,
- cumulative effect,
- per-capita effect,
- per-MW effect,
- per-$1B-capex effect.

Examples:

\[
GDPGainPerMW=\frac{EstimatedIncrementalGDP}{OperationalMW}
\]

\[
TaxRevenuePerMW=\frac{EstimatedIncrementalTaxRevenue}{OperationalMW}
\]

\[
JobsPerMW=\frac{EstimatedIncrementalEmployment}{OperationalMW}
\]

Do not calculate per-MW metrics where MW confidence is below the configured threshold.

---

# 29. Data Center Economic Dividend Index (DCEDI)

DCEDI should summarize quasi-causal economic estimates, not raw growth.

## 29.1 Initial component structure

Use the deliberated starting structure as a configurable default:

\[
DCEDI = 0.25E + 0.20I + 0.15B + 0.30F + 0.10M
\]

where:

- \(E\): employment and wage effect,
- \(I\): GDP and household-income effect,
- \(B\): business-formation effect,
- \(F\): fiscal-dividend effect,
- \(M\): migration/economic-attraction effect.

Weights must live in configuration files, not source code.

## 29.2 Component construction

Each component should be based on standardized modeled effects.

Example employment component:

\[
E = w_1 z(ATT_{employment}) + w_2 z(ATT_{realwage}) + w_3 z(ATT_{constructionemployment})
\]

Operational permanent employment should be distinguishable from temporary construction employment.

## 29.3 Shrinkage

Small-sample local estimates can be noisy.

Apply empirical-Bayes or precision weighting where appropriate:

\[
\tilde{\theta}_i=\lambda_i\hat{\theta}_i+(1-\lambda_i)\mu
\]

with \(\lambda_i\) increasing with estimate precision.

Publicly expose both raw estimate and stabilized score when possible.

## 29.4 0–100 transformation

Preferred approach:

1. calculate weighted standardized latent score,
2. convert to national empirical percentile or normal-CDF score,
3. anchor 50 near national median.

The score is a relative index, not a percentage of benefits.

---

# 30. Fiscal Dividend Index (DCFDi)

Keep fiscal effects separately inspectable even if fiscal value is included inside DCEDI.

Possible components:

- incremental property-tax revenue,
- incremental total local revenue,
- DC-specific tax/PILOT revenue,
- residential tax-rate relief,
- incremental public-service spending capacity,
- net fiscal effect where measurable.

A county can have high DCFDi and modest employment effects. That is analytically meaningful and should not be hidden.

---

# 31. Community Cost Index (DCCCI)

DCCCI should summarize measured burdens rather than opposition claims.

Use a configurable initial structure such as:

\[
DCCCI = 0.30P + 0.20W + 0.20H + 0.15I + 0.10L + 0.05E
\]

where:

- \(P\): power/electricity price and grid burden,
- \(W\): water burden,
- \(H\): housing affordability burden,
- \(I\): infrastructure/public-cost burden,
- \(L\): land-use burden,
- \(E\): measured environmental burden.

This exact weighting is a starting hypothesis, not a scientific constant. Store in configuration and run sensitivity analyses.

## 31.1 Missing-component handling

Do not treat missing water data as zero water burden.

If components are missing:

- calculate score only if minimum coverage threshold is met,
- reweight available components proportionally,
- publish coverage percentage,
- reduce confidence grade.

---

# 32. Opposition Data Architecture

Opposition should be modeled as multiple phenomena.

## 32.1 Public sentiment

Polls and surveys.

## 32.2 Search concern

Google Trends or similar aggregated search-interest signals.

## 32.3 Media discourse

Share/tone of data-center coverage focused on negative effects or opposition.

## 32.4 Grassroots mobilization

- opposition groups,
- petitions,
- petition signatures,
- signature velocity,
- protests,
- organized campaigns.

## 32.5 Civic/public-comment opposition

- opposing public comments,
- opposing speakers,
- hearing participation,
- opposition letters,
- meeting duration where attributable.

## 32.6 Regulatory/project resistance

- moratoria,
- restrictive ordinances,
- zoning denials,
- appeals,
- lawsuits,
- withdrawals,
- cancellations following opposition,
- restrictive state legislation.

Do not conflate sentiment with effective political resistance.

---

# 33. Polling Calibration

Polling should serve as a calibration/ground-truth layer when comparable repeated questions exist.

## 33.1 Same-series rule

Only calculate longitudinal percentage-point change directly when:

- question wording is materially consistent,
- sampling frame is comparable,
- pollster methodology is comparable.

Do not concatenate different pollsters into a fake time series.

## 33.2 Ensemble calibration

Different pollsters can provide cross-sectional validation.

Use hierarchical/meta-analytic calibration if combining them.

Represent poll result \(p_s\) with sampling variance:

\[
Var(p_s) \approx \frac{p_s(1-p_s)}{n_s}
\]

adjusted when design effects are available.

---

# 34. Search Opposition Modeling

Construct search baskets.

## 34.1 General-interest basket

Examples:

```text
data center
AI data center
data center near me
data center development
hyperscale data center
```

## 34.2 Opposition/concern basket

Examples:

```text
stop data center
data center opposition
data center moratorium
data center protest
data center noise
data center water use
data center electricity rates
data center power bill
data center zoning
```

Construct normalized ratio:

\[
SearchOpposition_t = \frac{NegativeQueryInterest_t+\epsilon}{GeneralDataCenterInterest_t+\epsilon}
\]

Use small \(\epsilon\) only to avoid division by zero and document it.

Because Trends values are normalized indexes, avoid treating them as absolute search counts.

---

# 35. Media Opposition Modeling

Create a document classifier with categories:

```text
PRO_BENEFIT
NEUTRAL_INFORMATIONAL
CONCERN_NEGATIVE
EXPLICIT_OPPOSITION
MIXED
```

Possible topic sublabels:

- jobs/investment,
- tax base,
- grid strain,
- electricity prices,
- water,
- noise,
- pollution/generators,
- farmland/land use,
- property values,
- housing,
- subsidies,
- secrecy/transparency,
- transmission infrastructure,
- moratorium,
- legal opposition.

Calculate:

\[
MediaOppositionRate_{g,t}=\frac{ExplicitOpposition+ConcernNegative}{AllRelevantDataCenterStories}
\]

Deduplicate syndication and near-duplicate articles before calculating rates.

---

# 36. Grassroots Mobilization Modeling

For each opposition group/petition/event store:

```text
group_id
project_id
county_fips
state
formation_date
first_observed_date
last_observed_date
member_count_if_public
petition_id
petition_start_date
signature_count
signature_observed_date
protest_date
```

## 36.1 Signature velocity

\[
SignatureVelocity = \frac{Signatures_{t_2}-Signatures_{t_1}}{Days(t_2-t_1)}
\]

## 36.2 Group density

\[
GroupDensity = \frac{ActiveOppositionGroups}{ProposedProjects}
\]

and optionally per population.

---

# 37. Civic Opposition Modeling

For public meetings classify speakers/comments into:

```text
SUPPORT
OPPOSE
NEUTRAL
UNCLEAR
```

Calculate:

\[
PublicCommentOpposition = \frac{OpposingComments}{SupportingComments+OpposingComments}
\]

and:

\[
ParticipationIntensity = \frac{RelevantComments}{Population}\times 10,000
\]

Also retain counts because ratios with tiny denominators can be misleading.

Apply minimum-count thresholds for public ratios.

---

# 38. Regulatory Resistance Modeling

Create event severity scores for outcomes such as:

```text
public hearing continuation
additional study requirement
restrictive ordinance
temporary moratorium
zoning denial
permit denial
lawsuit
project withdrawal
project cancellation
statewide moratorium proposal
statewide enacted restriction
```

Do not assume every delay is caused by opposition. Require source evidence linking the event to community/political resistance before coding it as opposition-related.

---

# 39. Data Center Opposition Index (DCOI)

Use the deliberated starting structure as a configurable default:

\[
DCOI = 0.30S + 0.20C + 0.15G + 0.15M + 0.10P + 0.10R
\]

where:

- \(S\): survey opposition,
- \(C\): civic/public-comment opposition,
- \(G\): search opposition,
- \(M\): media opposition,
- \(P\): petition/grassroots mobilization,
- \(R\): regulatory/project resistance.

## 39.1 Geographic availability problem

Survey data may be national or state-level while civic data are local.

Therefore build DCOI hierarchically:

- national DCOI,
- state DCOI,
- county/local DCOI.

Do not fabricate county survey values from a national poll.

Use higher-level sentiment as a prior/context variable, not an observed county value.

## 39.2 Relative normalization

Normalize component scores within comparable geography/time windows.

For local scores, do not let national survey coverage dominate the entire index.

## 39.3 Opposition growth

Calculate:

\[
g_{MoM}=\frac{DCOI_t-DCOI_{t-1}}{|DCOI_{t-1}|+\epsilon}
\]

\[
g_{YoY}=\frac{DCOI_t-DCOI_{t-12}}{|DCOI_{t-12}|+\epsilon}
\]

For 0–100 indexes, absolute point changes are often more interpretable than percentage growth. Publish both where useful.

## 39.4 Opposition velocity

\[
V_t=DCOI_t-DCOI_{t-3}
\]

## 39.5 Opposition acceleration

\[
A_t=V_t-V_{t-3}
\]

Use quarterly or annual equivalents when monthly data coverage is insufficient.

---

# 40. Normalize Opposition by Development Activity

This is a mandatory analytical layer.

Construct:

\[
OppositionIncidence=\frac{OpposedProjects}{ProposedProjects}
\]

\[
OppositionPerMW=\frac{OppositionEvents}{ProposedMW}
\]

\[
ResistanceSuccess=\frac{Blocked+Withdrawn+Cancelled}{OpposedProjects}
\]

This separates growth in the industry from growth in resistance.

---

# 41. Benefit–Sentiment Gap

Use standardized comparable 0–100 scores:

\[
BSG = DCEDI - DCOI
\]

Interpretation matrix:

| | Low opposition | High opposition |
|---|---|---|
| High economic dividend | broadly accepted benefit | benefit–sentiment disconnect |
| Low economic dividend | low-resistance/weak-benefit | potentially economically rational resistance |

Do not label any quadrant as irrational. The economic model may omit values communities care about.

---

# 42. Net Community Balance

Calculate:

\[
NCB = DCEDI - DCCCI
\]

Optional rescaling:

\[
NCB_{100}=50+\frac{DCEDI-DCCCI}{2}
\]

clipped to 0–100 only for display.

Store the unconstrained difference for analysis.

---

# 43. Uncertainty and Confidence

Every modeled county score should have two conceptually different confidence dimensions.

## 43.1 Statistical uncertainty

Derived from:

- standard errors,
- confidence intervals,
- bootstrap distributions,
- placebo tests.

## 43.2 Data confidence

Derived from:

- facility DQS,
- outcome coverage,
- source completeness,
- treatment-date precision,
- index component coverage.

Do not merge these into one opaque number.

---

# 44. Bootstrap and Simulation

Use bootstrap procedures where closed-form uncertainty is inadequate.

Potential approaches:

- cluster bootstrap by county,
- block bootstrap for time series,
- source-uncertainty Monte Carlo for facility attributes,
- index-weight sensitivity simulation.

For uncertain operational year:

If resolved date has a probability distribution over 2016–2018, sample treatment year in Monte Carlo runs rather than pretending 2017 is exact.

This should be an advanced robustness layer, not a prerequisite for initial v0.1.

---

# 45. Missing Data

## 45.1 Never convert missing to zero by default

A missing MW value does not mean 0 MW.

A suppressed employment value does not mean 0 employment.

## 45.2 Missingness flags

Create explicit flags:

```text
is_missing
is_suppressed
is_not_applicable
is_not_collected
is_estimated
```

## 45.3 Imputation

Avoid imputation in headline causal outcomes unless justified.

When used for covariates/matching:

- use documented methods,
- create imputation flags,
- test complete-case sensitivity.

## 45.4 Index coverage

Each index record must include:

```text
component_coverage_pct
required_component_count
available_component_count
index_confidence_grade
```

---

# 46. Statistical Significance and Practical Significance

Do not reduce interpretation to p-values.

For every headline estimate show:

- effect size,
- confidence interval,
- baseline mean,
- relative effect,
- sample size,
- practical interpretation.

Example:

> Estimated employment effect: +2.4% (95% CI +0.8% to +4.0%), corresponding to approximately 1,150 jobs relative to the modeled counterfactual.

Avoid “proved” and “caused” unless identification is unusually strong. Prefer “estimated effect,” “associated quasi-causal effect,” or “difference relative to modeled counterfactual.”

---

# 47. Multiple Testing

The project will estimate many outcomes and event-time coefficients.

Do not cherry-pick significance.

Designate:

- primary outcomes,
- secondary outcomes,
- exploratory outcomes.

For families of secondary/exploratory tests, provide false-discovery-rate-adjusted q-values where appropriate.

---

# 48. Robustness Test Suite

Each headline national economic result should run through a standardized robustness suite.

At minimum:

1. high-confidence treatment sample,
2. expanded treatment sample,
3. never-treated controls,
4. not-yet-treated controls,
5. alternative pre-period lengths,
6. alternative matching specifications,
7. neighboring-county exclusion,
8. population-weighted vs unweighted,
9. urban-only / rural-only,
10. pre-2015 vs post-2015 cohorts,
11. first-entry vs expansion treatment,
12. outlier-excluded specification,
13. placebo treatment dates,
14. conventional TWFE comparison,
15. missing-data sensitivity.

Store all model runs in a model registry.

---

# 49. Placebo and Falsification Tests

Potential falsification tests:

- assign treatment several years before actual treatment,
- estimate outcomes that should not plausibly react immediately,
- randomize treatment among matched counties,
- use placebo counties for synthetic control,
- test whether post-treatment effects appear implausibly in pre-periods.

Strong pre-treatment “effects” are a warning that causal identification is weak.

---

# 50. Model Registry

Every model run must have a unique ID.

Example fields:

```text
model_id
model_family
outcome
treatment_definition
sample_definition
start_year
end_year
control_group
covariates
fixed_effects
cluster_method
estimator
software_version
seed
created_at
code_commit_sha
input_data_hash
output_artifact_hash
```

The website should identify the model version behind published metrics.

---

# 51. Reproducibility

Hard requirements:

- deterministic seeds,
- version-pinned Python dependencies,
- data checksums,
- schema validation,
- model registry,
- source manifests,
- Git commit provenance,
- reproducible build command.

A clean checkout should be able to regenerate public derived artifacts from permitted source inputs.

---

# 52. Suggested Computational Stack

Use pragmatic tools optimized for local reproducibility.

Recommended:

- Python,
- DuckDB,
- Polars and/or Pandas,
- PyArrow/Parquet,
- GeoPandas where needed,
- Shapely,
- scikit-learn,
- statsmodels,
- linearmodels or equivalent,
- scipy,
- custom implementation/wrapper for staggered DiD if a stable Python package is unavailable,
- optional R subprocess for validated econometric packages if necessary and documented.

Do not choose an inferior estimator solely to remain Python-only. If an R package is substantially more reliable for a critical econometric method, create a reproducible bridge and export results to Parquet/JSON.

---

# 53. Pipeline Stages

Implement the analytical workflow as explicit stages.

```text
00_source_inventory
01_raw_ingest
02_document_extract
03_claim_extract
04_entity_resolution
05_claim_resolution
06_geocode
07_facility_event_panel
08_public_outcome_ingest
09_county_year_panel
10_treatment_build
11_descriptive_models
12_matching
13_did_models
14_event_studies
15_synthetic_control
16_intensity_models
17_fiscal_models
18_cost_models
19_opposition_models
20_index_build
21_uncertainty
22_robustness
23_publish_artifacts
24_site_build
```

Every stage should be rerunnable and should not mutate upstream raw data.

---

# 54. Recommended Data Zones

Use immutable layers.

## `raw/`

Original downloaded/public records and metadata, subject to licensing.

## `bronze/`

Parsed but minimally transformed data.

## `silver/`

Cleaned, standardized, deduplicated, geocoded records.

## `gold/`

Analytical county-year panels and final modeled datasets.

## `public/`

Static data artifacts safe and licensed for GitHub Pages distribution.

Never expose copyrighted full news text in the public repository unless redistribution rights allow it.

---

# 55. National Map Output Model

The map must consume precomputed county/state artifacts.

Each county summary JSON/Parquet record should include fields like:

```text
county_fips
county_name
state_abbr
facility_count_operating
facility_count_proposed
operational_mw_known
operational_mw_coverage_pct
first_operational_year
last_major_expansion_year
OEM
DCEDI
DCEDI_ci_low
DCEDI_ci_high
DCFDi
DCCCI
DCOI
DCOI_velocity
DCOI_acceleration
BSG
NCB
model_confidence_grade
data_quality_grade
component_coverage_pct
```

---

# 56. Map Layers

At minimum provide switchable layers for:

1. operating facilities,
2. proposed facilities,
3. cancelled/rejected facilities,
4. operational MW,
5. first data-center entry year,
6. observed economic momentum,
7. estimated employment dividend,
8. estimated GDP/income dividend,
9. fiscal dividend,
10. DCEDI,
11. electricity/community cost,
12. DCCCI,
13. DCOI,
14. opposition velocity,
15. Benefit–Sentiment Gap,
16. Net Community Balance,
17. data-quality/confidence.

Do not use a single red/green map to imply morally good/bad counties.

---

# 57. County Detail View

Every county detail page/panel should include:

## Data-center history

- facility timeline,
- project timeline,
- announced/known MW,
- capex claims,
- operator history,
- treatment confidence.

## Observed economy

- GDP,
- employment,
- wages,
- income,
- business formation,
- migration,
- housing.

## Counterfactual analysis

- treated vs matched control,
- event study,
- synthetic control where available,
- estimated effect with CI.

## Fiscal

- tax revenue,
- tax-rate trajectory,
- local revenue,
- public spending where available.

## Community cost

- electricity,
- water,
- housing affordability,
- infrastructure.

## Opposition

- media trend,
- civic opposition,
- petitions/groups,
- moratoria/legal events,
- project resistance.

## Provenance

- source links,
- confidence grades,
- last update,
- model version.

---

# 58. Time-Series UX

For every index distinguish:

- level,
- point change,
- percent change where meaningful,
- velocity,
- acceleration.

Example:

```text
DCOI: 74.2
YoY change: +9.7 points
3-month velocity: +4.1
3-month acceleration: +1.3
```

Do not call a 10-point change on a 0–100 index “10%” unless it literally represents percentage points of a survey measure.

---

# 59. Publication Language Rules

Hard-code editorial conventions in the site.

Use:

- “observed,”
- “estimated,”
- “modeled counterfactual,”
- “quasi-causal estimate,”
- “associated with,”
- “relative to matched controls.”

Avoid:

- “proved,”
- “caused” without qualification,
- “data centers created X jobs” when the result is an econometric estimate,
- treating index values as percentages,
- asserting missing data means no effect.

---

# 60. Model Confidence Classification

Create a transparent overall model-confidence grade per geography/model.

Example factors:

- treatment-date quality,
- number of treated observations,
- pre-treatment history length,
- pre-trend diagnostics,
- matched-balance quality,
- synthetic-control fit,
- outcome completeness,
- estimate precision.

Possible grades:

```text
A — strong quasi-experimental evidence
B — good evidence with limitations
C — suggestive modeled evidence
D — descriptive/model-limited
P — provisional / insufficient for causal interpretation
```

Do not use low-confidence local causal estimates to populate a misleadingly precise national choropleth. Consider hatching/opacity/coverage masks.

---

# 61. Index Sensitivity Analysis

Because index weights are normative/modeling choices, publish sensitivity.

For each index:

1. default weights,
2. equal weights,
3. alternative plausible weight sets,
4. leave-one-component-out scores.

Compute rank stability:

\[
\rho = SpearmanRankCorrelation(DefaultRank, AlternateRank)
\]

If rankings are highly unstable, flag the index as weight-sensitive.

---

# 62. Historical Backtesting

Use older data-center cohorts to validate whether the model detects known large clusters.

Backtest procedure:

1. truncate data at historical year \(T\),
2. build treatment and controls using only information known by \(T\),
3. estimate forward effects,
4. compare with subsequently observed outcomes,
5. record predictive/counterfactual error.

Backtesting is not proof of causal identification, but it improves model discipline.

---

# 63. Data Completeness Reporting

Publish national completeness dashboards.

Examples:

```text
% facilities with high-confidence coordinates
% facilities with operational year
% facilities with construction year
% facilities with MW
% facilities with square footage
% facilities with capex
% facilities with assessor record
% facilities with tax data
% proposed projects with outcome status
```

Also calculate completeness by year to expose historical degradation.

---

# 64. Avoid Survivorship Bias

Current operating-facility datasets exclude failures.

The canonical panel must preserve:

- cancelled,
- withdrawn,
- rejected,
- closed,
- never-built,
- delayed.

Opposition effectiveness cannot be measured correctly otherwise.

---

# 65. Avoid Selection Bias

Data centers choose locations non-randomly.

Major siting factors include:

- power,
- fiber,
- land,
- taxes,
- infrastructure,
- climate,
- existing tech ecosystem.

Therefore simple treated-vs-national-average comparisons cannot support causal claims.

Matching, staggered DiD, synthetic control, and potentially IV designs exist to mitigate this problem.

---

# 66. Advanced Instrumental-Variable Research Layer

Only implement after the main observational/quasi-experimental system is stable.

Potential instruments may be inspired by historical infrastructure such as legacy fiber-backbone proximity, but an instrument must satisfy:

1. relevance:

\[
Cov(Z,Treatment) \neq 0
\]

2. exclusion restriction:

\[
Z \text{ affects outcome only through treatment}
\]

The exclusion restriction is difficult and must be defended, not assumed.

If no defensible instrument exists, omit IV estimates.

---

# 67. Spatial Econometric Extension

Later versions may test spatial autocorrelation.

Calculate Moran's I for residuals.

If material spatial dependence exists, evaluate:

- spatial lag models,
- spatial error models,
- Conley standard errors,
- spatial HAC alternatives.

Do not use spatial models merely for novelty.

---

# 68. County vs Metro Analysis

County is the canonical national unit, but build optional metro aggregations.

Metro aggregation is useful because:

- labor markets cross county boundaries,
- housing spillovers cross counties,
- data-center clusters can span multiple counties.

Use OMB/Census CBSA crosswalks and retain county-level source estimates.

Never hide county heterogeneity inside metro totals.

---

# 69. State-Level Analysis

State-level dashboards should aggregate:

- facility count,
- proposed projects,
- MW,
- economic effects,
- opposition,
- legislation,
- community cost.

Aggregate county causal effects using population-, exposure-, or inverse-variance weighting depending on the statistic.

Document weighting.

---

# 70. National Aggregation

National estimated effects should not simply sum every county point estimate if models overlap or spillovers are present.

Use model-specific aggregation rules.

For ATT estimates:

\[
ATT_{national}=\sum_g \omega_g ATT_g
\]

with clearly defined cohort weights.

For local modeled dollar impacts, avoid double counting spillovers.

---

# 71. Versioned Public Artifacts

Create public versioned files such as:

```text
public/data/v1/county_summary.parquet
public/data/v1/county_summary.json
public/data/v1/facilities.geojson
public/data/v1/projects.parquet
public/data/v1/events.parquet
public/data/v1/state_summary.json
public/data/v1/national_summary.json
public/data/v1/methodology.json
public/data/v1/model_registry.json
```

Include schema version in every artifact.

---

# 72. Validation Tests

Automated validation must include:

## Referential integrity

- every project has valid facility,
- every claim has valid source,
- every event has valid entity,
- every county FIPS exists in reference geography.

## Temporal integrity

Flag impossible sequences such as:

- operational before construction,
- cancellation after closure without explanation,
- expansion before initial facility exists.

Do not automatically delete anomalies; flag for review.

## Unit validation

- MW within plausible ranges,
- square footage nonnegative,
- capex nonnegative,
- dates within expected historical range.

## Statistical validation

- no duplicate panel keys,
- no unexpected row-count collapse,
- treatment dates stable across builds unless source resolution changed,
- model sample counts tracked.

---

# 73. Human Review Queue

Automated extraction will produce ambiguous records.

Create review queues for:

- entity-resolution conflicts,
- high-impact claims with low confidence,
- conflicting MW/capex values,
- treatment-date uncertainty,
- project/facility merge ambiguity,
- opposition-causality ambiguity,
- unusually influential statistical observations.

Prioritize review by expected analytical impact.

---

# 74. Data Licensing and Copyright

The public site/repository must not redistribute content beyond source licenses.

For news:

- store metadata,
- source URL,
- archive URL,
- hashes,
- extracted structured claims,
- only short excerpts where legally appropriate.

Do not publish full copyrighted article text merely because it was accessible to the pipeline.

Government/open datasets may be redistributed according to their terms.

Maintain a machine-readable source-license manifest.

---

# 75. Recommended Repository Modeling Structure

```text
/modeling
  /config
    index_weights.yml
    treatment_rules.yml
    source_priors.yml
    model_specs.yml
  /src
    /claims
    /entities
    /geography
    /panels
    /matching
    /did
    /event_study
    /synthetic_control
    /intensity
    /spatial
    /fiscal
    /costs
    /opposition
    /indices
    /uncertainty
    /validation
  /tests
  /notebooks
  /reports
  /model_registry
```

Production calculations must live in tested modules, not only notebooks.

---

# 76. Configuration-Driven Methodology

All subjective thresholds and weights should be configuration-driven.

Examples:

```yaml
minimum_dqs_for_headline_treatment: 80
minimum_pre_treatment_years: 5
preferred_pre_treatment_years: 10
event_window_pre: 10
event_window_post: 15
minimum_local_index_coverage: 0.60
confidence_interval: 0.95
```

Index weights should also be YAML/JSON configuration with versioning.

---

# 77. Phased Modeling Build

## Phase 0 — Foundations

Deliver:

- schemas,
- county geography,
- data-source manifest,
- facility/event seed,
- provenance model,
- model registry.

## Phase 1 — Minimum viable historical treatment panel

Target fields:

```text
facility_id
county_fips
operational_year
facility_count
```

This is enough for first-entry economic studies.

## Phase 2 — Core economic outcome panel

Ingest:

- BLS,
- BEA,
- Census,
- IRS,
- FHFA,
- EIA.

Build county-year gold panel.

## Phase 3 — First causal economic models

Implement:

- staggered DiD,
- event study,
- matched peers,
- initial synthetic-control case studies.

Publish OEM separately from DCEDI.

## Phase 4 — Facility enrichment

Add:

- construction date,
- square footage,
- MW,
- expansions,
- capex,
- incentives.

## Phase 5 — Fiscal modeling

Add:

- assessor records,
- local revenue,
- tax agreements,
- tax-rate trajectories.

## Phase 6 — Community-cost modeling

Add:

- electricity,
- housing,
- water,
- infrastructure burdens.

## Phase 7 — Opposition data

Add:

- news/media,
- search,
- petitions/groups,
- civic comments,
- moratoria/legislation,
- project resistance.

## Phase 8 — Integrated indices

Publish:

- DCEDI,
- DCFDi,
- DCCCI,
- DCOI,
- BSG,
- NCB.

## Phase 9 — National interactive map

Publish all layers with confidence overlays and local drill-down.

## Phase 10 — Advanced research

Add:

- spatial models,
- IV designs where defensible,
- richer time frequency,
- metro spillovers,
- uncertainty simulation,
- historical backtesting.

---

# 78. Minimum Viable Analytical Release

Do not wait for perfect MW/capex coverage.

A legitimate v0.1 can be built from:

```text
facility_id
county_fips
operational_year
facility_count
```

plus high-quality public economic outcomes.

The first release should answer:

> What happened to county economic outcomes around first data-center entry relative to appropriately selected controls?

It should not yet claim to measure full community cost or opposition if those layers are incomplete.

---

# 79. Minimum Publication Standard for a Causal Map Layer

A county must not receive a headline DCEDI estimate unless:

- treatment date is sufficiently reliable,
- minimum pre-period history exists,
- minimum post-period history exists,
- model has an adequate comparison group,
- pre-trend diagnostics are acceptable or clearly flagged,
- estimate uncertainty is available,
- outcome coverage threshold is met.

Otherwise display:

> Insufficient evidence for local causal estimate.

Still allow observed descriptive data.

---

# 80. Anti-Patterns to Reject

Codex must reject or refactor the following approaches:

1. Treating all counties with a data center as identical.
2. Comparing treated counties only with the U.S. average.
3. Calling post-treatment growth “caused by data centers.”
4. Using current facility inventory as a complete historical project set.
5. Ignoring cancelled/rejected projects.
6. Treating missing MW as zero.
7. Treating survey percentages from different questions as one time series.
8. Counting negative articles without dividing by total data-center coverage.
9. Counting opposition events without controlling for growth in proposed projects.
10. Using a naive staggered TWFE estimate as the only causal model.
11. Including post-treatment outcomes as matching covariates.
12. Publishing an index without showing components and coverage.
13. Hiding wide confidence intervals behind a precise 0–100 score.
14. Using AI-extracted facts without preserving source provenance.
15. Force-merging ambiguous facility aliases.
16. Redistributing copyrighted source text without permission.
17. Running heavy econometrics in the GitHub Pages browser client.

---

# 81. Required Methodology Documentation

Generate a public methodology section explaining in accessible language:

- what a data center is for project purposes,
- how facilities/projects are discovered,
- how dates are resolved,
- what treatment means,
- why matching/counterfactuals are necessary,
- what DiD/event studies estimate,
- what synthetic control does,
- what each index means,
- what index values do not mean,
- how missing data are handled,
- how confidence is represented,
- limitations.

Also publish a technical appendix with equations and model specifications.

---

# 82. Model Output Acceptance Criteria

Before a model can be tagged for public production, require:

- reproducible run,
- input hash recorded,
- model spec recorded,
- sample counts recorded,
- no failed validation checks,
- pre-trend diagnostics generated,
- confidence intervals generated,
- robustness run status recorded,
- artifact schemas validated,
- human-readable model card generated.

---

# 83. Model Cards

Generate a model card for each headline model.

Example:

```text
Model: employment_first_entry_v1
Treatment: first high-confidence operational data center
Estimator: staggered group-time ATT
Outcome: log total employment
Control group: not-yet-treated counties
Pre-period: minimum 7 years
Event window: -7 to +10
Covariates: baseline population, GDP, industry mix, wages, electricity price...
Clustering: county
Sample: N counties / N county-years
Key limitations: treatment timing uncertainty, residual selection bias...
```

Make these available in the repository and optionally in the website methodology panel.

---

# 84. Public API-Like Static Data Contract

Although GitHub Pages is static, design public JSON/Parquet artifacts as a stable data contract so third parties can reuse the results.

Include:

- schema version,
- generated timestamp,
- data vintage,
- model vintage,
- license metadata,
- field descriptions.

---

# 85. Initial Codex Execution Instructions

When this document is supplied to Codex, the agent should begin by doing the following in order.

## Step 1 — Audit the repository

If a repository already exists:

- inspect current structure,
- preserve useful work,
- do not overwrite working components blindly,
- identify gaps relative to this specification.

## Step 2 — Create methodology and data dictionaries

Create:

```text
docs/methodology.md
docs/data-dictionary.md
docs/source-methodology.md
docs/modeling-methodology.md
```

Use this specification as the authoritative initial design.

## Step 3 — Create schemas

Implement schemas for:

- facility,
- project,
- event,
- operator,
- source,
- claim,
- claim resolution,
- county-year,
- model registry,
- index output.

## Step 4 — Build configuration files

Create versioned configs for:

- source reliability priors,
- treatment thresholds,
- model definitions,
- index weights,
- quality grades.

## Step 5 — Build the county geographic reference layer

Use authoritative Census FIPS and geometry.

## Step 6 — Build the facility seed ingest

Ingest a public current facility atlas and normalize it into the canonical schema.

## Step 7 — Build provenance-first enrichment

Create source and claim tables before aggressive enrichment.

Every extracted project fact must enter as a claim.

## Step 8 — Build the first historical timeline

Prioritize operational year and county FIPS.

Produce coverage report.

## Step 9 — Ingest core economic sources

Create scripted, cached ingestors for the public county-level outcome datasets.

## Step 10 — Build the county-year analytical panel

Validate keys, inflation adjustment, geographic consistency, suppression, and missingness.

## Step 11 — Implement OEM

Publish descriptive observed momentum with no causal language.

## Step 12 — Implement first-entry treatment

Use high-confidence operational date.

## Step 13 — Implement staggered DiD and event study

Generate national and cohort-level results with pre-trend diagnostics.

## Step 14 — Implement matched-control diagnostics

Generate balance reports and peer groups.

## Step 15 — Implement synthetic-control prototype

Choose several high-data-quality, high-exposure counties and produce local case studies.

## Step 16 — Implement DCEDI v0.1

Only include components supported by causal/model outputs available at that stage.

Do not fabricate missing fiscal or migration components. Label provisional weights and coverage.

## Step 17 — Add fiscal and cost layers incrementally

Build each as independent modules before combining.

## Step 18 — Add opposition system

Start with media/project resistance, then add civic records, petitions/groups, search, and polling calibration.

## Step 19 — Build DCOI

Respect geographic coverage limitations.

## Step 20 — Build integrated derived measures

Compute BSG and NCB only after component indices meet publication thresholds.

## Step 21 — Export static artifacts

Produce map-ready JSON/GeoJSON/Parquet.

## Step 22 — Render the national map

Use precomputed outputs and expose methodology/confidence in the UI.

## Step 23 — Add continuous update workflow

Automate safe source refreshes and model rebuilds using local scripts and/or GitHub Actions.

Never allow a new automated extraction to silently replace a high-confidence resolved claim without review/resolution logic.

---

# 86. Final Research Standard

The finished system should make it possible to inspect any county and answer, with explicit evidence and uncertainty:

1. **What data-center development occurred here?**
2. **When did it occur?**
3. **How certain are we about the development history?**
4. **What economic changes were observed?**
5. **What would a reasonable counterfactual suggest would have happened without the development?**
6. **What is the estimated economic dividend?**
7. **What is the estimated fiscal dividend?**
8. **What community costs are measurably associated with development?**
9. **How much opposition exists, and how quickly is it changing?**
10. **Is opposition high or low relative to measurable economic benefit?**
11. **Is the net measurable benefit high or low relative to measurable community burden?**
12. **How strong is the evidence behind every one of those statements?**

The objective is not to prove that data centers are good or bad. The objective is to create the most transparent public evidence system possible for determining **where, when, and under what conditions data-center development produces measurable economic benefits, measurable community burdens, and political opposition**.

---

# 87. Guiding Analytical Doctrine

Use this doctrine throughout the project:

> **Observed growth is not causal impact.**
>
> **Public opposition is not the same thing as measurable community cost.**
>
> **Measured community cost is not the same thing as opposition.**
>
> **A high tax contribution is not the same thing as broad economic development.**
>
> **A large capital investment is not the same thing as a large permanent employment effect.**
>
> **A current facility inventory is not a complete historical development record.**
>
> **Every modeled result must remain connected to the evidence, assumptions, uncertainty, and counterfactual that produced it.**

This principle is the foundation of the Data Center Community Impact Observatory.

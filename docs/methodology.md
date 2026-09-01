# Methodology overview

The Observatory is an evidence system first and an analytical product second. Public
outputs are generated from source records, claims, reviewed resolutions, observations,
registered model runs, and versioned index methods.

## Evidence states

The system distinguishes observed conditions, observed changes, modeled counterfactual
differences, quasi-causal estimates, perception/opposition indicators, and data-quality
measures. These labels are not interchangeable.

## Historical reconstruction

Present-day facilities are starting points, not a complete historical sample. Reverse
reconstruction identifies prior announcements, permits, construction, operations,
expansions, and operator changes. Forward discovery preserves rejected, withdrawn,
cancelled, closed, and never-built projects to reduce survivorship bias.

## Analytical design

The canonical analytical grain is county-year, with county-quarter used only when source
frequency and treatment timing support it. Construction, operation, and expansion are
separate treatments. Descriptive results are published independently from matched or
staggered-treatment estimates.

No county receives a headline causal score without adequate treatment-date evidence,
pre-treatment history, comparison units, diagnostics, uncertainty, and component
coverage. Missing evidence is displayed as insufficient evidence rather than zero.

## Current implementation status

The current site combines authoritative Census 2025 county geography with the OSM-derived
IM3 Open Source Data Center Atlas v2026.02.09 seed. IM3 rows are imported as provisional
source objects, not silently promoted to verified operating facilities. The public county
measure is therefore labeled “source records,” and a zero means no record in that release,
not evidence that no facility exists.

The ingest preserves all 1,479 source rows in bronze JSON, including five deliberate
cross-county duplicates and two Puerto Rico rows outside the current publication scope.
Canonical/public projections contain 1,472 distinct in-scope source objects. Single-county
centroids are assigned against the published Census polygons; source-reported assignments
remain preserved in evidence. Cross-county polygons retain multiple assignments without
inventing allocation shares.

The first identity-resolution pass is intentionally conservative. A governed rule links
252 building footprints wholly inside exactly one campus polygon and one point inside
exactly one campus. It groups 953 source operator assertions into 161 provisional
operator entities using Unicode, case, and whitespace normalization only. It does not
infer parent companies, ownership, or corporate aliases.

Spatial plausibility is not treated as proof of physical identity. A curated second pass
reviewed all sixteen candidates against source attributes, geometry diagnostics, and ten
official operator, SEC, or federal sources. Three address/name pairs were merged into
canonical physical facilities while preserving the superseded source record and redirect.
Eight point sites were explicitly not merged because they represent separately operated
sites, suites, exchanges, or computing systems inside a larger building; these now use a
`located_within_building` relationship. Two partial campus links were accepted, one
cross-operator campus link was rejected, and two geometrically inconsistent unnamed
campuses were escalated for source-history review.

A final boundary pass resolved both escalations from official OpenStreetMap way histories
and first-party site evidence. The smaller One Wilshire polygon had been explicitly
retagged as `building:part=yes`; it is now a fourth superseded source record that redirects
to the One Wilshire building rather than an active campus. The Phoenix boundary is the
separate, multi-building 4010 Data Center campus at 4010 North 3rd Street, not the Lumen
building at 215 East Indian School Road, so that proposed campus link was rejected. The
earlier escalation decisions remain in the downstream snapshot with superseded status.
The pinned ingest, first-pass resolution, and initial adjudication artifacts remain
immutable; final boundary review is another downstream JSON layer.

The seed does not establish operating dates, lifecycle status, historical completeness,
MW capacity, or causal effects. Historical outcome panels and econometric estimation
remain future work.

## County economic baseline

The first substantive outcome-source increment uses BEA's February 5, 2026 county release
for data year 2024. CAGDP1 line 1 supplies real GDP in thousands of chained 2017 dollars;
the adapter converts it to chained 2017 dollars. CAINC1 supplies current-dollar personal
income, population, and current-dollar per-capita personal income. Current-dollar measures
are explicitly registered and published as nominal rather than being assigned to real-value
metrics.

All 3,144 Census 2025 county and county-equivalent records remain in the projection. BEA
publishes exact compatible values for 3,091. Fifty-three current Census units do not receive
an exact source row because BEA uses combined or legacy geographies. Those values are marked
unavailable and are not divided, copied, or treated as zero. The 2024 baseline is descriptive
context only; it does not measure a data-center effect and is insufficient for pre/post or
quasi-causal analysis without historical observations and treatment dates.

## County employment and wage baseline

The second substantive outcome-source increment uses the final BLS QCEW annual release for
data year 2025. County total-covered rows supply the annual average of monthly employment,
the annual average of quarterly establishment counts, total annual wages, and average weekly
wages. Wage measures are current-dollar observations and are registered as nominal; they are
not assigned to the real-wage metric before a governed deflator is implemented.

Private construction employment comes from ownership code 5 and NAICS 23 because QCEW does
not publish an all-ownership county-industry aggregation. It therefore must not be described
as total construction employment. BLS disclosure code `N` is authoritative missingness: all
922 protected construction cells are suppressed, never parsed from their placeholder zeros.
Fourteen additional county records lack the private-construction row. Kalawao County lacks an
annual-by-area member and remains wholly unavailable.

The public projection retains all 3,144 Census counties: 2,207 are complete across the five
published measures, 936 are partial, and one is unavailable. As with the BEA baseline, these
are descriptive conditions and not evidence of a data-center effect.

## County-year history panel

The governed analytical materialization joins BEA and BLS observations at the current
Census county-year grain for 2001–2024. Each of the 75,456 panel rows references four
schema-valid observations: real GDP and population as covariates, annual-average covered
employment as the configured outcome, and nominal average weekly wage as context. The
public projection groups the same values by county for static delivery.

Current county identity is authoritative. No legacy county, combined geography, or former
Connecticut county is allocated into a present-day county equivalent. As a result, 3,064
counties have all four measures in all 24 years, 79 are partial, and Kalawao County is
unavailable. This is preferable to inventing a longitudinal crosswalk without an explicit
allocation method and uncertainty model.

The 24-year span can support the configured minimum of seven pre-treatment and three
post-treatment periods. The separate governed first-entry registry currently sets model
readiness to `insufficient_eligible_treatments`: no treatment assignment, comparison group,
estimate, index, or causal claim is produced.

## County first-entry treatment governance

`trt_first_entry_v1` requires a high-confidence operational event with at least year
precision, a data-quality score of 80, and at least one authoritative source. Candidate
quality is calculated as `source quality × claim confidence × date-precision multiplier ×
100`. The configured model also requires seven available pre-treatment and three available
post-treatment years.

Passing those checks is necessary but not sufficient. A facility opening becomes a county
first-entry treatment only when the reviewed adjudication explicitly verifies that it is the
first data-center operation in that county. The current registry retains three facility-event
candidates: NTT SV1 in Santa Clara County (2021-04-13, DQS 93.10, 20 pre/3 post years),
Apple's Mesa facility in Maricopa County (2017-03 month precision, DQS 85.74, 16 pre/7 post
years), and a contemporaneous observation of QTS Atlanta DC1 in Fulton County (2006-10-03,
DQS 84.60, 5 pre/18 post years). The Santa Clara and Maricopa candidates pass the evidence
and panel-window gates but fail county-first-entry verification. Fulton's trade-press candidate
also fails the authoritative-source and seven-pre-period gates and is independently rejected
by documented earlier operation. Therefore all 3,144 counties have an assessment, zero are
eligible, and no model run is authorized. Counties without a reviewed dated event remain
unknown for treatment purposes; they are not labeled never treated.

### First-entry research prioritization

The research queue is a governance tool, not a treatment model. Counties are eligible for
ranking only when the current canonical inventory contains at least one facility, all 24
core panel years are complete, and the county is not already treatment-eligible. This yields
217 candidates from 226 facility counties; nine facility counties fail the history gate.

Priority combines a governed dated-event anchor (30%), reviewed operational evidence (25%),
the feasibility of auditing the county's current facility inventory (20%), panel completeness
(15%), and source-identity coverage (10%). Inventory feasibility is inversely scaled by the
log of the active facility count, so a smaller inventory is treated as easier to audit—not as
more likely to be newly treated. The initial tranche contains 24 counties, six per Census
region and no more than two per state. Fulton, Maricopa, and Santa Clara counties are
`research_status: evidence_collected`; the other 214 records remain queued.

Every adjudication must establish an earliest dated operational event, exact facility identity,
county inventory completeness, and a documented search for earlier operations. Failure to
verify those findings yields `unresolved_not_never_treated`; it never establishes a control.

## Lifecycle verification pilot

The first historical-reconstruction increment is a governed 24-facility research queue.
It selects three active canonical facilities from each of the eight counties with the
largest canonical-facility counts. Within each county, deterministic priority scoring
uses county density, source naming, normalized operator linkage, mapped building
footprints, campus membership, and source quality. The policy and its weights are stored
in JSON and the public queue is rebuildable from the final identity snapshot.

The immutable pilot baseline begins with all 1,337 canonical facilities at
`current_status: unknown`. Queue membership is therefore not evidence that a facility
operates, was announced, or ever completed.

The first downstream evidence tranche reviews one facility in each pilot county. Six
facility statuses resolve as operational from facility-specific operator, regulatory, or
local-government records. One record remains partial because campus evidence cannot be
mapped to its specific building; one remains disputed because two Prince William County
records assign conflicting status. Site-wide capacity or area is not allocated to a
building unless the source identifies that building. The result is six verified statuses,
1,331 unknown statuses, and sixteen remaining queue records.

The second tranche reviews the sixteen remaining queue records and closes the pilot queue.
Four additional facilities resolve as operational from exact facility or address evidence.
Nine records remain unresolved because only operator-market or campus-level evidence is
available, and two additional Prince William County records remain disputed because the
current county GIS conflicts with the county's 2024 inventory. Across the complete pilot,
ten facilities are verified operational, eleven remain in research, three are disputed,
and 1,327 canonical facilities retain unknown status.

## National lifecycle expansion

The completed pilot produced a 41.67% status-resolution rate: ten of twenty-four reviewed
facilities resolved, eleven lacked a defensible building-level match, and three contained
conflicting official evidence. The expansion policy therefore makes exact-facility identity,
source precedence, conflict handling, and stop conditions explicit. A lifecycle claim must
match at least two accepted identifiers; campus or market evidence cannot be projected onto
an individual building; and conflicting official claims remain disputed rather than being
resolved by majority vote.

The deterministic national index contains all 1,327 facilities whose lifecycle status
remains unknown. Scoring combines source-name specificity, operator linkage, building
geometry, a source reference, non-campus specificity, source quality, state coverage need,
and county density. Records are also classified into research archetypes so campus mapping,
exact-reference buildings, named buildings, points, and low-context records can be evaluated
separately.

The first national evidence tranche contains 48 facilities, twelve from each Census region.
Selection is capped at three per state, two per county, and four per known operator. The
result covers 23 states, 37 counties, and 32 known operators. The fourteen unresolved or
disputed pilot records remain in the national backlog but are excluded from this tranche so
the expansion measures new evidence yield rather than repeating completed general research.

The first national review batch adjudicates initial-tranche ranks 1–8, two from each Census
region. All eight resolve as operational from current operator pages, exact-address local
government records, or facility-code rack-installation permits. The review does not infer an
opening date from present operation, and it does not treat Equinix colocation-space figures
as total building area. For the former Digital Realty HVN10 label, the current municipal
record supports operation at the building but also shows that the seed's operator name is
historical; no current Digital Realty relationship is asserted.

The batch adds fifteen governed claims, eight review decisions, and four facility-specific
observations. Cumulative lifecycle coverage is now eighteen verified operational facilities,
eleven unresolved pilot facilities still in research, three disputed pilot facilities, and
1,319 facilities with unknown status. The original 48-record tranche remains immutable and
the separate downstream queue contains the forty records at ranks 9–48.

The second national review batch adjudicates ranks 9–16. Six facilities resolve operational:
Equinix NY4, TierPoint Charlotte CL4, Digital Realty PHX15, QTS Piscataway 1, Csquare TPA1,
and H5 Phoenix. Exact first-party records support each facility code or name plus its street
address. CMH56 and CMH59 remain unresolved because official New Albany records identify AWS
projects only by generic building labels and the reviewed exact-code mappings are directory
leads, not independently corroborated official or operator records.

This batch adds twenty-one claims, eight review decisions, and five normalized observations.
Lower-bound total-space figures and colocation or raised-floor space are not promoted to exact
building area. Cumulative coverage is twenty-four verified operational facilities, thirteen
unresolved facilities in research, three disputed facilities, and 1,313 unknown statuses.
The immutable initial tranche now has thirty-two unreviewed records at ranks 17–48.

The third national review batch adjudicates ranks 17–24. Seven facilities resolve
operational: FirstLight Brunswick, Element Critical Chicago Two, the UF East Campus Research
Computing Center, Sandia Building 880 HPC, Markley Lowell, EdgeConneX DET01, and CoreSite AT2.
Current first-party facility records support exact identity for six; Sandia resolves at lower
confidence from an official Building 880 Annex data-center record combined with Sandia's
maintained HPC location page for the same building.

SAP COS02 remains unresolved. SAP's current cloud-location list establishes Colorado Springs
operation, and a local building record establishes a data-center project at the mapped address,
but only a directory joins the COS02 code to that building. Seven exact-facility observations
are normalized: five building-area values and two power-capacity values. Cumulative coverage is
thirty-one verified operational facilities, fourteen unresolved facilities in research, three
disputed facilities, and 1,306 unknown statuses. The immutable initial tranche now has
twenty-four unreviewed records at ranks 25–48.

The fourth national review batch adjudicates ranks 25–32. Five facilities resolve
operational: Prime DFW01-01, Equinix SE3, the Phillips Exeter IT Data Center, Fidelity's
Papillion facility, and Csquare's Lynnwood facility. Current operator, institutional, or
municipal records support the exact building in each case. The Csquare record resolves the
seed's legacy SE1 label to the current SEA3 label at the same address without treating the
legacy code itself as current.

Lumen Norristown, CyrusOne CIN3, and QTS DAL10 remain unresolved. Current sources establish
regional service, a legacy facility, or a current multi-building campus, but do not map the
operator or facility code to the mapped building with policy-compliant evidence. The batch
adds twenty-one claims, eight review decisions, and three normalized exact-facility
observations. Cumulative coverage is thirty-six verified operational facilities, seventeen
unresolved facilities in research, three disputed facilities, and 1,301 unknown statuses.
The immutable initial tranche now has sixteen unreviewed records at ranks 33–48.

The fifth national review batch adjudicates ranks 33–40. Five facilities resolve operational:
TierPoint Valley Forge, Csquare Allen DFW2, Serverfarm LAX1, CyrusOne Norwalk NYM5, and Switch
Las Vegas 12. Current operator records and exact-address operator specifications or official
records establish each building. Five observations are normalized: utility capacity for DFW2,
building area and IT capacity for LAX1, and building area and IT capacity for NYM5. Lower-bound
total space and raised-floor space remain contextual.

Google's Papillion campus and Union Pacific's Omaha presence do not map current operation to the
selected buildings, so both remain in research. The Microsoft Data Center 1 record is disputed:
Prince William County's current GIS identifies the exact selected point as completed Corscale
Gainesville Crossing 1 and places Microsoft's pending MNZ08 at a different nearby point. The
batch adds twenty-two claims, eight review decisions, and five observations. Cumulative coverage
is forty-one verified operational facilities, nineteen unresolved facilities in research, four
disputed or needs-review facilities, and 1,296 unknown statuses. The immutable initial tranche
now has eight unreviewed records at ranks 41–48.

The sixth national review batch adjudicates ranks 41–48 and completes the immutable balanced
initial tranche. Five facilities resolve operational: Flexential Alpharetta, Switch Las Vegas 7,
Bloomberg Orangeburg, the IU Bloomington Data Center, and QTS ATL1 DC1. Current operator,
institutional, utility, or regulatory records support each exact building. The former Flexential
Allentown operation resolves closed from exact-address vacancy evidence and the operator's current
portfolio; that status does not imply demolition or preclude reuse by another operator.

The Comcast Southgate and Verizon Centennial labels remain unresolved because local network or
telecommunications evidence does not establish data-center operation at either selected footprint.
Four exact-facility observations are normalized: area and capacity for Flexential Alpharetta,
building area for IU Bloomington, and total facility area for QTS ATL1 DC1. Cumulative coverage is
forty-seven verified lifecycle statuses, twenty-one unresolved facilities in research, four
disputed facilities, and 1,290 unknown statuses. No record remains in the 48-facility queue.

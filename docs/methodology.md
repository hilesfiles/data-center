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
MW capacity, or causal effects. Historical reconstruction, outcome panels, and
econometric estimation remain future work.

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

# Source registry

The initial machine-readable source registry is `config/v1/source-registry.json`.
Most entries are seeded from the project specifications and remain pending network
verification. The Census boundary source is now verified and implemented against the
official TIGERweb generalized Counties 5M feature layer.

## Implemented Census geography source

- Service: `Generalized_ACS2025/State_County/MapServer/12`
- Publisher: U.S. Census Bureau
- Reference vintage: January 1, 2025
- Scope: 50 states and District of Columbia
- Published records: 3,144 counties and county-equivalent entities
- Durable formats: JSON acquisition manifest, normalized JSON collection, JSON dataset
  manifest, and GeoJSON map projection
- Adapter: `scripts/acquire_census_counties.py`

Territories are present in the upstream service but intentionally excluded from the first
analytical geography scope. This prevents coverage from being implied where downstream
economic sources may not have compatible county-equivalent observations.

## Implemented IM3 facility seed

- Dataset: IM3 Open Source Data Center Atlas v2026.02.09
- Publisher: Pacific Northwest National Laboratory
- DOI: `10.57931/3017294`
- Upstream basis: OpenStreetMap-derived locations and footprints
- Source layers: point, building, and campus
- Source rows: 1,479; distinct in-scope source objects: 1,472
- Current publication scope: 50 states and District of Columbia
- License: Open Database License 1.0 (ODbL)
- Adapter: `scripts/acquire_im3_facilities.py`

The adapter pins the exact upstream repository commit and verifies the GeoPackage byte
size and SHA-256 before processing. The GeoPackage is temporary transport input only.
All retained source-shaped rows, provisional entities, evidence links, observations,
diagnostics, manifests, county coverage, and map features are JSON or GeoJSON.

## Implemented BEA county economic baseline

- Tables: CAGDP1 County GDP Summary and CAINC1 County Personal Income Summary
- Publisher: U.S. Bureau of Economic Analysis
- Data year: 2024
- Release vintage: February 5, 2026
- Measures: real GDP in chained 2017 dollars, current-dollar personal income,
  population, and current-dollar per-capita personal income
- Exact current Census county coverage: 3,091 of 3,144
- Adapter: `scripts/acquire_bea_county_economic_baseline.py`

The adapter pins both official ZIP byte sizes and SHA-256 hashes. ZIP and Windows-1252
CSV inputs are deleted with the temporary working directory after parsing. Durable bronze,
silver, acquisition, diagnostic, manifest, and public outputs are JSON. BEA aggregate or
legacy geographies—including Connecticut's former counties, Maui/Kalawao, and several
Virginia city/county combinations—are not allocated to current Census units. Their 53
current Census records carry explicit unavailable values.

Real GDP is converted from thousands of chained 2017 dollars to chained 2017 dollars.
Personal income is a current-dollar series, so the metric registry and public field names
label it nominal; it is not written to the registered real-personal-income metric.

## Implemented BLS QCEW county employment and wage baseline

- Dataset: Quarterly Census of Employment and Wages annual averages by area
- Publisher: U.S. Bureau of Labor Statistics
- Data year: 2025
- Final release vintage: August 28, 2026
- Measures: annual-average covered employment, annual-average establishments,
  current-dollar total annual wages, current-dollar average weekly wages, and
  private-sector construction employment (NAICS 23)
- Total-covered county coverage: 3,143 of 3,144
- Adapter: `scripts/acquire_bls_qcew_county_baseline.py`

The adapter pins the official annual-by-area ZIP byte size and SHA-256. ZIP and CSV inputs
are deleted with the temporary working directory after parsing; all durable acquisition,
bronze, silver, diagnostic, manifest, and public outputs are JSON. QCEW uses current Census
county codes, including Connecticut planning regions. Kalawao County has no source member
and is explicitly unavailable.

County total-covered rows are ownership code 0, industry code 10, aggregation level 70.
QCEW does not publish an all-ownership county-industry aggregate, so construction is
explicitly limited to private ownership code 5, NAICS 23, aggregation level 74. The 922
construction cells carrying BLS disclosure code `N` are published as suppressed rather
than zero; fourteen more counties have no private-construction row.

## Implemented BEA–BLS county-year panel

- Panel: `county-economic-core-2001-2024`
- Geography: 3,144 current Census counties and county equivalents
- Years: 2001–2024
- Rows: 75,456 county-years
- Governed observations: 301,824
- Measures: real GDP, population, annual-average covered employment, and nominal average
  weekly wage
- Public coverage: 3,064 complete counties, 79 partial counties, one unavailable county
- Builder: `scripts/build_county_economic_history_panel.py`

BEA observations are read from the already pinned February 2026 CAGDP1 and CAINC1
archives. BLS 2001–2020 all-industries members are independently retrieved and pinned from
the official annual-by-industry ZIP archives; 2021–2024 use independently pinned direct
data slices. Only temporary ZIP/CSV transport inputs are used, and durable data remain JSON.
The public projection is delivered as 51 state/DC partitions with a hash-and-size index;
county profiles lazy-load only their selected state partition.

## Governed county first-entry treatment registry

- Treatment definition: `trt_first_entry_v1`
- Geography: 3,144 current Census counties and county equivalents
- Reviewed dated operational events: 172
- Evidence-qualified events: 107
- History-window-qualified events: 95
- Evidence- and history-window-qualified events: 68
- Verified county first-entry dates: 0
- Eligible treatment counties: 0
- Builder: `scripts/build_county_first_entry_treatments.py`

The registry retains NTT's dated SV1 opening release, Apple's environmental report describing
Mesa customer service beginning in March 2017, a contemporaneous October 2006 observation of
operation at QTS Atlanta DC1, SunGard's signed March 27, 2002 filing documenting operation
at the exact present NY7 site in North Bergen, and Switch's year-level account of SUPERNAP/NAP7's
2009 debut, EdgeConneX's March 11, 2015 release establishing operation of its Southfield
facility no later than that date, FiberNet's signed March 28, 2003 filing documenting a
carrier-hotel operation at the exact present ORD11 address, UFIT's maintained history placing
the East Campus Research Computing Center's opening in 2012, and contemporaneous reporting that
Resilient Tier-V's Brunswick facility had opened by September 28, 2011, and Markley's operator
account that Phase One of its Lowell facility was open with customers by November 23, 2015. Clark County's September 3, 2008 franchise filing identifies NAP4 as an existing
data center while NAP7 was still under construction, so NAP7 cannot be the county's first entry.
The Clark candidate passes the panel window but fails the year-precision evidence gate. Fulton
also fails the evidence and pre-period gates; Hudson passes the evidence gate but has only one
available pre-period. Santa Clara, Maricopa, Fulton, Clark, and Monroe are rejected as county first entries
by documented earlier operation. Hudson remains unresolved because the 1987 lease history is not
an opening date and a complete historical inventory has not been established. Indiana University's
November 5, 2009 Data Center dedication passes both evidence and panel gates, but a 2003 IU state
record documents an operating Wrubel Computing Center machine room on October 24, 2001. Monroe's
2009 anchor is therefore rejected while its true first entry remains unresolved. Southfield's
2012-2013 financial report maps the later DET01 site to 21005 Lahser Road before its build-out,
while 123NET's June 20, 2014 operator release documents a separate operating and recently expanded
data center at 24700 Northwestern Highway. Oakland's 2015 DET01 anchor passes both quantitative
gates but is rejected as first entry. Cook's ORD11 anchor passes the evidence gate but has only
two pre-periods; Digital Realty's SEC filing documents the separate 350 East Cermak facility's
1999–2000 data-center conversion, so ORD11 is also rejected as first entry. Alachua's year-only
2012 candidate passes the panel window but fails the evidence threshold; UF's March 31, 2003
administrative record independently identifies the Northeast Regional Data Center as a separate
24/365 multipurpose computing facility, so the East Campus anchor is rejected too. Cumberland's
Brunswick anchor passes the panel window but fails the authoritative-source gate; the University of
Maine System's 2009 report identifies the separate 340 Cumberland Avenue site as an existing Portland
colocation facility, so the Brunswick anchor is also rejected. Middlesex's Markley Lowell anchor
passes both quantitative gates, but CoreSite's SEC property history and Somerville's permit record
document operating colocation space at 70 Inner Belt Road in 2007, so the Lowell anchor is rejected.
Hillsborough's TPA1 anchor passes both quantitative gates, but the Kentucky Public Service
Commission's May 9, 2006 filing places Peak 10 at 9417 Corporate Lake Drive; Florida's 2016
state inventory identifies the exact address as a Peak 10 data center, and Flexential's current
page connects that site to the mapped Tampa–West facility. TPA1 is therefore rejected as county
first entry.
Montgomery's TierPoint Valley Forge anchor passes both quantitative gates. A Kentucky Public
Service Commission filing received April 30, 2013 identifies DBSi at 1000 Adams Avenue as an
operational-redundancy data center, while Focal's August 2000 credit agreement and 2000 annual
report document switch and colocation operations at the separate exact 1000 Forge Avenue,
Building C site by December 31, 2000. Valley Forge is therefore rejected as county first entry.
Mecklenburg's TierPoint CL4 anchor also passes both quantitative gates. Windstream's official
release dates the candidate opening to March 3, 2014; Data Center Knowledge documents Peak 10's
second Charlotte data center operating at its headquarters by July 28, 2006, and Flexential's
SOC 3 report identifies the successor Charlotte - South facility at the exact mapped 8910 Lenox
Pointe Drive address. CL4 is therefore rejected as county first entry.
These counties'
true first entries remain unresolved. Public county
assessments
are JSON-only and split into 51 state/DC partitions. Missing reviewed events do not establish
a never-treated comparison group.

## Governed county first-entry research queue

- Policy: `config/v1/first-entry-research-policy.json`
- Eligible research counties: 217
- Initial tranche: 24 counties, six per Census region
- National backlog: 193 counties
- Active-facility counties excluded for incomplete history: 9
- Builder: `scripts/build_first_entry_research_queue.py`

The prioritization uses only governed local inputs: canonical facility counts, reviewed
lifecycle results, treatment-candidate counts, 2001–2024 panel completeness, and IM3 source
identity coverage. It introduces no new external factual claims. Public queue records are
JSON-only and split into 51 state/DC partitions. Evidence collection for the initial tranche
must use the source protocol in the policy; ranking alone cannot establish first entry.

Research is complete for all 217 candidates. The final baseline contains 59 rejected anchors
with documented predecessors, 113 unresolved dated anchors, and 45 counties without an
adjudicated dated anchor.

## Governed county first-entry resolution queue

- Policy: `config/v1/first-entry-resolution-policy.json`
- Successor candidates: 217
- Tracks: 59 predecessor promotions, 113 retained anchors, 45 anchor-establishment cases
- Initial tranche: 24 counties, six per Census region
- National backlog: 193 counties
- Evidence-collected: 24 (9 candidate rejections, 15 unresolved)
- Remaining queued: 193
- Builder: `scripts/build_first_entry_resolution_queue.py`

The resolution queue preserves all prior adjudications and creates new candidate lineage.
Selection uses governed evidence and audit-feasibility metadata only. The complete registry,
initial tranche, and 51 state/DC partitions are static JSON. A successor candidate—even one
that passes both quantitative gates—does not become a treatment until a new adjudication
verifies exact facility identity, county inventory completeness, and a conclusive search for
earlier operations.

The two resolution evidence tranches are stored in
`config/v1/first-entry-resolution-tranche-*-evidence-sources.json`, with their 24 decisions in the
matching `first-entry-resolution-tranche-*-adjudications.json` files. The second tranche completes
initial ranks 9–24 with state, local, legislative, regulatory, operator, and contemporaneous source
records. Public copies and all referenced source metadata are emitted as static JSON under
`site/public/data/v1/treatments/county-first-entry-resolution/`.

The panel retains current Census identities without crosswalking legacy source geographies.
Connecticut planning regions consequently lack BLS rows before their 2024 adoption, and the
BEA combined/legacy geography limitations remain. Missing cells and 26 suppressed
total-covered observations are explicit rather than zero.

## Candidate-adjudication evidence

The entity-review layer uses ten additional official or first-party source records:
operator facility pages and specification sheets from Centersquare, Digital Realty,
Equinix, Flexential, CoreSite, Rad Web Hosting, and QTS; a Digital Realty SEC filing; and
FY 2026 Department of Defense project data for the Texas Cryptologic Center. Only source
metadata and paraphrased findings are retained. Page bodies are not copied into the
repository.

Curated evidence metadata lives in `config/v1/im3-candidate-evidence-sources.json`, and
the one-to-one candidate decisions live in `config/v1/im3-candidate-adjudications.json`.
The deterministic builder is `scripts/adjudicate_im3_candidates.py`.

## Final campus-boundary evidence

The two escalated campus-boundary cases use three additional evidence sources: official
OpenStreetMap way revision histories, the One Wilshire building-management page, and the
4010 Data Center facility-specification page. The four complete OSM histories are retained
as JSON at `data/raw/openstreetmap/im3-final-boundary-way-history.json`, with a separate
JSON acquisition manifest containing the request URL, retrieval time, response status,
content hash, license, and parser version. No page body from the first-party sites is
stored; only source metadata and paraphrased findings are retained.

The reproducible acquisition adapter is `scripts/acquire_osm_boundary_histories.py`.
Final decisions are versioned in `config/v1/im3-final-boundary-decisions.json`, and the
downstream snapshot is built by `scripts/finalize_im3_boundary_reviews.py`.

## Lifecycle-pilot evidence

The completed 24-facility pilot uses official operator pages and local, state, regulatory,
permit, and assessor records. Evidence metadata and paraphrased findings are versioned in
`config/v1/lifecycle-tranche-1-*` and `config/v1/lifecycle-tranche-2-*`; copyrighted page
bodies are not retained. A reproducible JSON snapshot is retained for the Prince William
County GIS query because its current IAD14, IAD52, and IAD59 statuses conflict with the
county’s June 2024 inventory.

Facility-specific capacity or floor area is accepted only when the source defines the
measure for that facility. Colocation space is not treated as total building area, and
campus or market evidence is not projected onto an unnamed building. The tranche builders
are `scripts/adjudicate_lifecycle_tranche_1.py` and
`scripts/adjudicate_lifecycle_tranche_2.py`.

## National lifecycle expansion policy

The national queue adds no new source claims. It is a deterministic research-order layer
built from the final identity snapshot and completed pilot results. The governed policy is
`config/v1/lifecycle-national-expansion-policy.json`; it defines source precedence by
permitted use, requires two matching facility identifiers, prohibits campus-to-building and
market-to-building projection, and routes official-source conflicts to disputed review.

The builder `scripts/build_national_lifecycle_queue.py` publishes the complete priority
index, the balanced 48-facility initial tranche, the pilot-yield analysis, national county
coverage, metadata, and a content-hashed manifest. These outputs are JSON and contain no
copied source page bodies.

## First national lifecycle evidence batch

Initial-tranche ranks 1–8 use ten exact-facility sources: current Digital Realty pages for
CH1 and ORD11, current Equinix pages for SV2 and NY7, the current Cologix SV1 page, a Town of
Trumbull statement for the 80 Merritt Boulevard building, and Loudoun County permit reports
for IAD10 and IAD32 rack installations, plus signed SunGard and FiberNet SEC filings establishing
dated operation at the current NY7 and ORD11 addresses. Only governed metadata, paraphrased findings, claims,
review decisions, and normalized observations are retained; source page bodies are not
copied.

Evidence metadata is versioned in
`config/v1/national-lifecycle-tranche-1-evidence-sources.json`, and the one-to-one decisions
are in `config/v1/national-lifecycle-tranche-1-adjudications.json`. The deterministic builder
is `scripts/adjudicate_national_lifecycle_tranche_1.py`.

The Trumbull record establishes present operation at the exact building but describes
Digital Realty as the former operator, so the legacy seed label is retained only for record
continuity. Equinix publishes colocation space for SV2 and NY7; those figures remain source
context and are not normalized as total building area. The SEC filings establish conservative
operational-no-later-than dates for NY7 and ORD11; the other sources do not establish opening dates.

## Second national lifecycle evidence batch

Initial-tranche ranks 9–16 use current first-party pages or specification sheets from
Equinix, TierPoint, Digital Realty, QTS, Csquare, and H5 Data Centers. They establish exact
facility identity and current operation for six buildings. Five exact-facility observations
are normalized: building area for PHX15, QTS Piscataway DC1, and H5 Phoenix, plus capacity for
Csquare TPA1 and H5 Phoenix. Colocation space, raised-floor space, lower-bound totals, and
campus or expansion capacity remain contextual.

CMH56 and CMH59 use a City of New Albany project list, independent reporting on the Beech
Road AWS development, and exact-code directory leads. The official and independent sources
do not map either code to the IM3 building, and the directory records cannot establish status
alone under the national policy; both therefore remain unresolved.

Evidence metadata is versioned in
`config/v1/national-lifecycle-tranche-2-evidence-sources.json`, decisions are in
`config/v1/national-lifecycle-tranche-2-adjudications.json`, and the deterministic builder is
`scripts/adjudicate_national_lifecycle_tranche_2.py`. Only metadata and paraphrased findings
are retained.

## Third national lifecycle evidence batch

Initial-tranche ranks 17–24 use current first-party records from FirstLight, Element Critical,
the University of Florida, Sandia National Laboratories, Markley Group, EdgeConneX, and
CoreSite, supplemented by state or local records where a current operator page does not publish
the mapped street address. Seven facilities resolve operational. The normalized exact-facility
observations are building area for FirstLight Brunswick, Element Critical Chicago Two, Markley
Lowell, EdgeConneX DET01, and CoreSite AT2, plus power capacity for Chicago Two and DET01.
EdgeConneX's March 11, 2015 connectivity-partnership release supplies DET01's conservative
operational-no-later-than event, while Southfield's 2012-2013 financial report establishes that
the exact 21005 Lahser Road site was still a vacant shell before build-out. UFIT's maintained
history supplies the second event, a year-precision 2012 opening for the East Campus facility.

SAP's current list establishes a Colorado Springs data-center location, and a Pikes Peak Regional
Building Department record establishes data-center construction at 2345 Windswept View. The
reviewed official sources do not map COS02 to that address; because the exact mapping comes only
from a directory, the building remains unresolved under the national policy.

Evidence metadata is versioned in
`config/v1/national-lifecycle-tranche-3-evidence-sources.json`, decisions are in
`config/v1/national-lifecycle-tranche-3-adjudications.json`, and the deterministic builder is
`scripts/adjudicate_national_lifecycle_tranche_3.py`. Only metadata and paraphrased findings are
retained.

## Fourth national lifecycle evidence batch

Initial-tranche ranks 25–32 use current first-party or official records from Prime Data
Centers, Equinix, Phillips Exeter Academy, the City of Papillion, IBM, QTS, Lumen, and
Csquare, supplemented by historical filings and directory records for identity discovery.
Prime DFW01-01, Equinix SE3, Phillips Exeter's Data Center, Fidelity Papillion, and the
Csquare Lynnwood building resolve operational. Three exact-facility observations are
normalized: building area and power capacity for Prime DFW01-01, and power capacity for
Csquare Lynnwood.

Lumen's current materials do not name its Norristown building, current CyrusOne material
does not corroborate the legacy CIN3 mapping, and QTS's current Irving campus page does not
map DAL10 to one of its six buildings. Those three records remain unresolved rather than
projecting regional or campus evidence onto a building.

Evidence metadata is versioned in
`config/v1/national-lifecycle-tranche-4-evidence-sources.json`, decisions are in
`config/v1/national-lifecycle-tranche-4-adjudications.json`, and the deterministic builder is
`scripts/adjudicate_national_lifecycle_tranche_4.py`. Only metadata and paraphrased findings
are retained.

## Fifth national lifecycle evidence batch

Initial-tranche ranks 33–40 use current operator records from TierPoint, Google, Csquare,
Serverfarm, CyrusOne, Union Pacific, Microsoft, and Switch, supplemented by Papillion permits,
PeeringDB, Prince William County's live data-center building layer, and Clark County's Switch
operating permit. TierPoint Valley Forge, Csquare DFW2, Serverfarm LAX1, CyrusOne NYM5, and
Switch Las Vegas 12 resolve operational. Five exact-facility observations are normalized:
capacity for DFW2, area and capacity for LAX1, and area and capacity for NYM5.

Google's current record remains campus-level, and the exact Union Pacific claim remains supported
only by a directory, so those buildings are unresolved. Prince William County's GIS creates a
material identity conflict for Microsoft Data Center 1: the selected point is completed Corscale
GCDC1, while Microsoft's named MNZ08 is a separate pending building. The record is disputed and
reserved for entity correction rather than assigned either building's lifecycle status.

Evidence metadata is versioned in
`config/v1/national-lifecycle-tranche-5-evidence-sources.json`, decisions are in
`config/v1/national-lifecycle-tranche-5-adjudications.json`, and the deterministic builder is
`scripts/adjudicate_national_lifecycle_tranche_5.py`. Only metadata and paraphrased findings are
retained.

## Sixth national lifecycle evidence batch

Initial-tranche ranks 41–48 use current operator records from Flexential, Switch, Indiana
University, QTS, Comcast, and Verizon, supplemented by New York Power Authority, Orangetown,
Clark County, property-discovery, location, and market-availability records. Flexential
Alpharetta, Switch Las Vegas 7, Bloomberg Orangeburg, IU Bloomington, and QTS ATL1 DC1 resolve
operational. The former Flexential operation at 744 Roble Road resolves closed; the building's
availability is not treated as closure of the physical asset.

The Comcast Southgate property lead describes an office-scale improvement, and Comcast's current
local service page does not establish a data center at that building. Verizon's current material
establishes Colorado data-center capacity only at state level, while the selected Centennial
footprint is adjacent to a communications tower. Both records remain unresolved rather than
projecting market-level or telecommunications evidence onto a building.

Evidence metadata is versioned in
`config/v1/national-lifecycle-tranche-6-evidence-sources.json`, decisions are in
`config/v1/national-lifecycle-tranche-6-adjudications.json`, and the deterministic builder is
`scripts/adjudicate_national_lifecycle_tranche_6.py`. Only metadata and paraphrased findings are
retained.

Four source rows reported Prince William County, Virginia, while their centroids fall in
Manassas under the published 2025 Census polygons. Both values remain auditable: bronze
records preserve the source report and canonical/public geography uses point-in-polygon.
Five polygon objects span two counties; their multi-county assignments are retained
without an unsupported area allocation.

Each acquisition adapter must create an acquisition manifest and source artifact record
containing the request URL, retrieval time, response status, content hash, storage policy,
license, and parser version. A mutable URL without retrieval metadata is insufficient.

Discovery sources such as news archives and search indexes identify candidates. They do
not automatically establish canonical facts. Attribute-specific evidence quality and
independence are considered during claim resolution.

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

- Panel: `county-economic-core-2021-2024`
- Geography: 3,144 current Census counties and county equivalents
- Years: 2021–2024
- Rows: 12,576 county-years
- Governed observations: 50,304
- Measures: real GDP, population, annual-average covered employment, and nominal average
  weekly wage
- Public coverage: 3,081 complete counties, 62 partial counties, one unavailable county
- Builder: `scripts/build_county_economic_history_panel.py`

BEA observations are read from the already pinned February 2026 CAGDP1 and CAINC1
archives. Four BLS total-all-industries annual slices are independently pinned by byte size
and SHA-256. The source services expose 2021 onward as direct slices; older years require
the substantially larger historical archive route and are therefore a separate backfill.

The panel retains current Census identities without crosswalking legacy source geographies.
Connecticut planning regions consequently lack BLS rows before their 2024 adoption, and the
BEA combined/legacy geography limitations remain. Missing cells and the two suppressed
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

Initial-tranche ranks 1–8 use eight exact-facility sources: current Digital Realty pages for
CH1 and ORD11, current Equinix pages for SV2 and NY7, the current Cologix SV1 page, a Town of
Trumbull statement for the 80 Merritt Boulevard building, and Loudoun County permit reports
for IAD10 and IAD32 rack installations. Only governed metadata, paraphrased findings, claims,
review decisions, and normalized observations are retained; source page bodies are not
copied.

Evidence metadata is versioned in
`config/v1/national-lifecycle-tranche-1-evidence-sources.json`, and the one-to-one decisions
are in `config/v1/national-lifecycle-tranche-1-adjudications.json`. The deterministic builder
is `scripts/adjudicate_national_lifecycle_tranche_1.py`.

The Trumbull record establishes present operation at the exact building but describes
Digital Realty as the former operator, so the legacy seed label is retained only for record
continuity. Equinix publishes colocation space for SV2 and NY7; those figures remain source
context and are not normalized as total building area. No source in this batch establishes
a defensible operational start date.

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

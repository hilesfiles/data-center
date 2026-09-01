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

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

Each acquisition adapter must create an acquisition manifest and source artifact record
containing the request URL, retrieval time, response status, content hash, storage policy,
license, and parser version. A mutable URL without retrieval metadata is insufficient.

Discovery sources such as news archives and search indexes identify candidates. They do
not automatically establish canonical facts. Attribute-specific evidence quality and
independence are considered during claim resolution.

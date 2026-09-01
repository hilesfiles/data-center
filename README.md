# U.S. Data Center Community Impact Observatory

This repository contains the schema-first foundation and first static application slice
for the Observatory. County boundaries and identity fields come from the authoritative
2025 Census TIGERweb release. The facility seed is a provisional, OSM-derived projection
of IM3 Atlas v2026.02.09 source records. It is not a complete or lifecycle-verified
operating-facility inventory, and the application contains no impact findings.

The initial deliverables are:

- a conceptual data model in `docs/data-model.md`;
- a JSON-only persistence and publication contract in `docs/json-storage-contract.md`;
- versioned JSON Schemas in `schemas/v1/`;
- difficult-case fixtures in `fixtures/v1/`;
- schema and referential-integrity validation in `scripts/validate_data_contract.py`.
- versioned research configuration in `config/v1/`;
- a React, TypeScript, Vite, and MapLibre GitHub Pages site in `site/`;
- GitHub Actions for contract validation, site build, and Pages deployment.

Run validation with the bundled or system Python interpreter:

```powershell
python scripts/validate_data_contract.py
```

Rebuild the national county geography from the Census TIGERweb API:

```powershell
python scripts/acquire_census_counties.py
```

That adapter has no third-party dependency and writes only JSON-family artifacts: an
acquisition manifest, normalized geography JSON, a dataset manifest, and the compact
GeoJSON consumed by the browser.

Rebuild the provisional IM3 facility seed:

```powershell
python scripts/acquire_im3_facilities.py
```

The pinned GeoPackage is used only as a temporary transport input and is deleted after
processing. Durable bronze, silver, provenance, observation, manifest, and public outputs
are JSON or GeoJSON.

Rebuild the conservative IM3 identity-resolution layer from those JSON artifacts:

```powershell
python scripts/resolve_im3_entities.py
```

This offline step links only unambiguous campus containment, normalizes operator strings
only for Unicode/case/whitespace equivalence, and emits ambiguous spatial matches as a
JSON review queue. It does not merge physical source records.

Apply the curated candidate adjudications and rebuild the reviewed public overlays:

```powershell
python scripts/adjudicate_im3_candidates.py
```

The adjudication input is itself versioned JSON under `config/v1/`. Source records are
never deleted: reviewed duplicates redirect to a canonical facility, while separately
operated sites inside larger buildings receive an explicit containment relationship.

Acquire the official OSM histories and resolve the two final boundary escalations:

```powershell
python scripts/acquire_osm_boundary_histories.py
python scripts/finalize_im3_boundary_reviews.py
```

The acquisition retains only JSON. Finalization is offline and downstream: it preserves
the initial adjudication, marks the two earlier escalation decisions superseded, and emits
the final static review projections consumed by the site.

Build the static site:

```powershell
cd site
pnpm install --frozen-lockfile
pnpm run build
```

Run it locally with `pnpm run dev` from `site/`.

The validator has no third-party runtime dependency. It checks JSON parsing, schema
catalog integrity, local `$ref` resolution, required top-level fields, fixture
referential integrity, and expected valid/invalid fixture outcomes. Full JSON Schema
validation can be added later to CI with a standards-compliant Draft 2020-12 validator.

## Current coverage

- JSON-only domain and analytical contracts: implemented as schema v1.0.0.
- Configuration and taxonomy validation: implemented.
- Static map/application build: implemented with authoritative geography and provisional
  IM3 source-record coverage.
- National Census boundaries: implemented for 3,144 county and county-equivalent records
  across the 50 states and District of Columbia, January 1, 2025 vintage.
- PNNL/IM3 facility seed: implemented from v2026.02.09 with 1,479 source rows, 1,472
  in-scope source objects, 1,340 provisional facility candidates, and 132 campuses.
- Facility coverage: 249 counties have one or more source records; absence from the source
  is not interpreted as zero facilities.
- Entity resolution: 255 facility-to-campus links and 953 source-backed operator
  relationships are represented as provisional governed decisions. All sixteen spatial
  candidates are resolved: four source-record merges, eight distinct contained sites,
  two accepted campus links, and two rejected campus links. No candidate remains pending.
- Economic, fiscal, utility, housing, environmental, or opposition observations: not yet ingested.
- Econometric estimates and public indices: fixture-only; not substantive.

## Next priority

Enrich operator organizations beyond exact-text normalization, then reconstruct verified
opening and project dates needed for the first historical treatment panel.

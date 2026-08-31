# U.S. Data Center Community Impact Observatory

This repository contains the schema-first foundation and first static application slice
for the Observatory. County boundaries and identity fields come from the authoritative
2025 Census TIGERweb release. Facility and analytical records remain fictional fixtures;
the application contains no research findings.

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
- Static map/application build: implemented with authoritative geography and clearly
  labeled fictional facility/analytical fixtures.
- National Census boundaries: implemented for 3,144 county and county-equivalent records
  across the 50 states and District of Columbia, January 1, 2025 vintage.
- PNNL/IM3 facilities: not yet ingested.
- Economic, fiscal, utility, housing, environmental, or opposition observations: not yet ingested.
- Econometric estimates and public indices: fixture-only; not substantive.

## Next priority

Ingest the PNNL/IM3 facility seed while preserving source identifiers, evidence lineage,
and ODbL attribution. Facility-to-county assignment must use the published Census
geography and remain a precomputed JSON join.

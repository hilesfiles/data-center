# JSON storage and static publication contract

## Decision

All persisted project data use the JSON family. There is no canonical Parquet, CSV,
SQLite, or DuckDB artifact. Offline code may use in-memory tabular structures while
building outputs, but the durable inputs, intermediate zones, analytical results, and
GitHub Pages artifacts are JSON, JSON Lines, or GeoJSON.

## Formats

| Format | Use |
|---|---|
| `.json` | registries, configuration, manifests, small collections, model cards |
| `.jsonl` | append-oriented entities, claims, events, observations, estimates |
| `.geojson` | county boundaries, campuses, facilities, and other map features |

Every JSONL line is one complete object conforming to the named record schema. JSONL
files do not contain an enclosing array.

## Data zones

```text
data/raw/       acquisition metadata and redistributable source artifacts
data/bronze/    parsed source-shaped JSON/JSONL
data/silver/    normalized entities, evidence, and observations
data/gold/      analytical inputs, model results, and indices
public/data/    licensed static site projections
```

Upstream zones are immutable within a build. A downstream rebuild writes new artifacts
and manifests; it does not mutate raw evidence.

## Artifact envelope

Small collection artifacts use this envelope:

```json
{
  "schema_version": "1.0.0",
  "artifact_type": "facility_collection",
  "artifact_version": "2026-08-31+gitsha",
  "generated_at": "2026-08-31T12:00:00Z",
  "data_vintage": "2026-08-31",
  "record_schema": "https://dccio.org/schemas/v1/facility.schema.json",
  "record_count": 1,
  "sha256": "...",
  "records": []
}
```

Large JSONL artifacts use a neighboring manifest with the same information plus ordered
part names, byte sizes, record counts, and SHA-256 hashes.

## Partitioning

Research JSONL is partitioned by stable, low-cardinality dimensions and bounded file
size. Preferred partitions are entity type, observation year, state, and model run.
Do not create millions of tiny files.

Public delivery uses:

```text
public/data/v1/metadata.json
public/data/v1/national/summary.json
public/data/v1/states/{state_abbr}.json
public/data/v1/counties/index.json
public/data/v1/counties/facility-source-coverage.json
public/data/v1/counties/entity-resolution-coverage.json
public/data/v1/counties/entity-adjudication-coverage.json
public/data/v1/counties/{county_fips}/summary.json
public/data/v1/counties/{county_fips}/timeseries.json
public/data/v1/counties/{county_fips}/evidence.json
public/data/v1/facilities/index.json
public/data/v1/entity-resolution/index.json
public/data/v1/entity-resolution/metadata.json
public/data/v1/entity-resolution/adjudication-index.json
public/data/v1/entity-resolution/adjudication-metadata.json
public/data/v1/entity-resolution/review-queue.json
public/data/v1/entity-resolution/review-decisions.json
public/data/v1/entity-resolution/review-dossier.json
public/data/v1/facilities/{facility_id}.json
public/data/v1/maps/counties.geojson
public/data/v1/maps/facilities.geojson
```

The initial map request downloads only metadata, simplified county geometry, and a compact
county index. Evidence and time series load on demand.

## References

Durable records reference other records by ID. Public projection files may embed compact
denormalized labels for display but retain the canonical IDs. Referential integrity is
validated before publication.

## Numbers, dates, and nulls

- Store JSON numbers as numbers, never formatted strings.
- Monetary values include ISO currency and nominal/real basis.
- Quantities include unit and value status.
- Calendar dates use ISO 8601. Uncertain dates use lower/upper bounds and precision.
- Absence is not encoded as zero.
- A known missing value uses an explicit status and reason; optional fields may be absent
  only when the concept is not part of that record.
- Non-finite values (`NaN`, `Infinity`) are forbidden.

## Static-site guarantees

The browser performs filtering, selection, and display only. Entity resolution, joins,
counterfactual estimation, uncertainty simulation, index construction, and summary
aggregation occur before publication. A public artifact cannot require a runtime DBMS.

## Compatibility

Every record has `schema_version`. Consumers reject unsupported major versions and may
accept later compatible minor versions. Public artifact paths are major-versioned.

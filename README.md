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

Rebuild the BEA 2024 county economic baseline:

```powershell
python scripts/acquire_bea_county_economic_baseline.py
```

The adapter pins BEA's February 5, 2026 CAGDP1 and CAINC1 releases, uses the ZIP
and CSV files only as temporary transport inputs, and publishes governed JSON for
real GDP, nominal personal income, population, and nominal per-capita personal income.
BEA combined geographies are not allocated to individual Census counties.

Rebuild the BLS QCEW 2025 county employment and wage baseline:

```powershell
python scripts/acquire_bls_qcew_county_baseline.py
```

The adapter pins the final official annual-by-area archive, uses ZIP and CSV only as
temporary transport formats, and publishes governed JSON for annual-average covered
employment, establishments, nominal total and weekly wages, and private construction
employment. Disclosure-protected cells remain suppressed rather than becoming zero.

Rebuild the BEA–BLS county-year history panel:

```powershell
python scripts/build_county_economic_history_panel.py
```

The panel materializes 2001–2024 observations and schema-valid panel-row references for
real GDP, population, annual-average covered employment, and nominal average weekly wages.
Its history can support the configured seven-pre/three-post windows and remains descriptive
rather than model-ready.
The public history is split into 51 state/DC JSON partitions. The browser loads a partition
only after a county in that state is selected, and `#/county/{FIPS}` provides a shareable
county profile without requiring thousands of duplicate HTML pages.

Rebuild the governed county first-entry treatment registry:

```powershell
python scripts/build_county_first_entry_treatments.py
```

The registry evaluates reviewed dated operational events against the configured evidence
and panel-window rules, then requires a separate explicit verification that the event is the
county's first data-center entry. It publishes 51 lazy-loaded state/DC JSON partitions.
The current evidence contains 78 reviewed dated facility events. Forty-six pass the evidence
gate and 47 pass the panel-window gate, but zero have verified county-first-entry status, so model readiness is
`insufficient_eligible_treatments` and no model run is authorized. Absence of a reviewed event
is never interpreted as never treated.

Rebuild the governed county first-entry research queue:

```powershell
python scripts/build_first_entry_research_queue.py
```

The queue contains 217 counties that have at least one active canonical facility and all 24
years of core panel history. A deterministic policy selects a 24-county initial tranche with
six counties per Census region and no more than two per state. Scores order evidence work
only; they do not assign a treatment date, first-entry status, or comparison-group status.
The browser lazy-loads the queue through 51 state/DC JSON partitions.

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

Build the deterministic lifecycle-verification pilot from the final identity snapshot:

```powershell
python scripts/build_lifecycle_verification_pilot.py
```

The governed JSON policy selects 24 canonical facilities—three in each of the eight
highest-density counties—and publishes a static research queue plus national county
coverage. Selection changes research priority only; all lifecycle statuses remain unknown
until source claims are reviewed.

Acquire the current Prince William County GIS evidence snapshot and rebuild the first
governed evidence tranche:

```powershell
python scripts/acquire_pwc_lifecycle_gis.py
python scripts/adjudicate_lifecycle_tranche_1.py
python scripts/adjudicate_lifecycle_tranche_2.py
```

The downstream tranches keep earlier queue snapshots immutable, record source claims and
human review decisions in JSON, and publish separate verified, partial, disputed, and
remaining-queue states. Tranche two completes the governed review of the pilot.

Build the governed national lifecycle priority index and balanced first tranche:

```powershell
python scripts/build_national_lifecycle_queue.py
```

The national policy converts the pilot findings into explicit JSON rules for evidence
precedence, exact-building attribution, source conflicts, stop conditions, scoring, and
regional/operator diversity. It ranks all 1,327 facilities whose status remains unknown
and selects a 48-facility first tranche with twelve records from each Census region.

Adjudicate the first eight records in that national tranche from the governed evidence
metadata and review decisions:

```powershell
python scripts/adjudicate_national_lifecycle_tranche_1.py
python scripts/adjudicate_national_lifecycle_tranche_2.py
python scripts/adjudicate_national_lifecycle_tranche_3.py
python scripts/adjudicate_national_lifecycle_tranche_4.py
python scripts/adjudicate_national_lifecycle_tranche_5.py
python scripts/adjudicate_national_lifecycle_tranche_6.py
```

These downstream builds preserve the original 48-record tranche, publish all forty-eight reviewed
results and an empty remaining queue, and roll the verified, unresolved, and disputed states into
national county coverage. All generated artifacts remain JSON.

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
- Lifecycle verification: all 24 pilot facilities and all 48 records in the balanced initial
  national tranche have been reviewed. The final batch resolves Flexential Alpharetta, Switch
  Las Vegas 7, Bloomberg Orangeburg, the IU Bloomington Data Center, and QTS ATL1 DC1 as
  operational, and the former Flexential Allentown operation as closed. The small Comcast and
  Verizon-labeled footprints remain in research because reviewed evidence does not establish
  data-center operation at either exact building. Cumulative verified facilities now total 47,
  twenty-one remain in research, four are disputed or need review, and 1,290 statuses remain
  unknown. The immutable initial national tranche spans 23 states, 37 counties, and 32 known
  operators; no record remains queued.
- Economic observations: BEA 2024 real GDP, nominal personal income, population, and
  nominal per-capita personal income are implemented for 3,091 exact current Census
  counties. Fifty-three nonmatching or BEA-combined county equivalents are retained as
  unavailable, never zero. These are descriptive source observations, not impact estimates.
- Employment and wage observations: BLS QCEW 2025 annual totals are implemented for
  3,143 counties, with Kalawao County unavailable. Private construction employment is
  complete for 2,207 counties; 922 disclosure-protected cells remain suppressed and
  fourteen additional county construction rows are absent. Suppressed values are never zero.
- Historical panel: the BEA–BLS core panel contains 75,456 county-year rows and
  301,824 governed observations for 2001–2024. It is complete for 3,064 counties, partial
  for 79, and unavailable for Kalawao County. It is research infrastructure, not a model run.
- County first-entry treatment: all 3,144 counties have governed assessments. Dated candidates
  in Santa Clara, Maricopa, Fulton, Clark, Monroe, Oakland, Cook, Alachua, Cumberland, Middlesex, Hillsborough, Montgomery, and Mecklenburg counties are each rejected by
  documented earlier operations. Hudson County has an exact-facility operational-no-later-than anchor dated
  March 27, 2002, but its true first entry remains unresolved. The Santa Clara and Maricopa
  events pass evidence and history-window thresholds; Clark passes the history window but not
  the year-precision evidence threshold, Monroe passes both gates but has a documented 2001
  predecessor operation, Oakland passes both gates but has a documented earlier 123NET operation,
  Cook passes the evidence gate but has only two pre-periods and a documented earlier 350 East
  Cermak operation, Alachua passes the history window but its year-only date fails the evidence
  threshold and a separate UF data center was operating in 2003, and Cumberland passes the history
  window but its local-news anchor fails the authoritative-source gate and 340 Cumberland Avenue was
  already an existing Portland colocation facility in 2009. Middlesex passes both gates but its
  Markley Lowell anchor follows CoreSite BO1's documented 2007 operation. Hillsborough passes both
  gates, but its TPA1 anchor follows the mapped Tampa–West facility's documented presence at 9417
  Corporate Lake Drive by 2006. Montgomery passes both gates, but its TierPoint Valley Forge
  anchor follows Focal Communications switch and colocation operations documented at the exact
  1000 Forge Avenue, Building C site by the end of 2000. Mecklenburg passes both gates, but its
  TierPoint CL4 anchor follows Peak 10's documented Charlotte headquarters data-center operation
  at the exact mapped 8910 Lenox Pointe Drive site by July 2006. Fulton and Hudson also do
  not pass both gates.
  Zero counties are currently treatment-eligible and no county is classified as never treated.
- County first-entry research: 217 facility counties meet the complete-history prerequisite.
  Twenty-four are in the balanced initial tranche and 193 remain in the national backlog;
  nine additional facility counties lack a complete 24-year panel. Queue membership is not
  evidence of treatment eligibility.
- Fiscal, utility, housing, environmental, or opposition observations: not yet ingested.
- Econometric estimates and public indices: fixture-only; not substantive.

## Next priority

Continue the remaining 10 counties in the initial tranche against local-government, permit,
planning, assessor, utility, regulatory, operator, and contemporaneous news records. Each
adjudication must
identify the earliest dated operation, establish exact facility identity, assess county
inventory completeness, and document the search for earlier operations. Do not estimate
impacts until enough treatments and defensible comparison counties satisfy the registered
evidence and period requirements.

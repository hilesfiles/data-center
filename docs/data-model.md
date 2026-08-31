# DCCIO conceptual data model

## Purpose

This document defines the durable domain model for the U.S. Data Center Community
Impact Observatory before acquisition code or a user interface is built. It translates
the bootstrap and modeling specifications into an implementable JSON-first contract.

The model has six bounded domains: infrastructure, evidence, measurements, analytical
models, indices, and public projections. A record belongs to one domain and references
records in other domains by stable identifier. Public projections are disposable,
rebuildable views; evidence and reviewed resolutions are durable research records.

## Modeling rules

1. A source makes a claim. A claim does not directly mutate a canonical entity.
2. A resolution selects or constructs a canonical value while preserving every claim.
3. Observed, derived, estimated, modeled, imputed, suppressed, and missing values are
   distinct states.
4. A facility is a persistent physical operating asset. It is not an operator name.
5. A campus is a geographic grouping that may contain several facilities and may cross
   jurisdictional boundaries.
6. A project is a development proposal attached to a campus or facility. A project may
   contain phases and may never become operational.
7. An event records a lifecycle occurrence. Events do not overwrite prior events.
8. Measurements are long-form facts keyed by metric, geography/entity, and time. Wide
   county summary objects are generated publication projections, not source-of-truth
   analytical records.
9. Model estimates are separate from observed measurements and always reference a
   registered model run.
10. Every persisted record carries `schema_version`; every generated artifact carries
    its data and model vintage.

## Domain overview

```text
Source -> Claim -> ClaimResolution -> Canonical entity attribute
              \-> ReviewDecision

Campus -> Facility -> Project -> ProjectPhase -> Event
             |             |
             +-> OperatorRelationship <- Operator

Entity/Geography + Metric + Period -> Observation
Observation + TreatmentDefinition + ModelSpecification -> ModelRun
ModelRun -> Estimate + Diagnostic + DonorWeight
Estimates/Observations -> IndexScore -> Public county/state/national projections
```

## Infrastructure domain

### Campus

A bounded or approximate geographic development area. A campus can contain one or more
facilities and projects. It may have several county allocations when its geometry spans
county lines.

### Facility

A persistent physical data-center building or independently operated site. Renaming,
sale, acquisition, or operator replacement does not create a new facility. A materially
separate building may be a new facility within the same campus.

### Project

A proposed development undertaking. It can target a campus, an existing facility, or a
new facility that has not yet been resolved. Canceled, rejected, withdrawn, and
never-built projects remain first-class records.

### Project phase

A separately announced, permitted, constructed, or energized portion of a project.
Capacity, area, capital expenditure, and job commitments belong to sourced observations
or claims about a phase rather than being silently rolled into a facility total.

### Operator and operator relationship

The operator is an organization. The relationship record supplies effective dates and
the role (operator, owner, developer, tenant, or former operator). This preserves
operator history without changing facility identity.

### Event

A dated or bounded lifecycle occurrence linked to a facility, project, phase, campus,
or policy action. Date precision and earliest/latest bounds are mandatory whenever the
exact date is unknown.

## Evidence domain

### Source

Bibliographic and retrieval metadata for a government record, filing, announcement,
article, dataset, poll, petition, or other evidence source. Copyright and redistribution
policy are explicit.

### Source artifact

The particular downloaded file, archived capture, attachment, or API response used by
the pipeline. Multiple artifacts can belong to the same logical source. Hashes identify
the actual acquired bytes without requiring copyrighted content to be published.

### Claim

A source assertion about an entity attribute or relationship. Its value is a typed value
supporting text, number, quantity, date/interval, boolean, classification, identifier,
or structured JSON. Claims retain raw and normalized forms and the extraction context.

### Claim resolution

The auditable decision for one entity attribute. It references winning, supporting, and
conflicting claims and records whether the value is resolved, provisional, disputed, or
left unresolved. A resolution never deletes a losing claim.

### Review decision

A human or governed automated decision about entity matching, claim resolution,
classification, or publication eligibility. Revisions supersede earlier decisions by ID.

### Entity-resolution candidate

A non-decision work item linking two or more existing entities to the evidence that made
them plausible matches. Candidates retain the governed rule and spatial predicate that
created them, a recommended review action, and an explicit pending/accepted/rejected
state. Candidate generation never changes canonical identity by itself.

## Measurement domain

An observation stores one metric value for one subject and period. Subjects may be a
county, utility territory, facility, project, phase, state, or nation. Metric definitions
and units are referenced by stable codes. Periods support instants, calendar years,
quarters, months, and bounded ranges.

Observations contain:

- the typed value and unit;
- value status and missingness reason;
- source and claim references;
- derivation method when applicable;
- lower/upper uncertainty bounds;
- release vintage and geography assignment;
- suppression and revision metadata.

`county_year` is therefore a materialized view of observations rather than a monolithic
record with an ever-growing collection of source and model columns.

## Analytical model domain

### Treatment definition

Defines the qualifying lifecycle event, confidence threshold, exposure measure,
construction/operation distinction, spillover rules, and treatment tiers.

### Model specification and run

The specification describes the estimator, outcome, treatment, control group,
covariates, event window, inference, and diagnostics. A model run binds that immutable
specification to input hashes, software versions, code commit, seed, sample, and output
artifacts.

### Estimate and diagnostic

An estimate contains an estimand, geography/cohort/event time, point estimate, standard
error, confidence interval, sample counts, and practical interpretation unit. Diagnostics
store pre-trend tests, balance, RMSPE, placebo results, sensitivity results, and model
confidence grades. Synthetic-control donor weights are explicit records.

## Index domain

Index scores are versioned derived records. Each includes component values, configured
weights, eligible-weight coverage, calibration distribution, uncertainty, stability,
and publication status. OEM, DCEDI, DCFDi, DCCCI, DCOI, BSG, and NCB remain distinct.
BSG and NCB may only be produced when their required input scores are publishable for the
same geography and period.

## Public projection domain

Public JSON is optimized for static delivery and is never the research source of truth.
National and state summaries are small files. County and facility detail are sharded.
Every projection exposes source/model versions, quality, coverage, and uncertainty.

## Stable identifiers

Identifiers are opaque strings with a type prefix and UUID-compatible suffix, for
example `fac_01J...`, `prj_01J...`, or `src_01J...`. Human-readable names, FIPS codes,
URLs, coordinates, and operator aliases are never primary keys. External dataset IDs are
stored as namespaced identifiers.

Recommended prefixes:

| Entity | Prefix |
|---|---|
| campus | `cam_` |
| facility | `fac_` |
| project | `prj_` |
| project phase | `phs_` |
| event | `evt_` |
| operator | `opr_` |
| source | `src_` |
| source artifact | `art_` |
| claim | `clm_` |
| resolution | `res_` |
| review decision | `rev_` |
| entity-resolution candidate | `erc_` |
| observation | `obs_` |
| treatment definition | `trt_` |
| model specification | `msp_` |
| model run | `run_` |
| estimate | `est_` |
| diagnostic | `dia_` |
| index score | `idx_` |

## Referential and temporal invariants

- Every project references an existing campus or facility.
- Every phase references an existing project.
- Every event references at least one valid subject.
- Every claim references a source and a subject, unless it is an unresolved discovery
  candidate with an explicit candidate key.
- Every resolution references at least one claim about the same subject and attribute.
- Effective intervals use half-open semantics `[start, end)` when both bounds are known.
- A closure before an operational event, expansion before initial development, or
  operator relationship outside the facility lifetime is flagged for review rather than
  silently deleted.
- County FIPS is always five digits; names are display attributes, never join keys.

## Schema evolution

The initial contract is `1.0.0`. Additive optional fields may increment the minor
version. Changed meaning, removed fields, or incompatible enumeration changes require a
new major schema directory. Migrations must be explicit; generated public artifacts must
state both their schema version and build version.

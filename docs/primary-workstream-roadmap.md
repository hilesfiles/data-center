# Primary workstream roadmap

11 September 2026. This is the controlling execution plan for the Observatory's
primary research workstream. When an older planning, remediation, or modeling document
describes a different delivery order, this roadmap controls the order of current work.
Those documents remain useful design and audit records, but they do not authorize a
return to isolated project or county enrichment as the default activity.

## Primary objective

Build a national, evidence-governed comparison of U.S. counties with economically
material private-sector data-center development and similar counties without qualifying
exposure. Use that comparison to determine whether data-center construction and operation
are associated with, and where the evidence permits caused, changes in real GDP,
employment, wages, population, tax base, public revenue, public cost, infrastructure, and
resource conditions.

The public product must make four different statements distinguishable:

1. a data center or proposal was documented in a county;
2. a county's economic conditions changed before or after an event;
3. exposed counties changed differently from a defined comparison group; and
4. a model passed the additional evidence and diagnostic gates required for an
   attributable or causal interpretation.

The workstream is not complete when the original 35 counties have detailed profiles. It
is complete only when the national exposure universe has been normalized, an analytically
eligible treated cohort and defensible comparison samples have been produced, and the
resulting descriptive or inferential findings have been published with their limitations.

## Current baseline

The starting position for this roadmap is:

- 36 curated private-sector projects in 35 counties and 23 states;
- 30 project audits marked research-complete, six pending, and zero complete modeled
  county contribution accounts;
- seven rejected or withdrawn data-center proposals stored separately from operating
  projects;
- a 2001–2024 panel covering 3,144 counties and county equivalents, 75,456 county-years,
  and 301,824 governed observations for real GDP, population, covered employment, and
  nominal average weekly wages;
- 17 of the original 35 host counties with a governed treatment-anchor decision, 11 with
  a completed seven-domain treatment-history review, and zero causal-ready treated
  counties;
- 233 unique mechanically matched comparison candidates, one locally reviewed E0
  candidate, and zero controls authorized for a causal run;
- no published causal estimate or impact index.

The repository already contains a much larger facility-source universe:

| Source | Current records | Current county coverage or diagnostic |
| --- | ---: | --- |
| IM3 Open Source Data Center Atlas v2026.02.09 | 1,472 facility/campus records | 249 counties |
| Governed lifecycle inventory | 226 active-facility counties | 217 have a complete 24-year core panel |
| SueDataCenters / Compute Atlas v1.32.0 | 1,300 facility records | 378 counties with operational, under-construction, or permitted records |
| DEPLOY registry snapshot, 2026-09-09 | 3,431 reviewed facility records | 2,092 records currently resolve to 197 counties; 1,339 remain geographically unresolved |

The two external registries presently identify 413 unique counties containing at least
one operating, operational, under-construction, or permitted record under the current
matching diagnostic. This is a candidate-source count, not a verified treatment count.
It nevertheless establishes that the 35-county register is a curated case-study seed and
not the national treated-county universe.

## The three scopes that must remain separate

1. **National facility universe.** Every retained source record, including operating,
   construction, permitted, announced, planned, proposed, rejected, cancelled,
   decommissioned, and unresolved records. Inclusion means only that a source record
   exists.
2. **Analytical county cohort.** Counties with evidence sufficient to classify exposure,
   materiality, timing, panel availability, and model-specific eligibility. This cohort
   is built from governed rules rather than a predetermined county target.
3. **Curated case-study cohort.** The deeply researched project and county pages, presently
   36 projects in 35 counties. These pages provide narrative depth but do not define the
   national analysis population.

Rejected and withdrawn data-center proposals remain a distinct contextual cohort. They
can exclude a county from strict E0 control status and can support separately defined
proposal analyses, but they are not operating treatments. Non-data-center projects are
out of scope.

## Current execution status

| Item | Status at roadmap adoption | Next gate |
| --- | --- | --- |
| Repository checkpoint | Active prerequisite | Clean, validated, synchronized baseline |
| M1 — Governed national inventory | Next primary milestone | Complete Steps 1–4 |
| Step 1 — Source normalization | Queued immediately after checkpoint | One governed output covering all four source families |
| Steps 2–4 — Identity, classification, and geography | Not started as a unified national pipeline | Complete the Step 1 output and diagnostics |
| M2 — Expanded county product | Not started | M1 exit gate |
| M3 — Analysis-ready design | Existing 35-county work is partial; national design not started | M2 exit gate and full-universe ranking |
| M4 — Economic findings | Not started | Authorized treated and comparison samples from M3 |

This table must be updated whenever a milestone or step changes state. Counts belong in
the generated artifacts and progress reports described below; the table records execution
state rather than duplicating changing analytical totals.

## Immediate repository checkpoint

Before the national expansion begins, preserve the completed local work in a coherent
commit, validate it, and synchronize it with the remote. Expansion work must start from a
clean, reproducible baseline so source normalization is not mixed with unresolved county
audit changes.

Exit gate:

- working tree clean;
- local and tracked remote branch synchronized;
- data-contract tests and production site build pass; and
- the checkpoint commit is identified in the first expansion status report.

## Step 1 — Normalize the complete national source inventory

**Purpose:** Turn the already acquired IM3, lifecycle, SueDataCenters, and DEPLOY inputs
into one source-preserving national candidate feed. The larger registries must serve
treated-cohort discovery as well as control contamination screening.

Sub-steps:

1. Register source identity, publisher, license, retrieval date, version, byte hash, and
   adapter version for every input.
2. Define a cross-source status vocabulary without discarding the original status:
   operating, construction, permitted, announced/planned, proposed, rejected/cancelled,
   decommissioned, and unknown.
3. Normalize names, operators, addresses, coordinates, facility type, campus linkage,
   reported capacity, building area, investment, dates, and source URLs.
4. Preserve every source record and every unknown field. Missing capacity, cost, area, or
   date is not zero.
5. Record whether geography is source-reported, coordinate-derived, location-derived, or
   unresolved.
6. Produce source-level diagnostics for record counts, field coverage, status coverage,
   coordinate coverage, and parsing failures.

Deliverables:

- a versioned national source-normalization policy;
- a normalized facility-source artifact with provenance back to every bronze record;
- a schema, manifest, processing report, and deterministic focused tests; and
- generated per-source coverage and unresolved-field summaries.

Exit gate: all four source families reproduce from pinned inputs, retain their source
semantics, pass schema validation, and appear in one governed normalization output.

## Step 2 — Resolve duplicate facilities, campuses, and phases

**Purpose:** Prevent multiple registries, campus summaries, buildings, expansions, or
operator changes from being counted as independent county treatments.

Sub-steps:

1. Generate candidate matches using coordinates, address, parcel/site identity, normalized
   name, operator history, campus membership, and source identifiers.
2. Distinguish a campus from its buildings and distinguish an expansion phase from a new
   facility.
3. Preserve dated owner, operator, developer, and tenant relationships rather than
   overwriting them with the latest company name.
4. Assign canonical identities only when the match rule is satisfied; route ambiguous
   collisions to a review queue.
5. Retain every source record as provenance even when several records resolve to one
   canonical entity.
6. Test that cross-source resolution neither drops facilities nor double-counts capacity,
   investment, employment, or county events.

Deliverables:

- canonical facility, campus, and phase records;
- source-to-canonical crosswalks;
- an unresolved identity queue with reasons and candidate matches; and
- duplicate and aggregation diagnostics.

Exit gate: every normalized record either resolves to a canonical entity or has an
explicit unresolved disposition, and county counts can be reproduced without hidden
deduplication.

## Step 3 — Classify lifecycle status and economic materiality

**Purpose:** Separate literal evidence of computing infrastructure from exposure capable
of affecting county economic outcomes.

Sub-steps:

1. Apply the governed E0–E3 exposure policy:
   - E0: no documented dedicated exposure after the required negative-evidence review;
   - E1: accessory, enterprise, government, education, or health-care exposure;
   - E2: commercial edge, hosting, or colocation exposure;
   - E3: hyperscale, wholesale, AI/HPC, campus-scale, or otherwise economically material
     commercial exposure.
2. Evaluate the existing materiality indicators: at least 10 MW, at least $100 million in
   documented investment, at least 100,000 dedicated square feet, material incentives or
   infrastructure commitments, or documented construction/employment scale capable of
   affecting county outcomes.
3. Treat thresholds as evidence flags requiring scope review, not automatic conclusions.
4. Classify project lifecycle and materiality separately. A large planned project is not
   an operating treatment, and a small operating facility is not automatically E3.
5. Preserve conflicts, date bounds, and evidence confidence.
6. Keep rejected/cancelled proposals queryable and visually distinct.

Deliverables:

- governed lifecycle and materiality classifications;
- review queues for conflicting or insufficient evidence; and
- counts by state, county, lifecycle, E-tier, source, and confidence.

Exit gate: no county is promoted to the analytical treated cohort solely because it
appears in a registry, and every promoted exposure has source-linked status and materiality
evidence.

## Step 4 — Resolve geographic gaps, including DEPLOY's unmatched records

**Purpose:** Assign facilities to counties reproducibly without guessing, while exposing
the portion of the source universe that remains geographically unusable.

Sub-steps:

1. Apply point-in-polygon assignment to precise and approximate coordinates against the
   governed Census geography.
2. Propagate a county through a shared location identifier only when at least one reliable
   record establishes that location-to-county relationship.
3. Normalize city, state, postal address, and reported county fallbacks and record their
   precision.
4. Use authoritative address, assessor, planning, operator, or source-page evidence for
   unresolved high-priority records.
5. Flag multi-county campuses and service-area exposure rather than forcing a single
   county when the evidence supports several geographies.
6. Retain unresolved records in the national universe and exclude them from county-level
   models until resolved.

Deliverables:

- a geographic-resolution crosswalk;
- a ranked unresolved-geography queue, beginning with the 1,339 unmatched DEPLOY records;
- resolution method and confidence on every county assignment; and
- before/after county and record coverage diagnostics.

Exit gate: all automatically resolvable records are assigned, all remaining records have
documented reasons, and no unresolved location is silently omitted or assigned by
unsupported inference.

## Step 5 — Materialize the national exposure and analytical cohorts

**Purpose:** Convert the governed facility universe into transparent county-level scopes
rather than continuing to treat the original 35 counties as the full population.

Sub-steps:

1. Aggregate canonical facilities and phases to county exposure summaries without
   duplicating projects that share a county-year.
2. Publish the national facility universe, analytical candidate cohort, curated case-study
   cohort, and rejected-proposal cohort as separately labeled products.
3. Record why every county is included, excluded, unresolved, or deferred for each cohort.
4. Preserve all original 35 county pages while allowing newly qualified counties to enter
   the analytical register independently of bespoke narrative enrichment.
5. Generate maps and counts from the same versioned artifacts; do not hard-code totals in
   the interface.
6. Add release-to-release cohort diffs so additions, removals, and reclassifications are
   visible.

Deliverables:

- a national county-exposure register;
- explicit cohort-membership records and exclusion reasons;
- public summary projections and map layers; and
- a versioned cohort-change report.

Exit gate: the public and analytical products expose the full governed county candidate
universe, and the 35-county case-study register is visibly identified as a subset.

## Step 6 — Generate baseline pages for qualifying counties

**Purpose:** Expand useful public county coverage without making full bespoke project
chronologies a prerequisite for analytical inclusion.

Sub-steps:

1. Generate a stable route for every county in the national exposure register.
2. Display 2001–2024 real GDP, population, employment, and wage histories with annual year
   markers and source definitions.
3. Show linked facilities, lifecycle states, E-tier, evidence confidence, timing bounds,
   and unresolved gaps.
4. Distinguish registry-derived records from fully audited project histories.
5. Link a county to existing detailed project pages where available; otherwise provide the
   governed source record and research status rather than an empty narrative.
6. Validate map/list/page count agreement, deep links, missing-data behavior, accessibility,
   and narrow-screen layouts.

Deliverables:

- expanded county register and map navigation;
- generated exposure summaries on county pages; and
- browser and contract tests covering the expanded cohort.

Exit gate: every published exposure county has a working county page, traceable source
evidence, correctly labeled research status, and reproducible economic history.

## Step 7 — Rank counties for analytical eligibility

**Purpose:** Direct expensive historical review toward counties most capable of answering
the primary research question, without imposing an arbitrary final county count.

Sub-steps:

1. Screen panel completeness and require the model-specific minimum of seven pre-treatment
   and three post-treatment years where applicable.
2. Score timing evidence, E3 materiality evidence, identity confidence, facility-inventory
   auditability, outcome coverage, and source diversity.
3. Identify left-censoring, earlier E1/E2/E3 exposure, overlapping data-center projects,
   major contemporaneous investments, and likely spillovers.
4. Rank construction, operation, and expansion events separately because their dates,
   mechanisms, and relevant outcomes differ.
5. Publish the full queue, score components, exclusions, and tranche-selection rules.
6. Select research tranches by transparent analytical value and geographic coverage, not
   by whichever individual county was most recently discussed.

Deliverables:

- national treated-county eligibility and priority registers;
- event-specific candidate queues; and
- machine-readable selection and exclusion reasons.

Exit gate: every candidate county has a governed analytical disposition and the first
manual-review tranche is selected reproducibly from the full national universe.

## Step 8 — Adjudicate treatment histories in bounded tranches

**Purpose:** Establish defensible first-material-exposure and project-event dates for the
strongest candidates, after—not before—the national universe and ranking exist.

Sub-steps:

1. Review planning/zoning, incentives/economic development, utilities, environmental
   permits, property/site control, company/trade reporting, and local news/public debate.
2. Search explicitly for earlier enterprise, institutional, edge, colocation, wholesale,
   and hyperscale operations.
3. Distinguish announcement, site control, permitting, grading, construction,
   commissioning, opening, expansion, contraction, and closure dates.
4. Record exact dates where available and bounded dates where exact evidence is absent.
5. Audit competing local shocks and overlapping investments that could confound county
   outcomes.
6. Publish every tranche together with aggregate counts: reviewed, accepted, rejected,
   unresolved, left-censored, and insufficient-panel.
7. Stop serial review when a tranche gate is met; reassess the ranked national queue before
   selecting the next tranche.

Deliverables:

- append-only treatment-history adjudications and sources;
- county-year construction, operation, and expansion anchors;
- contamination and competing-shock records; and
- tranche-level progress reports.

Exit gate: a sufficiently broad, geographically varied treated sample passes timing,
panel, materiality, and contamination gates for at least one prespecified outcome. If no
sample passes, the failed gate is the published result and the model does not proceed.

## Step 9 — Construct control and comparison samples

**Purpose:** Compare treated counties with credible alternatives without describing an
unknown county as untreated.

Sub-steps:

1. Screen the complete national facility and proposal universe for known exposure.
2. Complete the seven-domain negative-evidence review through each treated event date for
   strict E0 candidates.
3. Build treatment-year- and outcome-specific matches using only pre-treatment values and
   trends.
4. Screen adjacent counties, shared utilities, labor markets, watersheds, and supply-chain
   regions for spillovers.
5. Record major competing shocks and exclude or separately model contaminated candidates.
6. Maintain two disclosed designs where supported:
   - strict never-exposed E0 controls; and
   - not-yet-exposed counties used only before their own qualifying treatment.
7. Test covariate balance, pre-trends, overlap, donor influence, and sensitivity to match
   specifications before authorizing estimation.

Deliverables:

- model-specific control-eligibility records;
- final matched or weighted samples;
- balance, pre-trend, spillover, and contamination diagnostics; and
- explicit exclusion reasons for every screened candidate.

Exit gate: at least one treatment/outcome design has an authorized treated sample,
comparison sample, acceptable diagnostics, and a frozen preregistered model definition.

## Step 10 — Estimate, interpret, and publish the economic results

**Purpose:** Determine whether exposed counties changed differently and whether the
evidence supports association or attribution.

Sub-steps:

1. Publish descriptive pre/post trajectories and distributions before inferential results.
2. Run the preregistered cohort-aware or stacked event study, matched difference-in-
   differences, synthetic-control, hierarchical, or other approved model appropriate to
   the outcome and exposure structure.
3. Report eligible county/year counts, effect scale, uncertainty intervals, clustering,
   weights, covariates, fixed effects, missing-data treatment, and software/input versions.
4. Test pre-trends, placebo dates and outcomes, influential counties, alternative timing,
   alternative materiality thresholds, spillover exclusions, and comparison definitions.
5. Separate construction, operation, and expansion results and stratify by E-tier or
   facility type only when the sample supports it.
6. Integrate fiscal, infrastructure, water, energy, and community-cost evidence only when
   geography, recipient, period, and accounting basis align.
7. Label results as descriptive, associative, or attributable/causal according to the
   gates actually passed. A failed gate cannot be described as a zero effect.
8. Publish model definition, run, diagnostics, estimates, limitations, and drill-down links
   to county exposure and source evidence.

Deliverables:

- versioned descriptive and inferential artifacts;
- reproducible model runs and diagnostic reports;
- public results views with uncertainty and evidence labels; and
- a plain-language answer to whether, when, and for which outcomes data centers appear to
  accelerate community economic growth.

Exit gate: every public claim reproduces from versioned inputs, exposes its eligible sample
and uncertainty, passes its stated publication gate, and links back to source evidence.

## Milestones

| Milestone | Included steps | Meaning |
| --- | --- | --- |
| M1 — Governed national inventory | 1–4 | The full source universe is normalized, resolved where possible, classified, and auditable |
| M2 — Expanded county product | 5–6 | National exposure counties are visible and have baseline county pages |
| M3 — Analysis-ready design | 7–9 | Treated events and comparison samples pass model-specific evidence and diagnostic gates |
| M4 — Economic findings | 10 | Descriptive and, where justified, causal findings are reproducible and public |

## Anti-drift execution rules

1. Steps proceed in order unless a documented blocker requires bounded work on a later
   dependency.
2. Isolated county or project enrichment is not a primary task unless the county appears
   in the active, published tranche and the work closes a named phase gate.
3. No fixed treated-county target will replace the evidence rules. The pipeline processes
   the full candidate universe; eligibility determines the final sample.
4. Detailed media timelines, additional rejected-project cases, demographic presentation,
   contribution-account gap filling, and cosmetic interface changes are secondary tracks
   unless they block the active primary milestone.
5. A source link is retained only when it is genuine, relevant, and traceable. Missing
   evidence remains missing; it is never fabricated or inferred merely to complete a page.
6. Generated counts must come from versioned artifacts. Narrative counts are updated in
   the same change as the artifacts that produce them.
7. No phase is described as complete because one county was completed. Completion is
   measured against the phase exit gate and reported for the whole batch.
8. New discoveries can change classifications or queue order, but they do not silently
   change the workstream objective or phase sequence.

## Required progress report for every primary-workstream increment

Every status update, release note, and handoff must state:

- current step and milestone;
- exact batch or national universe in scope;
- records and counties entering, passing, failing, and remaining unresolved;
- artifacts and public behavior changed;
- validation and build results;
- evidence limitations or blockers;
- the next phase exit gate, not merely the next county; and
- branch, commit, remote synchronization, and working-tree state.

This reporting contract is part of the primary workstream. A list of files changed or a
single-county narrative is not an adequate project-status report.

## Secondary workstreams

The following remain valid but do not supersede the roadmap:

- deeper contribution accounts for investment, construction, suppliers, operations,
  fiscal revenue, public cost, resources, and community contributions;
- comprehensive sourced media timelines for curated project pages;
- rejected-proposal case-study enrichment;
- demographic and other county-context presentation; and
- interface refinement unrelated to a primary phase gate.

Secondary work can proceed when explicitly requested or when it supplies a required input
to the active primary step. Its progress must not be reported as progress toward a national
treated cohort or causal finding unless it actually changes the relevant gate.

## Overall completion criteria

The primary workstream is complete only when:

- the full retained national facility universe is source-governed and reproducible;
- every county has an explicit exposure-state or unresolved-state basis;
- the analytical treated cohort is not limited to the original 35 counties;
- every modeled event has defensible materiality and timing evidence;
- every control is eligible for the specific treated event and outcome;
- descriptive and inferential results disclose samples, uncertainty, diagnostics, and
  limitations;
- causal language appears only for models that pass the causal gates; and
- every public result drills back to county, facility, event, and source evidence.

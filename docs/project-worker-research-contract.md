# Project-worker research and acceptance contract

This contract is mandatory for every project-scoped contribution-account worker. A
worker's commit is a handoff candidate, not evidence that the project is complete and
not authorization to publish it.

## Required two-pass workflow

1. **Direct-evidence discovery.** Establish the project boundary and chronology, then
   search every applicable source family using the operator, historical operators,
   legal entities, addresses, parcel and account identifiers, permit or application
   identifiers, facility codes, building phases, contractors, and recipient names.
2. **Gap closure.** Review the first-pass evidence by contribution category and return
   to every missing, ambiguous, blocked, or weakly sourced family through alternate
   indexes, archives, entities, document collections, and date ranges. Modeling must
   not begin until this pass is complete for the metric being modeled.

The worker must not describe either pass as exhaustive merely because a portal was
blocked, a useful source was found, a source count appears substantial, the fragment
validates, or a model can populate the category.

## Mandatory evidence matrix

The project updates must collectively document each applicable family below:

- operator and predecessor materials;
- assessor, parcel, personal-property, tax-bill, payment, exemption, and treasurer
  records;
- development, incentive, abatement, PILOT, bond, TIF, IRB, grant, compliance, audit,
  budget, ACFR, agenda, minutes, attachment, and check-register records;
- planning, zoning, building, grading, land-disturbance, stormwater, electrical,
  generator, environmental, and operating permits;
- electric, gas, water, wastewater, reclaimed-water, transmission, substation,
  tariff, regulatory, and public-infrastructure records;
- workforce, payroll, occupation, residence, training, apprenticeship, contractor,
  subcontractor, supplier, procurement, and local-spend records;
- community-grant lists and recipient-side confirmations; and
- relevant archives, structured datasets, local reporting, and federal or state
  filings that can lead to underlying project records.

For every family, record the exact portal, database, document collection, or archive;
the queries, legal entities, identifiers, and date range used; the material records
opened; the result or access outcome; and why any negative result cannot support a
claim. A generic statement that a family or agency was checked is not an auditable
search trail. A blocked portal requires documented alternate searches.

No fixed source quota substitutes for this matrix. Sources are retained when they
support a claim, establish a boundary, resolve overlap, or substantiate a material
negative finding. Missing evidence remains an explicit gap rather than zero.

## Modeling gate

Each proposed estimate must identify the exact direct metric sought and the matrix
entries demonstrating the metric-specific gap-closure search. It must also explain
why the model is decision-relevant, why its project boundary and inputs are defensible,
and why leaving the gap unresolved is less informative than the proposed synthesis.
Mechanically available county comparisons, transferred coefficients, unit conversions,
and category-filling estimates are not automatically eligible. Poor fit, unresolved
attribution, incompatible scopes, or missing local inputs require deletion of the model
or retention of the gap. Tests and the completed-account gate never justify a model.

## Handoff and orchestration acceptance

A worker may declare `handoff_ready` only after both passes, the evidence matrix,
model-by-model eligibility review, project-description contract, scope/diff review,
and applicable validation are complete. The handoff must report source and record
counts, actual/projection/model splits, exact searches and material negative findings,
boundary decisions, unresolved gaps, and every changed file.

The orchestrator independently inspects the fragment and source-family matrix before
reconciliation. Thin coverage, generic search assertions, uninspected underlying
documents, untested alternative searches, weak boundaries, or ineligible models return
the same worker and worktree to `gap_closure_in_progress`. Only an independently
accepted handoff may enter a batch release. The next batch cannot launch until all
three accepted handoffs are reconciled, rebuilt, fully validated, visually inspected,
committed, pushed, and verified live.

# Project-scoped modeled syntheses

Each parallel worker owns exactly one `prj_study_*.json` file in this directory. The
fragment must contain `schema_version`, `project_id`, `reviewed_on`, `scope_note`,
`sources`, and `estimates`. Every estimate must match the filename project ID.

The release builder merges fragments in project-ID order and validates the combined
payload against the study modeling policy and synthesis contract. Workers must not edit
the base synthesis file or generated aggregate outputs.

The corresponding evidence fragment must first satisfy the two-pass evidence matrix and
metric-specific modeling gate in
[`docs/project-worker-research-contract.md`](../../../docs/project-worker-research-contract.md).
Validation success, a mechanically available method, or a completed-account category
gap never establishes model eligibility.

Modeling begins only after the corresponding evidence fragment documents an auditable
public-source search. Every retained model needs a project-specific public anchor and
defensible parameters; transferred coefficients and assumptions must remain explicit.
Do not invent or preserve a synthesis simply to fill a contribution category or make
the account pass the completeness gate. A well-researched unresolved gap is an
acceptable—and preferable—result when eligibility is not met.

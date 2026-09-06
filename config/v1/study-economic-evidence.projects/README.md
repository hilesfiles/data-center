# Project-scoped economic evidence

Each parallel worker owns exactly one `prj_study_*.json` file in this directory. The
fragment must contain `schema_version`, `project_id`, `reviewed_on`, `scope_note`,
`sources`, `records`, and `project_updates`. Every record and update must match the
filename project ID. Global metric definitions remain in
`../study-economic-evidence.json` and are owned by the orchestrator.

The release builder merges fragments in project-ID order and validates the combined
payload with the existing economic-evidence contract. Workers must not edit the base
file or generated aggregate outputs.

Before residual-gap modeling, a worker must use `project_updates` to leave an
auditable direct-evidence search trail. The updates should identify the official
source families and portals searched, useful record or query identifiers, the review
date or date range, the categories addressed, and material negative findings. Search
the relevant local tax/assessor, permit/planning, incentive/compliance, utility and
regulatory, operator, workforce/procurement, and community-recipient records; record
why a source could not support a quantitative claim. A completed-account label is not
a quota: unsupported categories remain gaps, and a model must not be created or kept
only to satisfy the completeness gate.

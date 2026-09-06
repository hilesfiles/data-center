# Project-scoped economic evidence

Each parallel worker owns exactly one `prj_study_*.json` file in this directory. The
fragment must contain `schema_version`, `project_id`, `reviewed_on`, `scope_note`,
`sources`, `records`, and `project_updates`. Every record and update must match the
filename project ID. Global metric definitions remain in
`../study-economic-evidence.json` and are owned by the orchestrator.

The release builder merges fragments in project-ID order and validates the combined
payload with the existing economic-evidence contract. Workers must not edit the base
file or generated aggregate outputs.

Every worker must follow the mandatory two-pass discovery, gap-closure, evidence-matrix,
and independent-acceptance process in
[`docs/project-worker-research-contract.md`](../../../docs/project-worker-research-contract.md).
Schema or test success does not establish research completeness, and a worker commit is
only a handoff candidate until the orchestrator audits and accepts it.

Before residual-gap modeling, a worker must use `project_updates` to leave an
auditable direct-evidence search trail. The updates must identify the official
source families and portals searched, useful record or query identifiers, the review
date or date range, the categories addressed, and material negative findings. Search
the relevant local tax/assessor, permit/planning, incentive/compliance, utility and
regulatory, operator, workforce/procurement, and community-recipient records; record
why a source could not support a quantitative claim. A completed-account label is not
a quota: unsupported categories remain gaps, and a model must not be created or kept
only to satisfy the completeness gate.

Every project worker must also add `project_description` to exactly one
`project_updates` entry. It must be a factual two-to-four-sentence description between
80 and 1,000 characters that identifies the project, operator, host location,
facility/campus boundary, documented opening or operating chronology, and material
source-supported development characteristics. Distinguish the selected building from
a campus, regional portfolio, later expansion, tenant equipment, or other boundary
where applicable. Do not repeat the study-selection rationale or include advocacy,
economic conclusions, model results, unsupported claims, placeholders, research
instructions, or generic data-center language. A full modeled account cannot publish
without this description; the project page renders it as “About this project” above
“Why this project is in the study.”

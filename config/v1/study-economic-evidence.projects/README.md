# Project-scoped economic evidence

Each parallel worker owns exactly one `prj_study_*.json` file in this directory. The
fragment must contain `schema_version`, `project_id`, `reviewed_on`, `scope_note`,
`sources`, `records`, and `project_updates`. Every record and update must match the
filename project ID. Global metric definitions remain in
`../study-economic-evidence.json` and are owned by the orchestrator.

The release builder merges fragments in project-ID order and validates the combined
payload with the existing economic-evidence contract. Workers must not edit the base
file or generated aggregate outputs.

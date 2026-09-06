# Project-scoped modeled syntheses

Each parallel worker owns exactly one `prj_study_*.json` file in this directory. The
fragment must contain `schema_version`, `project_id`, `reviewed_on`, `scope_note`,
`sources`, and `estimates`. Every estimate must match the filename project ID.

The release builder merges fragments in project-ID order and validates the combined
payload against the study modeling policy and synthesis contract. Workers must not edit
the base synthesis file or generated aggregate outputs.

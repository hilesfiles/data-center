# Data dictionary

The machine-readable source of truth is the schema catalog at
`schemas/v1/catalog.json`. This document describes the major record families.

| Family | Principal records | Purpose |
|---|---|---|
| Infrastructure | campus, facility, project, project phase, event, operator relationship, facility containment relationship | Preserve physical identity, spatial nesting, and lifecycle history |
| Evidence and governance | source, source artifact, claim, claim resolution, review decision, entity-resolution candidate | Trace every material assertion, governed decision, and unresolved match |
| Source ingest | facility seed source record | Preserve source-shaped point, building, and campus rows before canonical projection |
| Measurement | metric definition, observation | Store observed, derived, estimated, modeled, suppressed, and missing values distinctly |
| Analytical input | panel row, treatment definition, analysis unit | Build reproducible samples without mixing model outputs into raw observations |
| Modeling | model specification, model run, estimate, diagnostic, donor weight | Record assumptions, inputs, uncertainty, fit, and reproducibility |
| Indices | index score | Preserve components, weights, coverage, calibration, uncertainty, and publication status |
| Publication | public county summary, facility-source coverage, entity-resolution record/coverage, dataset manifest | Deliver small versioned JSON projections to GitHub Pages |

Field definitions, constraints, enumerations, and required relationships are maintained
in the corresponding JSON Schema. Additions must follow the compatibility policy in
`schemas/v1/release.json`.

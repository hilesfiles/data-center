# Application release 1.50 — restore completed research to the community map

Application release 1.50 advances the generated study data to `private-sector-study-1.47.0` and corrects the community-map inclusion contract.

The map now distinguishes completed project research from analytical completeness. All nine reconciled projects are mapped: Apple Mesa, Switch Citadel / Tahoe Reno 1, Digital Crossroad Hammond, Meta Forest City, Microsoft San Antonio, EdgeConneX DET01, Expedient Milwaukee / Franklin, Google Council Bluffs, and Apple Washoe County campus. The six audited projects remain visible even when their residual evidence gaps keep them from the separate `full_modeled_account` gate.

Each published project summary carries `research_completion_status`. The map, filters, county selection panel, county-to-project links, legend, and caption use `account_research_complete`; project pages continue to use `model_completeness` for “Completed contribution account” versus “Partial evidence.” Future reconciled project fragments become map-eligible without manufacturing models for completeness.

The application fetches the study index with an explicit cache-busting URL and `no-store` request policy. A backward-compatible map predicate also recognizes the prior release shape, preventing a newly deployed JavaScript bundle from rendering an empty map when a browser or intermediary still holds pre-contract JSON.

The release preserves 660 sourced records—597 observations and 63 forecasts—138 separately governed modeled syntheses, three full modeled accounts, all project descriptions, and the direct county-detail link from the map popup.

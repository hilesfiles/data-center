# Application release 1.43 — completed-study map scope

Application release 1.43 narrows the public map to the three projects that pass the `full_modeled_account` gate in study release `private-sector-study-1.42.0`:

- Apple Mesa / Maricopa County, Arizona;
- Switch Citadel / Storey County, Nevada; and
- Digital Crossroad Hammond / Lake County, Indiana.

The change is limited to map presentation. It does not revise the study data release or delete legacy research assets. The 36-project private-sector register, all project profiles, the national IM3-derived inventory, county economic datasets, county routes and generated legacy map files remain in the repository for future research.

`MapPanel.tsx` no longer requests or renders `data/v1/maps/facilities.geojson`. The map route also no longer requests or displays the legacy facility-coverage, county economic, employment, entity-resolution, lifecycle or first-entry panels. Those files continue to support direct county-profile routes. Census county boundaries remain as neutral geography. A county is highlighted and a project marker is drawn only when its register record reports `model_completeness.status` equal to `full_modeled_account`. The map legend, filter, sidebar and banner state this narrower scope.

Browser verification enforces both sides of the contract: exactly three completed projects appear on the map; legacy facility and county datasets are not requested by the map route; legacy inventory metrics are absent from its sidebar; and the stored register still contains all 36 research candidates. TypeScript compilation and the production build also pass.

# Methodology overview

The Observatory is an evidence system first and an analytical product second. Public
outputs are generated from source records, claims, reviewed resolutions, observations,
registered model runs, and versioned index methods.

## Evidence states

The system distinguishes observed conditions, observed changes, modeled counterfactual
differences, quasi-causal estimates, perception/opposition indicators, and data-quality
measures. These labels are not interchangeable.

## Historical reconstruction

Present-day facilities are starting points, not a complete historical sample. Reverse
reconstruction identifies prior announcements, permits, construction, operations,
expansions, and operator changes. Forward discovery preserves rejected, withdrawn,
cancelled, closed, and never-built projects to reduce survivorship bias.

## Analytical design

The canonical analytical grain is county-year, with county-quarter used only when source
frequency and treatment timing support it. Construction, operation, and expansion are
separate treatments. Descriptive results are published independently from matched or
staggered-treatment estimates.

No county receives a headline causal score without adequate treatment-date evidence,
pre-treatment history, comparison units, diagnostics, uncertainty, and component
coverage. Missing evidence is displayed as insufficient evidence rather than zero.

## Current implementation status

The current site combines authoritative Census 2025 county geography with the OSM-derived
IM3 Open Source Data Center Atlas v2026.02.09 seed. IM3 rows are imported as provisional
source objects, not silently promoted to verified operating facilities. The public county
measure is therefore labeled “source records,” and a zero means no record in that release,
not evidence that no facility exists.

The ingest preserves all 1,479 source rows in bronze JSON, including five deliberate
cross-county duplicates and two Puerto Rico rows outside the current publication scope.
Canonical/public projections contain 1,472 distinct in-scope source objects. Single-county
centroids are assigned against the published Census polygons; source-reported assignments
remain preserved in evidence. Cross-county polygons retain multiple assignments without
inventing allocation shares.

The first identity-resolution pass is intentionally conservative. A governed rule links
252 building footprints wholly inside exactly one campus polygon and one point inside
exactly one campus. It groups 953 source operator assertions into 161 provisional
operator entities using Unicode, case, and whitespace normalization only. It does not
infer parent companies, ownership, or corporate aliases.

Spatial plausibility is not treated as proof of physical identity. A curated second pass
reviewed all sixteen candidates against source attributes, geometry diagnostics, and ten
official operator, SEC, or federal sources. Three address/name pairs were merged into
canonical physical facilities while preserving the superseded source record and redirect.
Eight point sites were explicitly not merged because they represent separately operated
sites, suites, exchanges, or computing systems inside a larger building; these now use a
`located_within_building` relationship. Two partial campus links were accepted, one
cross-operator campus link was rejected, and two geometrically inconsistent unnamed
campuses were escalated for source-history review.

A final boundary pass resolved both escalations from official OpenStreetMap way histories
and first-party site evidence. The smaller One Wilshire polygon had been explicitly
retagged as `building:part=yes`; it is now a fourth superseded source record that redirects
to the One Wilshire building rather than an active campus. The Phoenix boundary is the
separate, multi-building 4010 Data Center campus at 4010 North 3rd Street, not the Lumen
building at 215 East Indian School Road, so that proposed campus link was rejected. The
earlier escalation decisions remain in the downstream snapshot with superseded status.
The pinned ingest, first-pass resolution, and initial adjudication artifacts remain
immutable; final boundary review is another downstream JSON layer.

The seed does not establish operating dates, lifecycle status, historical completeness,
MW capacity, or causal effects. Historical reconstruction, outcome panels, and
econometric estimation remain future work.

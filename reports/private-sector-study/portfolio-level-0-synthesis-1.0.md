# 36-project portfolio synthesis 1.0

Built from `private-sector-study-1.60.0` and restricted to the 36 selected projects in their 35 host counties. This is a Level 0 descriptive publication. It contains no national comparison counties, new modeled values, portfolio benefit total, pooled association, attributable effect, or causal estimate.

## What the portfolio evidence supports

- The project-by-metric matrix contains 659 populated project/metric cells drawn from 1,818 reported observations, 162 source projections, and 304 separately governed modeled syntheses.
- Reported evidence reaches all 36 projects for operations and fiscal records. It reaches 29 projects for resources, 25 for construction, 24 for investment, 21 for community contributions, 11 for public costs, and only 2 for local suppliers.
- The strict timing screen finds 55 same-year reported-observation cohorts spanning at least three projects and three counties. Forty-three are fiscal cohorts, nine concern annual electricity use, and three concern incentive payments. No investment, construction, supplier, operations, or community metric currently clears that exact timing-and-definition screen.
- The largest strict cohort contains seven projects. This is enough for a descriptive range and median, but not enough to represent the national industry or support a transferable benchmark.
- The 48 retained modeled Level 0 values remain identity carry-forwards from individual project accounts. They are not mixed into the reported-observation distributions and are not summed across projects.
- All 288 project/category combinations have an explicit direct-evidence status: 184 contain partial reported evidence, 16 contain projections only, and 88 remain uncollected. Missing evidence is never encoded as zero.

## Category coverage

| Account category | Projects with reported evidence | Coverage |
|---|---:|---:|
| Investment | 24 of 36 | 66.7% |
| Construction | 25 of 36 | 69.4% |
| Suppliers | 2 of 36 | 5.6% |
| Operations | 36 of 36 | 100.0% |
| Fiscal | 36 of 36 | 100.0% |
| Public costs | 11 of 36 | 30.6% |
| Resources | 29 of 36 | 80.6% |
| Community | 21 of 36 | 58.3% |

Coverage means at least one reported observation in the category. It does not mean the category is complete, annualized, locally allocated, or comparable across projects.

## Timing-aligned descriptive findings

The 55 eligible cohorts use reported observations only. Every cohort matches metric code, unit, measure type, period kind, year, scope level, and inventory-allocation status. Each project contributes one unambiguous value; project/year groups containing multiple distinct values are excluded. Values with non-point qualifiers and county-context observations are also excluded.

The resulting cohorts cover six metric families: account assessed value, property taxes paid, property taxes billed, taxable property value, annual electricity use, and incentive payments. The published machine-readable record supplies the project values, source-claim identifiers, minimum, quartiles, median, and maximum for every cohort. These distributions describe the collected accounts; they are not portfolio totals, representative national benchmarks, or evidence of project effects.

## Why there is no portfolio total

The existing metric rules prohibit cross-project addition until project, campus, company-county, parcel, phase, recipient, period, and nested-component overlaps have been adjudicated. The observed accounts include stocks and flows, nominal dollars from different periods, campus and company-county scopes, and multiple project-linked accounts. Adding them would create a number with no stable accounting interpretation.

Accordingly, the publication gate records zero authorized portfolio totals. This is an analytical result, not unfinished arithmetic.

## Modeled-synthesis disposition

All 304 existing modeled syntheses retain their completed portfolio-policy review: 66 transparent arithmetic records are retained, 194 assumption-dependent records remain sensitivity-only, and 44 project-scoped county comparisons remain outside this Level 0 portfolio synthesis. The observed-data calibration screen still authorizes zero transferable parameters. No replacement or gap-filling model was created.

## Remaining evidence priorities

The portfolio matrix makes the next research priorities explicit. Supplier evidence is the largest common gap, followed by actual public-cost records, community funding coverage, and period/phase allocation for investment and construction. Those gaps should be addressed from project records before any modeled substitute is considered. A future cross-project total would additionally require metric-by-metric overlap adjudication; a future association or causal study would require a separately approved design.

## Published artifacts

- `data/silver/study/pooled/portfolio-level-0-synthesis.json` — governed analytical record.
- `site/public/data/v1/study/pooled/portfolio-level-0-synthesis.json` — identical public projection used by the application.
- `data/silver/study/pooled/portfolio-level-0-manifest.json` — builder, input, output, size, and SHA-256 provenance.

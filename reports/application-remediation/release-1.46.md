# Application release 1.46 — economic-model scope correction

Application release 1.46 corrects three material defects in the completed contribution accounts and advances the generated study data to `private-sector-study-1.43.0`. The 585 source records remain unchanged: 533 reported observations and 52 forecasts. The release still contains 104 separately governed modeled syntheses across Apple Mesa, Switch Citadel and Digital Crossroad Hammond, with zero modeled values in canonical claims.

## Fiscal correction

The prior annual net-fiscal rows mixed state or multi-jurisdiction incentives and abatements with local property-tax receipts. Their government scope and time horizons did not match, so the resulting negative balances were not valid county fiscal estimates. Those rows are retracted.

An intermediate replacement that allocated 20–50% of tax revenue to public-service cost was also rejected before publication because the formula was circular and mechanically forced a positive margin. Release 1.46 makes no net-fiscal claim. It presents the arithmetic sum of cited, same-period project-linked local property-tax claims and the annual same-scope public-cost threshold that would erase that contribution:

- Apple Mesa / Maricopa County: $1,873,375.92 per year;
- Switch Citadel / Storey County: $3,452,486.96 per year; and
- Digital Crossroad Hammond / Lake County: $641,685.14 per year (verified paid amount; the separate $751,127.92 gross distribution precedes credits and cap savings).

Actual marginal public-service cost remains an evidence gap. If same-scope annual cost is below the displayed threshold, the recurring property-tax margin is positive; if it is above the threshold, the margin is negative. State incentives, property-tax reductions, abatements, TIF debt service and other public-support measures remain visible as separate records with their own jurisdictions and periods.

## Construction and county-comparison corrections

The Prince William County construction benchmark excludes IT equipment. Apple and Switch construction job-year and labor-income scenarios now apply a visible 25–75% construction-cost share to broad capital totals before applying the benchmark coefficients. The central Apple construction benchmark is 8,749.10 job-years and $529,483,636.40 of labor income; the central Switch benchmark is 1,047.02 job-years and $63,364,149.71. These are low-confidence Prince William benchmark equivalents, not observed host-county outcomes.

The former county “effect” rows used an inverse-distance weighted comparison that did not meet the requirements for a causal synthetic-control design. They are now descriptive 2024 comparison gaps, use the `benchmark_application` method, carry no causal-design metadata, and state that they must not be interpreted as data-center effects.

## Presentation and validation

Completed project and county accounts now separate directly reported anchors, construction and operating contribution scenarios, recurring local tax contribution and break-even, public support and tax treatment, infrastructure and environmental demand, and descriptive county comparisons. The interface states that no net fiscal result is asserted without same-scope public-cost evidence.

Validation passes the 65-schema data contract, all 50 focused repository tests, TypeScript compilation, the Vite production build, and all 39 browser checks with zero runtime errors. The browser harness shuts down its exact preview process and verifies that its test port is closed.

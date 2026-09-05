# Study release 1.33 - Lake County industry employment and payroll context

Release `private-sector-study-1.33.0` publishes 537 source-checked economic records across all 36 candidates: 495 reported records and 42 source forecasts. The thirty-third evidence batch adds a 2016-2023 Lake County County Business Patterns series for NAICS 518210, Data Processing, Hosting, and Related Services.

## Lake County benchmark

- Eight annual rows report establishments, March employment and annual payroll for the exact six-digit industry. The source files contain every year, so no broader industry category or inferred zero was used.
- Establishments range from 7 in 2016 to 16 in 2020 and 11 in 2023. These are employer locations with payroll during the year, not a data-center facility count.
- Published March employment is 67 in 2016, reaches 429 in 2021 and is 44 in 2023. Annual payroll is $7.295 million in 2016, $18.443 million in 2021 and $4.047 million in 2023.
- Census disclosure flags are retained in every employment and payroll record. Several employment cells carry high-noise flags, so the series is not interpreted as precise year-to-year project performance.
- The scope is explicitly `county_context`: it includes data-processing and hosting firms beyond data centers, covers Lake County rather than Hammond alone, and is not attributed to Digital Crossroad.

Hammond now has 113 records: 103 reported observations and ten forecasts, plus 29 research updates.

## Sources and verification

- The records come from the official U.S. Census Bureau County Business Patterns county ZIP files for reference years 2016-2023.
- Rows were filtered to state `18`, county `089` and NAICS `518210`; annual payroll was converted from reported thousands of nominal dollars to dollars.
- The compact extract with disclosure flags and source hashes is stored in `hammond-cbp-2016-2023.csv`. SHA-256 values for all eight original ZIP files are stored on their source records.
- The 2023 table was released June 26, 2025; Census material available in September 2026 still identifies 2023 as the latest released CBP reference year, with 2024 expected later in September.

## Validation

- The evidence builder produces all 36 project profiles and 537 economic records.
- Forty unit tests pass, including values, timing, scope and noncausal-language checks for the new series.
- All 63 schemas, the valid fixture and three invalid fixtures pass the full contract validator.
- TypeScript compilation and the Vite production build pass.
- Thirty-four browser checks pass with no runtime errors.
- `hammond-cbp-employment-mobile.png` was visually reviewed at mobile width.

## Remaining Hammond gaps

The Census series does not identify Digital Crossroad employment, payroll, worker residence, job creation or causal effects. Project payroll and job-years, local worker and vendor shares, operating wages and purchases, public-service costs, measured water and electricity use, transaction-level incentive dates, EV-award payment and installation, exact NIPSCO payments, and realized EID financing remain uncollected.

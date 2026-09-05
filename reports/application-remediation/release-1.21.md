# Study release 1.21 - Digital Crossroad Hammond depth account

Release `private-sector-study-1.21.0` publishes 446 source-checked economic records across all 36 candidates: 412 reported records and 34 source forecasts. The twenty-first batch adds four reported records to Digital Crossroad DX-1 in Hammond.

## Evidence added

- NIPSCO's 2021 Integrated Resource Plan describes the Hammond facility as more than $50 million. The application retains the qualified amount as cumulative facility investment rather than audited annual or local spending.
- Hammond's adopted 2026 budget reports $30,328,680 of DX Hammond JV LLC personal-property assessed value for 2023 payable 2024. It remains separate from the existing leasehold real-property series and tax account.
- DX Hammond company testimony filed with the Indiana Utility Regulatory Commission states that the operating facility has 20 MW of data-center capacity. The record does not represent electricity consumption or peak demand.
- Indiana's air-permit revision lists eight diesel emergency generators, including three approved for construction in 2022. The application labels this as permit-listed equipment rather than actual runtime, fuel use, emissions or proof that every approved unit was commissioned.
- Lake County states that its Economic Development Commission provided seed money in fall 2019. No quantitative record is created because the county page supplies no project amount or terms.

## Application behavior

The Hammond profile now has 22 records: 20 reported records and two forecasts. The reported view preserves the five-year leasehold assessment and tax table while adding the separate personal-property value, cumulative investment, operating capacity and permit context. The expired 2025 expansion remains a dated research update, and its proposed amounts remain excluded from realized activity.

## Validation

- Data contract validation covers all schemas and fixtures.
- Private-sector study tests cover Hammond record counts, real/personal-property separation, qualified investment, resource metrics and unchanged forecasts.
- TypeScript and the Vite production build pass with MW and generator units in the public type contract.
- Browser checks cover the expanded Hammond profile and mobile account view with no runtime errors.

## Remaining limits

The case still lacks annual construction expenditure, construction job-years and payroll, verified direct and contractor operating headcount, wages, supplier purchases, recipient-level net fiscal receipts, revolving-loan amount and terms, public service costs, metered water and electricity use, and actual generator operation or emissions. These records do not establish a complete benefit-cost balance or causal community effect.

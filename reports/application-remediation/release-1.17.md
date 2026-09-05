# Study release 1.17 - Expedient Milwaukee / Franklin

Release `private-sector-study-1.17.0` publishes 426 source-checked economic records across 34 of 36 candidates: 397 reported records and 29 source forecasts. This batch adds seven records for Expedient's MKE1 facility at 4777 W Ironwood Drive in Franklin, Wisconsin.

## Evidence added

- The City of Franklin's 2024 and 2025 completed assessment rolls and current linked property record identify real parcel 930-1001-000 and report $297,700 of land plus $3,559,200 of improvements, or $3,856,900 total. The 2024–2026 values are separate annual stocks.
- The property record labels the 26,428-square-foot, 2007 structure “Expedient” and classifies the occupancy as a computer center. Because the structure predates Expedient's October 2021 opening, the profile identifies the event as adaptive reuse and does not present the parcel value as new construction.
- The linked property report records a $27,000 building permit issued in 2022, a $580,190 building permit issued in 2025 and a separate $250,132 mechanical permit issued in 2025. These administrative amounts are not summed or relabeled as verified expenditure, local purchasing or construction payroll.
- Expedient's opening release states that it planned to hire 12 employees in the following months. The profile retains that claim as a forecast because realized site employment, wages and retention were not found.
- No tax bill, tax payment, recipient-specific receipt, equipment value, incentive or public-cost amount is inferred from assessed value.

## Application behavior

The Expedient profile now has six reported-activity records and one plan. Its property-tax table displays assessed value while leaving billed and paid columns uncollected. The permit records remain individual construction-flow cards. The hiring forecast appears only on the Plans & forecasts tab. Register filtering now reports 34 candidates with economic evidence and two still awaiting it.

## Validation

- Data contract: 63 schemas, one valid fixture and three intentionally invalid fixtures passed.
- Private-sector study tests: 37 passed, including an adaptive-reuse test that keeps parcel stocks, permit amounts and the hiring plan separate.
- TypeScript and Vite production build passed.
- Browser suite: 32 checks passed with no runtime errors.
- Mobile visual review passed for `expedient-franklin-actuals-mobile.png` and `expedient-franklin-evidence-mobile.png`.

## Remaining limits

The evidence does not establish realized 2021 construction spending, permanent employment, payroll, supplier purchases, household effects, actual taxes paid, recipient-level receipts, incentives, public-service costs, equipment value or resource use. The unchanged 2024–2026 assessment reflects Franklin's revaluation and maintenance cycle and is not evidence of yearly new investment. Quicken Loans Technology Center and NTT Silicon Valley SV1 remain the two candidates without quantitative economic records.

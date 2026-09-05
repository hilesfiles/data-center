# Study release 1.32 - Hammond state-incentive chronology

Release `private-sector-study-1.32.0` publishes 513 source-checked economic records across all 36 candidates: 471 reported records and 42 source forecasts. The thirty-second evidence batch converts Digital Crossroad Hammond's current IEDC EDGE, IRTC and DATA balances into dated cumulative snapshots using the official 2018 and 2021-2025 Economic Incentives and Compliance Reports.

## Hammond incentive chronology

- EDGE paid/certified value is $0 at the 2018 cutoff, $11,763 by the 2021 report and unchanged in the 2022 and 2023 reports. The 2023 report records the September 27 contract end and a $5,209 recapture; the current portal preserves the two monetary amounts while now marking the contract compliant.
- IRTC is already fully paid/certified at $9,045,773.82 in the 2021 report and remains unchanged through the 2022-2025 reports and current portal. The repeated balances are cumulative observations and are never summed as annual credits.
- DATA reports $0 paid/certified and $0 actual qualified investment in 2023. The 2024 report leaves paid/certified blank and reports $0 actual qualified investment, so the blank is preserved as missing rather than inferred to be zero. The 2025 report records $28,369,398.27 paid/certified and $186,954,143 of actual qualified investment.
- DATA exemption value remains a state-tax expenditure; IRTC and EDGE are state credit statuses. None is labeled as local revenue, a cash grant, annual capital spending or a multiplier effect.
- The annual reports constrain the timing of cumulative balances but do not provide transaction-level certification dates, exempt-purchase detail or realized EDGE employment.

Hammond now has 89 records: 79 reported records and ten forecasts, plus 28 research updates.

## Sources and verification

- The 2018 and 2021-2025 reports were retrieved from the official [IEDC Transparency Portal](https://transparencyportal.iedc.in.gov/searchadditionalpublicinfo).
- Project rows 419942 and 419963 were text-extracted and visually verified on PDF pages 115, 184, 71-72, 55 and 83, 51, and 26 respectively.
- Artifact SHA-256 values are stored on every source record. The official portal's 2018 copy matches the previously reviewed document hash.

## Validation

- The evidence builder produces all 36 project profiles and 513 economic records.
- Forty unit tests pass, including program-specific cumulative-series checks.
- All 63 schemas, the valid fixture and three invalid fixtures pass the full contract validator.
- TypeScript compilation and the Vite production build pass.
- Thirty-four browser checks pass with no runtime errors. The Hammond check verifies all 14 paid/certified snapshots and the separate qualified-investment series.
- `hammond-incentive-timeline-mobile.png` and the current DATA incentive card were visually reviewed at mobile width.

## Remaining Hammond gaps

Transaction-level EDGE, IRTC and DATA certification dates, 2019-2020 archived compliance snapshots, realized direct and contractor employment, payroll and job-years, local worker and vendor shares, operating wages and purchases, public-service costs, measured water and electricity use, EV-award payment and installation, exact NIPSCO payments, and realized EID financing remain uncollected.

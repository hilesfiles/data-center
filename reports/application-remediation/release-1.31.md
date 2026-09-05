# Study release 1.31 - Hammond EDGE closeout status

Release `private-sector-study-1.31.0` publishes 499 source-checked economic records across all 36 candidates: 457 reported records and 42 source forecasts. The thirty-first evidence batch closes the current-status gap for Digital Crossroad Hammond's separate IEDC project 419942 EDGE agreement.

## Hammond EDGE reconciliation

- The current IEDC portal reports that the $750,000 EDGE contract ended September 27, 2023 and remains marked compliant.
- Paid or certified value increased from the $0 shown in the 2018 report to $11,763 in the current portal. Both observations remain in the account with their own reporting dates.
- The portal displays a negative $5,209 adjustment. The application stores the downward-adjustment magnitude separately and does not net it against the paid/certified field because the portal does not define whether that field is pre- or post-adjustment.
- The portal repeats 45 expected jobs by 2025 and reports $239,530,500 of expected qualified investment. The investment amount is retained as a source forecast; neither value is evidence of realized jobs or spending.
- The portal's $0 actual-qualified-investment field is not encoded as zero campus investment. It is program-specific, the underlying contract PDF remains in processing, and the related DATA agreement separately reports $186,954,143 of actual qualified investment.

Hammond now has 75 records: 65 reported records and ten forecasts, plus 27 research updates.

## Validation

- The evidence builder produces all 36 project profiles and 499 economic records.
- Forty unit tests pass.
- TypeScript compilation and the Vite production build pass.
- Thirty-four browser checks pass with no runtime errors. Hammond checks cover the dated EDGE balances, adjustment, ended status, expected investment and separation from realized campus activity.
- `hammond-edge-closeout-mobile.png` is visually reviewed at 390-pixel width.

## Remaining Hammond gaps

Annual EDGE, IRTC and DATA certification histories, realized direct and contractor employment, payroll and job-years, local worker and vendor shares, operating wages and purchases, public-service costs, measured water and electricity use, EV-award payment and installation, exact NIPSCO payments, and realized EID financing remain uncollected.

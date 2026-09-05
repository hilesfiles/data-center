# Study release 1.26 - Hammond EID debt and annual-report screen

Release `private-sector-study-1.26.0` publishes 479 source-checked economic records across all 36 candidates: 441 reported records and 38 source forecasts. The twenty-sixth batch adds two Hammond research updates and no quantitative record.

## Hammond financing screen

- Indiana Gateway's live Hammond Civil City outstanding Bond/Lease register lists 33 debt names, including the existing Taxable Economic Development Revenue Bonds, Series 2019 (Data Center).
- No separately named DX Hammond Economic Improvement District or EID bond appears in that City register.
- This is a bounded screen of current self-reported City debt. It does not rule out a private obligation, an unreported closing or a separately administered instrument.
- Gateway's rendered 2025 Debt Statement says Hammond has not yet submitted its 2025 Annual Financial Report. Apparent export values are excluded, so the audited Series 2019 histories continue to end in 2024.

The Hammond profile remains at 55 records: 49 reported records and six forecasts. It now has 17 research updates. EID bond-specific agreements, assessment schedules, owner bills and payments, district receipts and expenditures remain unverified.

## Validation

- The evidence builder produces all 36 project profiles and retains 479 economic records.
- Forty unit tests pass.
- Sixty-three schemas, one valid fixture and three intentionally invalid fixtures pass the full data-contract validator.
- TypeScript compilation and the Vite production build pass.
- Thirty-four browser checks pass with no runtime errors. The Hammond check verifies the two new research updates, the unchanged 55-record count and the separation of the EID gap from the existing TIF bond.
- `hammond-eid-debt-screen-mobile.png` was visually reviewed at 390-pixel width with no overflow.

## Remaining Hammond gaps

The next EID targets are a recorded bond-specific development agreement, closing documents, annual assessment schedules, owner bills and payments, and district receipts and expenditures. The operating account still lacks annual construction spending, payroll and job-years; operating payroll and purchases; recipient-level net fiscal receipts; public-service costs; and measured water and electricity use.

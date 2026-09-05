# Study release 1.24 - Digital Crossroad Hammond local-contractor spending

Release `private-sector-study-1.24.0` publishes 476 source-checked economic records across all 36 candidates: 441 reported records and 35 source forecasts. The twenty-fourth batch adds one reported supplier-spending record to Digital Crossroad DX-1 in Hammond.

## Evidence added

- Hammond's official June 9, 2025 Common Council minutes record Decennial Group co-founder David Pavlik reporting that the existing Building 1 had spent well over $80 million with local contractors.
- The source identifies electrical, mechanical, plumbing, roofing, re-roofing and fiber work.
- The application encodes $80 million as a greater-than cumulative lower bound. It preserves the developer attribution and does not treat the statement as an audited expenditure schedule.
- The source does not define the local geography, exact accumulation period, contractor-level payments, payroll, workforce, job-years, household spending or multiplier effects. Those measures remain uncollected.

## Application behavior

The Hammond profile now has 52 records: 49 reported records and three forecasts. The new supplier card displays “More than $80,000,000,” the Building 1 campus scope, source page and interpretation notes. The separate 301 Digital Crossroads/CoreWeave agreement remains marked expired; its proposed jobs, investment, abatements and community-impact payments are not presented as realized activity.

## Validation

- Data contract validation passes 63 schemas, the valid fixture and three expected-invalid fixtures.
- Forty private-sector study unit tests pass, including the amount, qualifier, supplier category and PDF page locator.
- TypeScript and the Vite production build pass.
- Thirty-four browser checks pass with no runtime errors. The Hammond check verifies the qualified local-contractor record, existing TIF reconciliation and mobile layout.
- The official source PDF page was text-extracted, rendered and visually checked; the stored SHA-256 is `c08a0ee263a8a3c9b9a4fd231cee132bd1c43989e4b5e10bd2f3c5522a22418d`.

## Remaining limits

Hammond still lacks annual construction expenditures, payroll and job-years; a defined contractor geography and payment ledger; operating payroll and supplier purchases; recipient-level net fiscal receipts; public-service costs; and measured water and electricity use. The new record supports a local-procurement contribution while leaving the broader benefit-cost and causal questions open.

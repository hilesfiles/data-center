# Study release 1.25 - Hammond EID cost and owner-assessment structure

Release `private-sector-study-1.25.0` publishes 479 source-checked economic records across all 36 candidates: 441 reported records and 38 source forecasts. The twenty-fifth batch adds three Hammond forecast records from Ordinance 9496.

## Evidence added

- Exhibit J-1 estimates Building 1 total capital expenditure at $88,656,629 across three phases.
- Section 46 caps potential annual special assessments at $3,415,000 in Zone 1 and $3,415,000 in Zone 2. Zone 3 is exempt, and assessments may remain for up to 25 years after an EID bond is issued.
- The ordinance states that City, state and political-subdivision faith, credit and taxing power are not pledged to EID debt. It assigns expenses above the bond-specific assessment schedule to the project owner.
- No EID bond issuance, final assessment schedule, owner bill or payment, district receipt or expenditure was verified. The three amounts therefore remain forecasts.
- The ordinance's attached U.S. Chamber model describes a typical data center. Its jobs, wages, output and tax estimates are deliberately excluded from Hammond facts.

## Application behavior

The Hammond profile now has 55 records: 49 reported records and six forecasts. Its forecast tab places the 2018 $40 million initial-phase plan, $200 million potential campus plan, 2021 $88.656629 million Building 1 estimate, two owner-assessment caps and the approximately 40-job plan in source order. The reported tab remains unchanged and retains the developer-reported greater-than-$80-million local-contractor amount.

## Validation

- Data contract validation passes 63 schemas, the valid fixture and three expected-invalid fixtures.
- Forty private-sector study unit tests pass, including the Building 1 estimate, two separately scoped zone caps, 25-year horizon and forecast basis.
- TypeScript and the Vite production build pass.
- Thirty-four browser checks pass with no runtime errors. The Hammond check verifies that EID estimates and caps remain separate from reported spending and TIF financing.
- Relevant ordinance pages were text-extracted, rendered and visually checked. The stored SHA-256 is `34a05cb9e4fbdd22eb5908557484f946f285a2dffa0b38186b62a0e97a99eabe`.

## Remaining limits

The EID financing account still lacks bond-specific agreements, issued debt, annual assessment schedules, owner bills and payments, district receipts and expenditures. Hammond also lacks annual construction spending, payroll and job-years; operating payroll and purchases; recipient-level net fiscal receipts; public-service costs; and measured water and electricity use.

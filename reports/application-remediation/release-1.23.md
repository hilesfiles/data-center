# Study release 1.23 - Digital Crossroad Hammond audited TIF bond lifecycle

Release `private-sector-study-1.23.0` publishes 475 source-checked economic records across all 36 candidates: 440 reported records and 35 source forecasts. The twenty-third batch adds 20 reported public-financing records to Digital Crossroad DX-1 in Hammond.

## Evidence added

- Indiana State Board of Accounts audits document $5 million of Series 2019 Data Center bond proceeds issued in fiscal 2019 and the remaining $3.04 million drawn in 2020.
- Year-end outstanding principal was $8.04 million in 2022, $7.975 million in 2023 and $7.81 million in 2024.
- Principal retired was an explicitly reported zero in 2022, $65,000 in 2023 and $165,000 in 2024. Interest and fees were $321,600, $321,600 and $317,700.
- Remaining principal-plus-interest commitments were $12,074,400, $11,687,800 and $11,205,100. These include future interest and remain distinct from principal balances.
- City pledged TIF revenue, City debt-service-fund transfers and the private fund's project-TIF repayment amounts are retained as three separate series. Only the 2022 transfer and private-fund amount agree exactly.

## Application behavior

The Hammond profile now has 51 records: 48 reported records and three forecasts. A reconciliation table places the three TIF revenue and transfer measures side by side without adding them. A separate debt-service table distinguishes annual principal and interest flows from the year-end principal stock. The remaining principal-plus-interest commitment stays in its own annual series.

## Validation

- Data contract validation covers all schemas and fixtures.
- Private-sector study tests cover the issuance, debt-stock, principal, interest, pledged-revenue, transfer and remaining-commitment series.
- TypeScript and the Vite production build pass with the new financing tables.
- Browser checks verify the reconciliation and debt-service tables at narrow width with no runtime errors.

## Remaining limits

The audits do not reconcile the later differences among pledged revenue, City transfers and private-fund project-tax amounts. The case still lacks annual construction expenditure, construction job-years and payroll, local-contractor participation, employee wages and retention, supplier purchases, recipient-level net fiscal receipts, public-service costs, metered resource use and actual generator operation. No complete benefit-cost balance or causal effect is claimed.

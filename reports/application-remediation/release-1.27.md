# Study release 1.27 - Hammond audited investment accounting

Release `private-sector-study-1.27.0` publishes 484 source-checked economic records across all 36 candidates: 446 reported records and 38 source forecasts. The twenty-seventh batch adds five Digital Crossroad Hammond observations from Principal Digital Real Estate Fund's 2025 annual report.

## Hammond investment account

- The audited consolidated schedule of investments reports cost basis of $211,110,564 at December 31, 2024 and $220,812,911 at December 31, 2025.
- It reports fair value of $240,300,000 and $249,400,000 for the same dates.
- Cost basis and fair value are separate year-end accounting stocks. They are not annual construction expenditure, local procurement, assessed value, tax revenue, sale proceeds or economic output. The $9.7 million cost-basis change is not recast as capital spending without a roll-forward.
- The manager's investment update reports 15 MW commissioned and 89.3% leased and occupied at year-end 2025. The 15 MW commissioned stock is encoded separately from the 20 MW utility-feed or operating-capacity descriptor and from measured electricity consumption.

The Hammond profile now has 60 records: 54 reported records and six forecasts, plus 18 research updates.

## Validation

- The evidence builder produces all 36 project profiles and 484 economic records.
- Forty unit tests pass.
- Sixty-three schemas, one valid fixture and three intentionally invalid fixtures pass the full data-contract validator.
- TypeScript compilation and the Vite production build pass.
- Thirty-four browser checks pass with no runtime errors. The Hammond check verifies both accounting histories, the commissioned-capacity record, the unchanged forecast account and the financing distinctions.
- `hammond-investment-cost-basis-mobile.png` was visually reviewed at 390-pixel width with no overflow.

## Remaining Hammond gaps

An audited or certified construction-cost roll-forward is still needed to identify annual additions and local supplier allocation. Construction payroll and job-years, operating payroll and purchases, recipient-level net fiscal receipts, public-service costs, measured water and electricity use, and realized EID financing remain uncollected.

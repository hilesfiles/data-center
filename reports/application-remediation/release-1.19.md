# Study release 1.19 - Quicken Corktown parcel boundary

Release `private-sector-study-1.19.0` publishes 434 source-checked economic records across all 36 candidates: 403 reported administrative records and 31 source forecasts. This batch adds four whole-parcel assessment records for the Quicken Loans Technology Center property in Detroit.

## Evidence added

- Detroit's official current parcel service resolves 1401 Rosa Parks Boulevard to taxable commercial-improved parcel 08008283-303, style `Computer Centers`, with six buildings and 68,718 square feet of total floor area.
- The parcel's legal description says it was split or combined in 2017 from parcels including the two historic Ward 08 tax IDs in Quicken's SEC-filed lease.
- Assessed value is $3,298,400 for 2025 and $3,643,800 for 2026. Taxable value is $2,679,332 and $2,813,298 for those years.
- The SEC-filed lease covers approximately 35,920 square feet in a 65,250-square-foot building. The operator describes the broader property as a roughly 66,000-square-foot data-center and office complex. All four values therefore remain whole-parcel stocks with no tenant or data-center allocation.
- Rocket's statement that the cooling design uses no water remains a qualitative, unmetered claim and is not converted to zero total facility water use.

## Application behavior

The Quicken profile now shows two assessed-value and two taxable-value observations in separate two-year histories. Research updates explain the current/historic parcel crosswalk, partial-building tenancy and water-claim boundary. The register now reports numerical economic evidence for all 36 candidates while retaining partial-coverage and causal-readiness limits.

## Validation

- Data contract: 63 schemas, one valid fixture and three intentionally invalid fixtures passed.
- Private-sector study tests: 39 passed, including a test that keeps the whole-parcel values unallocated.
- TypeScript and Vite production build passed.
- Browser suite: 34 checks passed with no runtime errors.
- Mobile visual review passed for `quicken-corktown-evidence-mobile.png`.

## Remaining limits

The evidence does not establish project construction cost or spending, construction jobs or payroll, realized site employment, supplier purchases, annual rent, property taxes billed or paid, recipient-specific receipts, incentives, public-service costs, metered water use or electricity use. The 2025/2026 parcel stocks cannot establish a causal effect of the 2015 opening, and their whole-parcel scope prevents allocation to the data-center function.

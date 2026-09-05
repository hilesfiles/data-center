# Study release 1.18 - NTT Silicon Valley SV1

Release `private-sector-study-1.18.0` publishes 430 source-checked economic records across 35 of 36 candidates: 399 reported administrative records and 31 source forecasts. This batch adds four records for NTT Silicon Valley SV1 in Santa Clara, California.

## Evidence added

- Santa Clara's development record identifies the RagingWire SV1 project at 1150 Walsh Avenue on APN 224-58-003. NTT's current facility page uses 1160 Walsh Avenue. The county appeal report names RagingWire Data Centers Inc. on that APN. No official address-renumbering instrument was located, so the profile discloses both address forms.
- The Santa Clara County Assessor's report dated April 30, 2025 records County Verified value positions of $159,579,996 for appeal 22.3790 and $83,066,779 for appeal 23.6405. They are appeal-docket property stocks, not final appeal determinations, annual investment, tax bills, payments or recipient receipts.
- The city's 2019 environmental study anticipated up to 40 employees every 24 hours. This remains a pre-opening forecast because realized site employment, FTE equivalence, payroll, worker residence and retention were not found.
- The city's Water and Sewer Utilities memorandum records the developer's annual water-use estimate of 173,752 gallons, approximately 0.53 acre-feet, and concludes that a formal water-supply assessment was not required. The profile keeps it as a design forecast rather than metered use.
- The environmental study describes closed-loop chilled-water cooling but contains internally inconsistent daily wastewater arithmetic. No daily-use value is inferred or published.

## Application behavior

The SV1 profile now has two reported administrative records and two plans. The appeal values appear only on the Reported activity tab with their appeal status and source-year labels. The employee maximum and annual water design estimate appear only on Plans & forecasts. Register filtering now reports 35 candidates with economic evidence and Quicken Loans Technology Center as the remaining candidate without a quantitative record.

## Validation

- Data contract: 63 schemas, one valid fixture and three intentionally invalid fixtures passed.
- Private-sector study tests: 38 passed, including a test that keeps appeal values, job plans and water design estimates distinct.
- TypeScript and Vite production build passed.
- Browser suite: 33 checks passed with no runtime errors.
- Mobile visual review passed for `ntt-sv1-evidence-mobile.png`.

## Remaining limits

The evidence does not establish final adjudicated parcel assessments, property taxes billed or paid, recipient-specific receipts, actual construction spending, construction employment or payroll, realized permanent employment, supplier purchases, household effects, incentives, public-service costs, metered water use or electricity use. The two county appeal positions cannot be interpreted as a comparable annual tax-base series without the final decisions and assessment basis. No causal effect is attributed to the 2021 opening.

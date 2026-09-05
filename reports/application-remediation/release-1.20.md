# Study release 1.20 - Meta Forest City depth account

Release `private-sector-study-1.20.0` publishes 442 source-checked economic records across all 36 candidates: 408 reported records and 34 source forecasts. The twentieth batch starts the depth phase with eight additional Meta Forest City records.

## Evidence added

- Meta's current Forest City factsheet reports at least $750 million in cumulative investment, at least 275 operational jobs supported and at least $6.4 million in direct funding to Rutherford County-area schools and nonprofits. These remain operator-reported amounts without annual schedules or independent audit.
- A 2015 North Carolina Rural Infrastructure Authority record reports 100 existing positions and approves a $148,900 grant to the Town of Forest City for an approximately 1,000-foot publicly owned water-line extension serving a new campus building.
- The same 2015 record's ten-job, two-year plan remains a forecast. The 2010 state announcement's approximately $450 million investment and more than 250 construction/mechanical jobs during an 18-month building phase also remain forecasts.
- North Carolina DEQ documents reuse of a contaminated former textile and boat-manufacturing site under a 2012 Brownfields Agreement. Its undated claim that Facebook represents approximately 14% of county revenue remains qualitative context because the page gives no measurement date or denominator.
- The factsheet's energy, water-service and cooling-efficiency statements remain qualitative operator claims. They are not encoded as metered use or verified customer-rate effects.

## Application behavior

The Forest City profile now has 23 records: 20 reported records and three forecasts. Its five-year fiscal table adds a documented difference equal to county taxes collected minus the separately disclosed incentive payment. The table states that this arithmetic is not a complete net fiscal benefit because other revenues, services, public costs, timing and the provisional taxpayer identification remain outside it. Community funding is now an eighth evidence category for every profile.

## Validation

- Data contract: 63 schemas, one valid fixture and three intentionally invalid fixtures passed.
- Private-sector study tests: 40 passed, including the Forest City depth-account separation test.
- TypeScript and Vite production build passed.
- Browser suite: 34 checks passed with no runtime errors.
- Mobile visual review passed for `fiscal-comparison-mobile.png` and `meta-forest-city-depth-mobile.png`.

## Remaining limits

The case still lacks annual campus spending, construction job-years and payroll, direct-versus-contractor operating headcount, wages, supplier purchases, community-funding payment schedules, grant disbursement and maintenance costs, recipient-level fiscal accounts beyond Rutherford County, and measured water and electricity use. The records do not establish causal community effects or a complete benefit-cost balance.

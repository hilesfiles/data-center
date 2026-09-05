# Study release 1.34 - Hammond local-labor records acquisition path

Release `private-sector-study-1.34.0` retains 537 source-checked economic records across all 36 candidates: 495 reported observations and 42 source forecasts. The thirty-fourth evidence batch identifies the record set needed to close Hammond's construction-labor gap and prepares a focused request for those existing records.

## Finding

- Section 1.9(B)(1) of the November 1, 2018 Digital Crossroad development agreement required good-faith priority for Hammond, Lake County and Indiana contractors and workers. It also required bid and award documentation.
- Section 1.9(B)(2) required the developer to maintain relevant compliance data and provide it to the Hammond Redevelopment Commission at least quarterly until construction completion.
- Keyword searches of the City's public document API found no named Digital Crossroad, DX Hammond, Hammond Contractors or quarterly-labor filing. The indexed Redevelopment Commission archive begins in 2021, after the initial 2019-2020 construction period, and uses generic meeting-date filenames.
- The application presents this as an unresolved acquisition target. It does not treat the archive result as evidence that the records do not exist, that reporting did not occur, or that local participation was zero.

Hammond remains at 113 economic records—103 reported observations and ten forecasts—and now has 30 research updates.

## Prepared request

`hammond-dx-local-labor-records-request-draft.md` requests the existing quarterly submissions, bidder and award records, worker-geography data, any recorded counts, hours, payroll, wages or trade classifications, and Commission review correspondence. It expressly avoids asking the City to create a new analysis and accepts aggregate or redacted records where personal identifiers are involved. The draft has not been sent.

## Validation

- The evidence builder produces all 36 project profiles and 537 economic records.
- Forty unit tests pass.
- All 63 schemas, the valid fixture and three invalid fixtures pass the full contract validator.
- TypeScript compilation and the Vite production build pass.
- Thirty-four browser checks pass with no runtime errors.
- `hammond-local-labor-acquisition-mobile.png` was visually reviewed at mobile width.

## Next decision

Obtaining the quarterly submissions would allow the study to measure realized contractor participation and possibly worker geography, hours or payroll. If the City confirms that no responsive records are held, the study should preserve that response as a documented data gap rather than substitute forecasts or modeled multipliers.

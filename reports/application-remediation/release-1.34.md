# Study release 1.34 - Hammond local-labor public-evidence gap

Release `private-sector-study-1.34.0` retained 537 source-checked economic records across all 36 candidates: 495 reported observations and 42 source forecasts. Its thirty-fourth evidence batch identified the record set needed to close Hammond's construction-labor gap. Release 1.41 supersedes the proposed acquisition path: the study now uses already-public evidence only and sends or recommends no solicitation.

## Finding

- Section 1.9(B)(1) of the November 1, 2018 Digital Crossroad development agreement required good-faith priority for Hammond, Lake County and Indiana contractors and workers. It also required bid and award documentation.
- Section 1.9(B)(2) required the developer to maintain relevant compliance data and provide it to the Hammond Redevelopment Commission at least quarterly until construction completion.
- Keyword searches of the City's public document API found no named Digital Crossroad, DX Hammond, Hammond Contractors or quarterly-labor filing. The indexed Redevelopment Commission archive begins in 2021, after the initial 2019-2020 construction period, and uses generic meeting-date filenames.
- The application presents this as an unresolved public-evidence gap. It does not treat the archive result as evidence that the records do not exist, that reporting did not occur, or that local participation was zero.

Hammond remains at 113 economic records—103 reported observations and ten forecasts—and now has 30 research updates.

## Superseded acquisition proposal

The former draft request and its browser capture were removed in release 1.41. No request was sent. The current modeling policy prohibits public-records requests, private-data requests, surveys, questionnaires and other solicitations.

## Validation

- The evidence builder produces all 36 project profiles and 537 economic records.
- Forty unit tests pass.
- All 63 schemas, the valid fixture and three invalid fixtures pass the full contract validator.
- TypeScript compilation and the Vite production build pass.
- Thirty-four browser checks pass with no runtime errors.
- The public-evidence-gap state was visually reviewed at mobile width.

## Current disposition

Public worker-residence, hours, payroll and trade data remain unavailable. Release 1.41 preserves that gap and publishes an explicitly labeled low-confidence residence-share sensitivity rather than presenting forecast realization, compliance, or a requested record as fact.

# Study release 1.35 - Switch Storey County abatement audit

Release `private-sector-study-1.35.0` publishes 545 source-checked economic records across all 36 candidates: 498 reported observations and 47 source forecasts. The thirty-fifth evidence batch adds five-year audit findings and original incentive terms for the Switch Storey County data-center agreement associated with the Citadel campus.

## Finding

- Nevada GOED's approved-abatement table identifies `Switch, LTD #2` as a new Storey County data-center project approved in July 2015.
- The five-year audit table marks the December 31, 2020 audit compliant and reports 111 jobs, a $50.97 average hourly wage and $179,943,184 of capital expenditure.
- The application keeps these three findings at company-county scope and does not allocate them to Tahoe Reno 1 or another Citadel building.
- The same 2023 table repeats the three audit findings on the `Switch, LTD #3` Clark County row. A 2021 report had left the separate Storey and Clark findings blank while reporting combined Switch results elsewhere. The Storey values therefore carry an explicit reporting-quality caution.

## Forecast account

The release also adds the agreement's original 50-job, $28.98-hourly-wage and $1,386,677,024 capital-investment projections. Its approved estimated $75,720,025 sales/use-tax abatement and $32,095,728 personal-property-tax abatement remain source forecasts over the 20-year term. They are not treated as realized tax expenditures or netted against the separate Storey County account bills and payments.

Switch Citadel / Tahoe Reno 1 now has 63 economic records: 57 reported observations and six source forecasts. Its prior personal-property account history remains unchanged, including the unexplained zero 2019 bill.

## Validation

- The evidence builder produces all 36 project profiles and 545 economic records.
- Forty unit tests pass.
- All 63 schemas, the valid fixture and three invalid fixtures pass the full contract validator.
- TypeScript compilation and the Vite production build pass.
- Thirty-five browser checks pass with no runtime errors.
- `nv-goed-switch-audit-page.png` confirms the source-table row. `switch-storey-audit-capex-mobile.png` and `switch-storey-agreement-forecasts-mobile.png` were visually reviewed at mobile width.

## Next pass

The strongest remaining Switch gap is a reconciled audit workpaper or agency explanation for the identical Storey and Clark allocations. Construction workforce, Nevada-resident participation, annual payroll, local supplier spending, realized tax abatements, campus real property and measured electricity and water use remain uncollected.

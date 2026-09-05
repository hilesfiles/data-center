# Study release 1.40 - Storey County modeled depth account

Release `private-sector-study-1.40.0` adds a governed Storey County modeling pass to the study-wide `study-modeled-synthesis-2.3.0` contract and retains `study-modeling-policy-1.2.0`. It publishes 585 source records—533 reported observations and 52 source forecasts—and 33 separately labeled modeled syntheses: 13 Apple Mesa records plus 20 Switch Citadel / Tahoe Reno 1 records. Modeled values remain excluded from canonical claims, sourced-record counts and realized-benefit totals.

## New direct evidence

One SEC-filed observation is admitted. Switch reported $59.4 million invested in the Citadel Campus during Q2 2021, primarily for power and cooling capacity, a new sector and Tahoe Reno 2 site work. It is a campus-level flow after the December 31, 2020 audit cutoff. It is not allocated to Tahoe Reno 1, payroll, contractors or local suppliers.

The Storey source account therefore contains 79 records: 72 reported observations and seven source forecasts. The 2016–2026 personal-property account, separate 2024–2026 real-property parcel, unexplained zero 2019 personal-property bill, completed and partial payment statuses, audited 111 jobs / $50.97 hourly wage / $179,943,184 capital expenditure, agreement forecasts, $356,000 contribution, greater-than-$2 million ladder-truck contribution and $100,000 equipment forecast remain separate.

## Storey modeled synthesis

Twenty Storey records cover:

- a $239,343,184 documented cumulative capital floor through Q2 2021 and its 17.2602% ratio to the $1,386,677,024 agreement commitment;
- Q2 2021 direct construction scenarios of 275.47–413.20 job-years, $27.44–$41.17 million direct labor income and 172.17–344.33 Nevada-resident job-year equivalents, transferred from a same-region public industrial-construction benchmark with explicit low confidence;
- 100.33–111 annual FTE equivalents and $10.64–$11.77 million annual wage payroll based on the audited 111 jobs and $50.97 hourly wage under 1,880–2,080 paid-hour assumptions;
- exact arithmetic reconciliations of real- and personal-property bills and completed payments for fiscal 2024–2025 and 2025–2026, plus an $11,324,644.79 cumulative completed-payment floor through fiscal 2025–2026;
- a $107,815,753 approved 20-year sales/use and personal-property abatement forecast aggregation and a $5,390,787.65 straight-line annual equivalent, both explicitly counterfactual and unrealized;
- a 75.4 MW 2018 occupied-capacity proxy, 528,403–660,504 MWh annual facility-electricity scenario, 80,604–188,715 MWh facility-overhead scenario, 54.84–295.74 million gallon onsite-water scenario and 154,042–192,553 metric-ton location-based CO2e scenario; and
- an 11,632.67-job descriptive difference between Storey County's 2011–2014 and 2017–2019 QCEW covered-employment means, explicitly noncausal.

## Deliberately unmodeled gaps

No local contractor or supplier spending is estimated because the public Citadel evidence does not identify vendor payments or purchasing geography. No indirect or induced contribution is published because the geographically relevant public IMPLAN benchmark combines those channels; separating them would manufacture unsupported values. Community contributions and the Fire District equipment plan are not netted because their amounts, timing and status differ. A Switch-only causal design is withheld because Tesla and broader Tahoe-Reno Industrial Center expansion are concurrent treatments and no eligible comparison geography or pretrend diagnostics isolate Switch. Strategic-infrastructure narratives are not monetized because no public model defines a local economic channel. Metered electricity, demand, PUE, water, cooling, supplier-specific emissions, backup-generator emissions and market-based accounting remain unresolved.

## Public benchmark provenance

The models cite Nevada GOED's Switch audit and current data-center requirements, Switch SEC filings, the public GOED Tesla/IMPLAN analysis for Washoe and Storey Counties, Switch's Tahoe Reno disclosures, DOE/LBNL PUE/WUE references, EPA eGRID2023 Nevada output emissions and BLS QCEW county data. Each record identifies dataset vintage, geography, transformation, benchmark-transfer limits, interval kind, named parameters and units, contribution channel, aggregation identity, confidence rationale, assumptions, limitations, evidence-search status and remaining gap.

## Validation

The release passes 65-schema data-contract validation, all 48 repository tests, TypeScript checking, the production build and 36 browser checks without runtime errors. Mobile captures verify the Storey modeled list, annual-account coverage and analysis-readiness sections without horizontal overflow. Full results are recorded in `reports/application-remediation/economic-evidence-checks.json`.

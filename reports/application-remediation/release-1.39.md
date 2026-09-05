# Private-sector study release 1.39

5 September 2026. Release `private-sector-study-1.39.0` extends the Apple Mesa account under `study-modeled-synthesis-2.2.0` and `study-modeling-policy-1.2.0`. The canonical evidence register remains unchanged at 584 sourced records: 532 reported observations and 52 source forecasts. Modeled values remain separate from canonical claims and are labeled `modeled_not_observed_or_audited`.

## Added Apple Mesa syntheses

- Apple-only 2024 employment allocation: 121.84 FTE, with a 98.05–145.62 sensitivity envelope.
- Apple-only annual payroll allocation: $11.56 million, with a $9.30–$13.81 million sensitivity envelope.
- Fiscal 2025 electricity-cost benchmark: $56.67 million, with a $44.48–$68.85 million sensitivity envelope.
- Location-based gross electricity emissions: 180,341.25 metric tons CO₂e per year.
- Cooling-treatment water-savings potential: 16.40 million gallons per year, with a zero-to-32.80-million-gallon sensitivity envelope.

The labor estimates use activated Foreign-Trade Zone acreage as a low-confidence allocation key. Payroll compounds that allocation with a county NAICS 518210 benchmark. Electricity cost uses Arizona sector-average prices rather than Apple's tariff or bill. Gross emissions use the AZNM eGRID rate and do not net renewable procurement. The cooling estimate transfers Apple's reported 30-percent pilot result only to the high scenario; it does not claim measured Mesa performance.

Construction job-years, local purchasing shares, indirect and induced effects, recipient-level net fiscal effects, and Apple-only causal effects remain unresolved because the reviewed public inputs do not support defensible estimates. The study sends no public-records requests, private data requests, surveys, questionnaires, or other solicitations.

## Verification

- 65 schemas validated, including configuration and public JSON.
- 48 repository tests passed.
- TypeScript compilation and the production build passed.
- 35 browser checks passed with no runtime errors.
- Apple Mesa displays 80 sourced records and 13 separately labeled modeled syntheses.

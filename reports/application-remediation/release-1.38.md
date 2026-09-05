# Study release 1.38 - study-wide modeled-synthesis contract

Release `private-sector-study-1.38.0` reconciles the Maricopa and Storey County work into one study release and generalizes the Apple Mesa modeled-synthesis prototype into a study-wide, versioned contract. It publishes 584 source records—532 reported observations and 52 source forecasts—and eight Apple Mesa syntheses. No modeled record is added for another real facility or county.

## Reconciled source accounts

The merged evidence input preserves both independently developed county increments. Apple Mesa contributes 24 sourced records covering operating electricity, renewable capacity, completed permit valuations, cumulative investment, original job and investment commitments, and the bounded state-credit estimate. Switch Citadel retains the 15 sourced records added on `main`: its real-property account for tax years 2024–2026, bills and verified or partial payments, two direct Fire District contributions, and the paired equipment-cost forecast. The builder regenerates every silver and public artifact from this combined evidence input rather than copying either worktree's generated outputs.

## Generic contract

`study-modeled-synthesis-2.1.0` supports construction and operating contributions, investment and fiscal counterfactuals, resource engineering, county longitudinal analysis and defensible strategic-infrastructure measures. It expands geographic scope to facilities, campuses, company-counties, counties, multi-county areas, utility service areas, states and supporting infrastructure. Temporal forms cover annual, fiscal, tax-year, construction-period, historical-peak, cumulative and projection-horizon estimates.

The API replaces the prototype `scenario` object with an `interval` object whose required `kind` distinguishes point estimates, deterministic counterfactuals, sensitivity envelopes, reported bands, confidence intervals and credible intervals. Statistical intervals require an explicit confidence level. Every estimate also declares:

- direct, indirect, induced, total or non-contribution channel;
- an aggregation identifier and role with explicit total-component identities;
- named numerical parameters, units, claim/source/assumption provenance and transformations;
- decision relevance, public-evidence search status and a remaining evidence gap;
- formula, method, model version, assumptions, limitations, confidence and review date; and
- the fixed presentation label `modeled_not_observed_or_audited`.

Input-output and contribution methods require named multiplier source, model/version, geography, vintage, local-purchase assumption and channel-separation metadata. Difference-in-differences, event-study and synthetic-control methods require treatment timing, comparison design, outcome definition, pre/post periods, diagnostics and limitations.

## Governance and overlap controls

The machine-readable `study-modeling-policy-1.1.0` requires review of already-public evidence first, preserves source projections, models only decision-relevant quantities with reproducible cited inputs and disclosed uncertainty, and documents the unresolved analytical limit otherwise. It prohibits public-records requests, private data requests, surveys, questionnaires and other solicitations. It applies identical evidence rules to benefits and costs, requires explicit allocation, separates contribution from causation, excludes models from canonical claims and realized-benefit totals, and prohibits overlapping aggregation.

Semantic validation rejects non-finite or misordered intervals, non-degenerate deterministic intervals, reversed construction periods, unknown or undeclared claim/source parameters, implicit facility allocation, missing causal design, incomplete multiplier provenance, duplicate estimate grain, invalid total channels, missing aggregation components and components reused by overlapping totals.

## Generality fixtures

Validation-only synthetic fixtures exercise a non-Apple construction job-year/payroll calculation, a facility electricity/water engineering scenario, a county fiscal counterfactual containing both revenue and public-cost inputs, and a county event-study record with a labeled statistical interval. They are test data only and are excluded from the builder and public release.

## Apple Mesa continuity

The eight Apple Mesa values from the isolated Maricopa prototype are unchanged. They carry typed intervals, named parameter provenance, contribution channels, aggregation identities, decision-use statements, unresolved evidence gaps, limitations and the explicit not-observed-or-audited presentation status. The public “Modeled synthesis” tab exposes those fields while retaining the separation from reported activity and source forecasts.

## Validation

- The full data-contract validator passes 65 schemas, one valid fixture and three expected-invalid fixtures.
- All 48 repository tests pass, including 47 focused study tests.
- TypeScript compilation and the Vite production build pass.
- All 35 browser checks pass without runtime errors.
- The Apple Mesa modeled view was captured at mobile width and visually inspected.

## Remaining limitations

The contract makes future modeling governable; it does not make unavailable inputs available. Measured facility water, current Apple-only employment and payroll, realized taxpayer credits, customs-entry benefits, facility-level multiplier inputs and eligible county causal designs remain disclosed evidence gaps. Applying the framework to additional real projects requires a separate evidence review and release.

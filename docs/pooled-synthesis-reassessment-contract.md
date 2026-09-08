# Cross-project synthesis reassessment contract

8 September 2026. This contract governs the portfolio-wide reassessment of the 304 modeled syntheses published in `private-sector-study-1.60.0`. It implements the pre-model gates without changing a source observation, treating a projection as realized, imputing a missing category, or fitting a pooled estimate. Portfolio-policy adjudication and conservative metric-rule registration are complete; empirical calibration failed its gate, numeric aggregation is limited to single-component Level 0 identities, and pooled estimation remains blocked.

## Evidence hierarchy

1. Reported observations remain the preferred analytical inputs.
2. Source projections remain separate scenarios and are never included in empirical calibration distributions.
3. Existing modeled syntheses may be evaluated but cannot train or validate a replacement model.
4. A cross-project empirical distribution may be estimated only from definitionally compatible reported observations with compatible period, geography, unit, accounting basis, and contribution channel.
5. The target project must be excluded from its own calibration sample. Every derived project estimate therefore requires leave-one-project-out construction.
6. Missing, suppressed, unresolved, and structurally incomparable values remain missing. They are not zeros.

## Reassessment decisions

Machine triage is an inventory aid, not an acceptance decision. Every synthesis must receive one substantive disposition before the synthesis layer changes:

- `retain`: the calculation and scope remain defensible without portfolio recalibration;
- `restrict_to_sensitivity`: the record is useful only as a bounded scenario;
- `supersede_with_empirical_calibration`: compatible reported observations support a better leave-one-project-out estimate;
- `migrate_to_pooled_outcome_framework`: a project-scoped county comparison must be replaced by a registered county-year analysis;
- `retire`: the record is redundant, circular, outside scope, or insufficiently supported; or
- `document_unmodeled_gap`: no eligible replacement exists.

No disposition may be selected to make an account appear complete. Superseded records remain traceable through version history and successor identifiers.

The completed adjudication retains 66 transparent project-level arithmetic aggregations as candidates for metric-specific exposure aggregation, restricts 194 assumption-dependent results to project sensitivity or counterfactual roles, and directs 44 project-scoped county comparisons to the future county-year framework. The subsequent rule gate registers 12 metric rules. Forty-eight explicitly dated records can enter the county-year layer only as Level 0 single-component identities; no same-county/year/metric sum is currently authorized. One cumulative record is excluded from annual allocation and 17 records across five metric rules remain blocked because they lack an explicit panel year.

## Empirical calibration gate

A metric family becomes eligible for parameter estimation only after review confirms:

- at least three independent projects contribute reported observations;
- project, campus, company-county, utility, and regional scopes are not silently mixed;
- stocks, annual flows, cumulative totals, peaks, and forecasts are not combined;
- nominal dollar values are aligned to an explicit price basis when compared across years;
- operator portfolios and multi-project totals are not allocated without a registered method;
- repeated annual records do not masquerade as independent projects; and
- the resulting sample and exclusions are published.

The preferred estimator is a robust empirical distribution or hierarchical partial-pooling model stratified by defensible project characteristics. Cross-validation is leave-one-project-out. Sparse families remain descriptive and do not generate imputations.

The observed-data screen evaluates twelve same-project, same-year ratio definitions. It produced 235 reproducible derived observations. Five tax/value ratios clear the three-project count floor but remain descriptive because assessment bases and effective tax regimes are jurisdiction-specific. The remaining seven definitions—two other tax/value ratios and five operational or resource ratios—do not clear the independent-project floor under exact scope matching. Consequently, the current calibration library contains zero authorized transferable parameters. This is a failed calibration gate, not permission to fall back to the older transferred benchmarks.

## Pooled-exposure boundary

The facility-year foundation inventories components without aggregation. The county-year layer may carry forward one retained synthesis unchanged only when its registered metric rule permits Level 0 identity aggregation and no second component shares the county, year, and metric. Multiple components block the result rather than being summed. Existing project-specific county GDP, employment, and wage comparisons are excluded from pooled inputs because projects in one county share those outcomes.

Modeled inputs that survive reassessment enter later county-year aggregation through repeated draws consistent with their registered interval kind. Point calculations may be degenerate draws, but uncertainty about attribution or completeness remains a separate sensitivity or eligibility condition.

## Publication gate

The foundation may publish coverage, Level 0 descriptive identities, and readiness diagnostics only. It must contain no pooled association, attributable effect, causal label, net-fiscal claim, or composite benefit score. The national comparison register covers all 3,144 panel counties but currently identifies zero eligible comparison counties: 35 are study hosts, 19 non-host counties are reviewed but unresolved, 166 non-host counties remain in the resolution queue, and 2,924 are unscreened. Statistical estimation therefore remains blocked pending county first-entry and exposure-history verification, outcome definitions, and diagnostics.

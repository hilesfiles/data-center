# Pooled county-impact model target state

5 September 2026. This document defines the target analytical layer that will connect the private-sector project register to cross-community statistical findings. It is a specification, not a claim that a pooled model currently exists.

## Current state and target boundary

Study release `private-sector-study-1.43.0` contains 36 selected projects across 35 counties and 23 states. Apple Mesa / Maricopa County, Switch Citadel / Storey County, and Digital Crossroad Hammond / Lake County currently pass the completed-contribution-account gate. The other 33 projects remain incomplete. The current release contains 585 source records and 104 separately governed modeled syntheses, but no pooled estimate and no causal estimate.

The pooled model will not replace the project and county accounts. Those accounts establish the exposure inputs, evidence state, scope, timing, uncertainty, and unresolved gaps. The pooled layer will evaluate whether consistent relationships appear across communities after projects and phases are aligned at a common county-year grain.

## Target analytical architecture

The target state has three linked levels:

1. **Facility-year evidence.** Annual project and phase records for construction, operation, expansion, and closure, preserving reported observations, source projections, and modeled syntheses as distinct evidence states.
2. **County-year exposure.** Compatible facility-year records aggregated across every project and phase affecting the same county and year, with overlap controls and uncertainty retained.
3. **Pooled inference.** Registered statistical models relating county-year exposure to economic, fiscal, infrastructure, and environmental outcomes, using a screened national comparison pool.

The canonical statistical unit for county outcomes is the county-year. A project remains a distinct research and reporting unit, but two projects in one county are not two independent observations of the county's GDP, employment, wages, or tax base. Utility-service-area, water-system, and watershed outcomes require separate geographic panels rather than forced county allocations.

## Population and comparison universe

All 36 selected projects must be represented in the facility-year layer, even when a field remains missing or a project is ineligible for a particular outcome model. The selected projects occupy 35 counties; their 23-state distribution is a geographic characteristic, not the number of county observations.

The comparison universe comes from the national county panel, not only from the selected project counties. Candidate comparison counties must be screened against the preserved national facility inventory, project histories, known prior and concurrent facilities, major overlapping investments, and relevant spillovers. Absence from the 36-project register does not establish that a county is untreated. An unknown exposure state remains unknown.

Not-yet-exposed counties may serve as comparisons only for years before their own qualifying exposure. Counties with unresolved historical exposure may appear in descriptive summaries but cannot enter a causal comparison set unless the registered design defines and tests the resulting contamination risk.

## Facility-year exposure contract

Each project-year record must identify:

- project, facility, campus, phase, county, and affected service-area identifiers;
- event state: pre-development, construction, commissioning, operation, expansion, contraction, closure, or unknown;
- period and date precision;
- observed, projected, or modeled evidence basis;
- source or synthesis identifiers;
- central value, unit, interval kind, low and high values where applicable;
- aggregation identity and component membership;
- geographic allocation and local-retention method;
- confidence, assumptions, limitations, and unresolved evidence gaps.

Exposure measures should be included only when their definitions and periods permit comparison. Target measures include:

| Channel | Candidate measures | Required separation |
|---|---|---|
| Construction | Construction-eligible spending, locally retained purchases, job-years, payroll | Building construction versus equipment; annual flow versus cumulative capital; direct versus indirect and induced contribution |
| Operations | Energized or occupied MW, direct FTE, contractor FTE, payroll, operating purchases | Reported employment versus modeled contribution; facility versus campus or company totals |
| Fiscal | Assessed value, taxes billed, taxes paid, receipts by recipient, incentives, abatements, financing, attributable public cost | Tax base versus revenue; gross versus net tax; local versus state; annual versus cumulative; actual cost versus break-even threshold |
| Infrastructure | Facility electricity, peak demand, utility investment, water withdrawal, water consumption, wastewater and reuse | Facility versus system; customer-funded versus public; county versus utility or watershed geography |
| Community | Direct grants, local supplier participation, training and institutional funding | Direct transfers versus induced activity; commitments versus realized payments |

Missing and suppressed values remain missing. A zero is valid only when a source explicitly establishes zero for the stated measure and period.

## County-year aggregation

The county-year builder must:

- combine overlapping projects and phases without duplicating a campus or company total;
- retain construction, operation, expansion, and closure as separate exposure channels;
- prevent source claims used in a modeled synthesis from being added again as independent benefits;
- preserve direct, indirect, induced, and total contribution channels;
- retain beneficiary and payer jurisdiction for fiscal measures;
- record the number of contributing projects and the share of exposure that is observed, projected, or modeled;
- propagate each modeled input's interval or distribution into the county-year value; and
- reject aggregation when geography, period, unit, or accounting basis cannot be reconciled.

Continuous exposure variables should be scaled for interpretable estimates, such as per $100 million of construction-eligible spending, per 100 MW of operating capacity, per 100 direct FTE, or as a share of pre-exposure county GDP or employment. Binary opening indicators may supplement these measures but must not replace the underlying intensity and phase history.

## Outcome families

Each outcome receives its own definition, eligibility decision, comparison set, and model run. Candidate outcomes include:

- real GDP and GDP growth;
- covered employment and employment growth;
- average weekly wages and total payroll;
- establishments and private construction employment;
- population, labor-force participation, and commuting where supported;
- taxable or assessed property value;
- taxes paid and receipts by recipient jurisdiction;
- attributable local public-service and infrastructure costs;
- electricity price, generation or capacity outcomes at the appropriate utility geography; and
- water withdrawal, consumption, wastewater, reuse, and stress outcomes at the appropriate system or watershed geography.

Project investment, payroll, supplier output, household output, tax payments, and public costs are not interchangeable outcomes. The model will not combine them into a single economic-benefit total or composite score.

## Registered model ladder

The study will advance through the following model ladder. A later level does not erase earlier descriptive results.

### Level 0: coverage and descriptive trajectories

Publish exposure coverage, distributions, county histories, and pre/post descriptive changes. These products establish what is measured and reveal scale, skew, timing, and missingness. They make no counterfactual or causal claim.

### Level 1: pooled associations

Estimate correlations between continuous exposure intensity and outcomes across county-years. Models should include county and year effects where the panel supports them, disclose functional form and weighting, and cluster uncertainty at county level. The output label is **pooled association**. A coefficient at this level is not an attributable effect.

### Level 2: adjusted longitudinal associations

Add prespecified time-varying covariates and regional time controls needed for a particular outcome. Candidate confounders include prior growth, population, industry mix, construction cycle, major non-data-center investment, power availability, fiber access, urbanization, and prior data-center exposure. Do not control for a variable that is a mediator of the effect being estimated without declaring that estimand change.

### Level 3: event and matched designs

For eligible events, estimate cohort-aware or stacked event studies, matched difference-in-differences, or another registered quasi-experimental design that handles staggered timing and heterogeneous effects. Conventional two-way fixed-effects event studies are not sufficient when treatment effects and timing vary unless the run demonstrates that their weighting is appropriate.

### Level 4: hierarchical partial pooling

Use a hierarchical model to estimate overall association or effect distributions and variation by construction versus operation, project scale, facility type, development vintage, community size, region, grid conditions, and water stress. Project-level random effects do not make projects within one county independent; county clustering and shared county outcomes remain explicit.

## Modeled-input uncertainty

Modeled synthesis values must not enter the pooled analysis as error-free observations. Each run must declare how input uncertainty is propagated. The preferred target is repeated-draw estimation:

1. draw each modeled facility-year input from a distribution consistent with its registered interval kind and bounds;
2. rebuild the county-year exposure panel for that draw;
3. refit the registered statistical model;
4. combine within-draw estimation uncertainty with between-draw input uncertainty; and
5. publish the draw count, distribution assumptions, convergence or stability diagnostics, and resulting interval.

Point estimates derived from exact arithmetic may remain degenerate at their stated value, while uncertainty about completeness or attribution remains represented through confidence, sensitivity runs, or explicit alternative allocations. Source projections are analyzed separately from realized observations and cannot silently fill historical exposure.

## Statistical inference

County is the minimum clustering unit for county outcomes. With a limited number of exposed counties, the run should use small-cluster methods such as wild cluster bootstrap or randomization inference where appropriate and should not rely only on asymptotic p-values. State, region, utility territory, or watershed dependence must be addressed when the outcome and comparison design require it.

Every estimate must report effect or association scale, standard error or posterior uncertainty, interval, eligible county and year counts, exposure coverage, comparison-set size, weighting, fixed effects, covariates, and missing-data treatment. Practical magnitude and uncertainty take precedence over a binary significance label.

## Diagnostics and publication gates

A pooled association may be published when:

- the exposure and outcome definitions are registered;
- county-year aggregation passes overlap and scope validation;
- the eligible sample and exclusions are disclosed;
- input uncertainty is propagated or a justified sensitivity analysis is supplied;
- influential-county and functional-form checks are reported; and
- the result is labeled as an association.

A result may be labeled an attributable or causal effect only when all association requirements pass and the run additionally demonstrates:

- defensible treatment timing and an adequate pre-period;
- a comparison design that does not treat unknown exposure as known absence;
- acceptable pre-trend diagnostics;
- treatment and spillover definitions appropriate to the outcome geography;
- placebo dates or outcomes where applicable;
- robustness to alternative comparison sets and reasonable timing definitions;
- sensitivity to donor contamination and major concurrent investments;
- influence analysis, including leave-one-county-out results; and
- a registered estimand and interpretation that match the implemented method.

Failure of a gate produces an explicit analytical limit. It does not produce a zero effect or permit relabeling a descriptive comparison as causal.

## Target machine-readable products

The pooled layer will publish five versioned JSON products:

| Artifact | Purpose |
|---|---|
| `county-year-exposures.json` | County-year exposure values, evidence-state shares, contributing projects, aggregation identities, uncertainty, and eligibility fields |
| `pooled-model-definition.json` | Outcome, exposure, estimand, model family, covariates, fixed effects, comparison rules, uncertainty method, diagnostics, and publication gates registered before estimation |
| `pooled-model-run.json` | Exact definition version, input hashes, software version, eligible sample, exclusions, draw configuration, runtime parameters, and completion status |
| `pooled-model-diagnostics.json` | Coverage, fit, pre-trends, placebos, balance, influence, contamination, stability, and gate results |
| `pooled-model-estimates.json` | Associations or effects with evidence label, estimate, uncertainty, interpretation, limitations, and references to the run and diagnostics |

These files require schemas, referential-integrity validation, deterministic builders, hash manifests, focused tests, and public TypeScript types before the application consumes them.

## Public presentation

The application should present pooled findings through:

- a sample and coverage statement showing projects, unique counties, states, years, and comparison counties;
- separate construction, operating, fiscal, infrastructure, and environmental results;
- coefficient or effect-distribution views with uncertainty;
- diagnostics and sensitivity results beside any causal claim;
- subgroup results only when prespecified and adequately supported;
- direct links from pooled estimates to county-year exposure and project evidence; and
- clear labels for reported observation, modeled synthesis, pooled association, and attributable effect.

National compute capacity and security implications remain a separate interpretive layer. They cannot be added to local economic totals without their own quantitative scope and model.

## Implementation sequence

1. Complete the common facility-year account contract for the remaining 33 projects while preserving explicit missingness.
2. Add schemas and builders for facility-year and county-year exposure, including overlap and evidence-state validation.
3. Research and version comparison-pool exposure screens using the preserved national inventory and project histories.
4. Register outcome-specific Level 0 and Level 1 definitions and run statistical power and influence simulations before publication.
5. Publish descriptive trajectories and pooled associations with uncertainty propagation.
6. Advance eligible outcomes to event, matched, or hierarchical designs only after their diagnostic gates pass.
7. Add pooled results to the application with drill-down to county and project evidence.

## Target-state acceptance criteria

The pooled target state is complete when:

- all 36 selected projects appear in the facility-year contract and all 35 project counties appear in the exposure system;
- no project is silently dropped because evidence is missing or unfavorable;
- projects sharing a county and year are aggregated without duplicated claims or outcomes;
- every modeled input retains and propagates its uncertainty;
- every outcome discloses its eligible project, county, year, and comparison samples;
- the five governed artifacts validate and reproduce from versioned inputs;
- descriptive, associative, and causal outputs use distinct machine-readable and visible labels;
- failed causal gates remain visible and prevent causal publication;
- fiscal netting occurs only for matched recipient, jurisdiction, period, and accounting basis; and
- every public pooled result drills back to its model definition, run, diagnostics, county-year exposures, and project evidence.

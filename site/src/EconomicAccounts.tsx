import { useState } from "react";
import type { EconomicRecord, EconomicSource, ModeledSynthesis, StudyProject } from "./studyTypes";

const numbers = new Intl.NumberFormat("en-US", { maximumFractionDigits: 2 });
const waterRates = new Intl.NumberFormat("en-US", { maximumFractionDigits: 3 });
function amount(r: EconomicRecord) {
  const prefix = { exact: "", at_least: "At least ", greater_than: "More than ", up_to: "Up to ", approximately: "About " }[r.value_qualifier || "exact"];
  if (r.unit === "USD") {
    const money = new Intl.NumberFormat("en-US", { minimumFractionDigits: Number.isInteger(r.value) ? 0 : 2, maximumFractionDigits: 2 });
    return `${prefix}$${money.format(r.value)}`;
  }
  if (r.unit === "USD_per_hour") return `${prefix}$${numbers.format(r.value)} / hour`;
  if (r.unit === "kWh_per_year") return `${prefix}${numbers.format(r.value)} kWh / year`;
  if (r.unit === "gallons_per_year") return `${prefix}${numbers.format(r.value)} gallons / year`;
  if (r.unit === "million_gallons_per_day") return `${prefix}${waterRates.format(r.value)} million gallons / day`;
  if (r.unit === "square_feet") return `${prefix}${numbers.format(r.value)} square feet`;
  if (r.unit === "percent") return `${prefix}${numbers.format(r.value)}%`;
  return `${prefix}${numbers.format(r.value)} ${r.unit}`;
}
function sourceUrl(r: EconomicRecord, sources: EconomicSource[]) {
  const source = sources.find(s => s.source_id === r.source_id)!;
  return r.pdf_page ? `${source.url.split("#")[0]}#page=${r.pdf_page}` : source.url;
}
function modeledAmount(value: number, unit: ModeledSynthesis["unit"]) {
  if (unit === "USD") return `$${numbers.format(value)}`;
  if (unit === "USD_per_year") return `$${numbers.format(value)} / year`;
  if (unit === "USD_per_FTE") return `$${numbers.format(value)} / FTE`;
  if (unit === "USD_per_hour") return `$${numbers.format(value)} / hour`;
  if (unit === "gallons_per_year") return `${numbers.format(value)} gallons / year`;
  if (unit === "gallons_per_day") return `${numbers.format(value)} gallons / day`;
  if (unit === "million_gallons_per_day") return `${waterRates.format(value)} million gallons / day`;
  if (unit === "percent") return `${numbers.format(value)}%`;
  if (unit === "percentage_points") return `${numbers.format(value)} percentage points`;
  const labels: Partial<Record<ModeledSynthesis["unit"], string>> = {
    FTE: "FTE", job_years: "job-years", employees: "employees", workers: "workers", jobs: "jobs",
    kWh_per_year: "kWh / year", MWh_per_year: "MWh / year", MW: "MW", ratio: "ratio",
    PUE_ratio: "PUE", WUE_liters_per_kWh: "L / kWh", metric_tons_co2e_per_year: "metric tons CO₂e / year",
    acre_feet_per_year: "acre-feet / year", square_feet: "square feet", establishments: "establishments", index_points: "index points",
  };
  return `${numbers.format(value)} ${labels[unit] || unit}`;
}
const intervalLabels: Record<ModeledSynthesis["interval"]["kind"], string> = {
  point_estimate: "Point estimate",
  deterministic_counterfactual: "Deterministic counterfactual",
  sensitivity_envelope: "Sensitivity envelope",
  confidence_interval: "Confidence interval",
  credible_interval: "Credible interval",
  reported_band: "Reported band with modeled midpoint",
};

const fiscalMetrics = ["study.property_tax_receipts", "study.incentive_payments"];
const billingMetrics = ["study.account_assessed_value", "study.property_taxes_billed", "study.property_taxes_paid"];
const billingLabels: Record<string, string> = {
  "study.account_assessed_value": "Account assessed value",
  "study.property_taxes_billed": "Taxes billed",
  "study.property_taxes_paid": "Taxes paid",
};
const tifRevenueMetrics = [
  "study.tif_bond_pledged_revenue",
  "study.tif_revenue_loan_repayment",
  "study.tif_debt_service_fund_transfer_in",
];
const tifRevenueLabels: Record<string, string> = {
  "study.tif_bond_pledged_revenue": "City pledged TIF revenue",
  "study.tif_revenue_loan_repayment": "Private fund: project TIF applied",
  "study.tif_debt_service_fund_transfer_in": "City debt-service-fund transfer",
};
const tifDebtMetrics = [
  "study.tif_bond_principal_retired",
  "study.tif_bond_interest_and_fees",
  "study.tif_bond_outstanding_principal",
];
const tifDebtLabels: Record<string, string> = {
  "study.tif_bond_principal_retired": "Principal retired",
  "study.tif_bond_interest_and_fees": "Interest and fees",
  "study.tif_bond_outstanding_principal": "Year-end principal",
};
function isAnnualRecord(r: EconomicRecord): r is EconomicRecord & { period: { kind: "fiscal_year" | "calendar_year" | "tax_year" | "source_year"; year: number; label: string } } {
  return r.period.kind === "fiscal_year" || r.period.kind === "calendar_year" || r.period.kind === "tax_year" || r.period.kind === "source_year";
}
function isTaxBillingRecord(r: EconomicRecord) {
  return r.basis === "reported_actual" && r.period.kind === "tax_year" &&
    (r.value_qualifier || "exact") === "exact" && !!r.annual_series_key && billingMetrics.includes(r.metric_code);
}
function isAnnualFiscalRecord(r: EconomicRecord) {
  return r.basis === "reported_actual" && r.period.kind === "fiscal_year" &&
    (r.value_qualifier || "exact") === "exact" && !!r.annual_series_key && fiscalMetrics.includes(r.metric_code);
}
function isTifRevenueRecord(r: EconomicRecord) {
  return r.basis === "reported_actual" && r.period.kind === "calendar_year" &&
    (r.value_qualifier || "exact") === "exact" && tifRevenueMetrics.includes(r.metric_code);
}
function isTifDebtRecord(r: EconomicRecord) {
  return r.basis === "reported_actual" && r.period.kind === "calendar_year" &&
    (r.value_qualifier || "exact") === "exact" && tifDebtMetrics.includes(r.metric_code);
}

function FiscalHistory({ records, sources }: { records: EconomicRecord[]; sources: EconomicSource[] }) {
  const years = records.map(r => r.period.kind === "fiscal_year" ? r.period.year : 0);
  const first = records[0];
  const min = Math.min(...years), max = Math.max(...years);
  return <figure className="fiscal-history">
    <figcaption><strong>Tax receipts and incentive payments</strong><span>{first.scope.label}</span></figcaption>
    <p className="study-muted">Reported receipts and incentive payments for the government and recipient named above, matched by fiscal year and source scope. Missing receipts remain uncollected, not zero. These are partial fiscal accounts; other revenues, services and public costs remain uncollected. The taxpayer link is provisional where the source does not name it.</p>
    <table><thead><tr><th scope="col">Fiscal year</th><th scope="col">Taxes collected</th><th scope="col">Incentives paid</th><th scope="col">Documented difference</th></tr></thead>
      <tbody>{Array.from({ length: max - min + 1 }, (_, i) => min + i).map(year => {
        const receipt = records.find(row => row.metric_code === "study.property_tax_receipts" && row.period.kind === "fiscal_year" && row.period.year === year);
        const incentive = records.find(row => row.metric_code === "study.incentive_payments" && row.period.kind === "fiscal_year" && row.period.year === year);
        const difference = receipt && incentive ? receipt.value - incentive.value : null;
        return <tr key={year}><th scope="row">FY{year}</th>{fiscalMetrics.map(metric => {
          const r = records.find(row => row.metric_code === metric && row.period.kind === "fiscal_year" && row.period.year === year);
          return <td key={metric}>{r ? <a href={sourceUrl(r, sources)} target="_blank" rel="noreferrer" aria-label={`FY${year} ${r.label}: ${amount(r)}; open source`}>{amount(r)} ↗</a> : <span>Not collected</span>}</td>;
        })}<td>{difference === null ? <span>Not calculated</span> : <span aria-label={`FY${year} documented difference: ${difference} dollars`}>${numbers.format(difference)}</span>}</td></tr>;
      })}</tbody>
    </table>
    <p className="study-muted">Nominal dollars. Documented difference is taxes collected minus the separately disclosed incentive payment for that row. It is not a complete net fiscal benefit: other revenues, services, public costs, timing and the provisional taxpayer identification remain outside the calculation.</p>
  </figure>;
}

function TaxBillingHistory({ records, sources }: { records: EconomicRecord[]; sources: EconomicSource[] }) {
  const rows = records.filter(isAnnualRecord);
  const years = rows.map(r => r.period.year);
  const min = Math.min(...years), max = Math.max(...years);
  return <figure className="fiscal-history tax-billing-history">
    <figcaption><strong>Assessed value and property-tax account</strong><span>{rows[0].scope.label}</span></figcaption>
    <p className="study-muted">Taxes billed are account charges reported by the source and are not verified cash collected. Taxes paid appear only when the account source reports payment; they do not allocate receipts among taxing entities. Assessed values follow each source's definition. Each taxpayer account or parcel remains separate.</p>
    <table><thead><tr><th scope="col">Tax year</th>{billingMetrics.map(metric => <th scope="col" key={metric}>{billingLabels[metric]}</th>)}</tr></thead>
      <tbody>{Array.from({ length: max - min + 1 }, (_, i) => min + i).map(year => <tr key={year}><th scope="row">{year}</th>{billingMetrics.map(metric => {
        const r = rows.find(row => row.metric_code === metric && row.period.year === year);
        return <td key={metric}>{r ? <a href={sourceUrl(r, sources)} target="_blank" rel="noreferrer" aria-label={`Tax year ${year} ${r.label}: ${amount(r)}; open source`}>{amount(r)} ↗</a> : <span>Not collected</span>}</td>;
      })}</tr>)}</tbody>
    </table>
    <p className="study-muted">Nominal dollars. Recipient shares and negotiated incentive-program fees remain outside this account view. No combined revenue or net-benefit total is inferred.</p>
  </figure>;
}

function TifRevenueHistory({ records, sources }: { records: EconomicRecord[]; sources: EconomicSource[] }) {
  const rows = records.filter(isAnnualRecord);
  const years = [...new Set(rows.map(r => r.period.year))].sort();
  return <figure className="fiscal-history tif-revenue-history">
    <figcaption><strong>TIF revenue and debt-service transfers</strong><span>Series 2019 Data Center financing</span></figcaption>
    <p className="study-muted">The City audit, City debt-service-fund statement and private fund use different labels and amounts. The columns are shown side by side for reconciliation; they are not interchangeable and must not be added together.</p>
    <table><thead><tr><th scope="col">Calendar year</th>{tifRevenueMetrics.map(metric => <th scope="col" key={metric}>{tifRevenueLabels[metric]}</th>)}</tr></thead>
      <tbody>{years.map(year => <tr key={year}><th scope="row">{year}</th>{tifRevenueMetrics.map(metric => {
        const r = rows.find(row => row.metric_code === metric && row.period.year === year);
        return <td key={metric}>{r ? <a href={sourceUrl(r, sources)} target="_blank" rel="noreferrer" aria-label={`${year} ${r.label}: ${amount(r)}; open source`}>{amount(r)} ↗</a> : <span>Not collected</span>}</td>;
      })}</tr>)}</tbody>
    </table>
    <p className="study-muted">Nominal dollars. Only the 2022 City transfer and private-fund project-TIF amount agree exactly. The sources do not reconcile the later differences, so no combined revenue or net-benefit figure is calculated.</p>
  </figure>;
}

function TifDebtHistory({ records, sources }: { records: EconomicRecord[]; sources: EconomicSource[] }) {
  const rows = records.filter(isAnnualRecord);
  const years = [...new Set(rows.map(r => r.period.year))].sort();
  return <figure className="fiscal-history tif-debt-history">
    <figcaption><strong>Data-center TIF bond debt service</strong><span>City of Hammond Series 2019</span></figcaption>
    <p className="study-muted">Principal retired and interest and fees are annual flows. Year-end principal is a debt stock. The table traces financing obligations; it is not a measure of project investment, public subsidy cost or community benefit.</p>
    <table><thead><tr><th scope="col">Calendar year</th>{tifDebtMetrics.map(metric => <th scope="col" key={metric}>{tifDebtLabels[metric]}</th>)}</tr></thead>
      <tbody>{years.map(year => <tr key={year}><th scope="row">{year}</th>{tifDebtMetrics.map(metric => {
        const r = rows.find(row => row.metric_code === metric && row.period.year === year);
        return <td key={metric}>{r ? <a href={sourceUrl(r, sources)} target="_blank" rel="noreferrer" aria-label={`${year} ${r.label}: ${amount(r)}; open source`}>{amount(r)} ↗</a> : <span>Not collected</span>}</td>;
      })}</tr>)}</tbody>
    </table>
    <p className="study-muted">Nominal dollars. The separate remaining-principal-and-interest series includes future interest and therefore exceeds outstanding principal.</p>
  </figure>;
}

function AnnualHistory({ records, sources }: { records: EconomicRecord[]; sources: EconomicSource[] }) {
  const rows = records.filter(isAnnualRecord).filter(r => r.basis === "reported_actual");
  const years = rows.map(r => r.period.year);
  const min = Math.min(...years), max = Math.max(...years);
  const ceiling = Math.max(...rows.map(r => r.value));
  const first = rows[0];
  if (!first) return null;
  const yearPrefix = first.period.kind === "fiscal_year" ? "FY" : first.period.kind === "calendar_year" ? "CY" : first.period.kind === "tax_year" ? "TY" : "";
  const yearBasis = first.period.kind === "fiscal_year" ? "Fiscal years" : first.period.kind === "calendar_year" ? "Calendar years" : first.period.kind === "tax_year" ? "Tax years" : "Source reference years";
  return <figure className="economic-history">
    <figcaption><strong>{first.label} over time</strong><span>{first.scope.label}</span></figcaption>
    <p className="study-muted">{yearBasis}; values as reported. {first.unit === "USD" && "Dollar values are nominal. "}Each bar starts at zero; uncollected years remain blank. {first.metric_code === "study.taxable_assessed_value" && "Taxable value is a stock of property value, not annual spending or tax receipts."}{first.metric_code === "study.taxable_property_value" && "Taxable value is a property stock, not annual spending or tax receipts."}{first.metric_code === "study.reported_asset_cost" && "Reported asset cost is a personal-property stock, not annual capital spending."}{first.metric_code === "study.campus_capital_expenditure" && "Campus capital expenditure is a flow across the stated multi-facility campus; it is not allocated to the mapped building or to local suppliers."}{first.metric_code === "study.estimated_actual_property_value" && "Reported valuation estimates are property stocks, not tax receipts or net tax capacity. Tax years here are payable years; assessment dates precede them and appear in the source records."}{first.metric_code === "study.appraised_property_value" && "County appraised value is a property stock; assessed value and account taxes are shown separately."}{first.metric_code === "study.full_cash_property_value" && "Full cash value is a property stock; assessed value, tax bills and paid account totals are shown separately."}</p>
    <div className="history-bars">{Array.from({ length: max - min + 1 }, (_, i) => min + i).map(year => {
      const row = rows.find(r => r.period.year === year);
      return <div className={`history-bar-row ${row ? "" : "uncollected"}`} key={year}>
        <span>{yearPrefix}{year}</span><div className="history-bar-track" aria-hidden="true">{row && <div style={{ width: `${ceiling ? row.value / ceiling * 100 : 0}%` }} />}</div>
        {row ? <a href={sourceUrl(row, sources)} target="_blank" rel="noreferrer" aria-label={`${yearPrefix}${year}: ${amount(row)}; open source`}>{amount(row)} ↗</a> : <span>Not collected</span>}
      </div>;
    })}</div>
  </figure>;
}

function ModeledCards({ project }: { project: StudyProject }) {
  return <>
    <p className="modeled-note"><strong>Modeled synthesis—not observed or audited.</strong> Every interval names its type: sensitivity envelopes and deterministic counterfactuals are not confidence intervals. Direct records remain preferred, source forecasts stay separate, and these values are excluded from sourced-record and realized-benefit totals.</p>
    <div className="economic-record-list modeled-record-list">{project.modeled_syntheses.map(r => <article className="economic-record modeled-record" key={r.estimate_id}>
      <div><span className="modeled-badge">Modeled synthesis · not observed or audited</span><h4>{r.label}</h4><p>{r.period.label}</p></div>
      <div><strong className="record-value">{modeledAmount(r.value, r.unit)}</strong><p className="scenario-range">{intervalLabels[r.interval.kind]}: {modeledAmount(r.interval.low, r.unit)}–{modeledAmount(r.interval.high, r.unit)}{r.interval.confidence_level ? ` · ${r.interval.confidence_level * 100}%` : ""}</p></div>
      <p className="record-scope"><span>{r.confidence} confidence · {r.contribution_channel.replace("not_applicable", "non-contribution")} channel</span>{r.scope.label}</p>
      <details><summary>Method, parameters, assumptions and sources</summary><p>{r.notes}</p><p><strong>Decision use:</strong> {r.decision_relevance}</p><p><strong>Method:</strong> {r.derivation.method.replaceAll("_", " ")} · {r.derivation.model_version}</p><p><strong>Formula:</strong> {r.derivation.formula}</p><p><strong>{intervalLabels[r.interval.kind]}:</strong> {r.interval.interpretation}</p><p><strong>Confidence:</strong> {r.confidence_rationale}</p><p><strong>Aggregation:</strong> {r.aggregation.role} in {r.aggregation.aggregation_id}; do not sum outside a declared total.</p><h5>Named parameters</h5><dl className="modeled-parameters">{r.parameters.map(parameter => <div key={parameter.name}><dt>{parameter.name.replaceAll("_", " ")}</dt><dd>{numbers.format(parameter.value)} {parameter.unit} · {parameter.provenance.kind}{parameter.provenance.reference_id ? ` ${parameter.provenance.reference_id}` : ""}<br />{parameter.transformation}</dd></div>)}</dl><h5>Assumptions</h5><ul>{r.derivation.assumptions.map(a => <li key={a}>{a}</li>)}</ul><h5>Limitations</h5><ul>{r.limitations.map(a => <li key={a}>{a}</li>)}</ul>{r.multiplier_provenance && <p><strong>Multiplier:</strong> {r.multiplier_provenance.model_name} {r.multiplier_provenance.model_version}, {r.multiplier_provenance.geography}, vintage {r.multiplier_provenance.vintage}. {r.multiplier_provenance.local_purchase_assumption}</p>}{r.causal_design && <p><strong>Causal design:</strong> {r.causal_design.comparison_design}. Treatment: {r.causal_design.treatment_timing}. Outcome: {r.causal_design.outcome_definition}. Pre: {r.causal_design.pre_period}; post: {r.causal_design.post_period}. Diagnostics: {r.causal_design.diagnostics.join("; ")}.</p>}<p><strong>Unresolved evidence gap:</strong> {r.evidence_search.remaining_evidence_gap}</p>{r.derivation.input_source_ids.map(sourceId => {
        const source = project.modeled_sources.find(s => s.source_id === sourceId);
        return source ? <a key={sourceId} href={source.url} target="_blank" rel="noreferrer">{source.title} ↗</a> : null;
      })}<small>{project.synthesis_version} · {project.modeling_policy_version} · reviewed {r.reviewed_on}</small></details>
    </article>)}</div>
    <details className="research-details"><summary>Modeled-synthesis limitations</summary><p>{project.modeled_scope_note}</p></details>
  </>;
}

export function EconomicAccounts({ project }: { project: StudyProject }) {
  type EvidenceTab = EconomicRecord["basis"] | "modeled_synthesis";
  const tabs: EvidenceTab[] = ["reported_actual", "source_projection", "modeled_synthesis"];
  const [basis, setBasis] = useState<EvidenceTab>(project.reported_actual_count ? "reported_actual" : project.projection_count ? "source_projection" : "modeled_synthesis");
  const rows = basis === "modeled_synthesis" ? [] : project.economic_records.filter(r => r.basis === basis);
  const fiscalRows = rows.filter(isAnnualFiscalRecord);
  const fiscalScopes = [...new Set(fiscalRows.map(r => JSON.stringify(r.scope)))];
  const billingRows = rows.filter(isTaxBillingRecord);
  const billingScopes = [...new Set(billingRows.map(r => JSON.stringify(r.scope)))];
  const tifRevenueRows = rows.filter(isTifRevenueRecord);
  const tifDebtRows = rows.filter(isTifDebtRecord);
  const series = [...new Set(rows.filter(r => !isAnnualFiscalRecord(r) && !isTaxBillingRecord(r) && !isTifRevenueRecord(r) && !isTifDebtRecord(r)).map(r => r.annual_series_key).filter((s): s is string => !!s))];
  return <section className="project-section economic-accounts" aria-labelledby="accounts-title">
    <div className="section-heading"><div><span className="eyebrow">Economic contribution over time</span><h3 id="accounts-title">Economic evidence</h3></div><span className="account-count">{project.economic_record_count} sourced records · {project.modeled_synthesis_count ? `${project.modeled_synthesis_count} modeled syntheses` : "partial coverage"}</span></div>
    <p className="study-intro">Source records and analyst-modeled syntheses are kept in separate views. Workforce snapshots and construction peaks do not establish new jobs, annual averages or local hiring. Models expose their inputs and assumptions and do not convert missing records into facts.</p>
    <div className="economic-tabs" role="tablist" aria-label="Economic evidence basis" onKeyDown={e => {
      if (!["ArrowLeft", "ArrowRight", "Home", "End"].includes(e.key)) return;
      e.preventDefault();
      const current = tabs.indexOf(basis);
      const next = e.key === "Home" ? tabs[0] : e.key === "End" ? tabs[tabs.length - 1] : tabs[(current + (e.key === "ArrowRight" ? 1 : -1) + tabs.length) % tabs.length];
      setBasis(next);
      e.currentTarget.querySelectorAll<HTMLButtonElement>("button")[tabs.indexOf(next)].focus();
    }}>
      <button type="button" id="actual-tab" role="tab" tabIndex={basis === "reported_actual" ? 0 : -1} aria-selected={basis === "reported_actual"} aria-controls="economic-records" onClick={() => setBasis("reported_actual")}>Reported activity <span>{project.reported_actual_count}</span></button>
      <button type="button" id="projection-tab" role="tab" tabIndex={basis === "source_projection" ? 0 : -1} aria-selected={basis === "source_projection"} aria-controls="economic-records" onClick={() => setBasis("source_projection")}>Plans & forecasts <span>{project.projection_count}</span></button>
      <button type="button" id="modeled-tab" role="tab" tabIndex={basis === "modeled_synthesis" ? 0 : -1} aria-selected={basis === "modeled_synthesis"} aria-controls="economic-records" onClick={() => setBasis("modeled_synthesis")}>Modeled synthesis <span>{project.modeled_synthesis_count}</span></button>
    </div>
    <div id="economic-records" role="tabpanel" aria-labelledby={basis === "reported_actual" ? "actual-tab" : basis === "source_projection" ? "projection-tab" : "modeled-tab"}>
      {basis === "modeled_synthesis" ? <ModeledCards project={project} /> : <>
      {basis === "source_projection" && <p className="projection-note">Plans retain their original announcement dates and time horizons, including unspecified completion dates. Realized spending, jobs and abatements have not been verified. Amounts with different horizons cannot be compared as a fiscal balance.</p>}
      {!rows.length && <p className="study-muted">No {basis === "reported_actual" ? "reported activity" : "plans or forecasts"} collected for this project.</p>}
      {fiscalScopes.map(scope => <FiscalHistory key={scope} records={fiscalRows.filter(r => JSON.stringify(r.scope) === scope)} sources={project.economic_sources} />)}
      {billingScopes.map(scope => <TaxBillingHistory key={scope} records={billingRows.filter(r => JSON.stringify(r.scope) === scope)} sources={project.economic_sources} />)}
      {!!tifRevenueRows.length && <TifRevenueHistory records={tifRevenueRows} sources={project.economic_sources} />}
      {!!tifDebtRows.length && <TifDebtHistory records={tifDebtRows} sources={project.economic_sources} />}
      {series.map(key => <AnnualHistory key={key} records={rows.filter(r => r.annual_series_key === key)} sources={project.economic_sources} />)}
      <div className="economic-record-list">{rows.map(r => <article className="economic-record" key={r.claim_id}>
        <div><h4>{r.label}</h4><p>{r.period.label}</p></div>
        <strong className="record-value">{amount(r)}</strong>
        <p className="record-scope"><span>{r.scope.level === "campus" ? "Campus scope" : r.scope.level === "supporting_infrastructure" ? "Supporting infrastructure" : r.scope.level === "county_context" ? "County industry context" : "Company / county context"}</span>{r.scope.label}</p>
        <details><summary>Source and interpretation</summary><p>{r.notes}</p><p className="study-muted">Not allocated to the individual mapped inventory record. {r.measure_type === "peak" ? "A peak workforce count; duration and job-years cannot be inferred." : r.measure_type === "stock" ? "A stock at the reported period; do not sum across years." : r.measure_type === "rate" ? "A rate; hours and payroll cannot be inferred." : "A flow for the stated period; no total economic-benefit sum is defined."}</p><a href={sourceUrl(r, project.economic_sources)} target="_blank" rel="noreferrer">{project.economic_sources.find(s => s.source_id === r.source_id)?.title} ↗</a><small>{r.pdf_page && <>PDF page {r.pdf_page} · printed page {r.printed_page} · </>}{r.source_locator}</small></details>
      </article>)}</div>
      </>}
    </div>
    <details className="research-details"><summary>Evidence review and source limitations</summary><p>{project.economic_scope_note}</p>{project.economic_sources.map(s => <div key={s.source_id}><a href={s.url} target="_blank" rel="noreferrer">{s.title} ↗</a><p>{s.notes}</p><small>Retrieved {s.retrieved_on} · {s.review_method === "pdf_text_and_page_image" ? "PDF text and page image checked" : s.review_method === "web_page" ? "Web page text checked" : s.review_method === "structured_data" ? "Structured data and published layout checked" : "Web-extracted PDF text checked"}</small></div>)}</details>
  </section>;
}

import { useEffect, useMemo, useState } from "react";
import type { CountyControlIndex, CountyControlRecord } from "./studyTypes";

const base = `${import.meta.env.BASE_URL}data/v1/analysis/county-control-eligibility/`;
const integer = new Intl.NumberFormat("en-US");
const money = new Intl.NumberFormat("en-US", { style: "currency", currency: "USD", notation: "compact", maximumFractionDigits: 1 });

function exposureLabel(status: CountyControlRecord["exposure_status"]) {
  return ({
    known_facility_inventory: "Known facility inventory",
    known_facility_and_stopped_proposal: "Facility + stopped proposal",
    known_stopped_proposal_only: "Stopped proposal only",
    no_known_project_record: "No known project record · audit pending",
  } as const)[status];
}

export function ControlRegistry() {
  const [index, setIndex] = useState<CountyControlIndex | null>(null);
  const [records, setRecords] = useState<CountyControlRecord[]>([]);
  const [state, setState] = useState("");
  const [search, setSearch] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [loadingState, setLoadingState] = useState(false);
  useEffect(() => {
    let active = true;
    fetch(`${base}index.json`).then(async response => {
      if (!response.ok) throw new Error("The comparison-county registry could not be loaded.");
      const result = await response.json() as CountyControlIndex;
      if (active) setIndex(result);
    }).catch((reason: unknown) => { if (active) setError(reason instanceof Error ? reason.message : "Unable to load registry."); });
    return () => { active = false; };
  }, []);
  useEffect(() => {
    let active = true;
    setRecords([]);
    if (!state || !index) return () => { active = false; };
    const partition = index.states.find(candidate => candidate.state_abbr === state);
    if (!partition) return () => { active = false; };
    setLoadingState(true);
    fetch(`${base}${partition.path}`).then(async response => {
      if (!response.ok) throw new Error(`The ${state} county screening records could not be loaded.`);
      const result = await response.json() as CountyControlRecord[];
      if (active) setRecords(result);
    }).catch((reason: unknown) => { if (active) setError(reason instanceof Error ? reason.message : "Unable to load state records."); })
      .finally(() => { if (active) setLoadingState(false); });
    return () => { active = false; };
  }, [state, index]);
  const visible = useMemo(() => records.filter(record => `${record.county_name} ${record.county_fips}`.toLowerCase().includes(search.trim().toLowerCase())), [records, search]);
  if (error) return <div className="error-panel" role="alert">{error}</div>;
  if (!index) return <p className="study-loading" role="status">Loading the comparison-county registry…</p>;
  const excluded = index.counts.by_control_eligibility.excluded_known_exposure ?? 0;
  const unresolved = index.counts.by_control_eligibility.unresolved_negative_evidence ?? 0;
  const verified = index.counts.by_control_eligibility.eligible_verified_no_known_project ?? 0;
  return <article className="control-registry">
    <header className="control-hero"><span className="eyebrow">National comparison design · screening release</span><h2>Comparison counties,<br />without pretending absence is evidence.</h2><p>This registry separates known data-center exposure from counties that still require a documented negative search. It is the foundation for treatment-year-specific matching—not a finished donor pool.</p></header>
    <section className="control-counts" aria-label="County screening status"><div><strong>{integer.format(index.counts.counties)}</strong><span>county panels screened</span></div><div><strong>{integer.format(excluded)}</strong><span>excluded by known exposure</span></div><div><strong>{integer.format(unresolved)}</strong><span>negative-evidence audits pending</span></div><div><strong>{verified}</strong><span>verified controls today</span></div></section>
    <aside className="control-warning"><strong>No known record does not mean “never considered.”</strong><p>{index.interpretation_warning}</p></aside>
    <section className="control-method"><div><span className="eyebrow">Eligibility gate</span><h3>What must be checked</h3><p>{index.scope}</p></div><ol>{index.required_negative_search_domains.map(domain => <li key={domain.code}>{domain.label}</li>)}</ol></section>
    <section className="control-browser" aria-labelledby="control-browser-title"><div className="section-heading"><div><span className="eyebrow">Inspect the screen</span><h3 id="control-browser-title">County registry</h3></div><a href={`${base}index.json`} download="county-control-eligibility-index.json">Download index JSON ↓</a></div>
      <div className="study-filters control-filters"><label>State<select value={state} onChange={event => { setState(event.target.value); setSearch(""); }}><option value="">Choose a state</option>{index.states.map(item => <option key={item.state_abbr} value={item.state_abbr}>{item.state_abbr} · {item.records} counties</option>)}</select></label><label className="study-search">Search selected state<input type="search" value={search} onChange={event => setSearch(event.target.value)} placeholder="County name or FIPS" disabled={!state} /></label></div>
      {!state ? <div className="study-empty"><h3>Select a state</h3><p>State partitions keep the national registry lightweight while preserving all {integer.format(index.counts.counties)} county records.</p></div> : loadingState ? <p role="status">Loading {state} county records…</p> : <><p className="results-line" role="status">Showing {visible.length} counties in {state}</p><div className="control-cards">{visible.map(record => <article key={record.county_fips} className={`control-card ${record.control_eligibility}`}><div><span className="control-status">{exposureLabel(record.exposure_status)}</span><span>FIPS {record.county_fips}</span></div><h4><a href={`#/county/${record.county_fips}`}>{record.county_name}, {record.state_abbr} ↗</a></h4><dl><div><dt>Population · 2024</dt><dd>{record.latest_metrics.population == null ? "Unavailable" : integer.format(record.latest_metrics.population)}</dd></div><div><dt>Real GDP · 2024</dt><dd>{record.latest_metrics.real_gdp_usd == null ? "Unavailable" : money.format(record.latest_metrics.real_gdp_usd)}</dd></div><div><dt>Panel</dt><dd>{record.panel.complete_year_count}/24 complete years</dd></div><div><dt>Known active facilities</dt><dd>{record.known_evidence.active_canonical_facility_count}</dd></div></dl><p>{record.required_next_step}</p></article>)}</div></>}
    </section>
    <section className="control-next"><span className="eyebrow">Before estimation</span><h3>Matching happens at the event date</h3><ul>{index.future_matching_requirements.map(requirement => <li key={requirement}>{requirement}</li>)}</ul><p>Current 2024 values are descriptive browser context only. They are not match scores and will not enter a pre-treatment match for an earlier project.</p></section>
  </article>;
}

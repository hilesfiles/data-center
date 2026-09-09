import { useEffect, useMemo, useState } from "react";
import type { CountyComparisonIndex, CountyComparisonHost, CountyControlIndex, CountyControlRecord } from "./studyTypes";

const base = `${import.meta.env.BASE_URL}data/v1/analysis/county-control-eligibility/`;
const integer = new Intl.NumberFormat("en-US");
const money = new Intl.NumberFormat("en-US", { style: "currency", currency: "USD", notation: "compact", maximumFractionDigits: 1 });
const percent = new Intl.NumberFormat("en-US", { style: "percent", maximumFractionDigits: 1 });

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
  const [matches, setMatches] = useState<CountyComparisonIndex | null>(null);
  const [hostFips, setHostFips] = useState("");
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
    fetch(`${import.meta.env.BASE_URL}data/v1/analysis/county-comparison-matches/index.json`).then(async response => {
      if (!response.ok) throw new Error("The host-to-comparison match register could not be loaded.");
      const result = await response.json() as CountyComparisonIndex;
      if (active) { setMatches(result); setHostFips(result.hosts[0]?.county_fips ?? ""); }
    }).catch((reason: unknown) => { if (active) setError(reason instanceof Error ? reason.message : "Unable to load matches."); });
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
  const selectedHost = matches?.hosts.find(host => host.county_fips === hostFips) ?? null;
  if (error) return <div className="error-panel" role="alert">{error}</div>;
  if (!index) return <p className="study-loading" role="status">Loading the comparison-county registry…</p>;
  const excluded = index.counts.by_control_eligibility.excluded_known_exposure ?? 0;
  const unresolved = index.counts.by_control_eligibility.unresolved_negative_evidence ?? 0;
  const verified = index.counts.by_control_eligibility.eligible_verified_no_known_project ?? 0;
  return <article className="control-registry">
    <header className="control-hero"><span className="eyebrow">Counties with and without data centers</span><h2>Comparable communities.<br />Different exposure.</h2><p>Each of the 35 active-project host counties has a 12-county analytical reserve drawn from counties clearing three national screens and the governed local positive-evidence screen. The five strongest preliminary matches are shown, with completed seven-domain absence reviews distinguished from unresolved candidates.</p></header>
    {matches && <ComparisonMatches matches={matches} selected={selectedHost} hostFips={hostFips} setHostFips={setHostFips} />}
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

export function CountyComparisonSummary({ fips }: { fips: string }) {
  const [host, setHost] = useState<CountyComparisonHost | null>(null);
  useEffect(() => {
    let active = true;
    fetch(`${import.meta.env.BASE_URL}data/v1/analysis/county-comparison-matches/index.json`).then(async response => {
      if (!response.ok) return null;
      return await response.json() as CountyComparisonIndex;
    }).then(result => { if (active && result) setHost(result.hosts.find(candidate => candidate.county_fips === fips) ?? null); }).catch(() => undefined);
    return () => { active = false; };
  }, [fips]);
  if (!host) return null;
  return <section className="county-comparison-section" aria-labelledby="county-comparison-title"><div className="section-heading"><div><span className="eyebrow">With / without data-center exposure</span><h3 id="county-comparison-title">Comparable counties without known data-center records</h3></div><a href="#/controls">Open full comparison register →</a></div><p className="study-muted">Showing the strongest five of 12 candidates ranked on the {host.baseline.start_year}–{host.baseline.end_year} economic baseline. Candidates clear three national data-center screens and the governed local positive-evidence screen; each candidate’s seven-domain review status is retained in the full register.</p><div className="county-comparison-list">{host.comparison_candidates.slice(0, 5).map(candidate => <article key={candidate.county_fips}><span>#{candidate.rank}</span><div><strong><a href={`#/county/${candidate.county_fips}`}>{candidate.county_name}, {candidate.state_abbr} ↗</a></strong><small>{candidate.census_division}{candidate.same_census_division ? " · same division" : candidate.same_census_region ? " · same region" : ""}</small></div><em>{candidate.match_score}<small>match</small></em></article>)}</div><p className="impact-account-note">Economic similarity is not a causal result. A completed absence review clears only the defined public-record search domains; treatment-year diagnostics and spillover screening remain separate gates.</p></section>;
}

function MetricPair({ label, host, candidate, format = integer.format }: { label: string; host: number; candidate: number; format?: (value: number) => string }) {
  return <div><dt>{label}</dt><dd><span>{format(host)}</span><span>{format(candidate)}</span></dd></div>;
}

function ComparisonMatches({ matches, selected, hostFips, setHostFips }: { matches: CountyComparisonIndex; selected: CountyComparisonHost | null; hostFips: string; setHostFips: (value: string) => void }) {
  return <section className="comparison-matches" aria-labelledby="comparison-matches-title">
    <div className="section-heading"><div><span className="eyebrow">Matched county sets</span><h3 id="comparison-matches-title">With a data center / without a known data-center record</h3></div><div className="comparison-downloads"><a href={`${import.meta.env.BASE_URL}data/v1/analysis/county-comparison-matches/index.json`} download="county-comparison-matches.json">Download matches JSON ↓</a><a href={`${import.meta.env.BASE_URL}data/v1/analysis/county-comparison-matches/verification-queue.json`} download="county-comparison-verification-queue.json">Download control audit queue ↓</a><a href={`${import.meta.env.BASE_URL}data/v1/analysis/county-treatment-anchor-review/index.json`} download="county-treatment-anchor-review.json">Download treatment-date queue ↓</a><a href={`${import.meta.env.BASE_URL}data/v1/methodology/county-data-center-exposure-policy.json`} download="county-data-center-exposure-policy.json">Download exposure policy ↓</a></div></div>
    <div className="comparison-summary"><div><strong>{matches.counts.host_counties}</strong><span>host counties</span></div><div><strong>{matches.counts.comparison_candidates}</strong><span>analytical candidate slots</span></div><div><strong>{matches.counts.unique_comparison_counties}</strong><span>unique comparison counties</span></div><div><strong>{integer.format(matches.counts.screened_candidate_pool_count)}</strong><span>counties clearing national + local positive screens</span></div><div><strong>{matches.counts.externally_verified_absent}</strong><span>seven-domain reviews cleared</span></div></div>
    <label className="comparison-host-select">Host county<select value={hostFips} onChange={event => setHostFips(event.target.value)}>{matches.hosts.map(host => <option key={host.county_fips} value={host.county_fips}>{host.county_name}, {host.state_abbr}</option>)}</select></label>
    {selected && <><div className="comparison-host-heading"><div><span className="eyebrow">County with data-center exposure</span><h4><a href={`#/county/${selected.county_fips}`}>{selected.county_name}, {selected.state_abbr} ↗</a></h4><p>{selected.project_names.join(" · ")}</p></div><aside><strong>{selected.baseline.start_year}–{selected.baseline.end_year}</strong><span>{selected.baseline.strategy === "pre_documented_project_anchor" ? "Pre-project matching window" : "Structural matching window"}</span></aside></div><p className="comparison-baseline-note">{selected.baseline.note}</p>
      <p className="comparison-baseline-note">Showing the strongest {matches.counts.presentation_candidates_per_host} of {matches.counts.analytical_candidates_per_host} ranked candidates. The downloadable audit queue includes the full reserve.</p><div className="comparison-candidate-grid">{selected.comparison_candidates.slice(0, matches.counts.presentation_candidates_per_host).map(candidate => <article key={candidate.county_fips} className="comparison-candidate"><div className="comparison-rank"><span>#{candidate.rank}</span><strong>{candidate.match_score}</strong><small>match score</small></div><div className="comparison-candidate-body"><div className="comparison-candidate-title"><div><h5><a href={`#/county/${candidate.county_fips}`}>{candidate.county_name}, {candidate.state_abbr} ↗</a></h5><span>{candidate.census_division}{candidate.same_census_division ? " · same division" : candidate.same_census_region ? " · same region" : ""}</span></div><em>{candidate.verification_status === "eligible_verified_no_known_project" ? "Seven-domain review cleared" : "Absence review required"}</em></div><dl className="comparison-metrics"><div className="comparison-metric-head"><dt>Baseline measure</dt><dd><span>Host</span><span>Candidate</span></dd></div><MetricPair label="Average population" host={selected.features.population_mean} candidate={candidate.features.population_mean} /><MetricPair label="Average real GDP" host={selected.features.real_gdp_usd_mean} candidate={candidate.features.real_gdp_usd_mean} format={money.format} /><MetricPair label="Average employment" host={selected.features.covered_employment_mean} candidate={candidate.features.covered_employment_mean} /><MetricPair label="GDP growth" host={selected.features.real_gdp_growth_rate} candidate={candidate.features.real_gdp_growth_rate} format={percent.format} /><MetricPair label="Employment growth" host={selected.features.covered_employment_growth_rate} candidate={candidate.features.covered_employment_growth_rate} format={percent.format} /></dl></div></article>)}</div>
    </>}
    <aside className="comparison-caveat"><strong>Candidate does not mean verified absence.</strong><p>{matches.interpretation_limits.join(" ")}</p><p>{matches.counts.candidate_specific_positive_exclusions} counties surfaced by candidate-specific research were removed in addition to the national screens. {matches.positive_exposure_findings.interpretation_note}</p><div>{matches.screening_sources.map(source => source.url ? <a href={source.url} target="_blank" rel="noreferrer" key={source.source_id}>{source.title} · v{source.version} ↗</a> : <span key={source.source_id}>{source.title} · {source.version}</span>)}</div></aside>
  </section>;
}

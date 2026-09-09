import { useEffect, useMemo, useState } from "react";
import type {
  RejectedProject,
  RejectedProjectIndex,
  RejectedProjectSummary,
  RejectedProjectTimelineEvent,
} from "./studyTypes";

const studyBase = `${import.meta.env.BASE_URL}data/v1/study/`;

const words = (value: string) => value.replaceAll("_", " ");

const readinessLabels: Record<RejectedProjectSummary["outcome_readiness"], string> = {
  disposition_verified: "Disposition verified",
  post_decision_tracking: "Post-decision tracking",
  early_outcome_evidence: "Early outcome evidence",
  comparison_ready: "Comparison ready",
};

const categoryLabels: Record<RejectedProjectTimelineEvent["category"], string> = {
  proposal: "Proposal",
  public_opposition: "Public opposition",
  government_review: "Government review",
  decision: "Decision",
  withdrawal: "Withdrawal",
  litigation: "Litigation",
  site_afterlife: "Site afterlife",
};

export function RejectedProjectRegister({ registry }: { registry: RejectedProjectIndex }) {
  const [search, setSearch] = useState("");
  const [disposition, setDisposition] = useState("");
  const [readiness, setReadiness] = useState("");
  const [state, setState] = useState("");
  const projects = useMemo(() => registry.projects.filter(project =>
    (!disposition || project.disposition === disposition) &&
    (!readiness || project.outcome_readiness === readiness) &&
    (!state || project.state_abbr === state) &&
    `${project.name} ${project.developer_label} ${project.county_name} ${project.state_abbr}`.toLocaleLowerCase()
      .includes(search.trim().toLocaleLowerCase()),
  ), [registry, search, disposition, readiness, state]);
  return <>
    <section className="study-hero rejected-hero">
      <div><span className="eyebrow">Private proposals that did not proceed</span>
        <h2>What happened<br />when communities said no?</h2>
        <p>Follow verified denials and withdrawals from proposal through public review, decision, litigation, redesign, and site aftermath. A stopped proposal is a documented event—not automatically proof of an economic gain or loss.</p>
        <a className="study-map-link" href="#/map">Compare both cohorts on the map <span aria-hidden="true">↗</span></a>
      </div>
      <div className="study-counts rejected-counts" aria-label="Rejected proposal coverage">
        <div><strong>{registry.counts.projects}</strong><span>verified proposals</span></div>
        <div><strong>{registry.counts.counties}</strong><span>affected counties</span></div>
        <div><strong>{registry.counts.states}</strong><span>states represented</span></div>
        <p>Curated comparison register · {registry.counts.by_disposition.rejected ?? 0} denied · {registry.counts.by_disposition.withdrawn ?? 0} withdrawn<br />Readiness is assessed separately for every proposal.</p>
      </div>
    </section>
    <section className="study-register rejected-register" aria-labelledby="rejected-register-title">
      <div className="section-heading"><div><span className="eyebrow">Verified case files</span><h2 id="rejected-register-title">Rejected & withdrawn proposals</h2></div><a href={`${studyBase}rejected-projects/index.json`} download="rejected-projects.json">Download register JSON ↓</a></div>
      <p className="study-intro">Cards distinguish disposition, community role, finality, and research readiness. Reported investment, jobs, capacity, and tax benefits remain proposal claims—not realized outcomes.</p>
      <div className="rejected-filters">
        <label>Search proposals<input type="search" value={search} onChange={event => setSearch(event.target.value)} placeholder="Project, developer, or county" /></label>
        <label>Disposition<select value={disposition} onChange={event => setDisposition(event.target.value)}><option value="">All dispositions</option><option value="rejected">Rejected</option><option value="withdrawn">Withdrawn</option><option value="cancelled">Cancelled</option></select></label>
        <label>Outcome evidence<select value={readiness} onChange={event => setReadiness(event.target.value)}><option value="">All readiness levels</option>{Object.entries(readinessLabels).map(([value, label]) => <option value={value} key={value}>{label}</option>)}</select></label>
        <label>State<select value={state} onChange={event => setState(event.target.value)}><option value="">All states</option>{[...new Set(registry.projects.map(project => project.state_abbr))].sort().map(value => <option key={value}>{value}</option>)}</select></label>
      </div>
      <div className="results-line"><p role="status">Showing {projects.length} of {registry.counts.projects} proposals</p><button type="button" onClick={() => { setSearch(""); setDisposition(""); setReadiness(""); setState(""); }}>Clear filters</button></div>
      <div className="project-cards">{projects.map(project => <RejectedProjectCard project={project} key={project.project_id} />)}</div>
    </section>
    <aside className="study-footnote rejected-footnote"><strong>A comparison cohort, not a victory ledger.</strong><p>{registry.selection_basis}</p><a href="#/methodology">Read the evidence rules →</a></aside>
  </>;
}

function RejectedProjectCard({ project }: { project: RejectedProjectSummary }) {
  return <article className="project-card rejected-project-card">
    <div className="card-type"><span>{words(project.proposal_sector)}</span><span>{project.decision_date.slice(0, 4)}</span></div>
    <h3><a href={`#/rejected/${project.project_id}`}>{project.name}</a></h3>
    <a className="card-county" href={`#/county/${project.county_fips}`}>{project.county_name}, {project.state_abbr} ↗</a>
    <p className="card-history">{project.summary}</p>
    <p className="card-economics has-evidence">{project.source_count} cited sources · {project.timeline_event_count} timeline events</p>
    <dl className="rejected-card-facts"><div><dt>Disposition</dt><dd>{words(project.disposition)}</dd></div><div><dt>Finality</dt><dd>{words(project.finality)}</dd></div><div><dt>Community role</dt><dd>{words(project.community_role)}</dd></div></dl>
    <div className="card-bottom"><span className={`outcome-badge readiness-${project.outcome_readiness}`}>{readinessLabels[project.outcome_readiness]}</span><a href={`#/rejected/${project.project_id}`} aria-label={`View ${project.name}`}>View case →</a></div>
  </article>;
}

export function RejectedProjectProfile({ summary }: { summary: RejectedProjectSummary }) {
  const [detail, setDetail] = useState<RejectedProject | null>(null);
  const [error, setError] = useState<string | null>(null);
  useEffect(() => {
    let active = true;
    setDetail(null); setError(null);
    fetch(`${studyBase}${summary.detail_path}`).then(async response => {
      if (!response.ok) throw new Error("This rejected-proposal case file could not be loaded.");
      const result = await response.json() as RejectedProject;
      if (result.project_id !== summary.project_id) throw new Error("The case file does not match the selected proposal.");
      if (active) setDetail(result);
    }).catch((reason: unknown) => { if (active) setError(reason instanceof Error ? reason.message : "Unable to load case file."); });
    return () => { active = false; };
  }, [summary]);
  const sources = useMemo(() => new Map(detail?.sources.map(source => [source.source_id, source]) ?? []), [detail]);
  return <article className="project-profile rejected-profile">
    <a className="back-link" href="#/rejected">← Rejected proposal register</a>
    <header className="project-heading rejected-project-heading"><span className="eyebrow">{words(summary.proposal_sector)} proposal · {summary.state_abbr}</span><h2>{summary.name}</h2><a href={`#/county/${summary.county_fips}`}>{summary.county_name}, {summary.state_abbr} · View county context ↗</a><div className="project-tags"><span>{words(summary.disposition)}</span><span>{words(summary.finality)}</span><span>{readinessLabels[summary.outcome_readiness]}</span></div></header>
    {error ? <div className="error-panel" role="alert">{error}</div> : !detail ? <p className="study-loading" role="status">Loading rejected-proposal evidence…</p> : <>
      <section className="project-description"><span className="eyebrow">The proposal</span><h3>{detail.developer_label}</h3><p>{detail.proposal_description}</p></section>
      <div className="rejected-case-grid">
        <section><span className="eyebrow">Decision</span><strong>{detail.decision_label}</strong><time dateTime={detail.decision_date}>{detail.decision_date}</time></section>
        <section><span className="eyebrow">Community role</span><strong>{words(detail.community_role)}</strong><p>Evidence classification, not a quantified causal share.</p></section>
        <section><span className="eyebrow">Outcome status</span><strong>{readinessLabels[detail.outcome_readiness]}</strong><p>{words(detail.finality)} finality classification</p></section>
      </div>
      <section className="project-section"><div className="section-heading"><div><span className="eyebrow">Proposal claims</span><h3>Promised scale and economics</h3></div><span className="projection-flag">Projections · not realized</span></div><div className="proposal-scale-grid">{detail.proposed_scale.map(item => { const source = sources.get(item.source_id); return <article key={`${item.label}-${item.source_id}`}><span>{item.label}</span><strong>{item.value}</strong>{source && <a href={source.url} target="_blank" rel="noreferrer">Source ↗</a>}</article>; })}</div></section>
      <section className="project-section"><div className="section-heading"><div><span className="eyebrow">Chronological record</span><h3>Proposal, opposition, decision, and aftermath</h3></div><span className="account-count">{detail.timeline_event_count} sourced events</span></div><ol className="project-timeline rejected-timeline">{detail.timeline.map(event => <li className={`timeline-${event.category}`} key={event.event_id}><span className="timeline-dot" /><div className="media-timeline-entry"><div className="timeline-meta"><time dateTime={event.date}>{event.date_label}</time><span>{categoryLabels[event.category]}</span></div><strong>{event.title}</strong><p>{event.summary}</p><div className="timeline-sources">{event.source_ids.map(sourceId => { const source = sources.get(sourceId); return source ? <a href={source.url} target="_blank" rel="noreferrer" key={sourceId}><strong>{source.title}</strong><span>{source.publisher} · {source.source_role} ↗</span></a> : null; })}</div></div></li>)}</ol></section>
      <section className="project-section site-afterlife"><span className="eyebrow">What happened afterward</span><h3>Site and community tracking</h3><p>{detail.site_afterlife}</p><aside><strong>Interpretation boundary</strong><p>{detail.evidence_note}</p></aside></section>
      <section className="project-section" id="rejected-sources"><div className="section-heading"><h3>Source ledger</h3><a href={`${studyBase}${summary.detail_path}`} download={`${summary.project_id}.json`}>Download case JSON ↓</a></div><ol className="source-list">{detail.sources.map(source => <li key={source.source_id}><a href={source.url} target="_blank" rel="noreferrer">{source.title} ↗</a><small>{source.publisher} · {source.source_role}</small></li>)}</ol></section>
    </>}
  </article>;
}

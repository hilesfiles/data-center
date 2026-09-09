import { useEffect, useMemo, useState } from "react";
import App from "./App";
import { EconomicAccounts } from "./EconomicAccounts";
import { ControlRegistry } from "./ControlRegistry";
import { StudyNav } from "./StudyNav";
import { RejectedProjectProfile, RejectedProjectRegister } from "./RejectedProjects";
import type { ProjectMediaTimeline, ProjectMediaTimelineDataset, RejectedProjectIndex, StudyIndex, StudyProject, StudyProjectSummary } from "./studyTypes";

const base = `${import.meta.env.BASE_URL}data/v1/study/`;

function StudyRegister({ study }: { study: StudyIndex }) {
  const [search, setSearch] = useState("");
  const [group, setGroup] = useState("");
  const [state, setState] = useState("");
  const [operator, setOperator] = useState("");
  const [history, setHistory] = useState("");
  const [coverage, setCoverage] = useState("");
  const projects = useMemo(() => study.projects.filter(p =>
    (!group || p.study_group === group) && (!state || p.state_abbr === state) &&
    (!operator || p.operator_label === operator) && (!history || p.history_status === history) &&
    (!coverage || (coverage === "available" ? p.economic_record_count > 0 : p.economic_record_count === 0)) &&
    `${p.name} ${p.county_name} ${p.state_abbr} ${p.operator_label}`.toLocaleLowerCase().includes(search.trim().toLocaleLowerCase()),
  ), [study, search, group, state, operator, history, coverage]);
  const reset = () => { setSearch(""); setGroup(""); setState(""); setOperator(""); setHistory(""); setCoverage(""); };
  return <>
    <section className="study-hero">
      <div><span className="eyebrow">Private-sector development · United States</span>
        <h2>The local economics<br />of data centers.</h2>
        <p>Follow investment from construction to operation and expansion. Explore the projects, their communities, and the evidence needed to measure lasting economic contributions.</p>
        <a className="study-map-link" href="#/map">Explore the community map <span aria-hidden="true">↗</span></a>
      </div>
      <div className="study-counts" aria-label="Study coverage">
        <div><strong>{study.counts.projects}</strong><span>candidate projects</span></div>
        <div><strong>{study.counts.counties}</strong><span>host counties</span></div>
        <div><strong>{study.counts.states}</strong><span>states represented</span></div>
        <p>Initial research queue · expandable coverage<br />{study.counts.projects_with_economic_evidence} projects with economic evidence · {study.counts.economic_records} source records · {study.counts.modeled_synthesis_records} modeled syntheses</p>
      </div>
    </section>
    <section className="study-register" aria-labelledby="register-title">
      <div className="section-heading"><div><span className="eyebrow">Explore the evidence</span><h2 id="register-title">Project register</h2></div>
        <a href={`${base}index.json`} download="private-sector-study.json">Download register JSON ↓</a>
      </div>
      <p className="study-intro">Hyperscale, colocation, and enterprise projects selected for historical research. Membership is provisional; it does not establish current operating status or economic impact.</p>
      <div className="study-filters">
        <label className="study-search">Search projects<input type="search" value={search} onChange={e => setSearch(e.target.value)} placeholder="Name, operator, or county" /></label>
        <label>Project type<select aria-label="Project type" value={group} onChange={e => setGroup(e.target.value)}><option value="">All types</option>{Object.keys(study.counts.groups).map(g => <option key={g}>{g}</option>)}</select></label>
        <label>State<select aria-label="State" value={state} onChange={e => setState(e.target.value)}><option value="">All states</option>{[...new Set(study.projects.map(p => p.state_abbr))].sort().map(s => <option key={s}>{s}</option>)}</select></label>
        <label>Operator name<select aria-label="Operator name" value={operator} onChange={e => setOperator(e.target.value)}><option value="">All operators</option>{[...new Set(study.projects.map(p => p.operator_label))].sort().map(o => <option key={o}>{o}</option>)}</select></label>
        <label>Historical evidence<select aria-label="Historical evidence" value={history} onChange={e => setHistory(e.target.value)}><option value="">All histories</option><option value="evidence_available">Evidence available</option><option value="needs_research">Chronology needs research</option></select></label>
        <label>Economic evidence<select aria-label="Economic evidence" value={coverage} onChange={e => setCoverage(e.target.value)}><option value="">All coverage</option><option value="available">Records available</option><option value="missing">Not yet collected</option></select></label>
      </div>
      <div className="results-line"><p role="status">Showing {projects.length} of {study.counts.projects} projects</p><button type="button" onClick={reset}>Clear filters</button></div>
      {projects.length === 0 ? <div className="study-empty"><h3>No matching projects</h3><p>Try another name or clear the filters to see the full research queue.</p></div> :
      <div className="project-cards">{projects.map(p => <ProjectCard key={p.project_id} project={p} />)}</div>}
    </section>
    <aside className="study-footnote"><strong>Scope grows with the evidence.</strong><p>{study.selection_basis} The queue is not a fixed sample or a national census. Public-sector and other facilities remain in the underlying inventory.</p><a href="#/methodology">Read the study approach →</a></aside>
  </>;
}

function ProjectCard({ project: p }: { project: StudyProjectSummary }) {
  return <article className="project-card">
    <div className="card-type"><span>{p.study_group}</span>{p.inventory_entity_type === "campus" && <span>Campus record</span>}</div>
    <h3><a href={`#/project/${p.project_id}`}>{p.name}</a></h3>
    <a className="card-county" href={`#/county/${p.county_fips}`}>{p.county_name}, {p.state_abbr} ↗</a>
    <p className="card-history">{p.documented_timing}</p>
    <p className={`card-economics ${p.economic_record_count ? "has-evidence" : ""}`}>{p.economic_record_count ? `${p.economic_record_count} source records${p.modeled_synthesis_count ? ` · ${p.modeled_synthesis_count} modeled ${p.modeled_synthesis_count === 1 ? "synthesis" : "syntheses"}` : " · partial coverage"}` : "Economic evidence not yet collected"}</p>
    <div className="card-bottom"><span className={`history-badge ${p.history_status === "needs_research" ? "pending" : ""}`}>{p.history_status === "needs_research" ? "Chronology needs research" : "Historical evidence available"}</span><a href={`#/project/${p.project_id}`} aria-label={`View ${p.name}`}>View →</a></div>
  </article>;
}

const timelineCategoryLabels: Record<ProjectMediaTimeline["events"][number]["presentation_category"], string> = {
  announcement: "Announcement",
  milestone: "Milestone",
  expansion: "Expansion",
  ownership: "Ownership",
  incident: "Incident",
  controversy: "Controversy",
};

function PublicProjectTimeline({ timeline, datasetNote }: { timeline: ProjectMediaTimeline; datasetNote: string }) {
  return <>
    <p className="timeline-coverage-note">{timeline.coverage_note}</p>
    <ol className="project-timeline media-timeline">{timeline.events.map(event => <li className={`timeline-${event.presentation_category}`} key={event.event_id}>
      <span className="timeline-dot" />
      <div className="media-timeline-entry">
        <div className="timeline-meta"><time dateTime={event.sort_date}>{event.date_label}</time><span>{timelineCategoryLabels[event.presentation_category]}</span>{event.resolution_status !== "resolved" && <span className="timeline-resolution">{event.resolution_status}</span>}</div>
        <strong>{event.title}</strong>
        <p>{event.summary}</p>
        {event.scope_note && <p className="timeline-scope-note">Scope: {event.scope_note}</p>}
        <div className="timeline-sources" aria-label={`Sources for ${event.title}`}>{event.sources.map(source => <a href={source.url} target="_blank" rel="noreferrer" key={source.source_id}><strong>{source.title}</strong><span>{source.publisher} · {source.source_role === "primary" ? "Read source" : source.source_role} ↗</span></a>)}</div>
      </div>
    </li>)}</ol>
    <div className="timeline-dataset-note"><p>{datasetNote}</p><a href={`${base}project-media-timelines.json`} download="project-media-timelines.json">Download timeline data ↓</a></div>
  </>;
}

function ProjectProfile({ summary, release, generatedAt }: { summary: StudyProjectSummary; release: string; generatedAt: string }) {
  const [detail, setDetail] = useState<StudyProject | null>(null);
  const [timeline, setTimeline] = useState<ProjectMediaTimeline | null>(null);
  const [timelineDatasetNote, setTimelineDatasetNote] = useState("");
  const [error, setError] = useState<string | null>(null);
  useEffect(() => {
    let active = true;
    setDetail(null); setError(null);
    fetch(`${base}${summary.detail_path}`).then(async response => {
      if (!response.ok) throw new Error("This project profile could not be loaded. Please reload or return to the register.");
      const result = await response.json() as StudyProject;
      if (result.project_id !== summary.project_id || result.release_id !== release || result.generated_at !== generatedAt) throw new Error("Project data and register versions differ. Reload to load a consistent release.");
      if (active) setDetail(result);
    }).catch((reason: unknown) => { if (active) setError(reason instanceof Error ? reason.message : "Unable to load project."); });
    return () => { active = false; };
  }, [summary, release, generatedAt]);
  useEffect(() => {
    let active = true;
    setTimeline(null);
    setTimelineDatasetNote("");
    fetch(`${base}project-media-timelines.json`).then(async response => {
      if (!response.ok) return null;
      return await response.json() as ProjectMediaTimelineDataset;
    }).then(dataset => {
      if (!active || !dataset) return;
      setTimeline(dataset.timelines.find(candidate => candidate.project_id === summary.project_id) ?? null);
      setTimelineDatasetNote(dataset.scope_note);
    }).catch(() => { if (active) setTimeline(null); });
    return () => { active = false; };
  }, [summary.project_id]);
  const projectSources = useMemo(() => {
    const byUrl = new Map<string, { source_id: string; title: string; url: string }>();
    for (const source of detail?.sources ?? []) byUrl.set(source.url, source);
    for (const event of timeline?.events ?? []) for (const source of event.sources) byUrl.set(source.url, source);
    return [...byUrl.values()];
  }, [detail, timeline]);
  return <article className="project-profile">
    <a className="back-link" href="#/study">← Project register</a>
    <header className="project-heading"><span className="eyebrow">{summary.study_group} · {summary.state_abbr}</span><h2>{summary.name}</h2><a href={`#/county/${summary.county_fips}`}>{summary.county_name}, {summary.state_abbr} · View county account ↗</a><div className="project-tags"><span>{summary.research_completion_status === "account_research_complete" ? "Research complete" : "Research candidate"}</span><span>{summary.inventory_entity_type === "campus" ? "Campus-linked project" : "Facility-linked project"}</span><span>Private-sector study</span></div></header>
    {error ? <div className="error-panel" role="alert">{error}</div> : !detail ? <p role="status">Loading project evidence…</p> : <>
      {detail.project_description && <section className="project-description" aria-labelledby="project-description-title"><span className="eyebrow">Project profile</span><h3 id="project-description-title">About this project</h3><p>{detail.project_description}</p></section>}
      <div className="project-overview"><section><h3>Why this project is in the study</h3><p>{detail.research_value}</p><p className="study-muted">{detail.scope_note}</p></section><aside><strong>{detail.panel_years} years</strong><span>Host-county economic history · 2001–2024</span><p>County trends provide context. Project contributions require separate employment, investment and fiscal records.</p></aside></div>
      {(detail.economic_records.length > 0 || detail.modeled_syntheses.length > 0) && <EconomicAccounts key={detail.project_id} project={detail} />}
      <details className="project-research-ledger" open={summary.model_completeness.status === "full_modeled_account" ? undefined : true}>
        <summary><span>Development chronology and research notes</span><small>{detail.research_updates.length} research updates</small></summary>
        <div className="project-research-ledger-body">
          <section className="project-section" aria-labelledby="timeline-title"><div className="section-heading"><div><span className="eyebrow">Project timeline</span><h3 id="timeline-title">Announcements, milestones, and public debate</h3></div><a href="#project-sources" onClick={e => { e.preventDefault(); document.getElementById("project-sources")?.scrollIntoView({ behavior: "smooth" }); }}>Inspect source ledger ↓</a></div>
            {timeline ? <PublicProjectTimeline timeline={timeline} datasetNote={timelineDatasetNote} /> : <ol className="project-timeline"><li><span className="timeline-dot" /><div><strong>{detail.history.description}</strong><p>{detail.history.date_note}</p>{detail.history.anchor && <small>Stored anchor precision: {detail.history.anchor.precision}</small>}</div></li><li className="timeline-pending"><span className="timeline-dot" /><div><strong>Complete the construction, operating and expansion history</strong><p>Additional phase dates, ownership history, public reporting, and annual financial records need review. Unrecorded milestones are not assumed to have occurred.</p></div></li></ol>}
          </section>
          {detail.research_updates.map(update => <aside className="project-research-update" key={`${update.source_id}-${update.as_of}`}><span className="eyebrow">Research update · {update.as_of}</span><h3>{update.title}</h3><p>{update.notes}</p><a href={update.source.url} target="_blank" rel="noreferrer">{update.source.title} ↗</a><small>Source checked {update.source.retrieved_on}</small></aside>)}
        </div>
      </details>
      <section className="project-section" id="project-sources"><div className="section-heading"><h3>Sources & research history</h3><a href={`${base}${summary.detail_path}`} download={`${summary.project_id}.json`}>Download core project JSON ↓</a></div><p className="study-muted">The source ledger combines the core study bibliography with the linked public reporting used in the project timeline.</p>
        <details className="source-ledger" open={summary.model_completeness.status === "full_modeled_account" ? undefined : true}><summary><span>View cited sources</span><small>{projectSources.length} sources</small></summary><ol className="source-list">{projectSources.map((s, i) => <li key={`${s.source_id}-${i}`}><a href={s.url} target="_blank" rel="noreferrer">{s.title} ↗</a><small>{new URL(s.url).hostname}</small></li>)}</ol></details>
        <details className="research-details"><summary>Inventory identity and earlier first-entry research</summary><p>Inventory name: {detail.inventory_name}</p><p className="identity-id">{detail.inventory_entity_id}</p><p>{detail.legacy_first_entry_note ?? "This candidate was added through a campus record. A complete project and phase history remains to be assembled."}</p><p>Earlier adjudications retain their original meaning. This profile does not assign a county-first-entry date.</p></details>
      </section>
    </>}
  </article>;
}

function Methodology({ study }: { study: StudyIndex }) {
  return <article className="study-methodology"><span className="eyebrow">Evidence & methodology</span><h2>Follow the project.<br />Measure the community.</h2><p className="methodology-lead">The study follows private-sector data-center construction, operation and expansion, linking documented contributions to community outcomes over time.</p>
    <section><h3>What the initial queue represents</h3><p>{study.counts.projects} provisional research candidates across {study.counts.counties} counties and {study.counts.states} states. {study.counts.campus_targets} candidates are linked to campus records. The queue is expandable and is not a representative national sample.</p><p>{study.selection_basis}</p><p>Hyperscale, colocation and dedicated enterprise projects are the focus. Publicly traded companies are part of the private sector. Owner, operator, developer and tenant roles need dated evidence; a historical name does not verify current ownership.</p></section>
    <section><h3>Separate questions, separate evidence</h3><ul><li><strong>Documented contributions:</strong> actual project investment, jobs, payroll, local purchasing and public receipts.</li><li><strong>Modeled synthesis:</strong> transparent calculations that combine source claims, public benchmarks, statutory rules and explicit assumptions.</li><li><strong>Attributable effects:</strong> estimates requiring eligible events, comparison communities and model diagnostics.</li></ul><p>This release contains {study.counts.economic_records} source-checked economic records linked to {study.counts.projects_with_economic_evidence} candidates: {study.counts.reported_actual_records} reported activity records and {study.counts.projection_records} source projections. It separately publishes {study.counts.modeled_synthesis_records} modeled syntheses. Models are excluded from source-record and realized-benefit totals. Each interval is explicitly typed so a sensitivity envelope, deterministic counterfactual or reported band cannot be presented as a statistical confidence interval.</p></section>
    <section><h3>Benefits and costs over time</h3><p>Annual accounts will distinguish construction job-years from permanent employment, announced investment from actual spending, and tax-base growth from tax receipts. Local supplier and household-spending estimates will identify their assumptions. Public costs, incentives and attributable electricity and water effects belong alongside benefits.</p><p>Campus and building claims must be reconciled before aggregation. Multiple projects can share county outcomes. Missing and suppressed data remain distinct from zero.</p></section>
    <section><h3>County first entry remains a specific question</h3><p>The existing first-entry registry asks whether an event was a county's first data center. Its rejected and unresolved decisions remain intact. A later private-sector project can still support construction, operations and fiscal research.</p><p>First-entry evidence is available in county profiles and project research details. It is not a blanket eligibility gate for this study.</p></section>
    <section><h3>Comparison counties require affirmative screening</h3><p>The national comparison-county registry separates counties excluded by known facility or stopped-proposal evidence from counties whose negative-evidence review is still unresolved. No known repository record is not proof that a project was never considered.</p><p>Donor eligibility is assigned separately for each treated project and event year, using only pre-treatment data and explicit spillover, contemporaneous-shock, panel-coverage and pre-trend checks. Current county values are descriptive context, not matching inputs for historical events.</p><a href="#/controls">Inspect the comparison-county screen →</a></section>
    <section><h3>Coverage and geography</h3><p>The underlying IM3 inventory is a provisional geographic seed. Source objects, campuses, canonical facilities, study projects and verified operating facilities are distinct counts. No source record does not mean no data center.</p><p>Water stress, climate risk, fiber access and utility geography provide context. Facility-specific consumption, cooling and cost allocation require their own evidence. National infrastructure and competitiveness are interpretive considerations rather than local benefit measurements.</p></section>
    <section><h3>Release and reproducibility</h3><p>Candidate screen: {study.screen_date}. Published register: {study.release_id}. Modeling policy: {study.modeling_policy_version}.</p><p>Profiles retain source wording and date uncertainty. Economic sources and claims have their own version, page references, scope and review notes. Modeled records separately expose formula, named parameters and provenance, assumptions, limitations, contribution channel, anti-overlap aggregation identity and confidence. Causal methods additionally require treatment timing, comparison design, outcome definition, pre/post periods and diagnostics.</p><a href={`${base}manifest.json`}>Publication manifest and source hashes ↗</a></section>
  </article>;
}

export default function StudyApp() {
  const [hash, setHash] = useState(() => window.location.hash);
  const [study, setStudy] = useState<StudyIndex | null>(null);
  const [rejected, setRejected] = useState<RejectedProjectIndex | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [rejectedError, setRejectedError] = useState<string | null>(null);
  useEffect(() => {
    const onRoute = () => { setHash(window.location.hash); window.scrollTo(0, 0); };
    window.addEventListener("hashchange", onRoute);
    return () => window.removeEventListener("hashchange", onRoute);
  }, []);
  useEffect(() => {
    let active = true;
    fetch(`${base}index.json?cache_bust=${Date.now()}`, { cache: "no-store" }).then(async response => {
      if (!response.ok) throw new Error("The study register could not be loaded. Reload to try again; the community map remains available.");
      const result = await response.json() as StudyIndex;
      if (active) setStudy(result);
    }).catch((reason: unknown) => { if (active) setError(reason instanceof Error ? reason.message : "Unable to load study register."); });
    return () => { active = false; };
  }, []);
  useEffect(() => {
    let active = true;
    fetch(`${base}rejected-projects/index.json?cache_bust=${Date.now()}`, { cache: "no-store" }).then(async response => {
      if (!response.ok) throw new Error("The rejected-proposal register could not be loaded.");
      const result = await response.json() as RejectedProjectIndex;
      if (active) setRejected(result);
    }).catch((reason: unknown) => { if (active) setRejectedError(reason instanceof Error ? reason.message : "Unable to load rejected proposals."); });
    return () => { active = false; };
  }, []);
  const projectId = hash.match(/^#\/project\/([a-z0-9_]+)$/)?.[1];
  const rejectedProjectId = hash.match(/^#\/rejected\/([a-z0-9_]+)$/)?.[1];
  const selected = study?.projects.find(p => p.project_id === projectId);
  const selectedRejected = rejected?.projects.find(project => project.project_id === rejectedProjectId);
  useEffect(() => { document.title = `${selected?.name ?? selectedRejected?.name ?? "Data Center Community Impact Observatory"} · Economic study`; }, [selected, selectedRejected]);
  if (hash === "#/map" || /^#\/county\/\d{5}$/.test(hash)) return <App study={study} studyError={error} rejected={rejected} rejectedError={rejectedError} />;
  const known = !hash || hash === "#/study" || hash === "#/rejected" || hash === "#/controls" || hash === "#/methodology" || selected || selectedRejected;
  return <div className="app-shell study-shell"><header className="topbar"><div className="brand-block"><span className="eyebrow">U.S. community economics</span><h1>Data Center Community Impact Observatory</h1></div><div className="version-block"><span className="status-dot" /><span>Research in progress</span></div></header><StudyNav />
    <main className="study-main">{hash === "#/controls" ? <ControlRegistry /> : hash.startsWith("#/rejected") ? rejectedError ? <div className="error-panel" role="alert">{rejectedError}</div> : !rejected ? <p className="study-loading" role="status">Loading the rejected-proposal register…</p> : selectedRejected ? <RejectedProjectProfile summary={selectedRejected} /> : rejectedProjectId ? <div className="study-empty"><h2>Proposal not found</h2><a href="#/rejected">Return to rejected proposals →</a></div> : <RejectedProjectRegister registry={rejected} /> : error ? <div className="error-panel" role="alert">{error}</div> : !study ? <p className="study-loading" role="status">Loading the project register…</p> : !known ? <div className="study-empty"><h2>Project or page not found</h2><p>This link does not identify a project in the current study register.</p><a href="#/study">Return to project register →</a></div> : selected ? <ProjectProfile summary={selected} release={study.release_id} generatedAt={study.generated_at} /> : hash === "#/methodology" ? <Methodology study={study} /> : <StudyRegister study={study} />}</main>
    <footer className="study-footer"><span>Historical evidence · Transparent assumptions · Community outcomes</span><span>{study ? `Candidate screen ${study.screen_date}` : "Loading release"}</span></footer>
  </div>;
}

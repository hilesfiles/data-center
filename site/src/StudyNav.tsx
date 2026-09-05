import type { StudyIndex } from "./studyTypes";

export function StudyNav() {
  const hash = window.location.hash;
  const active = hash.startsWith("#/county/") || hash === "#/map" ? "map" : hash === "#/methodology" ? "methodology" : "study";
  return <nav className="study-nav" aria-label="Main navigation">
    <a href="#/study" aria-current={active === "study" ? "page" : undefined}>Project study</a>
    <a href="#/map" aria-current={active === "map" ? "page" : undefined}>Map & communities</a>
    <a href="#/methodology" aria-current={active === "methodology" ? "page" : undefined}>Evidence & methodology</a>
  </nav>;
}

export function CountyStudyProjects({ study, fips, error }: { study: StudyIndex | null; fips: string; error?: string | null }) {
  const projects = study?.projects.filter(p => p.county_fips === fips);
  return <section className="county-study" aria-label="Study projects in this county">
    <h3>Projects in the economic study</h3>
    {error ? <p role="alert">{error}</p> : !projects ? <p>Loading project register…</p> : projects.length === 0
      ? <p>No project from this county is in the initial research queue. This does not establish an absence of data centers.</p>
      : <ul>{projects.map(p => <li key={p.project_id}><a href={`#/project/${p.project_id}`}>{p.name} <span aria-hidden="true">↗</span></a><small>{p.study_group} · Research candidate</small></li>)}</ul>}
    <a className="profile-link" href="#/study">Explore all study projects →</a>
  </section>;
}

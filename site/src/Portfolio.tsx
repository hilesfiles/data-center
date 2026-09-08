import { useEffect, useMemo, useState } from "react";

const base = `${import.meta.env.BASE_URL}data/v1/study/`;

type CategoryCoverage = {
  category: string;
  label: string;
  project_count: number;
  projects_with_reported_actual: number;
  reported_actual_coverage_rate: number;
  projects_with_source_projection: number;
  projects_with_modeled_synthesis: number;
};

type ProjectValue = {
  project_id: string;
  project_name: string;
  county_fips: string;
  value: number;
};

type Cohort = {
  cohort_id: string;
  metric_code: string;
  category: string;
  unit: string;
  year: number;
  scope_level: string;
  project_count: number;
  county_count: number;
  project_values: ProjectValue[];
  distribution: { minimum: number; p25: number; median: number; p75: number; maximum: number };
  limitations: string[];
};

type CategoryCell = {
  category: string;
  reported_actual_count: number;
  source_projection_count: number;
  modeled_synthesis_count: number;
  direct_evidence_status: "partial" | "projections_only" | "not_yet_collected";
};

type ProjectRow = {
  project_id: string;
  project_name: string;
  county_fips: string;
  county_name: string;
  state_abbr: string;
  reported_actual_count: number;
  source_projection_count: number;
  modeled_synthesis_count: number;
  categories: CategoryCell[];
};

type PortfolioData = {
  artifact_version: string;
  generated_at: string;
  source_release: string;
  scope: { project_count: number; county_count: number; state_count: number; boundary: string };
  counts: {
    reported_actual_records: number;
    source_projection_records: number;
    modeled_syntheses: number;
    timing_aligned_reported_cohorts: number;
    direct_evidence_gap_status_counts: Record<string, number>;
    retained_modeled_level_0_identities: number;
    authorized_portfolio_totals: 0;
  };
  category_coverage: CategoryCoverage[];
  timing_aligned_reported_cohorts: Cohort[];
  project_matrix: ProjectRow[];
};

const categoryLabels: Record<string, string> = {
  investment: "Investment",
  construction: "Construction",
  suppliers: "Suppliers",
  operations: "Operations",
  fiscal: "Fiscal",
  public_costs: "Public costs",
  resources: "Resources",
  community: "Community",
};

function metricLabel(code: string) {
  return code.replace(/^study\./, "").replaceAll("_", " ");
}

function formatValue(value: number, unit: string) {
  if (unit === "USD" || unit === "USD_per_year") {
    return new Intl.NumberFormat("en-US", { style: "currency", currency: "USD", maximumFractionDigits: 0 }).format(value);
  }
  if (unit === "percent") return `${value.toLocaleString(undefined, { maximumFractionDigits: 1 })}%`;
  return `${value.toLocaleString(undefined, { maximumFractionDigits: 2 })} ${unit.replaceAll("_", " ")}`;
}

function statusLabel(cell: CategoryCell) {
  if (cell.direct_evidence_status === "partial") return `${cell.reported_actual_count} reported`;
  if (cell.direct_evidence_status === "projections_only") return "Projection only";
  return "Uncollected";
}

export function Portfolio() {
  const [data, setData] = useState<PortfolioData | null>(null);
  const [error, setError] = useState<string | null>(null);
  useEffect(() => {
    let active = true;
    fetch(`${base}pooled/portfolio-level-0-synthesis.json?cache_bust=${Date.now()}`, { cache: "no-store" })
      .then(async response => {
        if (!response.ok) throw new Error("The portfolio synthesis could not be loaded.");
        return response.json() as Promise<PortfolioData>;
      })
      .then(result => { if (active) setData(result); })
      .catch((reason: unknown) => { if (active) setError(reason instanceof Error ? reason.message : "Unable to load portfolio synthesis."); });
    return () => { active = false; };
  }, []);
  const cohortsByCategory = useMemo(() => {
    const result = new Map<string, Cohort[]>();
    for (const cohort of data?.timing_aligned_reported_cohorts ?? []) {
      result.set(cohort.category, [...(result.get(cohort.category) ?? []), cohort]);
    }
    return result;
  }, [data]);

  if (error) return <div className="error-panel" role="alert">{error}</div>;
  if (!data) return <p className="study-loading" role="status">Loading the 36-project synthesis…</p>;
  return <article className="portfolio-page">
    <header className="portfolio-hero">
      <div><span className="eyebrow">Level 0 · completed project portfolio</span><h2>What the 36 accounts<br />can support together.</h2><p>{data.scope.boundary}</p></div>
      <div className="portfolio-counts" aria-label="Portfolio synthesis coverage">
        <div><strong>{data.scope.project_count}</strong><span>projects</span></div>
        <div><strong>{data.scope.county_count}</strong><span>host counties</span></div>
        <div><strong>{data.counts.timing_aligned_reported_cohorts}</strong><span>strict reported cohorts</span></div>
        <div><strong>{data.counts.authorized_portfolio_totals}</strong><span>authorized totals</span></div>
      </div>
    </header>

    <section className="portfolio-warning" aria-labelledby="portfolio-boundary-title"><span className="eyebrow">Analytical boundary</span><h3 id="portfolio-boundary-title">No invented completeness. No meaningless grand total.</h3><p>The distributions below use reported observations only and match year, metric, unit, measure type, period kind, scope level, and allocation status. Projections and modeled syntheses remain separate. A missing value is never zero.</p></section>

    <section className="portfolio-section" aria-labelledby="coverage-title"><div className="section-heading"><div><span className="eyebrow">Evidence coverage</span><h3 id="coverage-title">Where reported records exist</h3></div><a href={`${base}pooled/portfolio-level-0-synthesis.json`} download="portfolio-level-0-synthesis.json">Download full synthesis JSON ↓</a></div>
      <div className="coverage-grid">{data.category_coverage.map(row => <article key={row.category}><span>{row.label}</span><strong>{row.projects_with_reported_actual}<small> / {row.project_count}</small></strong><div className="coverage-bar" aria-label={`${Math.round(row.reported_actual_coverage_rate * 100)} percent coverage`}><i style={{ width: `${row.reported_actual_coverage_rate * 100}%` }} /></div><p>{Math.round(row.reported_actual_coverage_rate * 100)}% with reported evidence · {row.projects_with_source_projection} with projections · {row.projects_with_modeled_synthesis} with modeled synthesis</p></article>)}</div>
    </section>

    <section className="portfolio-section" aria-labelledby="cohorts-title"><div className="section-heading"><div><span className="eyebrow">Timing-aligned evidence</span><h3 id="cohorts-title">Reported distributions that clear the strict screen</h3></div><span className="account-count">Descriptive, not causal</span></div>
      <p className="study-intro">Only six metric families currently produce a same-year cohort across at least three projects and three counties. Dollar values are nominal within the displayed year. These ranges describe collected accounts and are not industry benchmarks.</p>
      {[...cohortsByCategory.entries()].map(([category, cohorts]) => <details className="portfolio-cohort-group" key={category} open><summary><span>{categoryLabels[category] ?? category}</span><small>{cohorts.length} cohorts</small></summary><div className="impact-table-wrap"><table><thead><tr><th>Metric and year</th><th>Projects</th><th>Minimum</th><th>Median</th><th>Maximum</th></tr></thead><tbody>{cohorts.map(cohort => <tr key={cohort.cohort_id}><th scope="row"><strong>{metricLabel(cohort.metric_code)}</strong><small>{cohort.year} · {cohort.scope_level.replaceAll("_", " ")}</small></th><td><details><summary>{cohort.project_count} projects / {cohort.county_count} counties</summary><ul>{cohort.project_values.map(row => <li key={row.project_id}><a href={`#/project/${row.project_id}`}>{row.project_name}</a>: {formatValue(row.value, cohort.unit)}</li>)}</ul></details></td><td>{formatValue(cohort.distribution.minimum, cohort.unit)}</td><td>{formatValue(cohort.distribution.median, cohort.unit)}</td><td>{formatValue(cohort.distribution.maximum, cohort.unit)}</td></tr>)}</tbody></table></div></details>)}
    </section>

    <section className="portfolio-section" aria-labelledby="matrix-title"><div className="section-heading"><div><span className="eyebrow">Project-by-category matrix</span><h3 id="matrix-title">Coverage and remaining gaps</h3></div><span className="account-count">All 36 projects</span></div>
      <p className="study-intro">“Reported” means at least one direct observation exists; it does not mean the category is complete. Projection-only and uncollected cells remain explicit.</p>
      <div className="impact-table-wrap portfolio-matrix"><table><thead><tr><th>Project</th>{data.category_coverage.map(row => <th key={row.category}>{categoryLabels[row.category] ?? row.category}</th>)}</tr></thead><tbody>{data.project_matrix.map(project => <tr key={project.project_id}><th scope="row"><a href={`#/project/${project.project_id}`}>{project.project_name}</a><small>{project.county_name}, {project.state_abbr}</small></th>{project.categories.map(cell => <td key={cell.category} className={`coverage-cell coverage-${cell.direct_evidence_status}`}><span>{statusLabel(cell)}</span>{cell.modeled_synthesis_count > 0 && <small>{cell.modeled_synthesis_count} modeled</small>}</td>)}</tr>)}</tbody></table></div>
    </section>

    <aside className="study-footnote"><strong>Modeled synthesis remains last resort.</strong><p>{data.counts.retained_modeled_level_0_identities} retained modeled identities are published separately from reported distributions. No new model was created, and the existing calibration screen authorizes no transferable parameter.</p><a href="#/methodology">Review the evidence rules →</a></aside>
  </article>;
}

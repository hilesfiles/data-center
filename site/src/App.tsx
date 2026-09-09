import { lazy, Suspense, useEffect, useMemo, useState } from "react";
import { ImpactAccount } from "./EconomicAccounts";
import { CountyStudyProjects, StudyNav } from "./StudyNav";
import { CountyComparisonSummary } from "./ControlRegistry";
import type { RejectedProjectIndex, RejectedProjectSummary, StudyIndex, StudyProject, StudyProjectSummary } from "./studyTypes";
import type {
  CountyEntityAdjudicationCoverage,
  CountyEconomicHistory,
  CountyTreatmentAssessment,
  FirstEntryResearchCandidate,
  CountyEconomicBaseline,
  CountyEmploymentWagesBaseline,
  CountyEntityResolutionCoverage,
  CountyLifecycleVerificationCoverage,
  FacilitySourceCoverage,
  SiteMetadata,
} from "./types";

const MapPanel = lazy(() =>
  import("./MapPanel").then((module) => ({ default: module.MapPanel })),
);

const integerFormat = new Intl.NumberFormat("en-US");
const compactFormat = new Intl.NumberFormat("en-US", {
  notation: "compact",
  maximumFractionDigits: 1,
});
const currencyFormat = new Intl.NumberFormat("en-US", {
  style: "currency",
  currency: "USD",
  maximumFractionDigits: 0,
});

const compactCurrency = (value: number | null | undefined) =>
  value == null ? "Unavailable" : `$${compactFormat.format(value)}`;

const wholeCurrency = (value: number | null | undefined) =>
  value == null ? "Unavailable" : currencyFormat.format(value);

const percentChange = (start: number | null | undefined, end: number | null | undefined) =>
  start == null || end == null || start === 0 ? null : ((end - start) / start) * 100;

const formatPercentChange = (value: number | null) =>
  value == null ? "Unavailable" : `${value >= 0 ? "+" : ""}${value.toFixed(1)}%`;

const studyDataBase = `${import.meta.env.BASE_URL}data/v1/study/`;

function CountyStudyAccount({ summary, release, generatedAt }: { summary: StudyProjectSummary; release: string; generatedAt: string }) {
  const [project, setProject] = useState<StudyProject | null>(null);
  const [error, setError] = useState<string | null>(null);
  useEffect(() => {
    let active = true;
    setProject(null);
    setError(null);
    fetch(`${studyDataBase}${summary.detail_path}`).then(async response => {
      if (!response.ok) throw new Error("The completed facility account could not be loaded.");
      const result = await response.json() as StudyProject;
      if (result.project_id !== summary.project_id || result.release_id !== release || result.generated_at !== generatedAt) throw new Error("The county and facility account releases do not match.");
      if (active) setProject(result);
    }).catch((reason: unknown) => {
      if (active) setError(reason instanceof Error ? reason.message : "The completed facility account could not be loaded.");
    });
    return () => { active = false; };
  }, [summary, release, generatedAt]);
  return <section className="county-study-account" aria-labelledby="county-account-title">
    <div className="section-heading"><div><span className="eyebrow">Completed private-sector study</span><h3 id="county-account-title">Facility contribution to {summary.county_name}</h3></div><a href={`#/project/${summary.project_id}`}>Open full project evidence →</a></div>
    <p className="study-intro">Construction, recurring operations, local public finances, public support, infrastructure demand, and county comparisons are presented separately. Reported and modeled figures remain labeled at the value.</p>
    {error ? <div className="error-panel" role="alert">{error}</div> : !project ? <p className="study-loading" role="status">Loading the completed economic account…</p> : <ImpactAccount project={project} countyView />}
  </section>;
}

function CountyRejectedProjects({ projects, error }: { projects: RejectedProjectSummary[]; error: string | null }) {
  if (error) return <section className="county-rejected-study"><h3>Rejected & withdrawn proposals</h3><p role="alert">{error}</p></section>;
  if (!projects.length) return null;
  return <section className="county-rejected-study" aria-label="Rejected and withdrawn proposals in this county">
    <h3>Rejected & withdrawn proposals</h3>
    <p>These cases are separate from operating facilities and proposal projections are not realized outcomes.</p>
    <ul>{projects.map(project => <li key={project.project_id}><a href={`#/rejected/${project.project_id}`}>{project.name} <span aria-hidden="true">↗</span></a><small>{project.decision_label} · {project.decision_date}</small></li>)}</ul>
    <a className="profile-link" href="#/rejected">Explore the comparison register →</a>
  </section>;
}

type CountyTrendKey = "real_gdp_usd" | "annual_avg_covered_employment" | "population" | "annual_avg_weekly_wage_nominal_usd";

const countyTrends: Array<{ key: CountyTrendKey; label: string; note: string }> = [
  { key: "real_gdp_usd", label: "Real GDP", note: "Chained 2017 dollars" },
  { key: "annual_avg_covered_employment", label: "Covered employment", note: "Annual average employment" },
  { key: "population", label: "Population", note: "Resident population" },
  { key: "annual_avg_weekly_wage_nominal_usd", label: "Average weekly wage", note: "Nominal dollars" },
];

function countyTrendValue(key: CountyTrendKey, value: number | null) {
  if (value == null) return "Unavailable";
  if (key === "real_gdp_usd") return compactCurrency(value);
  if (key === "annual_avg_weekly_wage_nominal_usd") return wholeCurrency(value);
  return integerFormat.format(value);
}

function CountyHistory({ history }: { history: CountyEconomicHistory }) {
  const firstYear = history.years[0]?.year;
  const lastYear = history.years.at(-1)?.year;
  const yearMarkers = history.years.filter(row => row.year === firstYear || row.year === lastYear || row.year % 5 === 0);
  return <section className="county-history-section" aria-labelledby="county-history-title">
    <div className="section-heading"><div><span className="eyebrow">County context · 2001–2024</span><h3 id="county-history-title">How the host economy changed</h3></div><span className="account-count">Descriptive county data</span></div>
    <p className="study-intro">These are observed county totals. They show the economic setting before and after development, but they do not by themselves assign the change to the data center.</p>
    <div className="county-trend-grid">{countyTrends.map(definition => {
      const available = history.years.map((row, index) => ({ index, year: row.year, value: row[definition.key] })).filter((row): row is { index: number; year: number; value: number } => row.value != null);
      if (!available.length) return <figure className="county-trend" key={definition.key}><figcaption><strong>{definition.label}</strong><span>{definition.note}</span></figcaption><p>Unavailable</p></figure>;
      const values = available.map(row => row.value);
      const min = Math.min(...values), max = Math.max(...values);
      const span = max - min || 1;
      const annualPoints = available.map(row => ({
        ...row,
        x: 10 + row.index / Math.max(history.years.length - 1, 1) * 300,
        y: 82 - (row.value - min) / span * 68,
      }));
      const points = annualPoints.map(row => `${row.x},${row.y}`).join(" ");
      const start = available[0], end = available[available.length - 1];
      const change = percentChange(start.value, end.value);
      return <figure className="county-trend" key={definition.key}>
        <figcaption><div><strong>{definition.label}</strong><span>{definition.note}</span></div><em>{formatPercentChange(change)}</em></figcaption>
        <svg viewBox="0 0 320 92" role="img" aria-label={`${definition.label}: ${countyTrendValue(definition.key, start.value)} in ${start.year}; ${countyTrendValue(definition.key, end.value)} in ${end.year}`} preserveAspectRatio="none"><line x1="10" y1="82" x2="310" y2="82" /><polyline points={points} />{annualPoints.map((row, index) => <circle className={`county-trend-point${index === 0 || index === annualPoints.length - 1 ? " endpoint" : ""}`} data-year={row.year} cx={row.x} cy={row.y} r={index === 0 || index === annualPoints.length - 1 ? 3.2 : 1.8} key={row.year}><title>{row.year}: {countyTrendValue(definition.key, row.value)}</title></circle>)}</svg>
        <div className="county-trend-years" aria-label="Year markers">{yearMarkers.map(row => <span style={{ left: `${(row.year - (firstYear ?? row.year)) / Math.max((lastYear ?? row.year) - (firstYear ?? row.year), 1) * 100}%` }} key={row.year}>{row.year}</span>)}</div>
        <div className="county-trend-values"><span>{start.year}<strong>{countyTrendValue(definition.key, start.value)}</strong></span><span>{end.year}<strong>{countyTrendValue(definition.key, end.value)}</strong></span></div>
      </figure>;
    })}</div>
    <details className="county-history-table"><summary>View all annual county observations</summary><div className="impact-table-wrap"><table><thead><tr><th scope="col">Year</th><th scope="col">Real GDP</th><th scope="col">Employment</th><th scope="col">Population</th><th scope="col">Weekly wage</th></tr></thead><tbody>{history.years.map(row => <tr key={row.year}><th scope="row">{row.year}</th><td>{countyTrendValue("real_gdp_usd", row.real_gdp_usd)}</td><td>{countyTrendValue("annual_avg_covered_employment", row.annual_avg_covered_employment)}</td><td>{countyTrendValue("population", row.population)}</td><td>{countyTrendValue("annual_avg_weekly_wage_nominal_usd", row.annual_avg_weekly_wage_nominal_usd)}</td></tr>)}</tbody></table></div></details>
  </section>;
}

const countyFipsFromHash = () => {
  const match = window.location.hash.match(/^#\/county\/(\d{5})$/);
  return match?.[1] ?? null;
};

export default function App({ study, studyError, rejected, rejectedError }: { study: StudyIndex | null; studyError: string | null; rejected: RejectedProjectIndex | null; rejectedError: string | null }) {
  const [metadata, setMetadata] = useState<SiteMetadata | null>(null);
  const [counties, setCounties] = useState<FacilitySourceCoverage[]>([]);
  const [economic, setEconomic] = useState<CountyEconomicBaseline[]>([]);
  const [employmentWages, setEmploymentWages] = useState<CountyEmploymentWagesBaseline[]>([]);
  const [economicHistoryByState, setEconomicHistoryByState] = useState<
    Record<string, CountyEconomicHistory[]>
  >({});
  const [treatmentByState, setTreatmentByState] = useState<
    Record<string, CountyTreatmentAssessment[]>
  >({});
  const [firstEntryResearchByState, setFirstEntryResearchByState] = useState<
    Record<string, FirstEntryResearchCandidate[]>
  >({});
  const [resolution, setResolution] = useState<CountyEntityResolutionCoverage[]>([]);
  const [adjudication, setAdjudication] = useState<CountyEntityAdjudicationCoverage[]>([]);
  const [lifecycle, setLifecycle] = useState<CountyLifecycleVerificationCoverage[]>([]);
  const [studyGroup, setStudyGroup] = useState("");
  const [showOperating, setShowOperating] = useState(true);
  const [showRejected, setShowRejected] = useState(true);
  const completedProjects = useMemo(
    () => study?.projects.filter(project =>
      project.research_completion_status === "account_research_complete" ||
      (project.research_completion_status == null && (
        project.model_completeness.status === "full_modeled_account" || project.modeled_synthesis_count > 0
      )),
    ) ?? [],
    [study],
  );
  const mappedProjects = useMemo(
    () => showOperating ? completedProjects.filter(project => !studyGroup || project.study_group === studyGroup) : [],
    [completedProjects, showOperating, studyGroup],
  );
  const mappedRejectedProjects = useMemo(() => showRejected ? rejected?.projects ?? [] : [], [rejected, showRejected]);
  const completedGroups = useMemo(
    () => [...new Set(completedProjects.map(project => project.study_group))].sort(),
    [completedProjects],
  );
  const [profileFips, setProfileFips] = useState<string | null>(() => countyFipsFromHash());
  const [selectedFips, setSelectedFips] = useState<string | null>(() => countyFipsFromHash());
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    const base = import.meta.env.BASE_URL;
    fetch(`${base}data/v1/metadata.json`)
      .then(async response => {
        if (!response.ok) throw new Error("Site metadata could not be loaded.");
        setMetadata((await response.json()) as SiteMetadata);
      })
      .catch((reason: unknown) =>
        setError(reason instanceof Error ? reason.message : "Site metadata could not be loaded."),
      );
  }, []);

  useEffect(() => {
    if (profileFips == null) return;
    const base = import.meta.env.BASE_URL;
    Promise.all([
      fetch(`${base}data/v1/counties/facility-source-coverage.json`),
      fetch(`${base}data/v1/counties/economic-baseline-2024.json`),
      fetch(`${base}data/v1/counties/employment-wages-baseline-2025.json`),
      fetch(`${base}data/v1/counties/entity-resolution-coverage.json`),
      fetch(`${base}data/v1/counties/final-review-coverage.json`),
      fetch(`${base}data/v1/counties/lifecycle-national-tranche-6-coverage.json`),
    ])
      .then(async ([coverageResponse, economicResponse, employmentWagesResponse, resolutionResponse, adjudicationResponse, lifecycleResponse]) => {
        if (!coverageResponse.ok || !economicResponse.ok || !employmentWagesResponse.ok || !resolutionResponse.ok || !adjudicationResponse.ok || !lifecycleResponse.ok) {
          throw new Error("The static data contract could not be loaded.");
        }
        setCounties((await coverageResponse.json()) as FacilitySourceCoverage[]);
        setEconomic((await economicResponse.json()) as CountyEconomicBaseline[]);
        setEmploymentWages((await employmentWagesResponse.json()) as CountyEmploymentWagesBaseline[]);
        setResolution(
          (await resolutionResponse.json()) as CountyEntityResolutionCoverage[],
        );
        setAdjudication(
          (await adjudicationResponse.json()) as CountyEntityAdjudicationCoverage[],
        );
        setLifecycle(
          (await lifecycleResponse.json()) as CountyLifecycleVerificationCoverage[],
        );
      })
      .catch((reason: unknown) =>
        setError(reason instanceof Error ? reason.message : "Static data could not be loaded."),
      );
  }, [profileFips]);

  useEffect(() => {
    const visible = [...mappedProjects, ...mappedRejectedProjects];
    if (profileFips == null && visible.length > 0 && !visible.some(project => project.county_fips === selectedFips)) {
      setSelectedFips(visible[0].county_fips);
    }
  }, [mappedProjects, mappedRejectedProjects, profileFips, selectedFips]);

  useEffect(() => {
    const syncRoute = () => {
      const countyFips = countyFipsFromHash();
      setProfileFips(countyFips);
      if (countyFips != null) setSelectedFips(countyFips);
    };
    window.addEventListener("hashchange", syncRoute);
    return () => window.removeEventListener("hashchange", syncRoute);
  }, []);

  const selectedCounty = useMemo(
    () => counties.find((county) => county.county_fips === selectedFips) ?? null,
    [counties, selectedFips],
  );
  const selectedCompletedProject = useMemo(
    () => completedProjects.find(project => project.county_fips === selectedFips) ?? null,
    [completedProjects, selectedFips],
  );
  const selectedRejectedProjects = useMemo(
    () => rejected?.projects.filter(project => project.county_fips === selectedFips) ?? [],
    [rejected, selectedFips],
  );
  useEffect(() => {
    const stateAbbr = selectedCounty?.state_abbr;
    if (stateAbbr == null || economicHistoryByState[stateAbbr] != null) return;
    let cancelled = false;
    const base = import.meta.env.BASE_URL;
    fetch(`${base}data/v1/panels/county-economic-history/by-state/${stateAbbr.toLowerCase()}.json`)
      .then(async (response) => {
        if (!response.ok) throw new Error(`Historical panel data could not be loaded for ${stateAbbr}.`);
        const records = (await response.json()) as CountyEconomicHistory[];
        if (!cancelled) {
          setEconomicHistoryByState((current) => ({...current, [stateAbbr]: records}));
        }
      })
      .catch((reason: unknown) => {
        if (!cancelled) {
          setError(reason instanceof Error ? reason.message : "Historical panel data could not be loaded.");
        }
      });
    return () => {
      cancelled = true;
    };
  }, [selectedCounty, economicHistoryByState]);
  useEffect(() => {
    const stateAbbr = selectedCounty?.state_abbr;
    if (stateAbbr == null || treatmentByState[stateAbbr] != null) return;
    let cancelled = false;
    const base = import.meta.env.BASE_URL;
    fetch(`${base}data/v1/treatments/county-first-entry/by-state/${stateAbbr.toLowerCase()}.json`)
      .then(async (response) => {
        if (!response.ok) throw new Error(`Treatment assessments could not be loaded for ${stateAbbr}.`);
        const records = (await response.json()) as CountyTreatmentAssessment[];
        if (!cancelled) {
          setTreatmentByState((current) => ({...current, [stateAbbr]: records}));
        }
      })
      .catch((reason: unknown) => {
        if (!cancelled) {
          setError(reason instanceof Error ? reason.message : "Treatment assessments could not be loaded.");
        }
      });
    return () => {
      cancelled = true;
    };
  }, [selectedCounty, treatmentByState]);
  useEffect(() => {
    const stateAbbr = selectedCounty?.state_abbr;
    if (stateAbbr == null || firstEntryResearchByState[stateAbbr] != null) return;
    let cancelled = false;
    const base = import.meta.env.BASE_URL;
    fetch(`${base}data/v1/treatments/county-first-entry-research/by-state/${stateAbbr.toLowerCase()}.json`)
      .then(async (response) => {
        if (!response.ok) throw new Error(`First-entry research queue could not be loaded for ${stateAbbr}.`);
        const records = (await response.json()) as FirstEntryResearchCandidate[];
        if (!cancelled) {
          setFirstEntryResearchByState((current) => ({...current, [stateAbbr]: records}));
        }
      })
      .catch((reason: unknown) => {
        if (!cancelled) {
          setError(reason instanceof Error ? reason.message : "First-entry research queue could not be loaded.");
        }
      });
    return () => {
      cancelled = true;
    };
  }, [firstEntryResearchByState, selectedCounty]);
  const selectedResolution = useMemo(
    () => resolution.find((county) => county.county_fips === selectedFips) ?? null,
    [resolution, selectedFips],
  );
  const selectedEconomic = useMemo(
    () => economic.find((county) => county.county_fips === selectedFips) ?? null,
    [economic, selectedFips],
  );
  const selectedEmploymentWages = useMemo(
    () => employmentWages.find((county) => county.county_fips === selectedFips) ?? null,
    [employmentWages, selectedFips],
  );
  const selectedEconomicHistory = useMemo(
    () => selectedCounty == null
      ? null
      : economicHistoryByState[selectedCounty.state_abbr]?.find(
          (county) => county.county_fips === selectedFips,
        ) ?? null,
    [economicHistoryByState, selectedCounty, selectedFips],
  );
  const selectedTreatment = useMemo(
    () => selectedCounty == null
      ? null
      : treatmentByState[selectedCounty.state_abbr]?.find(
          (county) => county.county_fips === selectedFips,
        ) ?? null,
    [selectedCounty, selectedFips, treatmentByState],
  );
  const selectedFirstEntryResearch = useMemo(
    () => selectedCounty == null
      ? null
      : firstEntryResearchByState[selectedCounty.state_abbr]?.find(
          (county) => county.county_fips === selectedFips,
        ) ?? null,
    [firstEntryResearchByState, selectedCounty, selectedFips],
  );
  const selectedAdjudication = useMemo(
    () => adjudication.find((county) => county.county_fips === selectedFips) ?? null,
    [adjudication, selectedFips],
  );
  const selectedLifecycle = useMemo(
    () => lifecycle.find((county) => county.county_fips === selectedFips) ?? null,
    [lifecycle, selectedFips],
  );
  const treatmentStatus = selectedTreatment?.assessment_status === "eligible"
    ? `Eligible · ${selectedTreatment.eligible_cohort_year}`
    : selectedTreatment?.assessment_status === "candidate_events_not_first_entry"
      ? selectedTreatment.candidate_rejection_count
        ? "Anchor rejected"
        : selectedTreatment.first_entry_adjudication_ids?.length
          ? "Anchor unresolved"
          : "Not eligible"
      : selectedTreatment == null
        ? "Loading…"
        : "No reviewed dated event";
  const treatmentNote = selectedTreatment?.assessment_status === "candidate_events_not_first_entry"
    ? selectedTreatment.first_entry_research_summary
      ?? `${selectedTreatment.candidate_event_count} dated facility opening${selectedTreatment.candidate_event_count === 1 ? "" : "s"}; county first entry unverified`
    : selectedTreatment?.assessment_status === "eligible"
      ? "governed county first-entry date"
      : "never-treated status is not inferred";
  const researchQueueStatus = selectedFirstEntryResearch?.research_status === "evidence_collected"
    ? selectedFirstEntryResearch.adjudication_status === "candidate_rejected_first_entry"
      ? "Evidence collected · anchor rejected"
      : "Evidence collected · first entry unresolved"
    : selectedFirstEntryResearch?.queue_status === "initial_tranche"
      ? `Initial tranche · #${selectedFirstEntryResearch.initial_tranche_rank}`
    : selectedFirstEntryResearch != null
      ? `Backlog · national #${selectedFirstEntryResearch.national_rank}`
      : selectedCounty != null && firstEntryResearchByState[selectedCounty.state_abbr] == null
        ? "Loading…"
        : "Not queued";
  const researchQueueNote = selectedFirstEntryResearch != null
    ? selectedFirstEntryResearch.research_summary
      ?? `priority ${selectedFirstEntryResearch.priority_score.toFixed(2)} · research ordering only`
    : (selectedLifecycle?.active_canonical_facility_count ?? 0) > 0
      ? "complete 24-year history requirement not met"
      : "no active canonical facility in current inventory";
  if (profileFips != null) {
    const historyLoaded = selectedCounty != null
      && economicHistoryByState[selectedCounty.state_abbr] != null;
    const treatmentLoaded = selectedCounty != null
      && treatmentByState[selectedCounty.state_abbr] != null;
    const researchQueueLoaded = selectedCounty != null
      && firstEntryResearchByState[selectedCounty.state_abbr] != null;
    return (
      <div className="app-shell county-profile-shell">
        <header className="topbar">
          <div className="brand-block">
            <span className="eyebrow">County profile</span>
            <h1>Data Center Community Impact Observatory</h1>
          </div>
          <div className="version-block">
            <span className="status-dot" />
            <span title={metadata?.data_version}>{metadata ? "Source-linked county data" : "Loading county data"}</span>
          </div>
        </header>
        <StudyNav />
        <main className="county-profile-page">
          <a className="back-link" href="#/map">← Back to national map</a>
          {error && <div className="error-panel">{error}</div>}
          {!error && counties.length > 0 && selectedCounty == null && (
            <div className="empty-panel">No current Census county exists for FIPS {profileFips}.</div>
          )}
          {!error && selectedCounty == null && counties.length === 0 && (
            <div className="empty-panel">Loading county profile…</div>
          )}
          {selectedCounty && (
            <>
              <div className="profile-heading">
                <div>
                  <span className="eyebrow">{selectedCounty.state_abbr} · FIPS {selectedCounty.county_fips}</span>
                  <h2>{selectedCounty.county_name}</h2>
                  <p>Host-county economy and the completed data-center contribution account.</p>
                </div>
                <span className="quality-badge grade-p">{selectedCompletedProject ? "Completed study" : "County context"}</span>
              </div>
              <CountyStudyProjects study={study} fips={selectedCounty.county_fips} error={studyError} />
              <CountyRejectedProjects projects={selectedRejectedProjects} error={rejectedError} />
              {selectedCompletedProject && study && <CountyStudyAccount summary={selectedCompletedProject} release={study.release_id} generatedAt={study.generated_at} />}
              <section className="county-baseline-section" aria-labelledby="county-baseline-title">
                <div className="section-heading"><div><span className="eyebrow">Current county baseline</span><h3 id="county-baseline-title">Scale of the host economy</h3></div></div>
                <div className="profile-grid" aria-label="County baseline measures">
                <article>
                  <span>Real GDP · 2024</span>
                  <strong>{compactCurrency(selectedEconomic?.real_gdp_usd)}</strong>
                  <small>chained 2017 dollars</small>
                </article>
                <article>
                  <span>Covered employment · 2025</span>
                  <strong>{selectedEmploymentWages?.annual_avg_covered_employment == null ? "Unavailable" : integerFormat.format(selectedEmploymentWages.annual_avg_covered_employment)}</strong>
                  <small>annual average of monthly levels</small>
                </article>
                <article>
                  <span>Population · 2024</span>
                  <strong>{selectedEconomic?.population == null ? "Unavailable" : integerFormat.format(selectedEconomic.population)}</strong>
                  <small>resident population</small>
                </article>
                <article>
                  <span>Personal income · 2024</span>
                  <strong>{compactCurrency(selectedEconomic?.personal_income_nominal_usd)}</strong>
                  <small>nominal dollars</small>
                </article>
                <article>
                  <span>Average weekly wage · 2025</span>
                  <strong>{wholeCurrency(selectedEmploymentWages?.annual_avg_weekly_wage_nominal_usd)}</strong>
                  <small>covered employment</small>
                </article>
                <article>
                  <span>Per-capita income · 2024</span>
                  <strong>{wholeCurrency(selectedEconomic?.per_capita_personal_income_nominal_usd)}</strong>
                  <small>nominal dollars</small>
                </article>
                </div>
              </section>
              {!historyLoaded ? <p className="study-loading" role="status">Loading county history…</p> : selectedEconomicHistory && <CountyHistory history={selectedEconomicHistory} />}
              <CountyComparisonSummary fips={selectedCounty.county_fips} />
              <details className="research-details">
                <summary>Historical treatment and inventory notes</summary>
                <p>First-entry treatment: {!treatmentLoaded ? "Loading…" : treatmentStatus}</p>
                <p>{treatmentNote}</p>
                <p>Research: {!researchQueueLoaded ? "Loading…" : researchQueueStatus}</p>
                <p>{researchQueueNote}</p>
                <p>This assessment addresses the county's first entry. Project construction, operations and fiscal research have separate evidence requirements.</p>
              </details>
            </>
          )}
        </main>
      </div>
    );
  }

  return (
    <div className="app-shell">
      <header className="topbar">
        <div className="brand-block">
          <span className="eyebrow">U.S. research infrastructure</span>
          <h1>Data Center Community Impact Observatory</h1>
        </div>
        <div className="version-block">
          <span className="status-dot" />
          <span title={metadata?.data_version}>{metadata ? "Source-linked county data" : "Loading county data"}</span>
        </div>
      </header>

      <StudyNav />
      <div className="fixture-banner" role="status">
        {study ? <><strong>{completedProjects.length} completed project accounts and {rejected?.counts.projects ?? 0} rejected or withdrawn proposals are mapped.</strong> Marker color and county shading distinguish the cohorts; readiness remains separately identified on every case.</> : studyError ?? "Loading the private-sector project register…"}
      </div>

      <main className="workspace">
        <aside className="sidebar">
          <section className="control-section">
            <fieldset className="map-layer-controls"><legend>Map layers</legend><label><input type="checkbox" checked={showOperating} onChange={event => setShowOperating(event.target.checked)} /> Operating-project research</label><label><input type="checkbox" checked={showRejected} onChange={event => setShowRejected(event.target.checked)} /> Rejected & withdrawn proposals</label></fieldset>
            <label className="study-map-filter" htmlFor="study-map-type">Operating-project type</label>
            <select id="study-map-type" aria-label="Research-complete project markers" value={studyGroup} onChange={e => setStudyGroup(e.target.value)}><option value="">All completed research</option>{completedGroups.map(group => <option key={group}>{group}</option>)}</select>
            <p className="control-note">Cyan shows completed operating-project research. Amber shows verified proposals that were denied or withdrawn. Mixed counties carry cyan shading with amber hatching.</p>
          </section>

          <section className="county-section" aria-live="polite">
            {studyError && <div className="error-panel">{studyError}</div>}
            {!studyError && !selectedCompletedProject && selectedRejectedProjects.length === 0 && <div className="empty-panel">Select a researched county on the map.</div>}
            {(selectedCompletedProject || selectedRejectedProjects.length > 0) && (
              <>
                <div className="county-heading">
                  <div>
                    <span className="eyebrow">Community research</span>
                    <h2>{selectedCompletedProject?.county_name ?? selectedRejectedProjects[0].county_name}</h2>
                    <p>{selectedCompletedProject?.state_abbr ?? selectedRejectedProjects[0].state_abbr} · FIPS {selectedCompletedProject?.county_fips ?? selectedRejectedProjects[0].county_fips}</p>
                  </div>
                  <span className={`quality-badge ${selectedCompletedProject ? "grade-p" : "grade-rejected"}`}>{selectedCompletedProject && selectedRejectedProjects.length ? "Both cohorts" : selectedCompletedProject ? "Operating study" : "Rejected proposal"}</span>
                </div>
                {selectedCompletedProject && <CountyStudyProjects study={study} fips={selectedCompletedProject.county_fips} error={studyError} completedOnly />}
                <CountyRejectedProjects projects={selectedRejectedProjects} error={rejectedError} />
              </>
            )}
          </section>
        </aside>

        <section className="map-section">
          <Suspense fallback={<div className="map-loading">Preparing interactive map…</div>}>
            <MapPanel selectedFips={selectedFips} onSelectCounty={setSelectedFips} studyProjects={mappedProjects} rejectedProjects={mappedRejectedProjects} />
          </Suspense>
          <div className="map-caption">
            <span>Census boundaries · Jan. 1, 2025</span>
            {study && <span>{completedProjects.length} operating audits · {rejected?.counts.projects ?? 0} stopped proposals</span>}
            <span>Proposal benefits remain labeled projections</span>
          </div>
        </section>
      </main>
    </div>
  );
}

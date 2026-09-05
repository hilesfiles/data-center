import { lazy, Suspense, useEffect, useMemo, useState } from "react";
import { CountyStudyProjects, StudyNav } from "./StudyNav";
import type { StudyIndex } from "./studyTypes";
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

const countyFipsFromHash = () => {
  const match = window.location.hash.match(/^#\/county\/(\d{5})$/);
  return match?.[1] ?? null;
};

export default function App({ study, studyError }: { study: StudyIndex | null; studyError: string | null }) {
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
  const completedProjects = useMemo(
    () => study?.projects.filter(project => project.model_completeness.status === "full_modeled_account") ?? [],
    [study],
  );
  const mappedProjects = useMemo(
    () => completedProjects.filter(project => !studyGroup || project.study_group === studyGroup),
    [completedProjects, studyGroup],
  );
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
    if (profileFips == null && mappedProjects.length > 0 && !mappedProjects.some(project => project.county_fips === selectedFips)) {
      setSelectedFips(mappedProjects[0].county_fips);
    }
  }, [mappedProjects, profileFips, selectedFips]);

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
  const selectedHistoryChange = useMemo(() => {
    const start = selectedEconomicHistory?.years.find((record) => record.year === 2001);
    const end = selectedEconomicHistory?.years.find((record) => record.year === 2024);
    return {
      employment: percentChange(start?.annual_avg_covered_employment, end?.annual_avg_covered_employment),
      realGdp: percentChange(start?.real_gdp_usd, end?.real_gdp_usd),
      population: percentChange(start?.population, end?.population),
      weeklyWage: percentChange(start?.annual_avg_weekly_wage_nominal_usd, end?.annual_avg_weekly_wage_nominal_usd),
    };
  }, [selectedEconomicHistory]);
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
                  <p>Community economic history and linked data-center research.</p>
                </div>
                <span className="quality-badge grade-p">Provisional</span>
              </div>
              <CountyStudyProjects study={study} fips={selectedCounty.county_fips} error={studyError} />
              <section className="profile-grid" aria-label="County profile measures">
                <article>
                  <span>IM3 source records</span>
                  <strong>{integerFormat.format(selectedCounty.source_record_count)}</strong>
                  <small>source observations, not deduplicated facilities</small>
                </article>
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
                  <span>History completeness · 2001–2024</span>
                  <strong>{!historyLoaded ? "Loading…" : selectedEconomicHistory == null ? "Unavailable" : `${selectedEconomicHistory.complete_year_count}/24`}</strong>
                  <small>four governed measures per year</small>
                </article>
                <article>
                  <span>Employment change · 2001–2024</span>
                  <strong>{!historyLoaded ? "Loading…" : formatPercentChange(selectedHistoryChange.employment)}</strong>
                  <small>descriptive, not a causal estimate</small>
                </article>
                <article>
                  <span>Real GDP change · 2001–2024</span>
                  <strong>{!historyLoaded ? "Loading…" : formatPercentChange(selectedHistoryChange.realGdp)}</strong>
                  <small>chained 2017 dollars</small>
                </article>
                <article>
                  <span>Population change · 2001–2024</span>
                  <strong>{!historyLoaded ? "Loading…" : formatPercentChange(selectedHistoryChange.population)}</strong>
                  <small>descriptive change</small>
                </article>
                <article>
                  <span>Weekly wage change · 2001–2024</span>
                  <strong>{!historyLoaded ? "Loading…" : formatPercentChange(selectedHistoryChange.weeklyWage)}</strong>
                  <small>nominal descriptive change</small>
                </article>
              </section>
              <details className="research-details">
                <summary>County first-entry methodology and research</summary>
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
        {study ? <><strong>{completedProjects.length} completed private-sector county accounts are mapped.</strong> The broader {study.counts.projects}-project research register and legacy national inventory remain preserved off-map for future study.</> : studyError ?? "Loading the private-sector project register…"}
      </div>

      <main className="workspace">
        <aside className="sidebar">
          <section className="control-section">
            <label className="study-map-filter" htmlFor="study-map-type">Completed project markers</label>
            <select id="study-map-type" value={studyGroup} onChange={e => setStudyGroup(e.target.value)}><option value="">All completed projects</option>{completedGroups.map(group => <option key={group}>{group}</option>)}</select>
            <p className="control-note">Only projects that pass the full modeled county-account gate appear here. Legacy inventory records and incomplete research candidates remain stored but are excluded from this map.</p>
          </section>

          <section className="county-section" aria-live="polite">
            {studyError && <div className="error-panel">{studyError}</div>}
            {!studyError && !selectedCompletedProject && <div className="empty-panel">Select a completed study on the map.</div>}
            {selectedCompletedProject && (
              <>
                <div className="county-heading">
                  <div>
                    <span className="eyebrow">Completed private-sector study</span>
                    <h2>{selectedCompletedProject.county_name}</h2>
                    <p>{selectedCompletedProject.state_abbr} · FIPS {selectedCompletedProject.county_fips}</p>
                  </div>
                  <span className="quality-badge grade-p">Full account</span>
                </div>
                <CountyStudyProjects study={study} fips={selectedCompletedProject.county_fips} error={studyError} completedOnly />
              </>
            )}
          </section>
        </aside>

        <section className="map-section">
          <Suspense fallback={<div className="map-loading">Preparing interactive map…</div>}>
            <MapPanel selectedFips={selectedFips} onSelectCounty={setSelectedFips} studyProjects={mappedProjects} />
          </Suspense>
          <div className="map-caption">
            <span>Census boundaries · Jan. 1, 2025</span>
            {study && <span>{completedProjects.length} completed county accounts · release {study.release_id}</span>}
            <span>Legacy inventory and county datasets retained off-map</span>
          </div>
        </section>
      </main>
    </div>
  );
}

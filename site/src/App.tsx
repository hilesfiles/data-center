import { lazy, Suspense, useEffect, useMemo, useState } from "react";
import type {
  CountyEntityAdjudicationCoverage,
  CountyEconomicHistory,
  CountyTreatmentAssessment,
  FirstEntryResearchCandidate,
  CountyEconomicBaseline,
  CountyEmploymentWagesBaseline,
  CountyEntityResolutionCoverage,
  CountyLifecycleVerificationCoverage,
  CountyMapMetric,
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

export default function App() {
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
  const [mapMetric, setMapMetric] = useState<CountyMapMetric>("im3-source-records");
  const [profileFips, setProfileFips] = useState<string | null>(() => countyFipsFromHash());
  const [selectedFips, setSelectedFips] = useState<string | null>(
    () => countyFipsFromHash() ?? "51107",
  );
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    const base = import.meta.env.BASE_URL;
    Promise.all([
      fetch(`${base}data/v1/metadata.json`),
      fetch(`${base}data/v1/counties/facility-source-coverage.json`),
      fetch(`${base}data/v1/counties/economic-baseline-2024.json`),
      fetch(`${base}data/v1/counties/employment-wages-baseline-2025.json`),
      fetch(`${base}data/v1/counties/entity-resolution-coverage.json`),
      fetch(`${base}data/v1/counties/final-review-coverage.json`),
      fetch(`${base}data/v1/counties/lifecycle-national-tranche-6-coverage.json`),
    ])
      .then(async ([metadataResponse, coverageResponse, economicResponse, employmentWagesResponse, resolutionResponse, adjudicationResponse, lifecycleResponse]) => {
        if (!metadataResponse.ok || !coverageResponse.ok || !economicResponse.ok || !employmentWagesResponse.ok || !resolutionResponse.ok || !adjudicationResponse.ok || !lifecycleResponse.ok) {
          throw new Error("The static data contract could not be loaded.");
        }
        setMetadata((await metadataResponse.json()) as SiteMetadata);
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
  }, []);

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
            <span>{metadata?.data_version ?? "Loading data version"}</span>
          </div>
        </header>
        <main className="county-profile-page">
          <a className="back-link" href="#">← Back to national map</a>
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
                  <p>Shareable static profile with history loaded only for {selectedCounty.state_abbr}.</p>
                </div>
                <span className="quality-badge grade-p">Provisional</span>
              </div>
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
                  <span>County first-entry treatment</span>
                  <strong>{!treatmentLoaded ? "Loading…" : treatmentStatus}</strong>
                  <small>{!treatmentLoaded ? "loading governed assessment" : treatmentNote}</small>
                </article>
                <article>
                  <span>First-entry research queue</span>
                  <strong>{!researchQueueLoaded ? "Loading…" : researchQueueStatus}</strong>
                  <small>{!researchQueueLoaded ? "loading governed priority" : researchQueueNote}</small>
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
              <div className="evidence-note profile-note">
                <span>{selectedFirstEntryResearch?.adjudication_status ? "First-entry adjudication" : "Research status"}</span>
                <p>{selectedFirstEntryResearch?.research_summary ?? "The governed first-entry queue contains 217 research candidates and a region-balanced 24-county initial tranche. Queue rank orders evidence work only: it does not establish a treatment date, first entry, or never-treated comparison status."}</p>
              </div>
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
          <span>{metadata?.data_version ?? "Loading data version"}</span>
        </div>
      </header>

      <div className="fixture-banner" role="status">
        <strong>The first fourteen dated anchors have been adjudicated.</strong> Earlier operations reject the Fulton, Maricopa, Santa Clara, Clark, Monroe, Oakland, Cook, Alachua, Cumberland, Middlesex, Hillsborough, Montgomery, and Mecklenburg anchors; Hudson's 2002 exact-facility anchor remains unresolved as county first entry. Complete historical inventories remain unresolved, zero treatment counties are eligible, and no impact model has been run.
      </div>

      <main className="workspace">
        <aside className="sidebar">
          <section className="control-section">
            <label htmlFor="metric">Map measure</label>
            <select
              id="metric"
              value={mapMetric}
              onChange={(event) => setMapMetric(event.target.value as CountyMapMetric)}
            >
              <option value="im3-source-records">IM3 source records</option>
              <option value="real-gdp">Real GDP (2024)</option>
              <option value="personal-income">Personal income, nominal (2024)</option>
              <option value="population">Population (2024)</option>
              <option value="per-capita-income">Per-capita personal income, nominal (2024)</option>
              <option value="covered-employment">Covered employment (2025)</option>
              <option value="establishments">Covered establishments (2025)</option>
              <option value="total-wages">Total wages, nominal (2025)</option>
              <option value="weekly-wage">Average weekly wage, nominal (2025)</option>
              <option value="private-construction-employment">Private construction jobs (2025)</option>
            </select>
            <p className="control-note">Facility counts use IM3 v2026.02.09. Economic measures use BEA 2024 and BLS QCEW 2025 annual data. Missing and suppressed values are never displayed as zero.</p>
          </section>

          <section className="county-section" aria-live="polite">
            {error && <div className="error-panel">{error}</div>}
            {!error && !selectedCounty && <div className="empty-panel">Select a county on the map.</div>}
            {selectedCounty && (
              <>
                <div className="county-heading">
                  <div>
                    <span className="eyebrow">IM3 source inventory</span>
                    <h2>{selectedCounty.county_name}</h2>
                    <p>{selectedCounty.state_abbr} · FIPS {selectedCounty.county_fips}</p>
                  </div>
                  <span className="quality-badge grade-p">Provisional</span>
                </div>
                <a className="profile-link" href={`#/county/${selectedCounty.county_fips}`}>
                  Open shareable county profile →
                </a>

                <div className="stat-grid">
                  <article>
                    <span>Source records</span>
                    <strong>{integerFormat.format(selectedCounty.source_record_count)}</strong>
                    <small>not deduplicated facilities</small>
                  </article>
                  <article>
                    <span>Building records</span>
                    <strong>{integerFormat.format(selectedCounty.building_record_count)}</strong>
                    <small>mapped footprints</small>
                  </article>
                  <article>
                    <span>Campus records</span>
                    <strong>{integerFormat.format(selectedCounty.campus_record_count)}</strong>
                    <small>mapped campus areas</small>
                  </article>
                  <article>
                    <span>Observed footprint</span>
                    <strong>{compactFormat.format(selectedCounty.observed_footprint_sqft)}</strong>
                    <small>sq ft · single-county records</small>
                  </article>
                </div>

                <div className="index-list">
                  <div>
                    <span>Point-only records</span>
                    <strong>{integerFormat.format(selectedCounty.point_record_count)}</strong>
                    <em>location without footprint</em>
                  </div>
                  <div>
                    <span>Records with source name</span>
                    <strong>{integerFormat.format(selectedCounty.named_record_count)}</strong>
                    <em>source completeness</em>
                  </div>
                  <div>
                    <span>Records with source operator</span>
                    <strong>{integerFormat.format(selectedCounty.operator_named_record_count)}</strong>
                    <em>raw source assertions</em>
                  </div>
                  <div>
                    <span>Cross-county records</span>
                    <strong>{integerFormat.format(selectedCounty.cross_county_source_record_count)}</strong>
                    <em>footprint not allocated</em>
                  </div>
                  <div>
                    <span>Campus-linked facilities</span>
                    <strong>{integerFormat.format(selectedAdjudication?.campus_linked_facility_count ?? selectedResolution?.campus_linked_facility_count ?? 0)}</strong>
                    <em>governed spatial decisions</em>
                  </div>
                  <div>
                    <span>Normalized operator links</span>
                    <strong>{integerFormat.format(selectedResolution?.operator_linked_record_count ?? 0)}</strong>
                    <em>case and whitespace only</em>
                  </div>
                  <div>
                    <span>Pending identity reviews</span>
                    <strong>{integerFormat.format(selectedAdjudication?.pending_candidate_count ?? 0)}</strong>
                    <em>{integerFormat.format(selectedAdjudication?.reviewed_candidate_count ?? 0)} candidates reviewed</em>
                  </div>
                  <div>
                    <span>Merged source records</span>
                    <strong>{integerFormat.format(selectedAdjudication?.merged_source_record_count ?? 0)}</strong>
                    <em>redirected, never deleted</em>
                  </div>
                  <div>
                    <span>Distinct sites in buildings</span>
                    <strong>{integerFormat.format(selectedAdjudication?.distinct_contained_facility_count ?? 0)}</strong>
                    <em>contained but not merged</em>
                  </div>
                  <div className="lifecycle-row lifecycle-start">
                    <span>Real GDP · 2024</span>
                    <strong>{compactCurrency(selectedEconomic?.real_gdp_usd)}</strong>
                    <em>chained 2017 dollars</em>
                  </div>
                  <div className="lifecycle-row">
                    <span>Personal income · 2024</span>
                    <strong>{compactCurrency(selectedEconomic?.personal_income_nominal_usd)}</strong>
                    <em>current dollars</em>
                  </div>
                  <div className="lifecycle-row">
                    <span>Population · 2024</span>
                    <strong>{selectedEconomic?.population == null ? "Unavailable" : integerFormat.format(selectedEconomic.population)}</strong>
                    <em>BEA county estimate</em>
                  </div>
                  <div className="lifecycle-row">
                    <span>Per-capita personal income · 2024</span>
                    <strong>{wholeCurrency(selectedEconomic?.per_capita_personal_income_nominal_usd)}</strong>
                    <em>current dollars per person</em>
                  </div>
                  <div className="lifecycle-row lifecycle-start">
                    <span>Covered employment · 2025</span>
                    <strong>{selectedEmploymentWages?.annual_avg_covered_employment == null ? "Unavailable" : integerFormat.format(selectedEmploymentWages.annual_avg_covered_employment)}</strong>
                    <em>annual average of monthly levels</em>
                  </div>
                  <div className="lifecycle-row">
                    <span>Covered establishments · 2025</span>
                    <strong>{selectedEmploymentWages?.annual_avg_establishments == null ? "Unavailable" : integerFormat.format(selectedEmploymentWages.annual_avg_establishments)}</strong>
                    <em>annual average of quarterly counts</em>
                  </div>
                  <div className="lifecycle-row">
                    <span>Total wages · 2025</span>
                    <strong>{compactCurrency(selectedEmploymentWages?.total_annual_wages_nominal_usd)}</strong>
                    <em>current dollars</em>
                  </div>
                  <div className="lifecycle-row">
                    <span>Average weekly wage · 2025</span>
                    <strong>{wholeCurrency(selectedEmploymentWages?.annual_avg_weekly_wage_nominal_usd)}</strong>
                    <em>current dollars per week</em>
                  </div>
                  <div className="lifecycle-row">
                    <span>Private construction employment · 2025</span>
                    <strong>{selectedEmploymentWages?.private_construction_annual_avg_employment == null ? "Suppressed or unavailable" : integerFormat.format(selectedEmploymentWages.private_construction_annual_avg_employment)}</strong>
                    <em>annual average · NAICS 23</em>
                  </div>
                  <div className="lifecycle-row lifecycle-start">
                    <span>Panel completeness · 2001–2024</span>
                    <strong>{selectedEconomicHistory == null ? "Unavailable" : `${selectedEconomicHistory.complete_year_count}/24 years`}</strong>
                    <em>governed descriptive history</em>
                  </div>
                  <div className="lifecycle-row">
                    <span>County first-entry treatment</span>
                    <strong>{treatmentStatus}</strong>
                    <em>{treatmentNote}</em>
                  </div>
                  <div className="lifecycle-row">
                    <span>First-entry research queue</span>
                    <strong>{researchQueueStatus}</strong>
                    <em>{researchQueueNote}</em>
                  </div>
                  <div className="lifecycle-row">
                    <span>Covered employment change · 2001–2024</span>
                    <strong>{formatPercentChange(selectedHistoryChange.employment)}</strong>
                    <em>descriptive change</em>
                  </div>
                  <div className="lifecycle-row">
                    <span>Real GDP change · 2001–2024</span>
                    <strong>{formatPercentChange(selectedHistoryChange.realGdp)}</strong>
                    <em>chained 2017 dollars</em>
                  </div>
                  <div className="lifecycle-row">
                    <span>Population change · 2001–2024</span>
                    <strong>{formatPercentChange(selectedHistoryChange.population)}</strong>
                    <em>descriptive change</em>
                  </div>
                  <div className="lifecycle-row">
                    <span>Weekly wage change · 2001–2024</span>
                    <strong>{formatPercentChange(selectedHistoryChange.weeklyWage)}</strong>
                    <em>nominal descriptive change</em>
                  </div>
                  <div className="lifecycle-row lifecycle-start">
                    <span>Canonical facilities</span>
                    <strong>{integerFormat.format(selectedLifecycle?.active_canonical_facility_count ?? 0)}</strong>
                    <em>deduplicated research entities</em>
                  </div>
                  <div className="lifecycle-row">
                    <span>National lifecycle queue</span>
                    <strong>{integerFormat.format(selectedLifecycle?.queued_facility_count ?? 0)}</strong>
                    <em>remaining in the initial tranche</em>
                  </div>
                  <div className="lifecycle-row">
                    <span>Verified lifecycle statuses</span>
                    <strong>{integerFormat.format(selectedLifecycle?.verified_facility_count ?? 0)}</strong>
                    <em>reviewed claims required</em>
                  </div>
                  <div className="lifecycle-row">
                    <span>Lifecycle in research</span>
                    <strong>{integerFormat.format(selectedLifecycle?.in_research_facility_count ?? 0)}</strong>
                    <em>evidence does not identify the building</em>
                  </div>
                  <div className="lifecycle-row">
                    <span>Lifecycle needs review</span>
                    <strong>{integerFormat.format(selectedLifecycle?.needs_review_facility_count ?? 0)}</strong>
                    <em>official evidence conflicts</em>
                  </div>
                  <div className="lifecycle-row">
                    <span>Unknown lifecycle status</span>
                    <strong>{integerFormat.format(selectedLifecycle?.unknown_status_facility_count ?? 0)}</strong>
                    <em>unknown is never treated as zero</em>
                  </div>
                </div>

                <div className="evidence-note">
                  <span>Interpretation</span>
                  <p>Halo color shows reviewed evidence state: blue means available evidence does not identify the building, red marks conflicting official records, and green marks a verified status. Unknown and disputed records are never treated as zero.</p>
                </div>
              </>
            )}
          </section>
        </aside>

        <section className="map-section">
          <Suspense fallback={<div className="map-loading">Preparing interactive map…</div>}>
            <MapPanel metric={mapMetric} selectedFips={selectedFips} onSelectCounty={setSelectedFips} />
          </Suspense>
          <div className="map-caption">
            <span>IM3 v2026.02.09 · 1,472 source objects</span>
            <span>Census boundaries · Jan. 1, 2025</span>
            <span>BEA county economy · 2024</span>
            <span>BLS QCEW employment and wages · 2025</span>
            <span>BEA–BLS core panel · 2001–2024</span>
            <span>First-entry treatment registry · 0 eligible counties</span>
            <span>First-entry research · 24 initial / 193 backlog</span>
            <span>Static JSON · No runtime database</span>
            <span>ODbL · © OpenStreetMap contributors</span>
          </div>
        </section>
      </main>
    </div>
  );
}

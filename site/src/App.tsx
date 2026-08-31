import { lazy, Suspense, useEffect, useMemo, useState } from "react";
import type { CountySummary, SiteMetadata } from "./types";

const MapPanel = lazy(() =>
  import("./MapPanel").then((module) => ({ default: module.MapPanel })),
);

const formatScore = (value: number | undefined) =>
  value === undefined ? "—" : value.toFixed(1);

export default function App() {
  const [metadata, setMetadata] = useState<SiteMetadata | null>(null);
  const [counties, setCounties] = useState<CountySummary[]>([]);
  const [selectedFips, setSelectedFips] = useState<string | null>("51059");
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    const base = import.meta.env.BASE_URL;
    Promise.all([
      fetch(`${base}data/v1/metadata.json`),
      fetch(`${base}data/v1/counties/index.json`),
    ])
      .then(async ([metadataResponse, countiesResponse]) => {
        if (!metadataResponse.ok || !countiesResponse.ok) {
          throw new Error("The static data contract could not be loaded.");
        }
        setMetadata((await metadataResponse.json()) as SiteMetadata);
        setCounties((await countiesResponse.json()) as CountySummary[]);
      })
      .catch((reason: unknown) =>
        setError(reason instanceof Error ? reason.message : "Static data could not be loaded."),
      );
  }, []);

  const selectedCounty = useMemo(
    () => counties.find((county) => county.county_fips === selectedFips) ?? null,
    [counties, selectedFips],
  );

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
        <strong>Schema demonstration.</strong> These records are fictional fixtures and are not research findings.
      </div>

      <main className="workspace">
        <aside className="sidebar">
          <section className="control-section">
            <label htmlFor="metric">Map measure</label>
            <select id="metric" defaultValue="active-facilities">
              <option value="active-facilities">Operating facilities</option>
            </select>
            <p className="control-note">Additional measures activate only after validated artifacts exist.</p>
          </section>

          <section className="county-section" aria-live="polite">
            {error && <div className="error-panel">{error}</div>}
            {!error && !selectedCounty && <div className="empty-panel">Select a county on the map.</div>}
            {selectedCounty && (
              <>
                <div className="county-heading">
                  <div>
                    <span className="eyebrow">County evidence profile</span>
                    <h2>{selectedCounty.county_name}</h2>
                    <p>{selectedCounty.state_abbr} · FIPS {selectedCounty.county_fips}</p>
                  </div>
                  <span className={`quality-badge grade-${selectedCounty.quality.data_quality_grade.toLowerCase()}`}>
                    Quality {selectedCounty.quality.data_quality_grade}
                  </span>
                </div>

                <div className="stat-grid">
                  <article>
                    <span>Operating</span>
                    <strong>{selectedCounty.facility_exposure.operating_count}</strong>
                    <small>facilities</small>
                  </article>
                  <article>
                    <span>First verified</span>
                    <strong>{selectedCounty.facility_exposure.first_operational_year ?? "—"}</strong>
                    <small>operational year</small>
                  </article>
                  <article>
                    <span>Observed capacity</span>
                    <strong>{selectedCounty.facility_exposure.operational_mw_observed ?? "—"}</strong>
                    <small>MW</small>
                  </article>
                  <article>
                    <span>Coverage</span>
                    <strong>{Math.round(selectedCounty.quality.component_coverage * 100)}%</strong>
                    <small>eligible components</small>
                  </article>
                </div>

                <div className="index-list">
                  <div>
                    <span>Economic dividend</span>
                    <strong>{formatScore(selectedCounty.indices.DCEDI?.score)}</strong>
                    <em>{selectedCounty.indices.DCEDI?.status ?? "insufficient_data"}</em>
                  </div>
                  <div>
                    <span>Opposition</span>
                    <strong>{formatScore(selectedCounty.indices.DCOI?.score)}</strong>
                    <em>{selectedCounty.indices.DCOI?.status ?? "insufficient_data"}</em>
                  </div>
                  <div>
                    <span>Community cost</span>
                    <strong>{formatScore(selectedCounty.indices.DCCCI?.score)}</strong>
                    <em>{selectedCounty.indices.DCCCI?.status ?? "insufficient_data"}</em>
                  </div>
                </div>

                <div className="evidence-note">
                  <span>Interpretation</span>
                  <p>Scores remain unavailable unless evidence, model fit, uncertainty, and component coverage pass publication thresholds.</p>
                </div>
              </>
            )}
          </section>
        </aside>

        <section className="map-section">
          <Suspense fallback={<div className="map-loading">Preparing interactive map…</div>}>
            <MapPanel selectedFips={selectedFips} onSelectCounty={setSelectedFips} />
          </Suspense>
          <div className="map-caption">
            <span>As of {metadata?.latest_facility_year ?? "—"}</span>
            <span>Static JSON · No runtime database</span>
            <span>Method {metadata?.methodology_version ?? "—"}</span>
          </div>
        </section>
      </main>
    </div>
  );
}

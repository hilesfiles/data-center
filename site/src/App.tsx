import { lazy, Suspense, useEffect, useMemo, useState } from "react";
import type {
  CountyEntityAdjudicationCoverage,
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

export default function App() {
  const [metadata, setMetadata] = useState<SiteMetadata | null>(null);
  const [counties, setCounties] = useState<FacilitySourceCoverage[]>([]);
  const [resolution, setResolution] = useState<CountyEntityResolutionCoverage[]>([]);
  const [adjudication, setAdjudication] = useState<CountyEntityAdjudicationCoverage[]>([]);
  const [lifecycle, setLifecycle] = useState<CountyLifecycleVerificationCoverage[]>([]);
  const [selectedFips, setSelectedFips] = useState<string | null>("51107");
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    const base = import.meta.env.BASE_URL;
    Promise.all([
      fetch(`${base}data/v1/metadata.json`),
      fetch(`${base}data/v1/counties/facility-source-coverage.json`),
      fetch(`${base}data/v1/counties/entity-resolution-coverage.json`),
      fetch(`${base}data/v1/counties/final-review-coverage.json`),
      fetch(`${base}data/v1/counties/lifecycle-national-tranche-2-coverage.json`),
    ])
      .then(async ([metadataResponse, coverageResponse, resolutionResponse, adjudicationResponse, lifecycleResponse]) => {
        if (!metadataResponse.ok || !coverageResponse.ok || !resolutionResponse.ok || !adjudicationResponse.ok || !lifecycleResponse.ok) {
          throw new Error("The static data contract could not be loaded.");
        }
        setMetadata((await metadataResponse.json()) as SiteMetadata);
        setCounties((await coverageResponse.json()) as FacilitySourceCoverage[]);
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

  const selectedCounty = useMemo(
    () => counties.find((county) => county.county_fips === selectedFips) ?? null,
    [counties, selectedFips],
  );
  const selectedResolution = useMemo(
    () => resolution.find((county) => county.county_fips === selectedFips) ?? null,
    [resolution, selectedFips],
  );
  const selectedAdjudication = useMemo(
    () => adjudication.find((county) => county.county_fips === selectedFips) ?? null,
    [adjudication, selectedFips],
  );
  const selectedLifecycle = useMemo(
    () => lifecycle.find((county) => county.county_fips === selectedFips) ?? null,
    [lifecycle, selectedFips],
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
        <strong>National lifecycle verification is underway.</strong> Six of the latest eight records are verified operational and two remain in research, bringing the cumulative verified total to 24; 32 facilities remain in the balanced initial tranche.
      </div>

      <main className="workspace">
        <aside className="sidebar">
          <section className="control-section">
            <label htmlFor="metric">Map measure</label>
            <select id="metric" defaultValue="im3-source-records">
              <option value="im3-source-records">IM3 source records</option>
            </select>
            <p className="control-note">Counts describe records in IM3 v2026.02.09. Absence from the source is not evidence that a county has no data center.</p>
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
            <MapPanel selectedFips={selectedFips} onSelectCounty={setSelectedFips} />
          </Suspense>
          <div className="map-caption">
            <span>IM3 v2026.02.09 · 1,472 source objects</span>
            <span>Census boundaries · Jan. 1, 2025</span>
            <span>Static JSON · No runtime database</span>
            <span>ODbL · © OpenStreetMap contributors</span>
          </div>
        </section>
      </main>
    </div>
  );
}

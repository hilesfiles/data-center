import { useEffect, useRef, useState } from "react";
import {
  AttributionControl,
  Map,
  NavigationControl,
  Popup,
  type MapGeoJSONFeature,
  type MapMouseEvent,
  type StyleSpecification,
} from "maplibre-gl";
import "maplibre-gl/dist/maplibre-gl.css";
import type {
  PublicEntityAdjudicationRecord,
  PublicEntityResolutionRecord,
  LifecycleVerificationCandidate,
  PublicLifecycleVerificationRecord,
} from "./types";

interface MapPanelProps {
  selectedFips: string | null;
  onSelectCounty: (fips: string) => void;
}

type FeaturePointerEvent = MapMouseEvent & { features?: MapGeoJSONFeature[] };

const escapeHtml = (value: unknown) =>
  String(value ?? "")
    .replaceAll("&", "&amp;")
    .replaceAll("<", "&lt;")
    .replaceAll(">", "&gt;")
    .replaceAll('"', "&quot;")
    .replaceAll("'", "&#039;");

const EMPTY_STYLE: StyleSpecification = {
  version: 8,
  sources: {},
  layers: [
    {
      id: "background",
      type: "background",
      paint: { "background-color": "#e6e9e3" },
    },
  ],
};

export function MapPanel({ selectedFips, onSelectCounty }: MapPanelProps) {
  const containerRef = useRef<HTMLDivElement>(null);
  const mapRef = useRef<Map | null>(null);
  const selectRef = useRef(onSelectCounty);
  const [message, setMessage] = useState("Loading map data…");

  useEffect(() => {
    selectRef.current = onSelectCounty;
  }, [onSelectCounty]);

  useEffect(() => {
    if (!containerRef.current || mapRef.current) return;

    const map = new Map({
      container: containerRef.current,
      style: EMPTY_STYLE,
      center: [-98.5, 38.5],
      zoom: 3.25,
      minZoom: 2.25,
      attributionControl: false,
    });
    mapRef.current = map;
    map.addControl(new NavigationControl({ showCompass: false }), "bottom-right");
    map.addControl(
      new AttributionControl({
        compact: true,
        customAttribution: "Counties: U.S. Census Bureau, 2025 · Locations: © OpenStreetMap contributors; IM3 Atlas (PNNL/DOE), ODbL",
      }),
      "bottom-right",
    );

    map.on("load", async () => {
      try {
        const base = import.meta.env.BASE_URL;
        const [countiesResponse, facilitiesResponse, coverageResponse, resolutionResponse, adjudicationResponse, lifecycleResponse, lifecycleResultsResponse] = await Promise.all([
          fetch(`${base}data/v1/maps/counties.geojson`),
          fetch(`${base}data/v1/maps/facilities.geojson`),
          fetch(`${base}data/v1/counties/facility-source-coverage.json`),
          fetch(`${base}data/v1/entity-resolution/index.json`),
          fetch(`${base}data/v1/entity-resolution/final-index.json`),
          fetch(`${base}data/v1/lifecycle/tranche-1-queue.json`),
          fetch(`${base}data/v1/lifecycle/tranche-1-results.json`),
        ]);
        if (!countiesResponse.ok || !facilitiesResponse.ok || !coverageResponse.ok || !resolutionResponse.ok || !adjudicationResponse.ok || !lifecycleResponse.ok || !lifecycleResultsResponse.ok) {
          throw new Error("A required map artifact could not be loaded.");
        }
        const counties = await countiesResponse.json();
        const facilities = await facilitiesResponse.json();
        const coverage = await coverageResponse.json();
        const resolution = (await resolutionResponse.json()) as PublicEntityResolutionRecord[];
        const adjudication = (await adjudicationResponse.json()) as PublicEntityAdjudicationRecord[];
        const lifecycle = (await lifecycleResponse.json()) as LifecycleVerificationCandidate[];
        const lifecycleResults = (await lifecycleResultsResponse.json()) as PublicLifecycleVerificationRecord[];
        const coverageByFips = new globalThis.Map(
          coverage.map((record: { county_fips: string; source_record_count: number }) => [
            record.county_fips,
            record,
          ]),
        );
        counties.features = counties.features.map(
          (feature: { properties: Record<string, unknown> }) => {
            const record = coverageByFips.get(feature.properties.county_fips as string) as
              | { source_record_count: number }
              | undefined;
            return {
              ...feature,
              properties: {
                ...feature.properties,
                source_record_count: record?.source_record_count ?? 0,
              },
            };
          },
        );
        const resolutionByEntity = new globalThis.Map(
          resolution.map((record) => [record.entity_id, record]),
        );
        const adjudicationByEntity = new globalThis.Map(
          adjudication.map((record) => [record.source_entity_id, record]),
        );
        const lifecycleByFacility = new globalThis.Map(
          lifecycle.map((record) => [record.facility_id, record]),
        );
        const lifecycleResultByFacility = new globalThis.Map(
          lifecycleResults.map((record) => [record.facility_id, record]),
        );
        facilities.features = facilities.features.map(
          (feature: { properties: Record<string, unknown> }) => {
            const record = resolutionByEntity.get(feature.properties.entity_id as string);
            const adjudicated = adjudicationByEntity.get(feature.properties.entity_id as string);
            const pendingCount = adjudicated?.candidate_outcomes.filter(
              (outcome) => outcome.decision === "escalate",
            ).length ?? 0;
            const resolvedEntityId = adjudicated?.resolved_entity_id ?? (feature.properties.entity_id as string);
            const lifecycleCandidate = lifecycleByFacility.get(resolvedEntityId);
            const lifecycleResult = lifecycleResultByFacility.get(resolvedEntityId);
            return {
              ...feature,
              properties: {
                ...feature.properties,
                campus_id: adjudicated?.campus_id ?? record?.campus_id ?? null,
                operator_canonical_name: record?.operator_canonical_name ?? null,
                pending_candidate_count: pendingCount,
                lifecycle_review_status: lifecycleCandidate?.review_status ?? "not_queued",
                lifecycle_priority_score: lifecycleCandidate?.priority_score ?? null,
                lifecycle_current_status: lifecycleResult?.resolved_current_status ?? null,
                lifecycle_resolution_status: lifecycleResult?.resolution_status ?? null,
                resolution_status: adjudicated?.identity_status ?? record?.resolution_status ?? "source_only",
                resolved_entity_id: resolvedEntityId,
                container_facility_id: adjudicated?.container_facility_id ?? null,
              },
            };
          },
        );

        map.addSource("counties", { type: "geojson", data: counties, promoteId: "county_fips" });
        map.addSource("facilities", { type: "geojson", data: facilities, promoteId: "entity_id" });
        map.addLayer({
          id: "county-fill",
          type: "fill",
          source: "counties",
          paint: {
            "fill-color": [
              "interpolate",
              ["linear"],
              ["get", "source_record_count"],
              0,
              "#d8ddd5",
              1,
              "#9cc8c0",
              10,
              "#4c9892",
              50,
              "#17687a",
              100,
              "#0d3544",
            ],
            "fill-opacity": 0.9,
          },
        });
        map.addLayer({
          id: "county-outline",
          type: "line",
          source: "counties",
          paint: { "line-color": "#f7f6f1", "line-width": ["interpolate", ["linear"], ["zoom"], 3, 0.35, 8, 1.4] },
        });
        map.addLayer({
          id: "county-selected",
          type: "line",
          source: "counties",
          filter: ["==", ["get", "county_fips"], ""],
          paint: { "line-color": "#f4a261", "line-width": 3.5 },
        });
        map.addLayer({
          id: "facility-points",
          type: "circle",
          source: "facilities",
          paint: {
            "circle-radius": [
              "interpolate",
              ["linear"],
              ["zoom"],
              3,
              ["match", ["get", "source_layer"], "campus", 3.5, "building", 2.5, 2],
              9,
              ["match", ["get", "source_layer"], "campus", 8, "building", 6, 5],
            ],
            "circle-color": [
              "match",
              ["get", "source_layer"],
              "campus",
              "#f4a261",
              "building",
              "#ffbf69",
              "#f7e2b2",
            ],
            "circle-stroke-color": ["match", ["get", "resolution_status"], "review_pending", "#c7522a", "merged", "#76518f", "distinct_within_building", "#277da1", "#172a33"],
            "circle-stroke-width": [
              "case",
              [">", ["get", "pending_candidate_count"], 0],
              2.75,
              1.25,
            ],
            "circle-opacity": 0.88,
          },
        });
        map.addLayer({
          id: "lifecycle-pilot-halo",
          type: "circle",
          source: "facilities",
          filter: ["!=", ["get", "lifecycle_review_status"], "not_queued"],
          paint: {
            "circle-radius": ["interpolate", ["linear"], ["zoom"], 3, 5.5, 9, 11],
            "circle-color": "rgba(0,0,0,0)",
            "circle-stroke-color": [
              "match",
              ["get", "lifecycle_review_status"],
              "verified",
              "#2f7d5b",
              "in_research",
              "#277da1",
              "needs_review",
              "#c7522a",
              "#c66a16",
            ],
            "circle-stroke-width": 2.25,
            "circle-opacity": 0.95,
          },
        });

        const popup = new Popup({ closeButton: false, closeOnClick: false, offset: 12 });
        map.on("mousemove", "county-fill", (event: FeaturePointerEvent) => {
          map.getCanvas().style.cursor = "pointer";
          const feature = event.features?.[0];
          if (!feature) return;
          const properties = feature.properties as Record<string, string | number>;
          const recordCount = Number(properties.source_record_count ?? 0);
          popup
            .setLngLat(event.lngLat)
            .setHTML(
              `<strong>${escapeHtml(properties.county_name)}, ${escapeHtml(properties.state_abbr)}</strong><br/>` +
                `${recordCount} IM3 source record${recordCount === 1 ? "" : "s"}`,
            )
            .addTo(map);
        });
        map.on("mouseleave", "county-fill", () => {
          map.getCanvas().style.cursor = "";
          popup.remove();
        });
        map.on("click", "county-fill", (event: FeaturePointerEvent) => {
          const fips = event.features?.[0]?.properties?.county_fips as string | undefined;
          if (fips) selectRef.current(fips);
        });
        map.on("mousemove", "facility-points", (event: FeaturePointerEvent) => {
          map.getCanvas().style.cursor = "pointer";
          const feature = event.features?.[0];
          if (!feature) return;
          const properties = feature.properties as Record<string, unknown>;
          const layer = escapeHtml(properties.source_layer);
          const operator = properties.source_operator
            ? `<br/>Source operator: ${escapeHtml(properties.source_operator)}`
            : "";
          const normalizedOperator = properties.operator_canonical_name
            ? `<br/>Normalized operator: ${escapeHtml(properties.operator_canonical_name)}`
            : "";
          const campusLink = properties.campus_id
            ? `<br/>Campus link: governed spatial rule`
            : "";
          const pending = Number(properties.pending_candidate_count ?? 0);
          const review = pending
            ? `<br/><strong>${pending} pending identity review${pending === 1 ? "" : "s"}</strong>`
            : "";
          const lifecycleState = String(properties.lifecycle_review_status ?? "not_queued");
          const lifecycleLabels: Record<string, string> = {
            queued: "queued for evidence review",
            in_research: "partial evidence; facility status unresolved",
            needs_review: "conflicting evidence; review required",
            verified: `verified ${String(properties.lifecycle_current_status ?? "lifecycle status")}`,
          };
          const lifecycleReview = lifecycleLabels[lifecycleState]
            ? `<br/><strong>Lifecycle pilot:</strong> ${escapeHtml(lifecycleLabels[lifecycleState])} (priority ${escapeHtml(properties.lifecycle_priority_score)})`
            : "";
          const identityStatus = properties.resolution_status === "merged"
            ? `<br/><strong>Merged:</strong> redirects to ${escapeHtml(properties.resolved_entity_id)}`
            : properties.resolution_status === "distinct_within_building"
              ? `<br/><strong>Reviewed:</strong> distinct site within a larger building`
              : "";
          const footprint = typeof properties.footprint_sqft === "number"
            ? `<br/>Mapped footprint: ${properties.footprint_sqft.toLocaleString()} sq ft`
            : "";
          popup
            .setLngLat(event.lngLat)
            .setHTML(
              `<strong>${escapeHtml(properties.display_name)}</strong><br/>` +
                `IM3 ${layer} source record${operator}${normalizedOperator}${campusLink}${footprint}${identityStatus}${review}${lifecycleReview}`,
            )
            .addTo(map);
        });
        map.on("mouseleave", "facility-points", () => {
          map.getCanvas().style.cursor = "";
          popup.remove();
        });
        map.on("click", "facility-points", (event: FeaturePointerEvent) => {
          const fips = event.features?.[0]?.properties?.primary_county_fips as string | undefined;
          if (fips) selectRef.current(fips);
        });
        setMessage("");
      } catch (error) {
        setMessage(error instanceof Error ? error.message : "The map could not be loaded.");
      }
    });

    return () => {
      map.remove();
      mapRef.current = null;
    };
  }, []);

  useEffect(() => {
    const map = mapRef.current;
    if (!map?.getLayer("county-selected")) return;
    map.setFilter("county-selected", ["==", ["get", "county_fips"], selectedFips ?? ""]);
  }, [selectedFips]);

  return (
    <div className="map-frame">
      <div ref={containerRef} className="map" aria-label="Interactive county facility map" />
      {message && <div className="map-message">{message}</div>}
      <div className="legend" aria-label="Map legend">
        <span className="legend-title">IM3 source records</span>
        <div className="legend-ramp" aria-hidden="true" />
        <div className="legend-labels"><span>no source record</span><span>100+</span></div>
        <div className="review-key">
          <span><i className="key-dot key-pending" />pending (0)</span>
          <span><i className="key-dot key-merged" />merged</span>
          <span><i className="key-dot key-contained" />contained</span>
          <span><i className="key-ring key-queued" />queued</span>
          <span><i className="key-ring key-research" />research</span>
          <span><i className="key-ring key-review" />conflict</span>
          <span><i className="key-ring key-verified" />verified</span>
        </div>
      </div>
    </div>
  );
}

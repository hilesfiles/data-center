import { useEffect, useRef, useState } from "react";
import {
  AttributionControl,
  Map,
  NavigationControl,
  Popup,
  setWorkerUrl,
  type ExpressionSpecification,
  type MapGeoJSONFeature,
  type MapMouseEvent,
  type StyleSpecification,
  type GeoJSONSource,
} from "maplibre-gl";
import "maplibre-gl/dist/maplibre-gl.css";
import maplibreWorkerUrl from "maplibre-gl/dist/maplibre-gl-worker.mjs?worker&url";
import type { StudyProjectSummary } from "./studyTypes";
import type {
  CountyEconomicBaseline,
  CountyEmploymentWagesBaseline,
  CountyMapMetric,
  PublicEntityAdjudicationRecord,
  PublicEntityResolutionRecord,
  LifecycleVerificationCandidate,
  NationalLifecyclePriorityRecord,
  PublicLifecycleVerificationRecord,
  PublicNationalLifecycleVerificationRecord,
} from "./types";

interface MapPanelProps {
  metric: CountyMapMetric;
  selectedFips: string | null;
  onSelectCounty: (fips: string) => void;
  studyProjects?: StudyProjectSummary[];
}

const studyFeatures = (projects: StudyProjectSummary[]) => ({
  type: "FeatureCollection" as const,
  features: projects.map(p => ({ type: "Feature" as const,
    geometry: { type: "Point" as const, coordinates: [p.longitude, p.latitude] },
    properties: { project_id: p.project_id, name: p.name, county_fips: p.county_fips, study_group: p.study_group, inventory_entity_type: p.inventory_entity_type },
  })),
});

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

const METRIC_CONFIG: Record<CountyMapMetric, {
  property: string;
  title: string;
  lowLabel: string;
  highLabel: string;
  stops: Array<[number, string]>;
}> = {
  "im3-source-records": {
    property: "source_record_count",
    title: "IM3 source records",
    lowLabel: "no source record",
    highLabel: "100+",
    stops: [[0, "#d8ddd5"], [1, "#9cc8c0"], [10, "#4c9892"], [50, "#17687a"], [100, "#0d3544"]],
  },
  "real-gdp": {
    property: "real_gdp_usd",
    title: "Real GDP · 2024",
    lowLabel: "unavailable / low",
    highLabel: "$1T+",
    stops: [[1_000_000_000, "#d8ddd5"], [10_000_000_000, "#9cc8c0"], [50_000_000_000, "#4c9892"], [200_000_000_000, "#17687a"], [1_000_000_000_000, "#0d3544"]],
  },
  "personal-income": {
    property: "personal_income_nominal_usd",
    title: "Personal income · 2024",
    lowLabel: "unavailable / low",
    highLabel: "$1T+",
    stops: [[1_000_000_000, "#d8ddd5"], [10_000_000_000, "#9cc8c0"], [50_000_000_000, "#4c9892"], [200_000_000_000, "#17687a"], [1_000_000_000_000, "#0d3544"]],
  },
  population: {
    property: "population",
    title: "Population · 2024",
    lowLabel: "unavailable / low",
    highLabel: "10M+",
    stops: [[10_000, "#d8ddd5"], [100_000, "#9cc8c0"], [500_000, "#4c9892"], [2_000_000, "#17687a"], [10_000_000, "#0d3544"]],
  },
  "per-capita-income": {
    property: "per_capita_personal_income_nominal_usd",
    title: "Per-capita income · 2024",
    lowLabel: "unavailable / low",
    highLabel: "$200k+",
    stops: [[30_000, "#d8ddd5"], [50_000, "#9cc8c0"], [75_000, "#4c9892"], [100_000, "#17687a"], [200_000, "#0d3544"]],
  },
  "covered-employment": {
    property: "annual_avg_covered_employment",
    title: "Covered employment · 2025",
    lowLabel: "unavailable / low",
    highLabel: "1M+",
    stops: [[5_000, "#d8ddd5"], [25_000, "#9cc8c0"], [100_000, "#4c9892"], [500_000, "#17687a"], [1_000_000, "#0d3544"]],
  },
  establishments: {
    property: "annual_avg_establishments",
    title: "Covered establishments · 2025",
    lowLabel: "unavailable / low",
    highLabel: "100k+",
    stops: [[500, "#d8ddd5"], [2_500, "#9cc8c0"], [10_000, "#4c9892"], [50_000, "#17687a"], [100_000, "#0d3544"]],
  },
  "total-wages": {
    property: "total_annual_wages_nominal_usd",
    title: "Total wages · 2025",
    lowLabel: "unavailable / low",
    highLabel: "$100B+",
    stops: [[250_000_000, "#d8ddd5"], [1_000_000_000, "#9cc8c0"], [5_000_000_000, "#4c9892"], [25_000_000_000, "#17687a"], [100_000_000_000, "#0d3544"]],
  },
  "weekly-wage": {
    property: "annual_avg_weekly_wage_nominal_usd",
    title: "Average weekly wage · 2025",
    lowLabel: "unavailable / low",
    highLabel: "$2.5k+",
    stops: [[500, "#d8ddd5"], [750, "#9cc8c0"], [1_000, "#4c9892"], [1_500, "#17687a"], [2_500, "#0d3544"]],
  },
  "private-construction-employment": {
    property: "private_construction_annual_avg_employment",
    title: "Private construction employment · 2025",
    lowLabel: "suppressed / low",
    highLabel: "100k+",
    stops: [[250, "#d8ddd5"], [1_000, "#9cc8c0"], [5_000, "#4c9892"], [25_000, "#17687a"], [100_000, "#0d3544"]],
  },
};

const countyFillExpression = (metric: CountyMapMetric): ExpressionSpecification => {
  const config = METRIC_CONFIG[metric];
  return [
    "case",
    ["==", ["get", config.property], null],
    "#d8ddd5",
    [
      "interpolate",
      ["linear"],
      ["get", config.property],
      ...config.stops.flatMap(([value, color]) => [value, color]),
    ],
  ] as ExpressionSpecification;
};

const compactNumber = new Intl.NumberFormat("en-US", { notation: "compact", maximumFractionDigits: 1 });
const wholeDollars = new Intl.NumberFormat("en-US", { style: "currency", currency: "USD", maximumFractionDigits: 0 });

const countyPopupValue = (metric: CountyMapMetric, properties: Record<string, string | number | null>) => {
  const value = properties[METRIC_CONFIG[metric].property];
  const qcewMetric = ["covered-employment", "establishments", "total-wages", "weekly-wage", "private-construction-employment"].includes(metric);
  if (value == null) return qcewMetric ? "BLS QCEW value suppressed or unavailable" : "BEA value unavailable for this Census geography";
  const number = Number(value);
  if (metric === "im3-source-records") {
    return `${number} IM3 source record${number === 1 ? "" : "s"}`;
  }
  if (metric === "population") return `2024 population: ${number.toLocaleString("en-US")}`;
  if (metric === "per-capita-income") return `2024 nominal per-capita personal income: ${wholeDollars.format(number)}`;
  if (metric === "covered-employment") return `2025 annual-average covered employment: ${number.toLocaleString("en-US")}`;
  if (metric === "establishments") return `2025 annual-average covered establishments: ${number.toLocaleString("en-US")}`;
  if (metric === "total-wages") return `2025 nominal total annual wages: $${compactNumber.format(number)}`;
  if (metric === "weekly-wage") return `2025 nominal average weekly wage: ${wholeDollars.format(number)}`;
  if (metric === "private-construction-employment") return `2025 annual-average private construction employment: ${number.toLocaleString("en-US")}`;
  const label = metric === "real-gdp" ? "real GDP (chained 2017 dollars)" : "nominal personal income";
  return `2024 ${label}: $${compactNumber.format(number)}`;
};

setWorkerUrl(maplibreWorkerUrl);

export function MapPanel({ metric, selectedFips, onSelectCounty, studyProjects = [] }: MapPanelProps) {
  const containerRef = useRef<HTMLDivElement>(null);
  const mapRef = useRef<Map | null>(null);
  const selectRef = useRef(onSelectCounty);
  const metricRef = useRef(metric);
  const [message, setMessage] = useState("Loading map data…");
  const projectsRef = useRef(studyProjects);
  const selectedRef = useRef(selectedFips);
  useEffect(() => {
    projectsRef.current = studyProjects;
    const source = mapRef.current?.getSource<GeoJSONSource>("study-projects");
    if (source) source.setData(studyFeatures(studyProjects));
  }, [studyProjects]);

  useEffect(() => {
    selectRef.current = onSelectCounty;
  }, [onSelectCounty]);

  useEffect(() => {
    metricRef.current = metric;
    const map = mapRef.current;
    if (map?.getLayer("county-fill")) {
      map.setPaintProperty("county-fill", "fill-color", countyFillExpression(metric));
    }
  }, [metric]);

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
        const [countiesResponse, facilitiesResponse, coverageResponse, economicResponse, employmentWagesResponse, resolutionResponse, adjudicationResponse, lifecycleResponse, lifecycleResultsResponse, nationalLifecycleResponse, nationalLifecycleResultsResponse, nationalLifecycleResults2Response, nationalLifecycleResults3Response, nationalLifecycleResults4Response, nationalLifecycleResults5Response, nationalLifecycleResults6Response] = await Promise.all([
          fetch(`${base}data/v1/maps/counties.geojson`),
          fetch(`${base}data/v1/maps/facilities.geojson`),
          fetch(`${base}data/v1/counties/facility-source-coverage.json`),
          fetch(`${base}data/v1/counties/economic-baseline-2024.json`),
          fetch(`${base}data/v1/counties/employment-wages-baseline-2025.json`),
          fetch(`${base}data/v1/entity-resolution/index.json`),
          fetch(`${base}data/v1/entity-resolution/final-index.json`),
          fetch(`${base}data/v1/lifecycle/tranche-2-queue.json`),
          fetch(`${base}data/v1/lifecycle/tranche-2-results.json`),
          fetch(`${base}data/v1/lifecycle/national-initial-tranche.json`),
          fetch(`${base}data/v1/lifecycle/national-tranche-1-results.json`),
          fetch(`${base}data/v1/lifecycle/national-tranche-2-results.json`),
          fetch(`${base}data/v1/lifecycle/national-tranche-3-results.json`),
          fetch(`${base}data/v1/lifecycle/national-tranche-4-results.json`),
          fetch(`${base}data/v1/lifecycle/national-tranche-5-results.json`),
          fetch(`${base}data/v1/lifecycle/national-tranche-6-results.json`),
        ]);
        if (!countiesResponse.ok || !facilitiesResponse.ok || !coverageResponse.ok || !economicResponse.ok || !employmentWagesResponse.ok || !resolutionResponse.ok || !adjudicationResponse.ok || !lifecycleResponse.ok || !lifecycleResultsResponse.ok || !nationalLifecycleResponse.ok || !nationalLifecycleResultsResponse.ok || !nationalLifecycleResults2Response.ok || !nationalLifecycleResults3Response.ok || !nationalLifecycleResults4Response.ok || !nationalLifecycleResults5Response.ok || !nationalLifecycleResults6Response.ok) {
          throw new Error("A required map artifact could not be loaded.");
        }
        const counties = await countiesResponse.json();
        const facilities = await facilitiesResponse.json();
        const coverage = await coverageResponse.json();
        const economic = (await economicResponse.json()) as CountyEconomicBaseline[];
        const employmentWages = (await employmentWagesResponse.json()) as CountyEmploymentWagesBaseline[];
        const resolution = (await resolutionResponse.json()) as PublicEntityResolutionRecord[];
        const adjudication = (await adjudicationResponse.json()) as PublicEntityAdjudicationRecord[];
        const lifecycle = (await lifecycleResponse.json()) as LifecycleVerificationCandidate[];
        const lifecycleResults = (await lifecycleResultsResponse.json()) as PublicLifecycleVerificationRecord[];
        const nationalLifecycle = (await nationalLifecycleResponse.json()) as NationalLifecyclePriorityRecord[];
        const nationalLifecycleResults = (await nationalLifecycleResultsResponse.json()) as PublicNationalLifecycleVerificationRecord[];
        const nationalLifecycleResults2 = (await nationalLifecycleResults2Response.json()) as PublicNationalLifecycleVerificationRecord[];
        const nationalLifecycleResults3 = (await nationalLifecycleResults3Response.json()) as PublicNationalLifecycleVerificationRecord[];
        const nationalLifecycleResults4 = (await nationalLifecycleResults4Response.json()) as PublicNationalLifecycleVerificationRecord[];
        const nationalLifecycleResults5 = (await nationalLifecycleResults5Response.json()) as PublicNationalLifecycleVerificationRecord[];
        const nationalLifecycleResults6 = (await nationalLifecycleResults6Response.json()) as PublicNationalLifecycleVerificationRecord[];
        const coverageByFips = new globalThis.Map(
          coverage.map((record: { county_fips: string; source_record_count: number }) => [
            record.county_fips,
            record,
          ]),
        );
        const economicByFips = new globalThis.Map(
          economic.map((record) => [record.county_fips, record]),
        );
        const employmentWagesByFips = new globalThis.Map(
          employmentWages.map((record) => [record.county_fips, record]),
        );
        counties.features = counties.features.map(
          (feature: { properties: Record<string, unknown> }) => {
            const record = coverageByFips.get(feature.properties.county_fips as string) as
              | { source_record_count: number }
              | undefined;
            const economicRecord = economicByFips.get(feature.properties.county_fips as string);
            const employmentWagesRecord = employmentWagesByFips.get(feature.properties.county_fips as string);
            return {
              ...feature,
              properties: {
                ...feature.properties,
                source_record_count: record?.source_record_count ?? 0,
                real_gdp_usd: economicRecord?.real_gdp_usd ?? null,
                personal_income_nominal_usd: economicRecord?.personal_income_nominal_usd ?? null,
                population: economicRecord?.population ?? null,
                per_capita_personal_income_nominal_usd: economicRecord?.per_capita_personal_income_nominal_usd ?? null,
                annual_avg_covered_employment: employmentWagesRecord?.annual_avg_covered_employment ?? null,
                annual_avg_establishments: employmentWagesRecord?.annual_avg_establishments ?? null,
                total_annual_wages_nominal_usd: employmentWagesRecord?.total_annual_wages_nominal_usd ?? null,
                annual_avg_weekly_wage_nominal_usd: employmentWagesRecord?.annual_avg_weekly_wage_nominal_usd ?? null,
                private_construction_annual_avg_employment: employmentWagesRecord?.private_construction_annual_avg_employment ?? null,
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
        const nationalLifecycleByFacility = new globalThis.Map(
          nationalLifecycle.map((record) => [record.facility_id, record]),
        );
        const nationalLifecycleResultByFacility = new globalThis.Map(
          [...nationalLifecycleResults, ...nationalLifecycleResults2, ...nationalLifecycleResults3, ...nationalLifecycleResults4, ...nationalLifecycleResults5, ...nationalLifecycleResults6].map((record) => [record.facility_id, record]),
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
            const nationalLifecycleCandidate = nationalLifecycleByFacility.get(resolvedEntityId);
            const nationalLifecycleResult = nationalLifecycleResultByFacility.get(resolvedEntityId);
            const currentLifecycleResult = nationalLifecycleResult ?? lifecycleResult;
            return {
              ...feature,
              properties: {
                ...feature.properties,
                campus_id: adjudicated?.campus_id ?? record?.campus_id ?? null,
                operator_canonical_name: record?.operator_canonical_name ?? null,
                pending_candidate_count: pendingCount,
                lifecycle_review_status: nationalLifecycleResult?.review_status ?? (nationalLifecycleCandidate ? "queued" : lifecycleCandidate?.review_status ?? "not_queued"),
                lifecycle_priority_score: nationalLifecycleCandidate?.priority_score ?? lifecycleCandidate?.priority_score ?? null,
                lifecycle_current_status: currentLifecycleResult?.resolved_current_status ?? null,
                lifecycle_resolution_status: currentLifecycleResult?.resolution_status ?? null,
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
            "fill-color": countyFillExpression(metricRef.current),
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
          const properties = feature.properties as Record<string, string | number | null>;
          popup
            .setLngLat(event.lngLat)
            .setHTML(
              `<strong>${escapeHtml(properties.county_name)}, ${escapeHtml(properties.state_abbr)}</strong><br/>` +
                countyPopupValue(metricRef.current, properties),
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
            ? `<br/><strong>Lifecycle review:</strong> ${escapeHtml(lifecycleLabels[lifecycleState])} (priority ${escapeHtml(properties.lifecycle_priority_score)})`
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
        map.addSource("study-projects", { type: "geojson", data: studyFeatures(projectsRef.current) });
        map.addLayer({ id: "study-project-points", type: "circle", source: "study-projects", paint: {
          "circle-radius": ["interpolate", ["linear"], ["zoom"], 3, 6, 9, 10],
          "circle-color": "#7145a0", "circle-stroke-color": "#fff", "circle-stroke-width": 2,
        } });
        map.on("mousemove", "study-project-points", (event: FeaturePointerEvent) => {
          const p = event.features?.[0]?.properties;
          if (!p) return;
          map.getCanvas().style.cursor = "pointer";
          popup.setLngLat(event.lngLat).setHTML(`<strong>${escapeHtml(p.name)}</strong><br/>${escapeHtml(p.study_group)} · Research candidate<br/>${escapeHtml(p.inventory_entity_type)} location from inventory<br/>Click to open project evidence`).addTo(map);
        });
        map.on("mouseleave", "study-project-points", () => { popup.remove(); map.getCanvas().style.cursor = ""; });
        map.on("click", "study-project-points", (event: FeaturePointerEvent) => {
          const id = event.features?.[0]?.properties?.project_id;
          if (typeof id === "string" && /^prj_study_[a-z0-9_]+$/.test(id)) window.location.hash = `/project/${id}`;
        });
        map.setFilter("county-selected", ["==", ["get", "county_fips"], selectedRef.current ?? ""]);
        map.resize();
        map.triggerRepaint();
        map.once("idle", () => setMessage(""));
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
    selectedRef.current = selectedFips;
    const map = mapRef.current;
    if (!map?.getLayer("county-selected")) return;
    map.setFilter("county-selected", ["==", ["get", "county_fips"], selectedFips ?? ""]);
  }, [selectedFips]);

  return (
    <div className="map-frame">
      <div ref={containerRef} className="map" aria-label="Interactive county facility map" />
      {message && <div className="map-message">{message}</div>}
      <div className="legend" aria-label="Map legend">
        <span className="legend-title">{METRIC_CONFIG[metric].title}</span>
        <div className="legend-ramp" aria-hidden="true" />
        <div className="legend-labels"><span>{METRIC_CONFIG[metric].lowLabel}</span><span>{METRIC_CONFIG[metric].highLabel}</span></div>
        <div className="review-key">
          <span><i className="key-dot key-study" />study candidates ({studyProjects.length})</span>
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

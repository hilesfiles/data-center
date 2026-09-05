import { useEffect, useRef, useState } from "react";
import {
  AttributionControl,
  Map,
  NavigationControl,
  Popup,
  setWorkerUrl,
  type GeoJSONSource,
  type MapGeoJSONFeature,
  type MapMouseEvent,
  type StyleSpecification,
} from "maplibre-gl";
import "maplibre-gl/dist/maplibre-gl.css";
import maplibreWorkerUrl from "maplibre-gl/dist/maplibre-gl-worker.mjs?worker&url";
import type { StudyProjectSummary } from "./studyTypes";

interface MapPanelProps {
  selectedFips: string | null;
  onSelectCounty: (fips: string) => void;
  studyProjects?: StudyProjectSummary[];
}

const studyFeatures = (projects: StudyProjectSummary[]) => ({
  type: "FeatureCollection" as const,
  features: projects.map(project => ({
    type: "Feature" as const,
    geometry: { type: "Point" as const, coordinates: [project.longitude, project.latitude] },
    properties: {
      project_id: project.project_id,
      name: project.name,
      county_fips: project.county_fips,
      county_name: project.county_name,
      state_abbr: project.state_abbr,
      study_group: project.study_group,
    },
  })),
});

const completedCountyFilter = (projects: StudyProjectSummary[]) => [
  "in",
  ["get", "county_fips"],
  ["literal", [...new Set(projects.map(project => project.county_fips))]],
] as never;

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
  layers: [{ id: "background", type: "background", paint: { "background-color": "#e6e9e3" } }],
};

setWorkerUrl(maplibreWorkerUrl);

export function MapPanel({ selectedFips, onSelectCounty, studyProjects = [] }: MapPanelProps) {
  const containerRef = useRef<HTMLDivElement>(null);
  const mapRef = useRef<Map | null>(null);
  const selectRef = useRef(onSelectCounty);
  const projectsRef = useRef(studyProjects);
  const selectedRef = useRef(selectedFips);
  const [message, setMessage] = useState("Loading completed studies…");

  useEffect(() => {
    projectsRef.current = studyProjects;
    const map = mapRef.current;
    map?.getSource<GeoJSONSource>("study-projects")?.setData(studyFeatures(studyProjects));
    if (map?.getLayer("completed-county-fill")) {
      map.setFilter("completed-county-fill", completedCountyFilter(studyProjects));
    }
  }, [studyProjects]);

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
    map.addControl(new AttributionControl({
      compact: true,
      customAttribution: "County boundaries: U.S. Census Bureau, 2025 · Study locations derived from the preserved research inventory",
    }), "bottom-right");

    map.on("load", async () => {
      try {
        const response = await fetch(`${import.meta.env.BASE_URL}data/v1/maps/counties.geojson`);
        if (!response.ok) throw new Error("County boundaries could not be loaded.");
        const counties = await response.json();
        map.addSource("counties", { type: "geojson", data: counties, promoteId: "county_fips" });
        map.addLayer({
          id: "county-fill",
          type: "fill",
          source: "counties",
          paint: { "fill-color": "#dfe4dc", "fill-opacity": 0.55 },
        });
        map.addLayer({
          id: "completed-county-fill",
          type: "fill",
          source: "counties",
          filter: completedCountyFilter(projectsRef.current),
          paint: { "fill-color": "#a98ac6", "fill-opacity": 0.55 },
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
          filter: ["==", ["get", "county_fips"], selectedRef.current ?? ""],
          paint: { "line-color": "#f4a261", "line-width": 3.5 },
        });

        const popup = new Popup({ closeButton: false, closeOnClick: false, offset: 12 });
        map.on("mousemove", "completed-county-fill", (event: FeaturePointerEvent) => {
          const properties = event.features?.[0]?.properties;
          if (!properties) return;
          map.getCanvas().style.cursor = "pointer";
          popup.setLngLat(event.lngLat).setHTML(
            `<strong>${escapeHtml(properties.county_name)}, ${escapeHtml(properties.state_abbr)}</strong><br/>Full modeled county account`,
          ).addTo(map);
        });
        map.on("mouseleave", "completed-county-fill", () => {
          map.getCanvas().style.cursor = "";
          popup.remove();
        });
        map.on("click", "completed-county-fill", (event: FeaturePointerEvent) => {
          const fips = event.features?.[0]?.properties?.county_fips;
          if (typeof fips === "string") selectRef.current(fips);
        });

        map.addSource("study-projects", { type: "geojson", data: studyFeatures(projectsRef.current) });
        map.addLayer({
          id: "study-project-points",
          type: "circle",
          source: "study-projects",
          paint: {
            "circle-radius": ["interpolate", ["linear"], ["zoom"], 3, 7, 9, 11],
            "circle-color": "#7145a0",
            "circle-stroke-color": "#fff",
            "circle-stroke-width": 2.5,
          },
        });
        map.on("mousemove", "study-project-points", (event: FeaturePointerEvent) => {
          const project = event.features?.[0]?.properties;
          if (!project) return;
          map.getCanvas().style.cursor = "pointer";
          popup.setLngLat(event.lngLat).setHTML(
            `<strong>${escapeHtml(project.name)}</strong><br/>${escapeHtml(project.county_name)}, ${escapeHtml(project.state_abbr)}<br/>Full modeled county account · click to open`,
          ).addTo(map);
        });
        map.on("mouseleave", "study-project-points", () => {
          map.getCanvas().style.cursor = "";
          popup.remove();
        });
        map.on("click", "study-project-points", (event: FeaturePointerEvent) => {
          const id = event.features?.[0]?.properties?.project_id;
          if (typeof id === "string" && /^prj_study_[a-z0-9_]+$/.test(id)) window.location.hash = `/project/${id}`;
        });

        map.resize();
        map.triggerRepaint();
        map.once("idle", () => setMessage(""));
      } catch (error) {
        setMessage(error instanceof Error ? error.message : "The completed-study map could not be loaded.");
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
    if (map?.getLayer("county-selected")) {
      map.setFilter("county-selected", ["==", ["get", "county_fips"], selectedFips ?? ""]);
    }
  }, [selectedFips]);

  return <div className="map-frame">
    <div ref={containerRef} className="map" aria-label="Completed private-sector county study map" />
    {message && <div className="map-message">{message}</div>}
    <div className="legend" aria-label="Map legend">
      <span className="legend-title">Completed private-sector county studies</span>
      <div className="review-key">
        <span><i className="key-dot key-study" />full modeled accounts ({studyProjects.length})</span>
      </div>
    </div>
  </div>;
}

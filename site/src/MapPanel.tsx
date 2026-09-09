import { useEffect, useRef, useState } from "react";
import {
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
import type { RejectedProjectSummary, StudyProjectSummary } from "./studyTypes";

interface MapPanelProps {
  selectedFips: string | null;
  onSelectCounty: (fips: string) => void;
  studyProjects?: StudyProjectSummary[];
  rejectedProjects?: RejectedProjectSummary[];
}

const OVERLAP_DISTANCE_DEGREES = 0.2;
const MARKER_LANE_PIXELS = 12;

const markerLanes = (projects: StudyProjectSummary[]) => {
  const lanes = new globalThis.Map<string, number>();
  const remaining = new Set(projects.map(project => project.project_id));
  const byId = new globalThis.Map(projects.map(project => [project.project_id, project]));
  while (remaining.size) {
    const first = remaining.values().next().value as string;
    const group = new Set([first]);
    const pending = [first];
    remaining.delete(first);
    while (pending.length) {
      const current = byId.get(pending.pop()!)!;
      for (const candidateId of [...remaining]) {
        const candidate = byId.get(candidateId)!;
        const latitude = (current.latitude + candidate.latitude) / 2 * Math.PI / 180;
        const distance = Math.hypot((current.longitude - candidate.longitude) * Math.cos(latitude), current.latitude - candidate.latitude);
        if (distance < OVERLAP_DISTANCE_DEGREES) {
          group.add(candidateId); pending.push(candidateId); remaining.delete(candidateId);
        }
      }
    }
    [...group].sort().forEach((projectId, index, rows) => lanes.set(projectId, 2 * index - (rows.length - 1)));
  }
  return lanes;
};

const studyFeatures = (projects: StudyProjectSummary[]) => {
  const lanes = markerLanes(projects);
  return {
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
      marker_lane: lanes.get(project.project_id) ?? 0,
    },
  })),
  };
};

const rejectedFeatures = (projects: RejectedProjectSummary[]) => ({
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
      disposition: project.disposition,
      decision_date: project.decision_date,
      finality: project.finality,
      outcome_readiness: project.outcome_readiness,
      coordinate_precision: project.coordinate_precision,
    },
  })),
});

const countyFilter = (fips: string[]) => [
  "in",
  ["get", "county_fips"],
  ["literal", fips],
] as never;

const countyCohorts = (operating: StudyProjectSummary[], rejected: RejectedProjectSummary[]) => {
  const operatingFips = new Set(operating.map(project => project.county_fips));
  const rejectedFips = new Set(rejected.map(project => project.county_fips));
  return {
    operatingOnly: [...operatingFips].filter(fips => !rejectedFips.has(fips)),
    rejectedOnly: [...rejectedFips].filter(fips => !operatingFips.has(fips)),
    both: [...operatingFips].filter(fips => rejectedFips.has(fips)),
    all: [...new Set([...operatingFips, ...rejectedFips])],
  };
};

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
  layers: [{ id: "background", type: "background", paint: { "background-color": "#10171b" } }],
};

setWorkerUrl(maplibreWorkerUrl);

export function MapPanel({ selectedFips, onSelectCounty, studyProjects = [], rejectedProjects = [] }: MapPanelProps) {
  const containerRef = useRef<HTMLDivElement>(null);
  const mapRef = useRef<Map | null>(null);
  const selectRef = useRef(onSelectCounty);
  const projectsRef = useRef(studyProjects);
  const rejectedRef = useRef(rejectedProjects);
  const selectedRef = useRef(selectedFips);
  const [message, setMessage] = useState("Loading completed studies…");

  useEffect(() => {
    projectsRef.current = studyProjects;
    const map = mapRef.current;
    map?.getSource<GeoJSONSource>("study-projects")?.setData(studyFeatures(studyProjects));
    const cohorts = countyCohorts(studyProjects, rejectedRef.current);
    for (const [layer, fips] of [["operating-county-fill", cohorts.operatingOnly], ["rejected-county-fill", cohorts.rejectedOnly], ["both-county-fill", cohorts.both], ["both-county-hatch", cohorts.both], ["researched-county-hit", cohorts.all]] as const) {
      if (map?.getLayer(layer)) map.setFilter(layer, countyFilter(fips));
    }
  }, [studyProjects]);

  useEffect(() => {
    rejectedRef.current = rejectedProjects;
    const map = mapRef.current;
    map?.getSource<GeoJSONSource>("rejected-projects")?.setData(rejectedFeatures(rejectedProjects));
    const cohorts = countyCohorts(projectsRef.current, rejectedProjects);
    for (const [layer, fips] of [["operating-county-fill", cohorts.operatingOnly], ["rejected-county-fill", cohorts.rejectedOnly], ["both-county-fill", cohorts.both], ["both-county-hatch", cohorts.both], ["researched-county-hit", cohorts.all]] as const) {
      if (map?.getLayer(layer)) map.setFilter(layer, countyFilter(fips));
    }
  }, [rejectedProjects]);

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
          paint: { "fill-color": "#172126", "fill-opacity": 0.92 },
        });
        const cohorts = countyCohorts(projectsRef.current, rejectedRef.current);
        const hatch = document.createElement("canvas");
        hatch.width = 10; hatch.height = 10;
        const context = hatch.getContext("2d");
        if (context) {
          context.clearRect(0, 0, 10, 10);
          context.strokeStyle = "rgba(240, 170, 88, 0.95)";
          context.lineWidth = 3;
          context.beginPath(); context.moveTo(-2, 10); context.lineTo(10, -2); context.stroke();
          context.beginPath(); context.moveTo(4, 12); context.lineTo(12, 4); context.stroke();
          map.addImage("rejected-county-hatch", context.getImageData(0, 0, 10, 10));
        }
        map.addLayer({ id: "operating-county-fill", type: "fill", source: "counties", filter: countyFilter(cohorts.operatingOnly), paint: { "fill-color": "#0d78a8", "fill-opacity": 0.82 } });
        map.addLayer({ id: "rejected-county-fill", type: "fill", source: "counties", filter: countyFilter(cohorts.rejectedOnly), paint: { "fill-color": "#b66b22", "fill-opacity": 0.78 } });
        map.addLayer({ id: "both-county-fill", type: "fill", source: "counties", filter: countyFilter(cohorts.both), paint: { "fill-color": "#0d78a8", "fill-opacity": 0.82 } });
        if (context) map.addLayer({ id: "both-county-hatch", type: "fill", source: "counties", filter: countyFilter(cohorts.both), paint: { "fill-pattern": "rejected-county-hatch", "fill-opacity": 0.9 } });
        map.addLayer({ id: "researched-county-hit", type: "fill", source: "counties", filter: countyFilter(cohorts.all), paint: { "fill-color": "#ffffff", "fill-opacity": 0.001 } });
        map.addLayer({
          id: "county-outline",
          type: "line",
          source: "counties",
          paint: { "line-color": "#314047", "line-width": ["interpolate", ["linear"], ["zoom"], 3, 0.35, 8, 1.4] },
        });
        map.addLayer({
          id: "county-selected",
          type: "line",
          source: "counties",
          filter: ["==", ["get", "county_fips"], selectedRef.current ?? ""],
          paint: { "line-color": "#f0aa58", "line-width": 3.5 },
        });

        const popup = new Popup({
          closeButton: false,
          closeOnClick: false,
          offset: 12,
          className: "study-map-popup",
        });
        map.on("mousemove", "researched-county-hit", (event: FeaturePointerEvent) => {
          const properties = event.features?.[0]?.properties;
          if (!properties) return;
          const fips = typeof properties.county_fips === "string" && /^\d{5}$/.test(properties.county_fips)
            ? properties.county_fips
            : null;
          map.getCanvas().style.cursor = "pointer";
          const operating = projectsRef.current.some(project => project.county_fips === fips);
          const stopped = rejectedRef.current.some(project => project.county_fips === fips);
          const label = operating && stopped ? "Operating research + rejected proposal" : operating ? "Operating project-research county" : "Rejected-proposal county";
          popup.setLngLat(event.lngLat).setHTML(`<strong>${escapeHtml(properties.county_name)}, ${escapeHtml(properties.state_abbr)}</strong><br/>${label}${fips ? `<br/><a href="#/county/${fips}">Open county detail →</a>` : ""}`).addTo(map);
        });
        map.on("mouseleave", "researched-county-hit", () => {
          map.getCanvas().style.cursor = "";
          popup.remove();
        });
        map.on("click", "researched-county-hit", (event: FeaturePointerEvent) => {
          const fips = event.features?.[0]?.properties?.county_fips;
          if (typeof fips === "string" && /^\d{5}$/.test(fips)) {
            selectRef.current(fips);
            window.location.hash = `/county/${fips}`;
          }
        });

        const projectData = studyFeatures(projectsRef.current);
        map.addSource("study-projects", { type: "geojson", data: projectData });
        const pointLayerIds = [...new Set(projectData.features.map(feature => feature.properties.marker_lane))].sort((a, b) => a - b).map(lane => {
          const id = `study-project-points-${lane < 0 ? `minus-${Math.abs(lane)}` : `plus-${lane}`}`;
          map.addLayer({ id, type: "circle", source: "study-projects", filter: ["==", ["get", "marker_lane"], lane], paint: { "circle-radius": ["interpolate", ["linear"], ["zoom"], 3, 4, 9, 8], "circle-color": "#20a8e0", "circle-stroke-color": "#d7f3ff", "circle-stroke-width": 1.5, "circle-translate": [lane * MARKER_LANE_PIXELS, 0], "circle-translate-anchor": "viewport" } });
          return id;
        });
        const rejectedData = rejectedFeatures(rejectedRef.current);
        map.addSource("rejected-projects", { type: "geojson", data: rejectedData });
        map.addLayer({ id: "rejected-project-points", type: "circle", source: "rejected-projects", paint: { "circle-radius": ["interpolate", ["linear"], ["zoom"], 3, 5.5, 9, 10], "circle-color": "#15100b", "circle-stroke-color": "#f0aa58", "circle-stroke-width": 3 } });
        const showProjectPopup = (event: FeaturePointerEvent) => {
          const project = event.features?.[0]?.properties;
          if (!project) return;
          map.getCanvas().style.cursor = "pointer";
          popup.setLngLat(event.lngLat).setHTML(
            `<strong>${escapeHtml(project.name)}</strong><br/>${escapeHtml(project.county_name)}, ${escapeHtml(project.state_abbr)}<br/>Completed project audit · click to open`,
          ).addTo(map);
        };
        const hideProjectPopup = () => {
          map.getCanvas().style.cursor = "";
          popup.remove();
        };
        const openProject = (event: FeaturePointerEvent) => {
          const id = event.features?.[0]?.properties?.project_id;
          if (typeof id === "string" && /^prj_study_[a-z0-9_]+$/.test(id)) window.location.hash = `/project/${id}`;
        };
        for (const layerId of pointLayerIds) {
          map.on("mousemove", layerId, showProjectPopup);
          map.on("mouseleave", layerId, hideProjectPopup);
          map.on("click", layerId, openProject);
        }
        map.on("mousemove", "rejected-project-points", (event: FeaturePointerEvent) => {
          const project = event.features?.[0]?.properties;
          if (!project) return;
          map.getCanvas().style.cursor = "pointer";
          popup.setLngLat(event.lngLat).setHTML(`<strong>${escapeHtml(project.name)}</strong><br/>${escapeHtml(project.county_name)}, ${escapeHtml(project.state_abbr)}<br/>${escapeHtml(project.disposition)} ${escapeHtml(project.decision_date)} · ${escapeHtml(project.finality)}<br/>Evidence: ${escapeHtml(project.outcome_readiness).replaceAll("_", " ")}<br/>Location precision: ${escapeHtml(project.coordinate_precision)} · click to open`).addTo(map);
        });
        map.on("mouseleave", "rejected-project-points", hideProjectPopup);
        map.on("click", "rejected-project-points", (event: FeaturePointerEvent) => {
          const id = event.features?.[0]?.properties?.project_id;
          if (typeof id === "string" && /^prj_rejected_[a-z0-9_]+$/.test(id)) window.location.hash = `/rejected/${id}`;
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
    <div ref={containerRef} className="map" aria-label="Operating-project and rejected-proposal research map" />
    {message && <div className="map-message">{message}</div>}
    <div className="legend" aria-label="Map legend">
      <span className="legend-title">Project research cohorts</span>
      <div className="review-key">
        <span><i className="key-dot key-study" />operating project audit ({studyProjects.length})</span>
        <span><i className="key-dot key-rejected" />rejected / withdrawn ({rejectedProjects.length})</span>
        <span><i className="key-county key-operating-county" />operating county</span>
        <span><i className="key-county key-rejected-county" />rejected-proposal county</span>
        <span><i className="key-county key-both-county" />both cohorts</span>
      </div>
    </div>
  </div>;
}

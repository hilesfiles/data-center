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
        const [countiesResponse, facilitiesResponse, coverageResponse] = await Promise.all([
          fetch(`${base}data/v1/maps/counties.geojson`),
          fetch(`${base}data/v1/maps/facilities.geojson`),
          fetch(`${base}data/v1/counties/facility-source-coverage.json`),
        ]);
        if (!countiesResponse.ok || !facilitiesResponse.ok || !coverageResponse.ok) {
          throw new Error("A required map artifact could not be loaded.");
        }
        const counties = await countiesResponse.json();
        const facilities = await facilitiesResponse.json();
        const coverage = await coverageResponse.json();
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
            "circle-stroke-color": "#172a33",
            "circle-stroke-width": 1.25,
            "circle-opacity": 0.88,
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
          const footprint = typeof properties.footprint_sqft === "number"
            ? `<br/>Mapped footprint: ${properties.footprint_sqft.toLocaleString()} sq ft`
            : "";
          popup
            .setLngLat(event.lngLat)
            .setHTML(
              `<strong>${escapeHtml(properties.display_name)}</strong><br/>` +
                `IM3 ${layer} source record${operator}${footprint}`,
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
      </div>
    </div>
  );
}

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
        customAttribution: "County boundaries: U.S. Census Bureau, 2025 · Analytical records: fixtures",
      }),
      "bottom-right",
    );

    map.on("load", async () => {
      try {
        const base = import.meta.env.BASE_URL;
        const [countiesResponse, facilitiesResponse, summariesResponse] = await Promise.all([
          fetch(`${base}data/v1/maps/counties.geojson`),
          fetch(`${base}data/v1/maps/facilities.geojson`),
          fetch(`${base}data/v1/counties/index.json`),
        ]);
        if (!countiesResponse.ok || !facilitiesResponse.ok || !summariesResponse.ok) {
          throw new Error("A required map artifact could not be loaded.");
        }
        const counties = await countiesResponse.json();
        const facilities = await facilitiesResponse.json();
        const summaries = await summariesResponse.json();
        const summaryByFips = new globalThis.Map(
          summaries.map((summary: { county_fips: string; facility_exposure: { operating_count: number } }) => [
            summary.county_fips,
            summary,
          ]),
        );
        counties.features = counties.features.map(
          (feature: { properties: Record<string, unknown> }) => {
            const summary = summaryByFips.get(feature.properties.county_fips as string) as
              | { facility_exposure: { operating_count: number } }
              | undefined;
            return {
              ...feature,
              properties: {
                ...feature.properties,
                fixture_record_available: Boolean(summary),
                ...(summary
                  ? { operating_count: summary.facility_exposure.operating_count }
                  : {}),
              },
            };
          },
        );

        map.addSource("counties", { type: "geojson", data: counties, promoteId: "county_fips" });
        map.addSource("facilities", { type: "geojson", data: facilities });
        map.addLayer({
          id: "county-fill",
          type: "fill",
          source: "counties",
          paint: {
            "fill-color": [
              "case",
              ["get", "fixture_record_available"],
              [
                "interpolate",
                ["linear"],
                ["get", "operating_count"],
                0,
                "#b8d2cd",
                1,
                "#4c9892",
                4,
                "#17687a",
                10,
                "#0d3544",
              ],
              "#d8ddd5",
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
            "circle-radius": 7,
            "circle-color": "#ffb15c",
            "circle-stroke-color": "#172a33",
            "circle-stroke-width": 2,
          },
        });

        const popup = new Popup({ closeButton: false, closeOnClick: false, offset: 12 });
        map.on("mousemove", "county-fill", (event: FeaturePointerEvent) => {
          map.getCanvas().style.cursor = "pointer";
          const feature = event.features?.[0];
          if (!feature) return;
          const properties = feature.properties as Record<string, string | number | boolean>;
          const fixtureLine = properties.fixture_record_available
            ? `${properties.operating_count} fictional operating facilit${properties.operating_count === 1 ? "y" : "ies"}`
            : "No analytical fixture published";
          popup
            .setLngLat(event.lngLat)
            .setHTML(
              `<strong>${properties.county_name}, ${properties.state_abbr}</strong><br/>` +
                fixtureLine,
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
        <span className="legend-title">Fictional operating facilities</span>
        <div className="legend-ramp" aria-hidden="true" />
        <div className="legend-labels"><span>none published</span><span>1+</span></div>
      </div>
    </div>
  );
}

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
      center: [-77.53, 38.95],
      zoom: 8.4,
      attributionControl: false,
    });
    mapRef.current = map;
    map.addControl(new NavigationControl({ showCompass: false }), "bottom-right");
    map.addControl(
      new AttributionControl({
        compact: true,
        customAttribution: "Fixture geometry · DCCIO schema v1",
      }),
      "bottom-right",
    );

    map.on("load", async () => {
      try {
        const base = import.meta.env.BASE_URL;
        const [countiesResponse, facilitiesResponse] = await Promise.all([
          fetch(`${base}data/v1/maps/counties.geojson`),
          fetch(`${base}data/v1/maps/facilities.geojson`),
        ]);
        if (!countiesResponse.ok || !facilitiesResponse.ok) {
          throw new Error("A required map artifact could not be loaded.");
        }
        const counties = await countiesResponse.json();
        const facilities = await facilitiesResponse.json();

        map.addSource("counties", { type: "geojson", data: counties, promoteId: "county_fips" });
        map.addSource("facilities", { type: "geojson", data: facilities });
        map.addLayer({
          id: "county-fill",
          type: "fill",
          source: "counties",
          paint: {
            "fill-color": [
              "interpolate",
              ["linear"],
              ["coalesce", ["get", "operating_count"], 0],
              0,
              "#d8ddd5",
              1,
              "#64a6a0",
              4,
              "#17687a",
              10,
              "#0d3544",
            ],
            "fill-opacity": 0.92,
          },
        });
        map.addLayer({
          id: "county-outline",
          type: "line",
          source: "counties",
          paint: { "line-color": "#f7f6f1", "line-width": 1.5 },
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
          const properties = feature.properties as Record<string, string | number>;
          popup
            .setLngLat(event.lngLat)
            .setHTML(
              `<strong>${properties.county_name}, ${properties.state_abbr}</strong><br/>` +
                `${properties.operating_count} operating facilit${properties.operating_count === 1 ? "y" : "ies"}`,
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
        <span className="legend-title">Operating facilities</span>
        <div className="legend-ramp" aria-hidden="true" />
        <div className="legend-labels"><span>0</span><span>10+</span></div>
      </div>
    </div>
  );
}

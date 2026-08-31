#!/usr/bin/env python3
"""Acquire and publish the Census 2025 generalized county geography.

The adapter uses only the Python standard library. It reads the Census TIGERweb
ArcGIS REST endpoint as GeoJSON, filters to the 50 states and District of
Columbia, and writes only JSON-family artifacts suitable for GitHub Pages.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode
from urllib.request import Request, urlopen


ROOT = Path(__file__).resolve().parents[1]
LAYER_URL = (
    "https://tigerweb.geo.census.gov/arcgis/rest/services/"
    "Generalized_ACS2025/State_County/MapServer/12"
)
QUERY_URL = f"{LAYER_URL}/query"
OUT_FIELDS = (
    "GEOID,STATE,COUNTY,COUNTYNS,BASENAME,NAME,LSADC,FUNCSTAT,"
    "AREALAND,AREAWATER,CENTLAT,CENTLON,OBJECTID"
)
PAGE_SIZE = 1000
REFERENCE_VINTAGE = "2025-01-01"
PARSER_VERSION = "1.0.0"

STATE_ABBREVIATIONS = {
    "01": "AL", "02": "AK", "04": "AZ", "05": "AR", "06": "CA",
    "08": "CO", "09": "CT", "10": "DE", "11": "DC", "12": "FL",
    "13": "GA", "15": "HI", "16": "ID", "17": "IL", "18": "IN",
    "19": "IA", "20": "KS", "21": "KY", "22": "LA", "23": "ME",
    "24": "MD", "25": "MA", "26": "MI", "27": "MN", "28": "MS",
    "29": "MO", "30": "MT", "31": "NE", "32": "NV", "33": "NH",
    "34": "NJ", "35": "NM", "36": "NY", "37": "NC", "38": "ND",
    "39": "OH", "40": "OK", "41": "OR", "42": "PA", "44": "RI",
    "45": "SC", "46": "SD", "47": "TN", "48": "TX", "49": "UT",
    "50": "VT", "51": "VA", "53": "WA", "54": "WV", "55": "WI",
    "56": "WY",
}


def compact_json_bytes(value: Any) -> bytes:
    return (
        json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
        + "\n"
    ).encode("utf-8")


def write_json(path: Path, value: Any, *, compact: bool = False) -> bytes:
    payload = (
        compact_json_bytes(value)
        if compact
        else (json.dumps(value, ensure_ascii=False, indent=2) + "\n").encode("utf-8")
    )
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(payload)
    return payload


def fetch_page(offset: int) -> tuple[bytes, dict[str, Any], str, int, dict[str, str]]:
    params = {
        "f": "geojson",
        "where": "1=1",
        "outFields": OUT_FIELDS,
        "returnGeometry": "true",
        "outSR": "4326",
        "geometryPrecision": "5",
        "orderByFields": "GEOID",
        "resultOffset": str(offset),
        "resultRecordCount": str(PAGE_SIZE),
    }
    request_url = f"{QUERY_URL}?{urlencode(params)}"
    request = Request(
        request_url,
        headers={"User-Agent": "DCCIO-county-adapter/1.0 (+https://github.com/)"},
    )
    try:
        with urlopen(request, timeout=120) as response:
            payload = response.read()
            headers = {
                "etag": response.headers.get("ETag", ""),
                "last_modified": response.headers.get("Last-Modified", ""),
            }
            status = response.status
    except (HTTPError, URLError, TimeoutError) as exc:
        raise RuntimeError(f"Census TIGERweb request failed at offset {offset}: {exc}") from exc

    try:
        document = json.loads(payload)
    except json.JSONDecodeError as exc:
        raise RuntimeError(f"Census returned invalid JSON at offset {offset}") from exc
    if document.get("error"):
        raise RuntimeError(f"Census query error at offset {offset}: {document['error']}")
    if document.get("type") != "FeatureCollection":
        raise RuntimeError(f"Census response at offset {offset} is not GeoJSON")
    return payload, document, request_url, status, headers


def acquire() -> tuple[list[dict[str, Any]], str, str, int, dict[str, str]]:
    features: list[dict[str, Any]] = []
    source_digest = hashlib.sha256()
    first_request_url = ""
    last_status = 0
    response_headers: dict[str, str] = {}

    for offset in range(0, 100_000, PAGE_SIZE):
        payload, page, request_url, status, headers = fetch_page(offset)
        if not first_request_url:
            first_request_url = request_url
            response_headers = headers
        source_digest.update(payload)
        source_digest.update(b"\n")
        last_status = status
        page_features = page.get("features", [])
        features.extend(page_features)
        if len(page_features) < PAGE_SIZE:
            break
    else:
        raise RuntimeError("Census pagination exceeded the adapter safety limit")

    return features, source_digest.hexdigest(), first_request_url, last_status, response_headers


def normalize(features: list[dict[str, Any]], generated_at: str) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    map_features: list[dict[str, Any]] = []
    geography_records: list[dict[str, Any]] = []
    seen_fips: set[str] = set()

    for feature in features:
        source = feature.get("properties", {})
        state_fips = str(source.get("STATE", "")).zfill(2)
        if state_fips not in STATE_ABBREVIATIONS:
            continue
        county_fips = str(source.get("GEOID", "")).zfill(5)
        if len(county_fips) != 5 or not county_fips.isdigit():
            raise RuntimeError(f"Invalid county GEOID from Census: {county_fips!r}")
        if county_fips in seen_fips:
            raise RuntimeError(f"Duplicate county GEOID from Census: {county_fips}")
        seen_fips.add(county_fips)
        geometry = feature.get("geometry")
        if not isinstance(geometry, dict) or geometry.get("type") not in {"Polygon", "MultiPolygon"}:
            raise RuntimeError(f"County {county_fips} is missing polygon geometry")

        county_name = str(source.get("NAME") or source.get("BASENAME") or "").strip()
        state_abbr = STATE_ABBREVIATIONS[state_fips]
        map_features.append(
            {
                "type": "Feature",
                "id": county_fips,
                "properties": {
                    "county_fips": county_fips,
                    "county_name": county_name,
                    "state_fips": state_fips,
                    "state_abbr": state_abbr,
                    "county_ns": str(source.get("COUNTYNS") or ""),
                    "legal_statistical_area_description": str(source.get("LSADC") or ""),
                    "functional_status": str(source.get("FUNCSTAT") or ""),
                    "land_area_m2": int(source.get("AREALAND") or 0),
                    "water_area_m2": int(source.get("AREAWATER") or 0),
                    "centroid_latitude": float(source["CENTLAT"]),
                    "centroid_longitude": float(source["CENTLON"]),
                    "reference_vintage": REFERENCE_VINTAGE,
                    "source_id": "src_census_boundaries",
                },
                "geometry": geometry,
            }
        )
        geography_records.append(
            {
                "schema_version": "1.0.0",
                "geography_id": county_fips,
                "geography_type": "county",
                "name": county_name,
                "county_fips": county_fips,
                "state_fips": state_fips,
                "state_abbr": state_abbr,
                "parent_geography_ids": [state_fips, "US"],
                "effective_interval": {
                    "start": {"date": REFERENCE_VINTAGE, "precision": "day"},
                    "ongoing": True,
                },
                "reference_vintage": REFERENCE_VINTAGE,
                "geometry_artifact_path": "site/public/data/v1/maps/counties.geojson",
                "external_identifiers": [
                    {
                        "namespace": "census_geoid",
                        "value": county_fips,
                        "source_id": "src_census_boundaries",
                    }
                ],
                "created_at": generated_at,
                "updated_at": generated_at,
                "record_status": "active",
            }
        )

    map_features.sort(key=lambda row: row["properties"]["county_fips"])
    geography_records.sort(key=lambda row: row["county_fips"])
    if len(map_features) < 3100:
        raise RuntimeError(f"Expected a national county layer; received {len(map_features)} records")
    states_present = {row["properties"]["state_fips"] for row in map_features}
    if states_present != set(STATE_ABBREVIATIONS):
        missing = sorted(set(STATE_ABBREVIATIONS) - states_present)
        raise RuntimeError(f"National county layer is missing state FIPS: {missing}")
    return map_features, geography_records


def build_artifacts(output_root: Path) -> dict[str, Any]:
    generated_at = datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")
    source_features, source_sha, request_url, status, headers = acquire()
    map_features, geography_records = normalize(source_features, generated_at)

    map_document = {
        "type": "FeatureCollection",
        "name": "census_2025_counties_5m_50_states_and_dc",
        "metadata": {
            "schema_version": "1.0.0",
            "source": "U.S. Census Bureau TIGERweb",
            "source_layer": "Generalized_ACS2025/State_County/MapServer/12",
            "reference_vintage": REFERENCE_VINTAGE,
            "geography_scope": "50 states and District of Columbia",
            "generated_at": generated_at,
            "record_count": len(map_features),
        },
        "features": map_features,
    }
    map_path = output_root / "site" / "public" / "data" / "v1" / "maps" / "counties.geojson"
    map_payload = write_json(map_path, map_document, compact=True)
    map_sha = hashlib.sha256(map_payload).hexdigest()

    geography_path = output_root / "data" / "silver" / "geography" / "counties-2025.json"
    geography_document = {
        "schema_version": "1.0.0",
        "artifact_type": "geography_reference_collection",
        "artifact_version": "2025.1",
        "generated_at": generated_at,
        "data_vintage": REFERENCE_VINTAGE,
        "record_schema": "https://dccio.org/schemas/v1/geography-reference.schema.json",
        "record_count": len(geography_records),
        "records": geography_records,
    }
    geography_payload = write_json(geography_path, geography_document, compact=True)

    manifest_path = output_root / "data" / "raw" / "census-tigerweb" / "2025-counties-5m.acquisition.json"
    manifest = {
        "schema_version": "1.0.0",
        "manifest_id": "acq_census_counties_2025",
        "source_id": "src_census_boundaries",
        "source_url": LAYER_URL,
        "request_url": request_url,
        "retrieved_at": generated_at,
        "http_status": status,
        "sha256": source_sha,
        "local_path": "site/public/data/v1/maps/counties.geojson",
        "license": "U.S. government data; source: U.S. Census Bureau",
        "parser_version": PARSER_VERSION,
        "attempt": 1,
        "created_at": generated_at,
        "updated_at": generated_at,
        "record_status": "active",
    }
    if headers.get("etag"):
        manifest["etag"] = headers["etag"]
    if headers.get("last_modified"):
        manifest["last_modified"] = headers["last_modified"]
    write_json(manifest_path, manifest)

    dataset_manifest = {
        "schema_version": "1.0.0",
        "dataset_id": "geo_counties_2025_5m",
        "artifact_type": "county_boundary_geojson",
        "artifact_version": "2025.1",
        "generated_at": generated_at,
        "data_vintage": REFERENCE_VINTAGE,
        "record_schema": "https://dccio.org/schemas/v1/geography-reference.schema.json",
        "format": "geojson",
        "parts": [
            {
                "path": "site/public/data/v1/maps/counties.geojson",
                "sha256": map_sha,
                "byte_size": len(map_payload),
                "record_count": len(map_features),
            }
        ],
        "record_count": len(map_features),
        "license_metadata": {
            "license": "U.S. government data",
            "redistribution_status": "allowed",
            "attribution": "Source: U.S. Census Bureau",
        },
    }
    write_json(output_root / "data" / "silver" / "geography" / "counties-2025.manifest.json", dataset_manifest)

    return {
        "record_count": len(map_features),
        "map_sha256": map_sha,
        "map_bytes": len(map_payload),
        "geography_bytes": len(geography_payload),
    }


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--output-root",
        type=Path,
        default=ROOT,
        help="repository root for generated JSON artifacts",
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    try:
        result = build_artifacts(args.output_root.resolve())
    except RuntimeError as exc:
        print(f"Census county acquisition failed: {exc}", file=sys.stderr)
        return 1
    print(
        "Census county acquisition passed: "
        f"{result['record_count']} counties, {result['map_bytes']} GeoJSON bytes, "
        f"sha256 {result['map_sha256']}."
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())

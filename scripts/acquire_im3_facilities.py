#!/usr/bin/env python3
"""Acquire and normalize the IM3 v2026.02.09 facility seed as JSON.

The pinned GeoPackage is a temporary transport input only. The adapter converts its
three source layers to JSON, creates provisional canonical entities with evidence
lineage, validates county assignments against the published Census geography, and
publishes compact static JSON/GeoJSON for GitHub Pages.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import sqlite3
import struct
import sys
import tempfile
from collections import defaultdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, BinaryIO
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen


ROOT = Path(__file__).resolve().parents[1]
RELEASE_VERSION = "2026.02.09"
RELEASE_DATE = "2026-02-09"
PARSER_VERSION = "1.0.0"
SOURCE_ID = "src_im3_atlas_20260209"
ARTIFACT_ID = "art_im3_gpkg_20260209"
ACQUISITION_ID = "acq_im3_atlas_20260209"
DOI_URL = "https://doi.org/10.57931/3017294"
REPOSITORY_COMMIT = "74ab37d5b9d200400a01639f9ffc3c3a8b716314"
DOWNLOAD_URL = (
    "https://raw.githubusercontent.com/IMMM-SFA/datacenter-atlas/"
    f"{REPOSITORY_COMMIT}/data_center_database/im3_us_data_center_locations.gpkg"
)
EXPECTED_SHA256 = "1c0d8c206eb2070785e594784fda90f615e6ed7fd9646d67e1a9de237b8cc9f4"
EXPECTED_BYTES = 843_776
SOURCE_LAYERS = ("point", "building", "campus")
ATTRIBUTION = "© OpenStreetMap contributors; IM3 Open Source Data Center Atlas (PNNL/DOE)"


def json_bytes(value: Any, *, compact: bool) -> bytes:
    if compact:
        text = json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
    else:
        text = json.dumps(value, ensure_ascii=False, indent=2)
    return (text + "\n").encode("utf-8")


def write_json(path: Path, value: Any, *, compact: bool = False) -> bytes:
    payload = json_bytes(value, compact=compact)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(payload)
    return payload


def download_to_temp() -> tuple[Path, dict[str, Any]]:
    request = Request(
        DOWNLOAD_URL,
        headers={"User-Agent": "DCCIO-IM3-adapter/1.0 (+https://github.com/)"},
    )
    temporary = tempfile.NamedTemporaryFile(prefix="dccio-im3-", suffix=".gpkg", delete=False)
    temporary_path = Path(temporary.name)
    digest = hashlib.sha256()
    byte_size = 0
    try:
        with temporary as output, urlopen(request, timeout=120) as response:
            while chunk := response.read(1024 * 1024):
                output.write(chunk)
                digest.update(chunk)
                byte_size += len(chunk)
            metadata = {
                "http_status": response.status,
                "etag": response.headers.get("ETag"),
                "last_modified": response.headers.get("Last-Modified"),
                "content_type": response.headers.get("Content-Type", "application/geopackage+sqlite3"),
                "sha256": digest.hexdigest(),
                "byte_size": byte_size,
            }
    except (HTTPError, URLError, TimeoutError) as exc:
        temporary_path.unlink(missing_ok=True)
        raise RuntimeError(f"IM3 download failed: {exc}") from exc

    if metadata["sha256"] != EXPECTED_SHA256 or byte_size != EXPECTED_BYTES:
        temporary_path.unlink(missing_ok=True)
        raise RuntimeError(
            "Pinned IM3 artifact does not match the expected SHA-256 and byte size; "
            "review the upstream revision before ingesting it"
        )
    return temporary_path, metadata


def _read_uint32(data: memoryview, offset: int, endian: str) -> tuple[int, int]:
    return struct.unpack_from(f"{endian}I", data, offset)[0], offset + 4


def _read_coordinate(
    data: memoryview, offset: int, endian: str, dimensions: int
) -> tuple[list[float], int]:
    values = struct.unpack_from(f"{endian}{'d' * dimensions}", data, offset)
    return [round(values[0], 7), round(values[1], 7)], offset + 8 * dimensions


def parse_wkb(data: memoryview, offset: int = 0) -> tuple[dict[str, Any], int]:
    byte_order = data[offset]
    endian = "<" if byte_order == 1 else ">"
    type_code, offset = _read_uint32(data, offset + 1, endian)

    has_z = bool(type_code & 0x80000000)
    has_m = bool(type_code & 0x40000000)
    base_type = type_code & 0x0FFFFFFF
    if base_type >= 3000:
        has_z = True
        has_m = True
        base_type -= 3000
    elif base_type >= 2000:
        has_m = True
        base_type -= 2000
    elif base_type >= 1000:
        has_z = True
        base_type -= 1000
    dimensions = 2 + int(has_z) + int(has_m)

    if base_type == 1:
        coordinate, offset = _read_coordinate(data, offset, endian, dimensions)
        return {"type": "Point", "coordinates": coordinate}, offset
    if base_type == 3:
        ring_count, offset = _read_uint32(data, offset, endian)
        rings: list[list[list[float]]] = []
        for _ in range(ring_count):
            point_count, offset = _read_uint32(data, offset, endian)
            ring: list[list[float]] = []
            for _ in range(point_count):
                coordinate, offset = _read_coordinate(data, offset, endian, dimensions)
                ring.append(coordinate)
            rings.append(ring)
        return {"type": "Polygon", "coordinates": rings}, offset
    if base_type == 6:
        polygon_count, offset = _read_uint32(data, offset, endian)
        polygons: list[Any] = []
        for _ in range(polygon_count):
            polygon, offset = parse_wkb(data, offset)
            if polygon["type"] != "Polygon":
                raise RuntimeError("IM3 MultiPolygon contains a non-polygon geometry")
            polygons.append(polygon["coordinates"])
        return {"type": "MultiPolygon", "coordinates": polygons}, offset
    raise RuntimeError(f"Unsupported GeoPackage WKB geometry type {base_type}")


def decode_geopackage_geometry(blob: bytes) -> dict[str, Any]:
    data = memoryview(blob)
    if len(data) < 9 or bytes(data[:2]) != b"GP":
        raise RuntimeError("Invalid GeoPackage geometry header")
    flags = data[3]
    envelope_indicator = (flags >> 1) & 0b111
    envelope_dimensions = {0: 0, 1: 4, 2: 6, 3: 6, 4: 8}.get(envelope_indicator)
    if envelope_dimensions is None:
        raise RuntimeError(f"Unsupported GeoPackage envelope indicator {envelope_indicator}")
    geometry_offset = 8 + envelope_dimensions * 8
    geometry, _ = parse_wkb(data, geometry_offset)
    return geometry


def geometry_bbox(geometry: dict[str, Any]) -> tuple[float, float, float, float]:
    coordinates = geometry["coordinates"]
    points: list[list[float]] = []

    def collect(value: Any) -> None:
        if isinstance(value, list) and len(value) >= 2 and all(
            isinstance(item, (int, float)) for item in value[:2]
        ):
            points.append(value)
        elif isinstance(value, list):
            for item in value:
                collect(item)

    collect(coordinates)
    return (
        min(point[0] for point in points),
        min(point[1] for point in points),
        max(point[0] for point in points),
        max(point[1] for point in points),
    )


def point_in_ring(longitude: float, latitude: float, ring: list[list[float]]) -> bool:
    inside = False
    previous = ring[-1]
    for current in ring:
        x1, y1 = previous[:2]
        x2, y2 = current[:2]
        if ((y1 > latitude) != (y2 > latitude)) and (
            longitude < (x2 - x1) * (latitude - y1) / (y2 - y1) + x1
        ):
            inside = not inside
        previous = current
    return inside


def point_in_geometry(longitude: float, latitude: float, geometry: dict[str, Any]) -> bool:
    polygons = (
        [geometry["coordinates"]]
        if geometry["type"] == "Polygon"
        else geometry["coordinates"]
    )
    for polygon in polygons:
        if not polygon or not point_in_ring(longitude, latitude, polygon[0]):
            continue
        if not any(point_in_ring(longitude, latitude, hole) for hole in polygon[1:]):
            return True
    return False


def load_county_reference(output_root: Path) -> tuple[dict[str, dict[str, Any]], dict[str, list[dict[str, Any]]]]:
    path = output_root / "site" / "public" / "data" / "v1" / "maps" / "counties.geojson"
    document = json.loads(path.read_text(encoding="utf-8"))
    by_fips: dict[str, dict[str, Any]] = {}
    by_state: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for feature in document["features"]:
        properties = feature["properties"]
        item = {
            "properties": properties,
            "geometry": feature["geometry"],
            "bbox": geometry_bbox(feature["geometry"]),
        }
        by_fips[properties["county_fips"]] = item
        by_state[properties["state_fips"]].append(item)
    return by_fips, by_state


def centroid_county(
    longitude: float,
    latitude: float,
    state_fips: str,
    counties_by_state: dict[str, list[dict[str, Any]]],
) -> str | None:
    for county in counties_by_state.get(state_fips, []):
        min_x, min_y, max_x, max_y = county["bbox"]
        if min_x <= longitude <= max_x and min_y <= latitude <= max_y:
            if point_in_geometry(longitude, latitude, county["geometry"]):
                return county["properties"]["county_fips"]
    return None


def read_source_rows(
    package_path: Path,
    generated_at: str,
    county_reference: dict[str, dict[str, Any]],
) -> list[dict[str, Any]]:
    connection = sqlite3.connect(f"file:{package_path.as_posix()}?mode=ro", uri=True)
    connection.row_factory = sqlite3.Row
    records: list[dict[str, Any]] = []
    try:
        for layer in SOURCE_LAYERS:
            rows = connection.execute(
                f"SELECT geom, id, state, state_abb, state_id, county, county_id, "
                f"operator, ref, name, sqft, lon, lat, type FROM {layer} ORDER BY id, county_id"
            )
            for row in rows:
                state_fips = str(row["state_id"]).zfill(2)
                county_fips = state_fips + str(row["county_id"]).zfill(3)
                if row["type"] != layer:
                    raise RuntimeError(f"IM3 layer/type mismatch for {layer}:{row['id']}")
                geometry = decode_geopackage_geometry(row["geom"])
                records.append(
                    {
                        "schema_version": "1.0.0",
                        "source_id": SOURCE_ID,
                        "source_artifact_id": ARTIFACT_ID,
                        "source_layer": layer,
                        "source_record_id": str(row["id"]),
                        "source_row_id": f"{layer}:{row['id']}:{county_fips}",
                        "state_name": str(row["state"]),
                        "state_fips": state_fips,
                        "state_abbr": str(row["state_abb"]),
                        "county_fips": county_fips,
                        "county_name": str(row["county"]),
                        "name": row["name"],
                        "operator": row["operator"],
                        "source_ref": row["ref"],
                        "footprint_sqft": row["sqft"],
                        "latitude": row["lat"],
                        "longitude": row["lon"],
                        "geometry": geometry,
                        "release_vintage": RELEASE_VERSION,
                        "in_public_scope": county_fips in county_reference,
                        "created_at": generated_at,
                    }
                )
    finally:
        connection.close()
    return records


def entity_id(layer: str, source_record_id: str) -> str:
    prefix = "cam" if layer == "campus" else "fac"
    return f"{prefix}_im3_{layer}_{source_record_id}"


def entity_name(record: dict[str, Any]) -> str:
    return (
        record.get("name")
        or record.get("operator")
        or f"Unnamed IM3 {record['source_layer']} {record['source_record_id']}"
    )


def group_in_scope_rows(records: list[dict[str, Any]]) -> list[list[dict[str, Any]]]:
    grouped: dict[tuple[str, str], list[dict[str, Any]]] = defaultdict(list)
    for record in records:
        if record["in_public_scope"]:
            grouped[(record["source_layer"], record["source_record_id"])].append(record)
    return [grouped[key] for key in sorted(grouped)]


def canonical_county_assignment(
    group: list[dict[str, Any]],
    counties_by_state: dict[str, list[dict[str, Any]]],
) -> tuple[list[str], list[str], str | None, str, float]:
    first = group[0]
    source_reported = sorted({row["county_fips"] for row in group})
    centroid_fips = centroid_county(
        first["longitude"], first["latitude"], first["state_fips"], counties_by_state
    )
    if len(source_reported) > 1:
        return source_reported, source_reported, centroid_fips, "geometry_intersection", 0.85
    if centroid_fips:
        return [centroid_fips], source_reported, centroid_fips, "point_in_polygon", 0.95
    return source_reported, source_reported, None, "source_reported", 0.6


def make_source_records(generated_at: str, acquisition: dict[str, Any]) -> tuple[dict[str, Any], dict[str, Any]]:
    source = {
        "schema_version": "1.0.0",
        "source_id": SOURCE_ID,
        "source_type": "federal_dataset",
        "publisher": "Pacific Northwest National Laboratory",
        "agency": "U.S. Department of Energy, Office of Science",
        "jurisdiction": "United States",
        "title": f"IM3 Open Source Data Center Atlas (v{RELEASE_VERSION})",
        "url": DOI_URL,
        "publication_date": {"date": RELEASE_DATE, "precision": "day"},
        "language": "en",
        "license": "Open Database License 1.0 (ODbL); OSM-derived",
        "copyright_policy": "redistributable",
        "source_quality_prior": 0.75,
        "created_at": generated_at,
        "updated_at": generated_at,
        "record_status": "active",
    }
    artifact = {
        "schema_version": "1.0.0",
        "artifact_id": ARTIFACT_ID,
        "source_id": SOURCE_ID,
        "request_url": DOWNLOAD_URL,
        "archive_url": DOI_URL,
        "retrieved_at": generated_at,
        "content_type": acquisition["content_type"],
        "http_status": acquisition["http_status"],
        "sha256": acquisition["sha256"],
        "byte_size": acquisition["byte_size"],
        "storage_policy": "not_retained",
        "parser_version": PARSER_VERSION,
        "created_at": generated_at,
        "updated_at": generated_at,
        "record_status": "active",
    }
    if acquisition.get("etag"):
        artifact["etag"] = acquisition["etag"]
    if acquisition.get("last_modified"):
        artifact["last_modified"] = acquisition["last_modified"]
    return source, artifact


def make_canonical_collections(
    groups: list[list[dict[str, Any]]],
    generated_at: str,
    county_reference: dict[str, dict[str, Any]],
    counties_by_state: dict[str, list[dict[str, Any]]],
) -> tuple[dict[str, list[dict[str, Any]]], dict[str, Any]]:
    facilities: list[dict[str, Any]] = []
    campuses: list[dict[str, Any]] = []
    observations: list[dict[str, Any]] = []
    claims: list[dict[str, Any]] = []
    resolutions: list[dict[str, Any]] = []
    centroid_mismatches: list[dict[str, Any]] = []
    county_name_mismatches: list[dict[str, Any]] = []

    for group in groups:
        first = group[0]
        layer = first["source_layer"]
        source_record_id = first["source_record_id"]
        canonical_id = entity_id(layer, source_record_id)
        (
            assigned_fips,
            source_reported_fips,
            centroid_fips,
            assignment_method,
            assignment_confidence,
        ) = canonical_county_assignment(
            group, counties_by_state
        )
        geography_consistent = centroid_fips in source_reported_fips
        if not geography_consistent:
            centroid_mismatches.append(
                {
                    "source_record": f"{layer}:{source_record_id}",
                    "reported_counties": source_reported_fips,
                    "centroid_county_fips": centroid_fips,
                    "canonical_counties": assigned_fips,
                }
            )
        for row in group:
            reference_name = county_reference[row["county_fips"]]["properties"]["county_name"]
            if row["county_name"] != reference_name:
                county_name_mismatches.append(
                    {
                        "source_row_id": row["source_row_id"],
                        "source_county_name": row["county_name"],
                        "census_county_name": reference_name,
                    }
                )

        quality_components = {
            "source_location_present": 1.0,
            "source_name_present": 1.0 if first.get("name") else 0.0,
            "source_operator_present": 1.0 if first.get("operator") else 0.0,
            "geography_consistency": 1.0 if geography_consistent else 0.0,
        }
        quality_score = round(sum(quality_components.values()) * 25, 1)
        geography_assignments = [
            {
                "geography_type": "county",
                "geography_id": county_fips,
                "assignment_method": assignment_method,
                "confidence": assignment_confidence,
            }
            for county_fips in assigned_fips
        ]
        external_identifiers = [
            {
                "namespace": "im3_atlas_record",
                "value": f"{layer}:{source_record_id}",
                "source_id": SOURCE_ID,
            }
        ]
        common = {
            "schema_version": "1.0.0",
            "canonical_name": entity_name(first),
            "coordinates": {
                "latitude": first["latitude"],
                "longitude": first["longitude"],
                "precision": {"building": "rooftop", "campus": "campus"}.get(layer, "unknown"),
            },
            "geography_assignments": geography_assignments,
            "external_identifiers": external_identifiers,
            "data_quality": {
                "score": quality_score,
                "grade": "P",
                "method_version": "im3_seed_v1",
                "component_scores": quality_components,
            },
            "created_at": generated_at,
            "updated_at": generated_at,
            "record_status": "provisional",
        }
        if layer == "campus":
            campuses.append(
                {
                    **common,
                    "campus_id": canonical_id,
                    "geometry": first["geometry"],
                }
            )
            subject_type = "campus"
        else:
            facilities.append(
                {
                    **common,
                    "facility_id": canonical_id,
                    "facility_type": "building" if layer == "building" else "unknown",
                    "current_status": "unknown",
                }
            )
            subject_type = "facility"

        observation: dict[str, Any] = {
            "schema_version": "1.0.0",
            "observation_id": f"obs_im3_{layer}_{source_record_id}_sqft",
            "metric_code": "facility.area.building_sqft_observed",
            "subject": {"subject_type": subject_type, "subject_id": canonical_id},
            "period": {"date": RELEASE_DATE, "precision": "day"},
            "source_ids": [SOURCE_ID],
            "release_vintage": RELEASE_VERSION,
            "revision_number": 0,
            "created_at": generated_at,
            "updated_at": generated_at,
            "record_status": "provisional",
        }
        if first.get("footprint_sqft") is None:
            observation.update(
                {"value_status": "not_available", "missingness_reason": "not_available"}
            )
        else:
            observation.update(
                {
                    "value_status": "observed",
                    "value": {
                        "type": "quantity",
                        "value": first["footprint_sqft"],
                        "unit": "square_feet",
                    },
                }
            )
        observations.append(observation)

        normalized_record = {
            "source_layer": layer,
            "source_record_id": source_record_id,
            "name": first.get("name"),
            "operator": first.get("operator"),
            "source_ref": first.get("source_ref"),
            "footprint_sqft": first.get("footprint_sqft"),
            "latitude": first["latitude"],
            "longitude": first["longitude"],
            "county_fipses": assigned_fips,
            "source_reported_county_fipses": source_reported_fips,
            "centroid_county_fips": centroid_fips,
            "geometry_type": first["geometry"]["type"],
        }
        claim_id = f"clm_im3_{layer}_{source_record_id}_source"
        claims.append(
            {
                "schema_version": "1.0.0",
                "claim_id": claim_id,
                "source_id": SOURCE_ID,
                "source_artifact_id": ARTIFACT_ID,
                "subject": {"entity_type": subject_type, "entity_id": canonical_id},
                "attribute_path": "source_record",
                "raw_value": {"type": "json", "value": normalized_record},
                "normalized_value": {"type": "json", "value": normalized_record},
                "claim_date": {"date": RELEASE_DATE, "precision": "day"},
                "extraction_method": "imported",
                "extractor_version": PARSER_VERSION,
                "source_quality_score": 0.75,
                "claim_confidence": 0.8,
                "review_status": "unreviewed",
                "notes": "OSM-derived IM3 source inventory record; not independently lifecycle-verified.",
                "created_at": generated_at,
                "updated_at": generated_at,
                "record_status": "provisional",
            }
        )
        resolutions.append(
            {
                "schema_version": "1.0.0",
                "resolution_id": f"res_im3_{layer}_{source_record_id}_source",
                "subject": {"entity_type": subject_type, "entity_id": canonical_id},
                "attribute_path": "source_record",
                "resolution_status": "provisional",
                "resolved_value": {"type": "json", "value": normalized_record},
                "claim_refs": {
                    "winning": claim_id,
                    "supporting": [claim_id],
                    "conflicting": [],
                },
                "resolution_method": "deterministic_transform",
                "resolution_confidence": 0.8,
                "rationale": "Deterministic import preserves the source record without asserting reviewed canonical identity or operating status.",
                "model_version": PARSER_VERSION,
                "resolved_at": generated_at,
                "created_at": generated_at,
                "updated_at": generated_at,
                "record_status": "provisional",
            }
        )

    return (
        {
            "facility": facilities,
            "campus": campuses,
            "observation": observations,
            "claim": claims,
            "claim_resolution": resolutions,
        },
        {
            "centroid_county_mismatch_count": len(centroid_mismatches),
            "centroid_county_mismatches": centroid_mismatches,
            "county_name_mismatch_count": len(county_name_mismatches),
            "county_name_mismatches": county_name_mismatches,
        },
    )


def make_public_data(
    groups: list[list[dict[str, Any]]],
    generated_at: str,
    county_reference: dict[str, dict[str, Any]],
    counties_by_state: dict[str, list[dict[str, Any]]],
) -> tuple[dict[str, Any], list[dict[str, Any]], list[dict[str, Any]]]:
    features: list[dict[str, Any]] = []
    facility_index: list[dict[str, Any]] = []
    coverage_by_fips: dict[str, dict[str, Any]] = {}
    for county_fips, county in sorted(county_reference.items()):
        properties = county["properties"]
        coverage_by_fips[county_fips] = {
            "schema_version": "1.0.0",
            "county_fips": county_fips,
            "county_name": properties["county_name"],
            "state_abbr": properties["state_abbr"],
            "source_id": SOURCE_ID,
            "release_vintage": RELEASE_VERSION,
            "source_record_count": 0,
            "point_record_count": 0,
            "building_record_count": 0,
            "campus_record_count": 0,
            "named_record_count": 0,
            "operator_named_record_count": 0,
            "observed_footprint_sqft": 0,
            "cross_county_source_record_count": 0,
            "coverage_status": "no_source_record",
            "generated_at": generated_at,
        }

    for group in groups:
        first = group[0]
        layer = first["source_layer"]
        source_record_id = first["source_record_id"]
        canonical_id = entity_id(layer, source_record_id)
        (
            county_fipses,
            source_reported_fipses,
            _,
            assignment_method,
            _,
        ) = canonical_county_assignment(group, counties_by_state)
        properties = {
            "entity_id": canonical_id,
            "entity_type": "campus" if layer == "campus" else "facility",
            "source_layer": layer,
            "source_record_id": source_record_id,
            "display_name": entity_name(first),
            "source_name": first.get("name"),
            "source_operator": first.get("operator"),
            "source_ref": first.get("source_ref"),
            "footprint_sqft": first.get("footprint_sqft"),
            "county_fipses": county_fipses,
            "primary_county_fips": county_fipses[0],
            "source_reported_county_fipses": source_reported_fipses,
            "geography_assignment_method": assignment_method,
            "data_status": "provisional_source_record",
            "release_vintage": RELEASE_VERSION,
        }
        features.append(
            {
                "type": "Feature",
                "id": canonical_id,
                "properties": properties,
                "geometry": {
                    "type": "Point",
                    "coordinates": [first["longitude"], first["latitude"]],
                },
            }
        )
        facility_index.append(
            {
                **properties,
                "latitude": first["latitude"],
                "longitude": first["longitude"],
            }
        )
        for county_fips in county_fipses:
            coverage = coverage_by_fips[county_fips]
            coverage["source_record_count"] += 1
            coverage[f"{layer}_record_count"] += 1
            coverage["named_record_count"] += int(bool(first.get("name")))
            coverage["operator_named_record_count"] += int(bool(first.get("operator")))
            if len(county_fipses) > 1:
                coverage["cross_county_source_record_count"] += 1
            elif first.get("footprint_sqft") is not None:
                coverage["observed_footprint_sqft"] += first["footprint_sqft"]
            coverage["coverage_status"] = "source_records_present"

    features.sort(key=lambda feature: feature["id"])
    facility_index.sort(key=lambda record: record["entity_id"])
    coverage = [coverage_by_fips[fips] for fips in sorted(coverage_by_fips)]
    geojson = {
        "type": "FeatureCollection",
        "name": "im3_2026_02_09_provisional_source_records",
        "metadata": {
            "schema_version": "1.0.0",
            "source_id": SOURCE_ID,
            "source": "IM3 Open Source Data Center Atlas",
            "release_vintage": RELEASE_VERSION,
            "record_count": len(features),
            "interpretation": "OSM-derived source records; not a deduplicated or lifecycle-verified operating facility inventory.",
            "license": "ODbL 1.0",
            "attribution": ATTRIBUTION,
            "generated_at": generated_at,
        },
        "features": features,
    }
    return geojson, facility_index, coverage


def build_artifacts(output_root: Path) -> dict[str, Any]:
    generated_at = (
        datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")
    )
    county_reference, counties_by_state = load_county_reference(output_root)
    package_path, acquisition = download_to_temp()
    try:
        source_rows = read_source_rows(package_path, generated_at, county_reference)
    finally:
        package_path.unlink(missing_ok=True)

    groups = group_in_scope_rows(source_rows)
    source, artifact = make_source_records(generated_at, acquisition)
    collections, diagnostics = make_canonical_collections(
        groups, generated_at, county_reference, counties_by_state
    )
    collections["source"] = [source]
    collections["source_artifact"] = [artifact]
    ordered_collections = {
        key: collections[key]
        for key in (
            "source",
            "source_artifact",
            "campus",
            "facility",
            "claim",
            "claim_resolution",
            "observation",
        )
    }

    excluded_rows = [row for row in source_rows if not row["in_public_scope"]]
    bronze_document = {
        "schema_version": "1.0.0",
        "artifact_type": "im3_facility_seed_source_rows",
        "artifact_version": RELEASE_VERSION,
        "generated_at": generated_at,
        "source_artifact_id": ARTIFACT_ID,
        "record_schema": "https://dccio.org/schemas/v1/facility-seed-source-record.schema.json",
        "record_count": len(source_rows),
        "in_scope_row_count": len(source_rows) - len(excluded_rows),
        "excluded_from_public_scope_count": len(excluded_rows),
        "records": source_rows,
    }
    bronze_path = output_root / "data" / "bronze" / "im3-atlas" / f"{RELEASE_VERSION}-source-rows.json"
    bronze_payload = write_json(bronze_path, bronze_document, compact=True)

    silver_document = {
        "schema_version": "1.0.0",
        "artifact_type": "im3_provisional_facility_seed",
        "artifact_version": RELEASE_VERSION,
        "generated_at": generated_at,
        "record_count": sum(len(records) for records in ordered_collections.values()),
        "collections": ordered_collections,
    }
    silver_path = output_root / "data" / "silver" / "infrastructure" / f"im3-{RELEASE_VERSION}.json"
    silver_payload = write_json(silver_path, silver_document, compact=True)

    public_geojson, facility_index, coverage = make_public_data(
        groups, generated_at, county_reference, counties_by_state
    )
    facilities_map_path = output_root / "site" / "public" / "data" / "v1" / "maps" / "facilities.geojson"
    map_payload = write_json(facilities_map_path, public_geojson, compact=True)
    index_path = output_root / "site" / "public" / "data" / "v1" / "facilities" / "index.json"
    index_payload = write_json(index_path, facility_index, compact=True)
    coverage_path = output_root / "site" / "public" / "data" / "v1" / "counties" / "facility-source-coverage.json"
    coverage_payload = write_json(coverage_path, coverage, compact=True)

    acquisition_manifest: dict[str, Any] = {
        "schema_version": "1.0.0",
        "manifest_id": ACQUISITION_ID,
        "source_id": SOURCE_ID,
        "source_url": DOI_URL,
        "request_url": DOWNLOAD_URL,
        "retrieved_at": generated_at,
        "http_status": acquisition["http_status"],
        "sha256": acquisition["sha256"],
        "license": "Open Database License 1.0 (ODbL); OSM-derived",
        "parser_version": PARSER_VERSION,
        "attempt": 1,
        "created_at": generated_at,
        "updated_at": generated_at,
        "record_status": "active",
    }
    if acquisition.get("etag"):
        acquisition_manifest["etag"] = acquisition["etag"]
    if acquisition.get("last_modified"):
        acquisition_manifest["last_modified"] = acquisition["last_modified"]
    write_json(
        output_root / "data" / "raw" / "im3-atlas" / f"{RELEASE_VERSION}.acquisition.json",
        acquisition_manifest,
    )

    processing_report = {
        "schema_version": "1.0.0",
        "source_release": RELEASE_VERSION,
        "generated_at": generated_at,
        "source_row_count": len(source_rows),
        "in_scope_row_count": len(source_rows) - len(excluded_rows),
        "distinct_in_scope_source_record_count": len(groups),
        "facility_candidate_count": len(collections["facility"]),
        "campus_record_count": len(collections["campus"]),
        "cross_county_source_record_count": sum(len(group) > 1 for group in groups),
        "excluded_rows": [
            {
                "source_row_id": row["source_row_id"],
                "state_abbr": row["state_abbr"],
                "county_fips": row["county_fips"],
                "reason": "outside_50_states_and_dc_geography_scope",
            }
            for row in excluded_rows
        ],
        **diagnostics,
    }
    write_json(
        output_root / "data" / "silver" / "infrastructure" / f"im3-{RELEASE_VERSION}.processing-report.json",
        processing_report,
    )

    dataset_manifest = {
        "schema_version": "1.0.0",
        "dataset_id": f"im3_facility_seed_{RELEASE_VERSION.replace('.', '')}",
        "artifact_type": "provisional_facility_seed",
        "artifact_version": RELEASE_VERSION,
        "generated_at": generated_at,
        "data_vintage": RELEASE_DATE,
        "record_schema": "https://dccio.org/schemas/v1/catalog.json",
        "format": "json",
        "parts": [
            {
                "path": f"data/bronze/im3-atlas/{RELEASE_VERSION}-source-rows.json",
                "sha256": hashlib.sha256(bronze_payload).hexdigest(),
                "byte_size": len(bronze_payload),
                "record_count": len(source_rows),
                "partition_values": {"zone": "bronze"},
            },
            {
                "path": f"data/silver/infrastructure/im3-{RELEASE_VERSION}.json",
                "sha256": hashlib.sha256(silver_payload).hexdigest(),
                "byte_size": len(silver_payload),
                "record_count": silver_document["record_count"],
                "partition_values": {"zone": "silver"},
            },
            {
                "path": "site/public/data/v1/maps/facilities.geojson",
                "sha256": hashlib.sha256(map_payload).hexdigest(),
                "byte_size": len(map_payload),
                "record_count": len(public_geojson["features"]),
                "partition_values": {"zone": "public", "projection": "map"},
            },
            {
                "path": "site/public/data/v1/facilities/index.json",
                "sha256": hashlib.sha256(index_payload).hexdigest(),
                "byte_size": len(index_payload),
                "record_count": len(facility_index),
                "partition_values": {"zone": "public", "projection": "facility_index"},
            },
            {
                "path": "site/public/data/v1/counties/facility-source-coverage.json",
                "sha256": hashlib.sha256(coverage_payload).hexdigest(),
                "byte_size": len(coverage_payload),
                "record_count": len(coverage),
                "partition_values": {"zone": "public", "projection": "county_coverage"},
            },
        ],
        "record_count": len(source_rows) + silver_document["record_count"] + len(public_geojson["features"]) + len(facility_index) + len(coverage),
        "license_metadata": {
            "license": "Open Database License 1.0 (ODbL)",
            "redistribution_status": "allowed",
            "attribution": ATTRIBUTION,
        },
    }
    write_json(
        output_root / "data" / "silver" / "infrastructure" / f"im3-{RELEASE_VERSION}.manifest.json",
        dataset_manifest,
    )

    metadata_path = output_root / "site" / "public" / "data" / "v1" / "metadata.json"
    metadata = {
        "schema_version": "1.0.0",
        "data_version": f"2026-08-31+im3-{RELEASE_VERSION}+census-2025",
        "data_status": "provisional",
        "generated_at": generated_at,
        "latest_facility_year": 2026,
        "latest_economic_year": None,
        "methodology_version": "0.1.0",
        "notices": [
            "County boundaries and identity fields are authoritative U.S. Census Bureau data, January 1, 2025 vintage.",
            f"Location records are OSM-derived IM3 Atlas v{RELEASE_VERSION} source observations and remain provisional.",
            "Source record counts are not deduplicated or lifecycle-verified operating facility counts and are not a complete historical project inventory.",
            "No economic, opposition, fiscal, or community-cost result is yet available for substantive interpretation.",
            "The browser consumes precomputed JSON and GeoJSON only.",
        ],
    }
    write_json(metadata_path, metadata)

    return {
        "source_rows": len(source_rows),
        "in_scope_rows": len(source_rows) - len(excluded_rows),
        "source_objects": len(groups),
        "facilities": len(collections["facility"]),
        "campuses": len(collections["campus"]),
        "counties_with_records": sum(row["source_record_count"] > 0 for row in coverage),
        "centroid_mismatches": diagnostics["centroid_county_mismatch_count"],
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
    except (RuntimeError, sqlite3.Error, OSError, ValueError, KeyError) as exc:
        print(f"IM3 facility acquisition failed: {exc}", file=sys.stderr)
        return 1
    print(
        "IM3 facility acquisition passed: "
        f"{result['source_rows']} source rows, {result['source_objects']} in-scope source objects "
        f"({result['facilities']} facility candidates, {result['campuses']} campuses) across "
        f"{result['counties_with_records']} counties; "
        f"{result['centroid_mismatches']} centroid/county mismatch(es)."
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())

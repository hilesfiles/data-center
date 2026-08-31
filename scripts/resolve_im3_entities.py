#!/usr/bin/env python3
"""Build a conservative, reviewable identity-resolution layer for the IM3 seed.

The resolver never merges physical records from proximity alone. It links a facility to
one campus only when a governed spatial rule is unambiguous, groups operator names only
after Unicode/case/whitespace normalization, and emits all possible point/building
duplicates and uncertain campus memberships as pending review candidates.
"""

from __future__ import annotations

import hashlib
import json
import unicodedata
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any, Iterable

from acquire_im3_facilities import (
    ATTRIBUTION,
    RELEASE_VERSION,
    SOURCE_ID,
    entity_id,
    geometry_bbox,
    group_in_scope_rows,
    point_in_geometry,
    write_json,
)


ROOT = Path(__file__).resolve().parents[1]
RULE_ID = "im3_identity_resolution_v1"
DATASET_ID = "im3_entity_resolution_20260209"


def stable_id(prefix: str, *parts: str) -> str:
    digest = hashlib.sha256("\x1f".join(parts).encode("utf-8")).hexdigest()[:20]
    return f"{prefix}_im3_{digest}"


def claim_id(record: dict[str, Any]) -> str:
    return f"clm_im3_{record['source_layer']}_{record['source_record_id']}_source"


def normalize_operator(value: str) -> str:
    return " ".join(unicodedata.normalize("NFKC", value).casefold().split())


def bbox_intersects(
    left: tuple[float, float, float, float], right: tuple[float, float, float, float]
) -> bool:
    return not (
        left[2] < right[0]
        or right[2] < left[0]
        or left[3] < right[1]
        or right[3] < left[1]
    )


def exterior_rings(geometry: dict[str, Any]) -> list[list[list[float]]]:
    if geometry["type"] == "Polygon":
        return [geometry["coordinates"][0]]
    if geometry["type"] == "MultiPolygon":
        return [polygon[0] for polygon in geometry["coordinates"]]
    return []


def exterior_vertices(geometry: dict[str, Any]) -> Iterable[list[float]]:
    for ring in exterior_rings(geometry):
        yield from ring


def orientation(a: list[float], b: list[float], c: list[float]) -> float:
    return (b[0] - a[0]) * (c[1] - a[1]) - (b[1] - a[1]) * (c[0] - a[0])


def on_segment(a: list[float], b: list[float], point: list[float]) -> bool:
    tolerance = 1e-12
    return (
        abs(orientation(a, b, point)) <= tolerance
        and min(a[0], b[0]) - tolerance <= point[0] <= max(a[0], b[0]) + tolerance
        and min(a[1], b[1]) - tolerance <= point[1] <= max(a[1], b[1]) + tolerance
    )


def segments_intersect(a: list[float], b: list[float], c: list[float], d: list[float]) -> bool:
    ab_c = orientation(a, b, c)
    ab_d = orientation(a, b, d)
    cd_a = orientation(c, d, a)
    cd_b = orientation(c, d, b)
    if ((ab_c > 0 > ab_d) or (ab_d > 0 > ab_c)) and (
        (cd_a > 0 > cd_b) or (cd_b > 0 > cd_a)
    ):
        return True
    return any(
        (
            abs(value) <= 1e-12,
            on_segment(start, end, point),
        )
        == (True, True)
        for value, start, end, point in (
            (ab_c, a, b, c),
            (ab_d, a, b, d),
            (cd_a, c, d, a),
            (cd_b, c, d, b),
        )
    )


def geometries_intersect(left: dict[str, Any], right: dict[str, Any]) -> bool:
    left_rings = exterior_rings(left)
    right_rings = exterior_rings(right)
    for left_ring in left_rings:
        for right_ring in right_rings:
            for left_index in range(1, len(left_ring)):
                for right_index in range(1, len(right_ring)):
                    if segments_intersect(
                        left_ring[left_index - 1],
                        left_ring[left_index],
                        right_ring[right_index - 1],
                        right_ring[right_index],
                    ):
                        return True
    for point in exterior_vertices(left):
        if point_in_geometry(point[0], point[1], right):
            return True
    for point in exterior_vertices(right):
        if point_in_geometry(point[0], point[1], left):
            return True
    return False


def fully_within(inner: dict[str, Any], outer: dict[str, Any]) -> bool:
    vertices = list(exterior_vertices(inner))
    return bool(vertices) and all(point_in_geometry(point[0], point[1], outer) for point in vertices)


def make_candidate(
    candidate_type: str,
    subjects: list[dict[str, str]],
    evidence_claim_ids: list[str],
    predicate: str,
    recommended_action: str,
    generated_at: str,
    notes: str,
) -> dict[str, Any]:
    subject_key = [subject["entity_id"] for subject in subjects]
    return {
        "schema_version": "1.0.0",
        "resolution_candidate_id": stable_id("erc", candidate_type, *subject_key),
        "candidate_type": candidate_type,
        "subject_refs": subjects,
        "evidence_claim_ids": sorted(set(evidence_claim_ids)),
        "spatial_evidence": {"predicate": predicate, "match_count": len(subjects) - 1, "notes": notes},
        "recommended_action": recommended_action,
        "candidate_status": "pending",
        "governed_rule_id": RULE_ID,
        "created_at": generated_at,
        "updated_at": generated_at,
        "record_status": "provisional",
    }


def build_resolution(
    groups: list[list[dict[str, Any]]],
    seed: dict[str, Any],
    generated_at: str,
) -> tuple[dict[str, list[dict[str, Any]]], dict[str, Any], dict[str, dict[str, Any]]]:
    records = {(group[0]["source_layer"], group[0]["source_record_id"]): group[0] for group in groups}
    by_entity = {entity_id(layer, record_id): record for (layer, record_id), record in records.items()}
    campuses = [record for record in records.values() if record["source_layer"] == "campus"]
    buildings = [record for record in records.values() if record["source_layer"] == "building"]
    points = [record for record in records.values() if record["source_layer"] == "point"]
    campus_spatial = [(record, geometry_bbox(record["geometry"])) for record in campuses]
    building_spatial = [(record, geometry_bbox(record["geometry"])) for record in buildings]

    campus_links: dict[str, str] = {}
    campus_link_predicate: dict[str, str] = {}
    candidates: list[dict[str, Any]] = []

    for building in buildings:
        building_id = entity_id("building", building["source_record_id"])
        building_bbox = geometry_bbox(building["geometry"])
        intersecting: list[dict[str, Any]] = []
        fully_containing: list[dict[str, Any]] = []
        for campus, campus_bbox in campus_spatial:
            if not bbox_intersects(building_bbox, campus_bbox):
                continue
            if geometries_intersect(building["geometry"], campus["geometry"]):
                intersecting.append(campus)
                if fully_within(building["geometry"], campus["geometry"]):
                    fully_containing.append(campus)
        if len(fully_containing) == 1:
            campus = fully_containing[0]
            campus_links[building_id] = entity_id("campus", campus["source_record_id"])
            campus_link_predicate[building_id] = "building_geometry_within_single_campus"
        else:
            unresolved = fully_containing if fully_containing else intersecting
            for campus in unresolved:
                campus_id = entity_id("campus", campus["source_record_id"])
                predicate = (
                    "centroid_within_campus"
                    if point_in_geometry(building["longitude"], building["latitude"], campus["geometry"])
                    else "geometry_intersects_campus"
                )
                candidates.append(
                    make_candidate(
                        "building_campus_membership",
                        [
                            {"entity_type": "facility", "entity_id": building_id},
                            {"entity_type": "campus", "entity_id": campus_id},
                        ],
                        [claim_id(building), claim_id(campus)],
                        predicate,
                        "review_membership",
                        generated_at,
                        "The geometries intersect, but the building is not wholly inside exactly one campus polygon.",
                    )
                )

    for point in points:
        point_id = entity_id("point", point["source_record_id"])
        campus_matches = [
            campus
            for campus, bbox in campus_spatial
            if bbox[0] <= point["longitude"] <= bbox[2]
            and bbox[1] <= point["latitude"] <= bbox[3]
            and point_in_geometry(point["longitude"], point["latitude"], campus["geometry"])
        ]
        if len(campus_matches) == 1:
            campus_links[point_id] = entity_id("campus", campus_matches[0]["source_record_id"])
            campus_link_predicate[point_id] = "point_within_single_campus"
        elif len(campus_matches) > 1:
            for campus in campus_matches:
                candidates.append(
                    make_candidate(
                        "point_campus_membership",
                        [
                            {"entity_type": "facility", "entity_id": point_id},
                            {"entity_type": "campus", "entity_id": entity_id("campus", campus["source_record_id"])},
                        ],
                        [claim_id(point), claim_id(campus)],
                        "centroid_within_campus",
                        "review_membership",
                        generated_at,
                        "The point lies within more than one campus polygon.",
                    )
                )

        for building, bbox in building_spatial:
            if not (
                bbox[0] <= point["longitude"] <= bbox[2]
                and bbox[1] <= point["latitude"] <= bbox[3]
                and point_in_geometry(point["longitude"], point["latitude"], building["geometry"])
            ):
                continue
            candidates.append(
                make_candidate(
                    "point_building_identity",
                    [
                        {"entity_type": "facility", "entity_id": point_id},
                        {"entity_type": "facility", "entity_id": entity_id("building", building["source_record_id"])},
                    ],
                    [claim_id(point), claim_id(building)],
                    "point_within_building",
                    "review_merge",
                    generated_at,
                    "Spatial containment alone does not establish that the point and building represent the same physical facility.",
                )
            )

    operator_groups: dict[str, list[tuple[str, dict[str, Any], str]]] = defaultdict(list)
    for subject_id, record in sorted(by_entity.items()):
        raw_operator = record.get("operator")
        if raw_operator:
            operator_groups[normalize_operator(raw_operator)].append((subject_id, record, raw_operator))

    operators: list[dict[str, Any]] = []
    operator_relationships: list[dict[str, Any]] = []
    operator_by_entity: dict[str, tuple[str, str]] = {}
    review_decisions: list[dict[str, Any]] = []
    operator_variant_counts: dict[str, int] = {}
    for normalized_name, members in sorted(operator_groups.items()):
        name_counts = Counter(raw_name for _, _, raw_name in members)
        canonical_name = sorted(name_counts, key=lambda value: (-name_counts[value], value.casefold(), value))[0]
        aliases = sorted(name for name in name_counts if name != canonical_name)
        operator_id = stable_id("opr", normalized_name)
        operator_variant_counts[operator_id] = len(name_counts)
        operators.append(
            {
                "schema_version": "1.0.0",
                "operator_id": operator_id,
                "canonical_name": canonical_name,
                "organization_type": "unknown",
                "aliases": aliases,
                "external_identifiers": [
                    {"namespace": "im3_operator_normalized_name", "value": normalized_name, "source_id": SOURCE_ID}
                ],
                "created_at": generated_at,
                "updated_at": generated_at,
                "record_status": "provisional",
            }
        )
        evidence = sorted({claim_id(record) for _, record, _ in members})
        review_decisions.append(
            {
                "schema_version": "1.0.0",
                "review_decision_id": stable_id("rev", "operator_exact_text", operator_id),
                "review_type": "entity_match",
                "subject_refs": [{"entity_type": "operator", "entity_id": operator_id}],
                "decision": "provisional",
                "rationale": "Unicode, case, and whitespace normalization only; no corporate alias or ownership inference was applied.",
                "evidence_claim_ids": evidence,
                "reviewer": {"type": "governed_rule", "identifier": RULE_ID},
                "decided_at": generated_at,
                "created_at": generated_at,
                "updated_at": generated_at,
                "record_status": "provisional",
            }
        )
        for subject_id, record, _ in members:
            operator_by_entity[subject_id] = (operator_id, canonical_name)
            subject_type = "campus" if record["source_layer"] == "campus" else "facility"
            operator_relationships.append(
                {
                    "schema_version": "1.0.0",
                    "relationship_id": stable_id("rel", operator_id, subject_id, "operator"),
                    "operator_id": operator_id,
                    "subject_type": subject_type,
                    "subject_id": subject_id,
                    "relationship_type": "operator",
                    "effective_interval": {},
                    "source_claim_ids": [claim_id(record)],
                    "confidence": 0.75,
                    "created_at": generated_at,
                    "updated_at": generated_at,
                    "record_status": "provisional",
                }
            )

    for facility_id, campus_id in sorted(campus_links.items()):
        facility_record = by_entity[facility_id]
        campus_record = by_entity[campus_id]
        review_decisions.append(
            {
                "schema_version": "1.0.0",
                "review_decision_id": stable_id("rev", "campus_link", facility_id, campus_id),
                "review_type": "entity_match",
                "subject_refs": [
                    {"entity_type": "facility", "entity_id": facility_id},
                    {"entity_type": "campus", "entity_id": campus_id},
                ],
                "decision": "accept",
                "rationale": f"Unambiguous governed spatial rule: {campus_link_predicate[facility_id]}.",
                "evidence_claim_ids": [claim_id(facility_record), claim_id(campus_record)],
                "reviewer": {"type": "governed_rule", "identifier": RULE_ID},
                "decided_at": generated_at,
                "created_at": generated_at,
                "updated_at": generated_at,
                "record_status": "provisional",
            }
        )

    facilities = []
    for facility in seed["collections"]["facility"]:
        resolved = dict(facility)
        if facility["facility_id"] in campus_links:
            resolved["campus_id"] = campus_links[facility["facility_id"]]
        facilities.append(resolved)

    collections = {
        "campus": seed["collections"]["campus"],
        "facility": facilities,
        "operator": operators,
        "operator_relationship": operator_relationships,
        "review_decision": sorted(review_decisions, key=lambda item: item["review_decision_id"]),
        "entity_resolution_candidate": sorted(candidates, key=lambda item: item["resolution_candidate_id"]),
    }
    report = {
        "schema_version": "1.0.0",
        "artifact_type": "entity_resolution_processing_report",
        "artifact_version": RELEASE_VERSION,
        "generated_at": generated_at,
        "governed_rule_id": RULE_ID,
        "policies": {
            "physical_record_merge": "No automatic merges; proximity and containment produce review candidates only.",
            "campus_membership": "Auto-link only a building wholly within exactly one campus geometry or a point within exactly one campus geometry.",
            "operator_identity": "Group Unicode/case/whitespace-equivalent source strings only; do not infer corporate aliases, ownership, or parentage.",
        },
        "counts": {
            "source_object_count": len(records),
            "facility_count": len(facilities),
            "campus_count": len(campuses),
            "campus_linked_facility_count": len(campus_links),
            "campus_linked_building_count": sum(key.startswith("fac_im3_building_") for key in campus_links),
            "campus_linked_point_count": sum(key.startswith("fac_im3_point_") for key in campus_links),
            "operator_source_record_count": len(operator_relationships),
            "normalized_operator_count": len(operators),
            "raw_operator_variant_count": sum(len(Counter(raw for _, _, raw in members)) for members in operator_groups.values()),
            "operator_groups_with_multiple_raw_variants": sum(count > 1 for count in operator_variant_counts.values()),
            "pending_candidate_count": len(candidates),
            "point_building_candidate_count": sum(item["candidate_type"] == "point_building_identity" for item in candidates),
            "campus_membership_candidate_count": sum(item["candidate_type"] in {"building_campus_membership", "point_campus_membership"} for item in candidates),
            "governed_review_decision_count": len(review_decisions),
        },
    }
    runtime = {
        "by_entity": by_entity,
        "campus_links": campus_links,
        "operator_by_entity": operator_by_entity,
        "candidates": candidates,
    }
    return collections, report, runtime


def build_public_data(
    source_index: list[dict[str, Any]],
    source_coverage: list[dict[str, Any]],
    runtime: dict[str, Any],
    report: dict[str, Any],
    generated_at: str,
) -> tuple[list[dict[str, Any]], list[dict[str, Any]], dict[str, Any]]:
    candidates_by_entity: dict[str, list[str]] = defaultdict(list)
    for candidate in runtime["candidates"]:
        for subject in candidate["subject_refs"]:
            candidates_by_entity[subject["entity_id"]].append(candidate["resolution_candidate_id"])

    records = []
    source_by_entity = {item["entity_id"]: item for item in source_index}
    for source in source_index:
        entity_id_value = source["entity_id"]
        pending_ids = sorted(candidates_by_entity.get(entity_id_value, []))
        campus_id = runtime["campus_links"].get(entity_id_value)
        operator = runtime["operator_by_entity"].get(entity_id_value)
        campus_status = "not_applicable" if source["source_layer"] == "campus" else "not_linked"
        if campus_id:
            campus_status = "linked_by_governed_rule"
        elif any(
            candidate["candidate_type"] in {"building_campus_membership", "point_campus_membership"}
            and entity_id_value in {ref["entity_id"] for ref in candidate["subject_refs"]}
            for candidate in runtime["candidates"]
        ):
            campus_status = "review_pending"
        resolution_status = "review_pending" if pending_ids else (
            "governed_links_present" if campus_id or operator else "source_only"
        )
        record = {
            "schema_version": "1.0.0",
            "entity_id": entity_id_value,
            "entity_type": source["entity_type"],
            "source_layer": source["source_layer"],
            "source_record_id": source["source_record_id"],
            "campus_membership_status": campus_status,
            "operator_resolution_status": "exact_text_normalized" if operator else "source_operator_absent",
            "pending_candidate_ids": pending_ids,
            "resolution_status": resolution_status,
            "release_vintage": RELEASE_VERSION,
            "generated_at": generated_at,
        }
        if campus_id:
            record["campus_id"] = campus_id
        if operator:
            record["operator_id"], record["operator_canonical_name"] = operator
        records.append(record)

    coverage = []
    coverage_by_fips: dict[str, dict[str, Any]] = {}
    for source in source_coverage:
        item = {
            "schema_version": "1.0.0",
            "county_fips": source["county_fips"],
            "county_name": source["county_name"],
            "state_abbr": source["state_abbr"],
            "release_vintage": RELEASE_VERSION,
            "source_record_count": source["source_record_count"],
            "campus_linked_facility_count": 0,
            "operator_linked_record_count": 0,
            "pending_candidate_count": 0,
            "point_building_candidate_count": 0,
            "campus_membership_candidate_count": 0,
            "resolution_status": "no_source_record" if source["source_record_count"] == 0 else "source_only",
            "generated_at": generated_at,
        }
        coverage.append(item)
        coverage_by_fips[item["county_fips"]] = item

    resolution_by_entity = {item["entity_id"]: item for item in records}
    for entity_id_value, source in source_by_entity.items():
        resolution = resolution_by_entity[entity_id_value]
        for county_fips in source["county_fipses"]:
            county = coverage_by_fips[county_fips]
            county["campus_linked_facility_count"] += int(bool(resolution.get("campus_id")))
            county["operator_linked_record_count"] += int(bool(resolution.get("operator_id")))

    for candidate in runtime["candidates"]:
        first_subject = candidate["subject_refs"][0]["entity_id"]
        county_fips = source_by_entity[first_subject]["primary_county_fips"]
        county = coverage_by_fips[county_fips]
        county["pending_candidate_count"] += 1
        if candidate["candidate_type"] == "point_building_identity":
            county["point_building_candidate_count"] += 1
        else:
            county["campus_membership_candidate_count"] += 1

    for county in coverage:
        if county["pending_candidate_count"]:
            county["resolution_status"] = "review_pending"
        elif county["campus_linked_facility_count"] or county["operator_linked_record_count"]:
            county["resolution_status"] = "governed_links_present"

    metadata = {
        "schema_version": "1.0.0",
        "artifact_type": "public_entity_resolution_summary",
        "artifact_version": RELEASE_VERSION,
        "generated_at": generated_at,
        "data_status": "provisional",
        "governed_rule_id": RULE_ID,
        "counts": report["counts"],
        "notices": [
            "No physical source records were automatically merged.",
            "Campus links and normalized operators remain provisional and traceable to source claims.",
            "Pending candidates require review before canonical identity decisions.",
        ],
    }
    return records, coverage, metadata


def sha256(payload: bytes) -> str:
    return hashlib.sha256(payload).hexdigest()


def main() -> int:
    bronze = json.loads((ROOT / "data/bronze/im3-atlas/2026.02.09-source-rows.json").read_text(encoding="utf-8"))
    seed = json.loads((ROOT / "data/silver/infrastructure/im3-2026.02.09.json").read_text(encoding="utf-8"))
    source_index = json.loads((ROOT / "site/public/data/v1/facilities/index.json").read_text(encoding="utf-8"))
    source_coverage = json.loads((ROOT / "site/public/data/v1/counties/facility-source-coverage.json").read_text(encoding="utf-8"))
    generated_at = seed["generated_at"]
    groups = group_in_scope_rows(bronze["records"])
    collections, report, runtime = build_resolution(groups, seed, generated_at)
    public_records, public_coverage, public_metadata = build_public_data(
        source_index, source_coverage, runtime, report, generated_at
    )

    resolution_document = {
        "schema_version": "1.0.0",
        "artifact_type": "provisional_entity_resolution",
        "artifact_version": RELEASE_VERSION,
        "generated_at": generated_at,
        "record_count": sum(len(records) for records in collections.values()),
        "collections": collections,
    }
    outputs = [
        ("data/silver/infrastructure/im3-2026.02.09-entity-resolution.json", resolution_document, True, resolution_document["record_count"], "silver", "resolved_entities"),
        ("data/silver/infrastructure/im3-2026.02.09-entity-resolution.processing-report.json", report, False, 1, "silver", "processing_report"),
        ("site/public/data/v1/entity-resolution/index.json", public_records, True, len(public_records), "public", "entity_resolution_index"),
        ("site/public/data/v1/counties/entity-resolution-coverage.json", public_coverage, True, len(public_coverage), "public", "county_resolution_coverage"),
        ("site/public/data/v1/entity-resolution/metadata.json", public_metadata, False, 1, "public", "entity_resolution_metadata"),
    ]
    parts = []
    for relative_path, value, compact, record_count, zone, projection in outputs:
        payload = write_json(ROOT / relative_path, value, compact=compact)
        parts.append(
            {
                "path": relative_path,
                "sha256": sha256(payload),
                "byte_size": len(payload),
                "record_count": record_count,
                "partition_values": {"zone": zone, "projection": projection},
            }
        )
    manifest = {
        "schema_version": "1.0.0",
        "dataset_id": DATASET_ID,
        "artifact_type": "provisional_entity_resolution",
        "artifact_version": RELEASE_VERSION,
        "generated_at": generated_at,
        "data_vintage": "2026-02-09",
        "record_schema": "https://dccio.org/schemas/v1/catalog.json",
        "format": "json",
        "parts": parts,
        "record_count": sum(part["record_count"] for part in parts),
        "input_dataset_ids": ["im3_facility_seed_20260209"],
        "license_metadata": {
            "license": "Open Database License 1.0 (ODbL)",
            "redistribution_status": "allowed",
            "attribution": ATTRIBUTION,
        },
    }
    write_json(
        ROOT / "data/silver/infrastructure/im3-2026.02.09-entity-resolution.manifest.json",
        manifest,
    )
    print(json.dumps(report["counts"], indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

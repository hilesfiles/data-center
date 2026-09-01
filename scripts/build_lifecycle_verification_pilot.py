#!/usr/bin/env python3
"""Build a deterministic JSON lifecycle-verification pilot queue."""

from __future__ import annotations

import hashlib
import json
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any

from acquire_im3_facilities import ATTRIBUTION, write_json
from resolve_im3_entities import stable_id


ROOT = Path(__file__).resolve().parents[1]
DATASET_ID = "im3_lifecycle_verification_pilot_20260831"
ARTIFACT_VERSION = "2026.08.31"


def load(relative_path: str) -> Any:
    return json.loads((ROOT / relative_path).read_text(encoding="utf-8"))


def digest(payload: bytes) -> str:
    return hashlib.sha256(payload).hexdigest()


def build_pilot() -> tuple[list[dict[str, Any]], list[dict[str, Any]], dict[str, Any]]:
    final_review = load("data/silver/infrastructure/im3-2026.02.09-final-boundary-review.json")
    source_index = load("site/public/data/v1/facilities/index.json")
    county_reference = load("site/public/data/v1/counties/facility-source-coverage.json")
    policy = load("config/v1/lifecycle-pilot-policy.json")
    generated_at = policy["updated_at"]

    source_by_id = {item["entity_id"]: item for item in source_index}
    county_by_fips = {item["county_fips"]: item for item in county_reference}
    operators_by_id = {
        item["operator_id"]: item for item in final_review["collections"]["operator"]
    }
    operator_link_by_facility: dict[str, dict[str, Any]] = {}
    for relationship in final_review["collections"]["operator_relationship"]:
        if relationship["relationship_type"] != "operator":
            continue
        operator_link_by_facility.setdefault(relationship["subject_id"], relationship)

    facilities = [
        item
        for item in final_review["collections"]["facility"]
        if item["record_status"] != "superseded" and item["current_status"] == "unknown"
    ]
    eligible = []
    for facility in facilities:
        source = source_by_id.get(facility["facility_id"])
        if source and source.get("primary_county_fips"):
            eligible.append((facility, source))

    facility_count_by_county = Counter(
        source["primary_county_fips"] for _, source in eligible
    )
    ranked_counties = sorted(
        facility_count_by_county,
        key=lambda fips: (-facility_count_by_county[fips], fips),
    )[: policy["county_count"]]
    if policy["pilot_size"] != policy["county_count"] * policy["per_county_quota"]:
        raise RuntimeError("Pilot size must equal county count times per-county quota")
    maximum_count = max(facility_count_by_county.values())
    weights = policy["scoring_weights"]

    candidates_by_county: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for facility, source in eligible:
        county_fips = source["primary_county_fips"]
        if county_fips not in ranked_counties:
            continue
        operator_link = operator_link_by_facility.get(facility["facility_id"])
        operator = operators_by_id.get(operator_link["operator_id"]) if operator_link else None
        named = bool(source.get("source_name")) and not facility["canonical_name"].startswith("Unnamed IM3 ")
        building = source["source_layer"] == "building"
        campus_member = bool(facility.get("campus_id"))
        source_quality = facility.get("data_quality", {}).get("score", 0) / 100
        score = (
            weights["county_density"] * facility_count_by_county[county_fips] / maximum_count
            + weights["named_source"] * int(named)
            + weights["operator_link"] * int(operator_link is not None)
            + weights["building_footprint"] * int(building)
            + weights["campus_membership"] * int(campus_member)
            + weights["source_quality"] * source_quality
        )
        reasons = [
            f"Selected from a top-{policy['county_count']} county by active canonical facility count."
        ]
        if named:
            reasons.append("Source supplies a facility name suitable for evidence search.")
        if operator_link:
            reasons.append("A source-backed normalized operator relationship is available.")
        if building:
            reasons.append("Mapped building footprint supports parcel and permit lookup.")
        if campus_member:
            reasons.append("Campus membership supports project and phase history research.")
        county = county_by_fips[county_fips]
        candidate = {
            "schema_version": "1.0.0",
            "verification_candidate_id": stable_id(
                "lvc", policy["policy_id"], facility["facility_id"]
            ),
            "facility_id": facility["facility_id"],
            "canonical_name": facility["canonical_name"],
            "primary_county_fips": county_fips,
            "county_name": county["county_name"],
            "state_abbr": county["state_abbr"],
            "source_layer": source["source_layer"],
            "target_attributes": policy["target_attributes"],
            "suggested_source_types": policy["suggested_source_types"],
            "priority_score": round(score, 2),
            "priority_tier": "pilot_high" if score >= 70 else "pilot_standard",
            "selection_reasons": reasons,
            "evidence_status": "no_external_evidence",
            "review_status": "queued",
            "created_at": generated_at,
            "updated_at": generated_at,
            "record_status": "active",
        }
        if facility.get("campus_id"):
            candidate["campus_id"] = facility["campus_id"]
        if operator_link and operator:
            candidate["operator_id"] = operator["operator_id"]
            candidate["operator_canonical_name"] = operator["canonical_name"]
        candidates_by_county[county_fips].append(candidate)

    queue = []
    for county_fips in ranked_counties:
        ranked = sorted(
            candidates_by_county[county_fips],
            key=lambda item: (-item["priority_score"], item["facility_id"]),
        )
        selected = ranked[: policy["per_county_quota"]]
        if len(selected) != policy["per_county_quota"]:
            raise RuntimeError(f"County {county_fips} does not satisfy the pilot quota")
        queue.extend(selected)
    queue.sort(key=lambda item: (-item["priority_score"], item["primary_county_fips"], item["facility_id"]))
    if len(queue) != policy["pilot_size"]:
        raise RuntimeError("Lifecycle pilot size is inconsistent with policy")

    queued_by_county = Counter(item["primary_county_fips"] for item in queue)
    coverage = []
    for county_fips in sorted(county_by_fips):
        county = county_by_fips[county_fips]
        active_count = facility_count_by_county[county_fips]
        queued_count = queued_by_county[county_fips]
        coverage.append(
            {
                "schema_version": "1.0.0",
                "county_fips": county_fips,
                "county_name": county["county_name"],
                "state_abbr": county["state_abbr"],
                "active_canonical_facility_count": active_count,
                "queued_facility_count": queued_count,
                "in_research_facility_count": 0,
                "verified_facility_count": 0,
                "unknown_status_facility_count": active_count,
                "coverage_status": (
                    "pilot_queued"
                    if queued_count
                    else "backlog"
                    if active_count
                    else "no_active_facility"
                ),
                "generated_at": generated_at,
            }
        )

    metadata = {
        "schema_version": "1.0.0",
        "artifact_type": "public_lifecycle_verification_pilot_summary",
        "artifact_version": ARTIFACT_VERSION,
        "generated_at": generated_at,
        "policy_id": policy["policy_id"],
        "input_dataset_id": policy["input_dataset_id"],
        "counts": {
            "active_canonical_facility_count": len(facilities),
            "eligible_facility_count": len(eligible),
            "unknown_status_facility_count": len(eligible),
            "pilot_facility_count": len(queue),
            "pilot_county_count": len(ranked_counties),
            "verified_facility_count": 0,
        },
        "pilot_counties": [
            {
                "county_fips": fips,
                "county_name": county_by_fips[fips]["county_name"],
                "state_abbr": county_by_fips[fips]["state_abbr"],
                "active_canonical_facility_count": facility_count_by_county[fips],
                "queued_facility_count": queued_by_county[fips],
            }
            for fips in ranked_counties
        ],
        "notices": [
            "Queue membership is a research priority, not evidence of operating status.",
            "Every pilot facility still has unknown lifecycle status and no external lifecycle evidence in this artifact.",
            "Final status, dates, operator roles, and capacity require claims and reviewed resolutions from independent sources.",
        ],
    }
    return queue, coverage, metadata


def main() -> int:
    queue, coverage, metadata = build_pilot()
    document = {
        "schema_version": "1.0.0",
        "artifact_type": "lifecycle_verification_pilot",
        "artifact_version": ARTIFACT_VERSION,
        "generated_at": metadata["generated_at"],
        "record_count": len(queue),
        "collections": {"lifecycle_verification_candidate": queue},
    }
    report = {
        **metadata,
        "artifact_type": "lifecycle_verification_pilot_processing_report",
    }
    outputs = [
        ("data/silver/infrastructure/im3-2026.02.09-lifecycle-pilot.json", document, True, len(queue), "silver", "lifecycle_pilot"),
        ("data/silver/infrastructure/im3-2026.02.09-lifecycle-pilot.processing-report.json", report, False, 1, "silver", "processing_report"),
        ("site/public/data/v1/lifecycle/pilot-queue.json", queue, True, len(queue), "public", "lifecycle_pilot_queue"),
        ("site/public/data/v1/counties/lifecycle-verification-coverage.json", coverage, True, len(coverage), "public", "lifecycle_coverage"),
        ("site/public/data/v1/lifecycle/metadata.json", metadata, False, 1, "public", "lifecycle_metadata"),
    ]
    parts = []
    for relative_path, value, compact, record_count, zone, projection in outputs:
        payload = write_json(ROOT / relative_path, value, compact=compact)
        parts.append(
            {
                "path": relative_path,
                "sha256": digest(payload),
                "byte_size": len(payload),
                "record_count": record_count,
                "partition_values": {"zone": zone, "projection": projection},
            }
        )
    manifest = {
        "schema_version": "1.0.0",
        "dataset_id": DATASET_ID,
        "artifact_type": "lifecycle_verification_pilot",
        "artifact_version": ARTIFACT_VERSION,
        "generated_at": metadata["generated_at"],
        "data_vintage": "2026-08-31",
        "record_schema": "https://dccio.org/schemas/v1/lifecycle-verification-candidate.schema.json",
        "format": "json",
        "parts": parts,
        "record_count": sum(part["record_count"] for part in parts),
        "input_dataset_ids": ["im3_final_boundary_review_20260831"],
        "license_metadata": {
            "license": "ODbL applies to IM3-derived records",
            "redistribution_status": "allowed",
            "attribution": ATTRIBUTION,
        },
    }
    write_json(
        ROOT / "data/silver/infrastructure/im3-2026.02.09-lifecycle-pilot.manifest.json",
        manifest,
    )
    print(json.dumps(metadata, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

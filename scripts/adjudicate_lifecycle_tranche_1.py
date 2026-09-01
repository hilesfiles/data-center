#!/usr/bin/env python3
"""Build the first governed lifecycle-evidence tranche from JSON adjudications."""

from __future__ import annotations

import hashlib
import json
from collections import Counter
from copy import deepcopy
from pathlib import Path
from typing import Any

from acquire_im3_facilities import ATTRIBUTION, write_json
from resolve_im3_entities import stable_id


ROOT = Path(__file__).resolve().parents[1]
DATASET_ID = "im3_lifecycle_tranche_1_20260831"
ARTIFACT_VERSION = "2026.08.31"


def load(relative_path: str) -> Any:
    return json.loads((ROOT / relative_path).read_text(encoding="utf-8"))


def digest(payload: bytes) -> str:
    return hashlib.sha256(payload).hexdigest()


def claim_id(candidate_id: str, index: int) -> str:
    return stable_id("clm", "lifecycle_tranche_1", candidate_id, str(index))


def validate_pwc_snapshot() -> None:
    snapshot = load("data/raw/prince-william-county/lifecycle-tranche-1-iad14.json")
    matches = [
        feature["attributes"]
        for feature in snapshot.get("features", [])
        if feature.get("attributes", {}).get("BuildingID") == "IAD14"
    ]
    if len(matches) != 1:
        raise RuntimeError("Expected exactly one IAD14 record in the Prince William County snapshot")
    record = matches[0]
    if record.get("BuildingStatus") != "Planned" or record.get("PermitStatus") != "Planned":
        raise RuntimeError("The governed IAD14 conflict must be revisited because the GIS status changed")


def build() -> tuple[dict[str, Any], list[dict[str, Any]], list[dict[str, Any]], dict[str, Any]]:
    validate_pwc_snapshot()
    pilot = load("data/silver/infrastructure/im3-2026.02.09-lifecycle-pilot.json")
    final_review = load("data/silver/infrastructure/im3-2026.02.09-final-boundary-review.json")
    baseline_coverage = load("site/public/data/v1/counties/lifecycle-verification-coverage.json")
    source_document = load("config/v1/lifecycle-tranche-1-evidence-sources.json")
    adjudication_document = load("config/v1/lifecycle-tranche-1-adjudications.json")
    generated_at = adjudication_document["generated_at"]

    sources = source_document["records"]
    source_ids = {record["source_id"] for record in sources}
    candidates = pilot["collections"]["lifecycle_verification_candidate"]
    candidate_by_id = {record["verification_candidate_id"]: record for record in candidates}
    facilities_by_id = {
        record["facility_id"]: record
        for record in final_review["collections"]["facility"]
        if record["record_status"] != "superseded"
    }
    adjudications = adjudication_document["records"]
    if len(adjudications) != 8 or len({a["verification_candidate_id"] for a in adjudications}) != 8:
        raise RuntimeError("Lifecycle tranche 1 must contain eight distinct adjudications")

    claims: list[dict[str, Any]] = []
    resolutions: list[dict[str, Any]] = []
    reviews: list[dict[str, Any]] = []
    events: list[dict[str, Any]] = []
    observations: list[dict[str, Any]] = []
    updated_facilities: list[dict[str, Any]] = []
    public_results: list[dict[str, Any]] = []
    queue_by_id = {record["verification_candidate_id"]: deepcopy(record) for record in candidates}

    for adjudication in adjudications:
        candidate_id = adjudication["verification_candidate_id"]
        if candidate_id not in candidate_by_id:
            raise RuntimeError(f"Unknown lifecycle candidate {candidate_id}")
        candidate = candidate_by_id[candidate_id]
        facility_id = candidate["facility_id"]
        evidence_claims: list[dict[str, Any]] = []
        for index, evidence in enumerate(adjudication["evidence"]):
            if evidence["source_id"] not in source_ids:
                raise RuntimeError(f"Unknown source {evidence['source_id']}")
            current_claim_id = claim_id(candidate_id, index)
            claim = {
                "schema_version": "1.0.0",
                "claim_id": current_claim_id,
                "source_id": evidence["source_id"],
                "subject": {"entity_type": "facility", "entity_id": facility_id},
                "attribute_path": evidence["attribute_path"],
                "raw_value": evidence["raw_value"],
                "extraction_method": "manual",
                "extractor_version": "lifecycle-tranche-1-v1",
                "source_quality_score": next(source["source_quality_prior"] for source in sources if source["source_id"] == evidence["source_id"]),
                "claim_confidence": evidence["claim_confidence"],
                "review_status": "accepted" if adjudication["decision"] == "accept" else "needs_review",
                "notes": evidence["finding"],
                "created_at": generated_at,
                "updated_at": generated_at,
                "record_status": "active" if adjudication["resolution_state"] == "resolved" else "provisional",
            }
            if "normalized_value" in evidence:
                claim["normalized_value"] = evidence["normalized_value"]
            if adjudication["resolution_state"] == "conflicting":
                claim["conflict_group"] = f"{candidate_id}:facility.current_status"
            claims.append(claim)
            evidence_claims.append(claim)

        review_id = stable_id("rvw", "lifecycle_tranche_1", candidate_id)
        review = {
            "schema_version": "1.0.0",
            "review_decision_id": review_id,
            "review_type": "classification",
            "subject_refs": [
                {"entity_type": "lifecycle_verification_candidate", "entity_id": candidate_id},
                {"entity_type": "facility", "entity_id": facility_id},
            ],
            "decision": adjudication["decision"],
            "rationale": adjudication["rationale"],
            "evidence_claim_ids": [claim["claim_id"] for claim in evidence_claims],
            "reviewer": {"type": "human", "identifier": "dccio-bootstrap-review"},
            "decided_at": generated_at,
            "created_at": generated_at,
            "updated_at": generated_at,
            "record_status": "active" if adjudication["resolution_state"] == "resolved" else "provisional",
        }
        reviews.append(review)

        status_claims = [claim for claim in evidence_claims if claim["attribute_path"] == "facility.current_status"]
        resolution_status = {
            "resolved": "resolved",
            "partial": "unresolved",
            "conflicting": "disputed",
        }[adjudication["resolution_state"]]
        supporting = [
            claim["claim_id"]
            for claim, evidence in zip(evidence_claims, adjudication["evidence"])
            if claim["attribute_path"] == "facility.current_status" and evidence["disposition"] == "supporting"
        ]
        conflicting = [
            claim["claim_id"]
            for claim, evidence in zip(evidence_claims, adjudication["evidence"])
            if claim["attribute_path"] == "facility.current_status" and evidence["disposition"] == "conflicting"
        ]
        resolution = {
            "schema_version": "1.0.0",
            "resolution_id": stable_id("res", "lifecycle_tranche_1", candidate_id),
            "subject": {"entity_type": "facility", "entity_id": facility_id},
            "attribute_path": "facility.current_status",
            "resolution_status": resolution_status,
            "claim_refs": {"supporting": supporting, "conflicting": conflicting},
            "resolution_method": "human_review" if resolution_status == "resolved" else "unresolved",
            "rationale": adjudication["rationale"],
            "review_decision_id": review_id,
            "resolved_at": generated_at,
            "created_at": generated_at,
            "updated_at": generated_at,
            "record_status": "active" if resolution_status == "resolved" else "provisional",
        }
        if resolution_status == "resolved":
            resolution["resolved_value"] = {"type": "classification", "code": adjudication["resolved_current_status"]}
            resolution["resolution_confidence"] = adjudication["confidence"]
            resolution["claim_refs"]["winning"] = supporting[0]
            facility = deepcopy(facilities_by_id[facility_id])
            facility["current_status"] = adjudication["resolved_current_status"]
            facility["updated_at"] = generated_at
            updated_facilities.append(facility)
        resolutions.append(resolution)

        for event_index, event_spec in enumerate(adjudication.get("events", [])):
            matching_claims = [
                claim["claim_id"]
                for claim in evidence_claims
                if claim["source_id"] == event_spec["source_id"] and claim["attribute_path"] == f"event.{event_spec['event_type']}"
            ]
            events.append(
                {
                    "schema_version": "1.0.0",
                    "event_id": stable_id("evt", "lifecycle_tranche_1", candidate_id, str(event_index)),
                    "event_type": event_spec["event_type"],
                    "subjects": [{"entity_type": "facility", "entity_id": facility_id}],
                    "when": event_spec["when"],
                    "resolution_status": "resolved",
                    "confidence": event_spec["confidence"],
                    "source_claim_ids": matching_claims,
                    "notes": event_spec["notes"],
                    "created_at": generated_at,
                    "updated_at": generated_at,
                    "record_status": "active",
                }
            )

        for observation_index, observation_spec in enumerate(adjudication.get("observations", [])):
            attribute_path = {
                "facility.capacity.mw_observed": "observation.capacity_mw",
                "facility.area.building_sqft_observed": "observation.floor_area_sqft",
            }[observation_spec["metric_code"]]
            matching_claims = [
                claim["claim_id"]
                for claim in evidence_claims
                if claim["source_id"] == observation_spec["source_id"] and claim["attribute_path"] == attribute_path
            ]
            observations.append(
                {
                    "schema_version": "1.0.0",
                    "observation_id": stable_id("obs", "lifecycle_tranche_1", candidate_id, str(observation_index)),
                    "metric_code": observation_spec["metric_code"],
                    "subject": {"subject_type": "facility", "subject_id": facility_id},
                    "period": observation_spec["period"],
                    "value": {"type": "quantity", "value": observation_spec["value"], "unit": observation_spec["unit"]},
                    "value_status": "observed",
                    "source_ids": [observation_spec["source_id"]],
                    "source_claim_ids": matching_claims,
                    "release_vintage": "2026-08-31",
                    "revision_number": 0,
                    "created_at": generated_at,
                    "updated_at": generated_at,
                    "record_status": "active",
                }
            )

        queue_record = queue_by_id[candidate_id]
        queue_record["evidence_status"] = {"resolved": "sufficient", "partial": "partial", "conflicting": "conflicting"}[adjudication["resolution_state"]]
        queue_record["review_status"] = {"resolved": "verified", "partial": "in_research", "conflicting": "needs_review"}[adjudication["resolution_state"]]
        queue_record["updated_at"] = generated_at

        result = {
            "schema_version": "1.0.0",
            "verification_candidate_id": candidate_id,
            "facility_id": facility_id,
            "canonical_name": candidate["canonical_name"],
            "county_fips": candidate["primary_county_fips"],
            "county_name": candidate["county_name"],
            "state_abbr": candidate["state_abbr"],
            "evidence_status": queue_record["evidence_status"],
            "review_status": queue_record["review_status"],
            "resolution_status": resolution_status,
            "evidence_source_ids": sorted({claim["source_id"] for claim in evidence_claims}),
            "review_decision_id": review_id,
            "rationale": adjudication["rationale"],
            "generated_at": generated_at,
        }
        if resolution_status == "resolved":
            result["resolved_current_status"] = adjudication["resolved_current_status"]
            result["resolution_confidence"] = adjudication["confidence"]
        operational_events = [item for item in adjudication.get("events", []) if item["event_type"] == "operational"]
        if operational_events:
            result["operational_date"] = operational_events[0]["when"]
        for observation_spec in adjudication.get("observations", []):
            if observation_spec["metric_code"] == "facility.capacity.mw_observed":
                result["capacity_mw"] = observation_spec["value"]
            elif observation_spec["metric_code"] == "facility.area.building_sqft_observed":
                result["floor_area_sqft"] = observation_spec["value"]
        public_results.append(result)

    queue = sorted(queue_by_id.values(), key=lambda item: (-item["priority_score"], item["primary_county_fips"], item["facility_id"]))
    queue_counts_by_county: dict[str, Counter[str]] = {}
    for record in queue:
        queue_counts_by_county.setdefault(record["primary_county_fips"], Counter())[record["review_status"]] += 1
    coverage = []
    verified_total = len(updated_facilities)
    for baseline in baseline_coverage:
        record = deepcopy(baseline)
        counts = queue_counts_by_county.get(record["county_fips"], Counter())
        record["queued_facility_count"] = counts["queued"]
        record["in_research_facility_count"] = counts["in_research"]
        record["needs_review_facility_count"] = counts["needs_review"]
        record["verified_facility_count"] = counts["verified"]
        record["unknown_status_facility_count"] = record["active_canonical_facility_count"] - counts["verified"]
        if sum(counts.values()):
            record["coverage_status"] = "pilot_reviewed" if counts["verified"] == sum(counts.values()) else "pilot_in_progress"
        record["generated_at"] = generated_at
        coverage.append(record)

    metadata = {
        "schema_version": "1.0.0",
        "artifact_type": "public_lifecycle_verification_tranche_summary",
        "artifact_version": ARTIFACT_VERSION,
        "generated_at": generated_at,
        "input_dataset_id": "im3_lifecycle_verification_pilot_20260831",
        "counts": {
            "active_canonical_facility_count": sum(record["active_canonical_facility_count"] for record in coverage),
            "pilot_facility_count": len(queue),
            "reviewed_facility_count": len(public_results),
            "verified_facility_count": verified_total,
            "in_research_facility_count": sum(record["in_research_facility_count"] for record in coverage),
            "needs_review_facility_count": sum(record["needs_review_facility_count"] for record in coverage),
            "queued_facility_count": sum(record["queued_facility_count"] for record in coverage),
            "unknown_status_facility_count": sum(record["unknown_status_facility_count"] for record in coverage),
            "source_count": len(sources),
            "claim_count": len(claims),
            "event_count": len(events),
            "observation_count": len(observations),
        },
        "notices": [
            "Six facility statuses are resolved as operational from reviewed first-party or government evidence.",
            "Amazon IAD14 remains disputed because current Prince William County GIS conflicts with a 2024 county inventory.",
            "Amazon CMH50 remains in research because available evidence identifies mixed campus status but not the specific building.",
            "Campus- or site-wide capacity and floor area are not assigned to individual facilities.",
        ],
    }
    document = {
        "schema_version": "1.0.0",
        "artifact_type": "lifecycle_verification_tranche",
        "artifact_version": ARTIFACT_VERSION,
        "generated_at": generated_at,
        "record_count": sum(map(len, [sources, claims, resolutions, reviews, events, observations, updated_facilities])),
        "collections": {
            "source": sources,
            "claim": claims,
            "claim_resolution": resolutions,
            "review_decision": reviews,
            "event": events,
            "observation": observations,
            "facility": updated_facilities,
        },
    }
    return document, queue, coverage, {"metadata": metadata, "results": public_results}


def main() -> int:
    document, queue, coverage, public = build()
    metadata = public["metadata"]
    results = public["results"]
    report = {**metadata, "artifact_type": "lifecycle_verification_tranche_processing_report"}
    outputs = [
        ("data/silver/infrastructure/im3-2026.02.09-lifecycle-tranche-1.json", document, True, document["record_count"], "silver", "lifecycle_tranche"),
        ("data/silver/infrastructure/im3-2026.02.09-lifecycle-tranche-1.processing-report.json", report, False, 1, "silver", "processing_report"),
        ("site/public/data/v1/lifecycle/tranche-1-queue.json", queue, True, len(queue), "public", "lifecycle_queue"),
        ("site/public/data/v1/lifecycle/tranche-1-results.json", results, True, len(results), "public", "lifecycle_results"),
        ("site/public/data/v1/counties/lifecycle-tranche-1-coverage.json", coverage, True, len(coverage), "public", "lifecycle_coverage"),
        ("site/public/data/v1/lifecycle/tranche-1-metadata.json", metadata, False, 1, "public", "lifecycle_metadata"),
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
        "artifact_type": "lifecycle_verification_tranche",
        "artifact_version": ARTIFACT_VERSION,
        "generated_at": metadata["generated_at"],
        "data_vintage": "2026-08-31",
        "record_schema": "https://dccio.org/schemas/v1/public-lifecycle-verification-record.schema.json",
        "format": "json",
        "parts": parts,
        "record_count": sum(part["record_count"] for part in parts),
        "input_dataset_ids": ["im3_lifecycle_verification_pilot_20260831"],
        "license_metadata": {
            "license": "Mixed source metadata; IM3-derived records remain ODbL",
            "redistribution_status": "mixed",
            "attribution": ATTRIBUTION,
        },
    }
    write_json(ROOT / "data/silver/infrastructure/im3-2026.02.09-lifecycle-tranche-1.manifest.json", manifest)
    print(json.dumps(metadata, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

#!/usr/bin/env python3
"""Build the second governed national lifecycle-evidence tranche."""

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
DATASET_ID = "im3_lifecycle_national_tranche_2_20260831"
TRANCHE_ID = "trn_lifecycle_national_2_20260831"
POLICY_ID = "pol_lifecycle_national_20260831"
ARTIFACT_VERSION = "2026.08.31"
NAMESPACE = "national_lifecycle_tranche_2"
PRIOR_QUEUE_PATH = "site/public/data/v1/lifecycle/national-tranche-1-remaining-queue.json"
BASELINE_COVERAGE_PATH = "site/public/data/v1/counties/lifecycle-national-tranche-1-coverage.json"
SOURCE_CONFIG_PATH = "config/v1/national-lifecycle-tranche-2-evidence-sources.json"
ADJUDICATION_CONFIG_PATH = "config/v1/national-lifecycle-tranche-2-adjudications.json"
EXPECTED_RANKS = set(range(9, 17))
EXPECTED_RANK_LABEL = "nine through sixteen"
INPUT_DATASET_ID = "im3_lifecycle_national_tranche_1_20260831"
OUTPUT_TRANCHE_NUMBER = "2"
EXTRACTOR_VERSION = "national-lifecycle-tranche-2-v1"
METADATA_NOTICES = [
    "National initial-tranche ranks nine through sixteen are reviewed: six resolve operational and two remain unresolved.",
    "CMH56 and CMH59 lack a policy-compliant exact-building match from an official or first-party source.",
    "Cyxtera is retained as a historical TPA1 seed label; Csquare publishes the current facility record.",
    "Thirty-two facilities remain queued in the balanced initial national tranche.",
]


def load(relative_path: str) -> Any:
    return json.loads((ROOT / relative_path).read_text(encoding="utf-8"))


def digest(payload: bytes) -> str:
    return hashlib.sha256(payload).hexdigest()


def make_id(prefix: str, priority_id: str, suffix: str | None = None) -> str:
    parts = [NAMESPACE, priority_id]
    if suffix is not None:
        parts.append(suffix)
    return stable_id(prefix, *parts)


def build() -> tuple[
    dict[str, Any],
    list[dict[str, Any]],
    list[dict[str, Any]],
    list[dict[str, Any]],
    dict[str, Any],
]:
    prior_queue = load(PRIOR_QUEUE_PATH)
    baseline_coverage = load(BASELINE_COVERAGE_PATH)
    final_review = load("data/silver/infrastructure/im3-2026.02.09-final-boundary-review.json")
    source_document = load(SOURCE_CONFIG_PATH)
    adjudication_document = load(ADJUDICATION_CONFIG_PATH)
    generated_at = adjudication_document["generated_at"]

    candidates_by_id = {record["national_priority_id"]: record for record in prior_queue}
    facilities_by_id = {
        record["facility_id"]: record
        for record in final_review["collections"]["facility"]
        if record["record_status"] != "superseded"
    }
    sources = source_document["records"]
    source_by_id = {record["source_id"]: record for record in sources}
    adjudications = adjudication_document["records"]
    adjudication_ids = [record["national_priority_id"] for record in adjudications]
    if len(adjudications) != 8 or len(adjudication_ids) != len(set(adjudication_ids)):
        raise RuntimeError("The second national tranche must contain eight distinct adjudications")
    if any(priority_id not in candidates_by_id for priority_id in adjudication_ids):
        raise RuntimeError("National adjudication references a candidate outside the prior remaining queue")
    if {candidates_by_id[priority_id]["initial_tranche_rank"] for priority_id in adjudication_ids} != EXPECTED_RANKS:
        raise RuntimeError(f"The national tranche must review initial queue ranks {EXPECTED_RANK_LABEL}")

    claims: list[dict[str, Any]] = []
    resolutions: list[dict[str, Any]] = []
    reviews: list[dict[str, Any]] = []
    events: list[dict[str, Any]] = []
    observations: list[dict[str, Any]] = []
    updated_facilities: list[dict[str, Any]] = []
    public_results: list[dict[str, Any]] = []

    for adjudication in adjudications:
        priority_id = adjudication["national_priority_id"]
        candidate = candidates_by_id[priority_id]
        facility_id = candidate["facility_id"]
        evidence_claims: list[dict[str, Any]] = []
        for index, evidence in enumerate(adjudication["evidence"]):
            source = source_by_id.get(evidence["source_id"])
            if source is None:
                raise RuntimeError(f"Unknown source {evidence['source_id']}")
            claim = {
                "schema_version": "1.0.0",
                "claim_id": make_id("clm", priority_id, str(index)),
                "source_id": evidence["source_id"],
                "subject": {"entity_type": "facility", "entity_id": facility_id},
                "attribute_path": evidence["attribute_path"],
                "raw_value": evidence["raw_value"],
                "extraction_method": "manual",
                "extractor_version": EXTRACTOR_VERSION,
                "source_quality_score": source["source_quality_prior"],
                "claim_confidence": evidence["claim_confidence"],
                "review_status": "accepted" if adjudication["decision"] == "accept" else "needs_review",
                "notes": evidence["finding"],
                "created_at": generated_at,
                "updated_at": generated_at,
                "record_status": "active" if adjudication["resolution_state"] == "resolved" else "provisional",
            }
            if "normalized_value" in evidence:
                claim["normalized_value"] = evidence["normalized_value"]
            claims.append(claim)
            evidence_claims.append(claim)

        review_id = make_id("rvw", priority_id)
        reviews.append(
            {
                "schema_version": "1.0.0",
                "review_decision_id": review_id,
                "review_type": "classification",
                "subject_refs": [
                    {"entity_type": "lifecycle_national_priority_record", "entity_id": priority_id},
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
        )

        resolution_status = {"resolved": "resolved", "partial": "unresolved", "conflicting": "disputed"}[
            adjudication["resolution_state"]
        ]
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
            "resolution_id": make_id("res", priority_id),
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
            if not supporting:
                raise RuntimeError(f"Resolved priority record {priority_id} has no supporting status claim")
            resolution["resolved_value"] = {
                "type": "classification",
                "code": adjudication["resolved_current_status"],
            }
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
                if claim["source_id"] == event_spec["source_id"]
                and claim["attribute_path"] == f"event.{event_spec['event_type']}"
            ]
            if not matching_claims:
                raise RuntimeError(f"Event for {priority_id} lacks a matching source claim")
            events.append(
                {
                    "schema_version": "1.0.0",
                    "event_id": make_id("evt", priority_id, str(event_index)),
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

        for index, spec in enumerate(adjudication.get("observations", [])):
            attribute_path = {
                "facility.capacity.mw_observed": "observation.capacity_mw",
                "facility.area.building_sqft_observed": "observation.floor_area_sqft",
            }[spec["metric_code"]]
            matching_claims = [
                claim["claim_id"]
                for claim in evidence_claims
                if claim["source_id"] == spec["source_id"] and claim["attribute_path"] == attribute_path
            ]
            if not matching_claims:
                raise RuntimeError(f"Observation for {priority_id} lacks a matching source claim")
            observations.append(
                {
                    "schema_version": "1.0.0",
                    "observation_id": make_id("obs", priority_id, str(index)),
                    "metric_code": spec["metric_code"],
                    "subject": {"subject_type": "facility", "subject_id": facility_id},
                    "period": spec["period"],
                    "value": {"type": "quantity", "value": spec["value"], "unit": spec["unit"]},
                    "value_status": "observed",
                    "source_ids": [spec["source_id"]],
                    "source_claim_ids": matching_claims,
                    "release_vintage": "2026-08-31",
                    "revision_number": 0,
                    "created_at": generated_at,
                    "updated_at": generated_at,
                    "record_status": "active",
                }
            )

        result = {
            "schema_version": "1.0.0",
            "national_priority_id": priority_id,
            "initial_tranche_rank": candidate["initial_tranche_rank"],
            "facility_id": facility_id,
            "canonical_name": candidate["canonical_name"],
            "county_fips": candidate["primary_county_fips"],
            "county_name": candidate["county_name"],
            "state_abbr": candidate["state_abbr"],
            "census_region": candidate["census_region"],
            "evidence_status": {"resolved": "sufficient", "partial": "partial", "conflicting": "conflicting"}[
                adjudication["resolution_state"]
            ],
            "review_status": {"resolved": "verified", "partial": "in_research", "conflicting": "needs_review"}[
                adjudication["resolution_state"]
            ],
            "resolution_status": resolution_status,
            "evidence_source_ids": sorted({claim["source_id"] for claim in evidence_claims}),
            "review_decision_id": review_id,
            "rationale": adjudication["rationale"],
            "generated_at": generated_at,
        }
        if resolution_status == "resolved":
            result["resolved_current_status"] = adjudication["resolved_current_status"]
            result["resolution_confidence"] = adjudication["confidence"]
        operational_events = [
            event for event in adjudication.get("events", [])
            if event["event_type"] == "operational"
        ]
        if operational_events:
            result["operational_date"] = operational_events[0]["when"]
        for spec in adjudication.get("observations", []):
            if spec["metric_code"] == "facility.capacity.mw_observed":
                result["capacity_mw"] = spec["value"]
            elif spec["metric_code"] == "facility.area.building_sqft_observed":
                result["floor_area_sqft"] = spec["value"]
        public_results.append(result)

    public_results.sort(key=lambda item: item["initial_tranche_rank"])
    reviewed_ids = set(adjudication_ids)
    remaining_queue = sorted(
        [record for record in prior_queue if record["national_priority_id"] not in reviewed_ids],
        key=lambda item: item["initial_tranche_rank"],
    )

    reviewed_by_county: dict[str, Counter[str]] = {}
    for result in public_results:
        reviewed_by_county.setdefault(result["county_fips"], Counter())[result["review_status"]] += 1
    coverage = []
    for baseline in baseline_coverage:
        record = deepcopy(baseline)
        counts = reviewed_by_county.get(record["county_fips"], Counter())
        reviewed_count = sum(counts.values())
        record["queued_facility_count"] -= reviewed_count
        record["verified_facility_count"] += counts["verified"]
        record["in_research_facility_count"] += counts["in_research"]
        record["needs_review_facility_count"] += counts["needs_review"]
        record["unknown_status_facility_count"] -= counts["verified"]
        if record["queued_facility_count"] < 0 or record["unknown_status_facility_count"] < 0:
            raise RuntimeError(f"Coverage counters became negative for {record['county_fips']}")
        if record["queued_facility_count"]:
            record["coverage_status"] = "national_in_progress"
        elif reviewed_count:
            record["coverage_status"] = "national_reviewed"
        record["generated_at"] = generated_at
        coverage.append(record)

    reviewed_by_region = Counter(result["census_region"] for result in public_results)
    tranche_verified = sum(result["review_status"] == "verified" for result in public_results)
    metadata = {
        "schema_version": "1.0.0",
        "artifact_type": "public_national_lifecycle_verification_tranche_summary",
        "artifact_version": ARTIFACT_VERSION,
        "generated_at": generated_at,
        "tranche_id": TRANCHE_ID,
        "policy_id": POLICY_ID,
        "input_dataset_ids": [INPUT_DATASET_ID],
        "counts": {
            "active_canonical_facility_count": sum(record["active_canonical_facility_count"] for record in coverage),
            "initial_tranche_facility_count": 48,
            "reviewed_facility_count": len(public_results),
            "tranche_verified_facility_count": tranche_verified,
            "cumulative_verified_facility_count": sum(record["verified_facility_count"] for record in coverage),
            "in_research_facility_count": sum(record["in_research_facility_count"] for record in coverage),
            "needs_review_facility_count": sum(record["needs_review_facility_count"] for record in coverage),
            "remaining_queue_facility_count": len(remaining_queue),
            "unknown_status_facility_count": sum(record["unknown_status_facility_count"] for record in coverage),
            "source_count": len(sources),
            "claim_count": len(claims),
            "event_count": len(events),
            "observation_count": len(observations),
        },
        "reviewed_by_region": dict(sorted(reviewed_by_region.items())),
        "notices": METADATA_NOTICES,
    }
    document = {
        "schema_version": "1.0.0",
        "artifact_type": "national_lifecycle_verification_tranche",
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
    return document, public_results, remaining_queue, coverage, metadata


def main() -> int:
    document, results, remaining_queue, coverage, metadata = build()
    report = {**metadata, "artifact_type": "national_lifecycle_verification_tranche_processing_report"}
    outputs = [
        (f"data/silver/infrastructure/im3-2026.02.09-lifecycle-national-tranche-{OUTPUT_TRANCHE_NUMBER}.json", document, True, document["record_count"], "silver", "national_lifecycle_tranche"),
        (f"data/silver/infrastructure/im3-2026.02.09-lifecycle-national-tranche-{OUTPUT_TRANCHE_NUMBER}.processing-report.json", report, False, 1, "silver", "processing_report"),
        (f"site/public/data/v1/lifecycle/national-tranche-{OUTPUT_TRANCHE_NUMBER}-results.json", results, True, len(results), "public", "national_lifecycle_results"),
        (f"site/public/data/v1/lifecycle/national-tranche-{OUTPUT_TRANCHE_NUMBER}-remaining-queue.json", remaining_queue, True, len(remaining_queue), "public", "national_lifecycle_remaining_queue"),
        (f"site/public/data/v1/counties/lifecycle-national-tranche-{OUTPUT_TRANCHE_NUMBER}-coverage.json", coverage, True, len(coverage), "public", "national_lifecycle_coverage"),
        (f"site/public/data/v1/lifecycle/national-tranche-{OUTPUT_TRANCHE_NUMBER}-metadata.json", metadata, False, 1, "public", "national_lifecycle_metadata"),
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
        "artifact_type": "national_lifecycle_verification_tranche",
        "artifact_version": ARTIFACT_VERSION,
        "generated_at": metadata["generated_at"],
        "data_vintage": "2026-08-31",
        "record_schema": "https://dccio.org/schemas/v1/public-national-lifecycle-verification-record.schema.json",
        "format": "json",
        "parts": parts,
        "record_count": sum(part["record_count"] for part in parts),
        "input_dataset_ids": [INPUT_DATASET_ID],
        "license_metadata": {
            "license": "Mixed source metadata; IM3-derived records remain ODbL",
            "redistribution_status": "mixed",
            "attribution": ATTRIBUTION,
        },
    }
    write_json(
        ROOT / f"data/silver/infrastructure/im3-2026.02.09-lifecycle-national-tranche-{OUTPUT_TRANCHE_NUMBER}.manifest.json",
        manifest,
    )
    print(json.dumps(metadata, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

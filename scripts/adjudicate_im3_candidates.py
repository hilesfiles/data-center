#!/usr/bin/env python3
"""Apply curated, evidence-backed decisions to the IM3 resolution candidates."""

from __future__ import annotations

import hashlib
import json
from collections import defaultdict
from pathlib import Path
from typing import Any

from acquire_im3_facilities import ATTRIBUTION, RELEASE_VERSION, write_json
from resolve_im3_entities import stable_id


ROOT = Path(__file__).resolve().parents[1]
RULE_ID = "im3_candidate_adjudication_v1"
DATASET_ID = "im3_entity_adjudication_20260831"


def load(relative_path: str) -> Any:
    return json.loads((ROOT / relative_path).read_text(encoding="utf-8"))


def make_external_claim(
    candidate: dict[str, Any],
    adjudication: dict[str, Any],
    evidence: dict[str, str],
    generated_at: str,
) -> dict[str, Any]:
    subject = candidate["subject_refs"][0]
    decision = adjudication["decision"]
    claim_id = stable_id(
        "clm", "candidate_evidence", candidate["resolution_candidate_id"], evidence["source_id"]
    )
    value = {
        "resolution_candidate_id": candidate["resolution_candidate_id"],
        "decision_context": decision,
        "finding": evidence["finding"],
    }
    return {
        "schema_version": "1.0.0",
        "claim_id": claim_id,
        "source_id": evidence["source_id"],
        "subject": subject,
        "attribute_path": "identity.adjudication_evidence",
        "raw_value": {"type": "json", "value": value},
        "normalized_value": {"type": "json", "value": value},
        "extraction_method": "manual",
        "extractor_version": RULE_ID,
        "source_quality_score": 0.9,
        "claim_confidence": 0.9 if decision != "escalate" else 0.6,
        "review_status": "accepted" if decision != "escalate" else "needs_review",
        "notes": "Paraphrased finding retained with source metadata; no copyrighted page body is stored.",
        "created_at": generated_at,
        "updated_at": generated_at,
        "record_status": "provisional",
    }


def outcome_status(decision: str) -> str:
    if decision in {"merge", "accept"}:
        return "accepted"
    if decision in {"do_not_merge", "reject"}:
        return "rejected"
    return "pending"


def build_adjudication() -> tuple[dict[str, Any], dict[str, Any], dict[str, Any]]:
    base = load("data/silver/infrastructure/im3-2026.02.09-entity-resolution.json")
    source_index = load("site/public/data/v1/facilities/index.json")
    source_coverage = load("site/public/data/v1/counties/facility-source-coverage.json")
    evidence_sources_document = load("config/v1/im3-candidate-evidence-sources.json")
    adjudication_document = load("config/v1/im3-candidate-adjudications.json")
    generated_at = base["generated_at"]

    candidates = base["collections"]["entity_resolution_candidate"]
    candidate_by_id = {item["resolution_candidate_id"]: item for item in candidates}
    adjudications = adjudication_document["records"]
    adjudication_by_id = {item["resolution_candidate_id"]: item for item in adjudications}
    source_by_id = {item["source_id"]: item for item in evidence_sources_document["records"]}
    source_index_by_id = {item["entity_id"]: item for item in source_index}
    if set(candidate_by_id) != set(adjudication_by_id):
        raise RuntimeError("Every candidate must have exactly one curated adjudication")

    external_claims: list[dict[str, Any]] = []
    new_decisions: list[dict[str, Any]] = []
    containment_relationships: list[dict[str, Any]] = []
    merge_targets: dict[str, str] = {}
    campus_accepts: dict[str, str] = {}
    dossier: list[dict[str, Any]] = []

    for candidate in candidates:
        candidate_id = candidate["resolution_candidate_id"]
        adjudication = adjudication_by_id[candidate_id]
        evidence_claim_ids = list(candidate["evidence_claim_ids"])
        evidence_details: list[dict[str, Any]] = []
        for evidence in adjudication["evidence"]:
            if evidence["source_id"] == "src_im3_atlas_20260209":
                evidence_details.append(
                    {
                        **evidence,
                        "url": "https://doi.org/10.57931/3017294",
                        "title": "IM3 Open Source Data Center Atlas v2026.02.09",
                    }
                )
                continue
            claim = make_external_claim(candidate, adjudication, evidence, generated_at)
            external_claims.append(claim)
            evidence_claim_ids.append(claim["claim_id"])
            source = source_by_id[evidence["source_id"]]
            evidence_details.append(
                {**evidence, "url": source["url"], "title": source["title"]}
            )

        decision_id = stable_id("rev", "candidate_adjudication", candidate_id)
        new_decisions.append(
            {
                "schema_version": "1.0.0",
                "review_decision_id": decision_id,
                "review_type": "entity_match",
                "subject_refs": candidate["subject_refs"],
                "decision": adjudication["decision"],
                "rationale": adjudication["rationale"],
                "evidence_claim_ids": sorted(set(evidence_claim_ids)),
                "reviewer": {"type": "governed_rule", "identifier": RULE_ID},
                "decided_at": generated_at,
                "created_at": generated_at,
                "updated_at": generated_at,
                "record_status": "provisional",
            }
        )

        if adjudication["decision"] == "merge":
            source_entity_id = candidate["subject_refs"][0]["entity_id"]
            merge_targets[source_entity_id] = adjudication["canonical_entity_id"]
        elif adjudication["decision"] == "do_not_merge":
            contained_id = candidate["subject_refs"][0]["entity_id"]
            container_id = adjudication["container_facility_id"]
            containment_relationships.append(
                {
                    "schema_version": "1.0.0",
                    "relationship_id": stable_id("fcr", contained_id, container_id),
                    "contained_facility_id": contained_id,
                    "container_facility_id": container_id,
                    "relationship_type": "located_within_building",
                    "relationship_basis": "point_in_polygon_with_distinct_identity",
                    "source_claim_ids": sorted(set(evidence_claim_ids)),
                    "review_decision_id": decision_id,
                    "confidence": 0.9,
                    "created_at": generated_at,
                    "updated_at": generated_at,
                    "record_status": "provisional",
                }
            )
        elif (
            adjudication["decision"] == "accept"
            and candidate["candidate_type"] in {"building_campus_membership", "point_campus_membership"}
        ):
            campus_accepts[candidate["subject_refs"][0]["entity_id"]] = candidate["subject_refs"][1]["entity_id"]

        subjects = []
        for subject in candidate["subject_refs"]:
            source_record = source_index_by_id[subject["entity_id"]]
            subjects.append(
                {
                    "entity_id": subject["entity_id"],
                    "entity_type": subject["entity_type"],
                    "source_layer": source_record["source_layer"],
                    "display_name": source_record["display_name"],
                    "source_operator": source_record.get("source_operator"),
                    "primary_county_fips": source_record["primary_county_fips"],
                }
            )
        dossier.append(
            {
                "schema_version": "1.0.0",
                "resolution_candidate_id": candidate_id,
                "candidate_type": candidate["candidate_type"],
                "spatial_evidence": candidate["spatial_evidence"],
                "subjects": subjects,
                "decision": adjudication["decision"],
                "rationale": adjudication["rationale"],
                "evidence": evidence_details,
                "review_decision_id": decision_id,
                "generated_at": generated_at,
            }
        )

    updated_candidates = []
    for candidate in candidates:
        updated = dict(candidate)
        updated["candidate_status"] = outcome_status(
            adjudication_by_id[candidate["resolution_candidate_id"]]["decision"]
        )
        updated_candidates.append(updated)

    facilities = []
    facility_by_id = {
        item["facility_id"]: dict(item) for item in base["collections"]["facility"]
    }
    for source_entity_id, target_entity_id in merge_targets.items():
        source_facility = facility_by_id[source_entity_id]
        target_facility = facility_by_id[target_entity_id]
        source_facility["record_status"] = "superseded"
        preferred_name = source_facility["canonical_name"]
        aliases = set(target_facility.get("aliases", []))
        if (
            target_facility["canonical_name"] != preferred_name
            and not target_facility["canonical_name"].startswith("Unnamed IM3 ")
        ):
            aliases.add(target_facility["canonical_name"])
        target_facility["canonical_name"] = preferred_name
        if aliases:
            target_facility["aliases"] = sorted(aliases)
        target_facility["external_identifiers"] = sorted(
            target_facility.get("external_identifiers", [])
            + source_facility.get("external_identifiers", []),
            key=lambda item: (item["namespace"], item["value"]),
        )
    for facility_id, campus_id in campus_accepts.items():
        facility_by_id[facility_id]["campus_id"] = campus_id
    facilities = [facility_by_id[item["facility_id"]] for item in base["collections"]["facility"]]

    relationship_by_key: dict[tuple[str, str, str], dict[str, Any]] = {}
    for relationship in base["collections"]["operator_relationship"]:
        updated = dict(relationship)
        updated["subject_id"] = merge_targets.get(updated["subject_id"], updated["subject_id"])
        updated["relationship_id"] = stable_id(
            "rel", updated["operator_id"], updated["subject_id"], updated["relationship_type"]
        )
        key = (updated["operator_id"], updated["subject_id"], updated["relationship_type"])
        if key in relationship_by_key:
            existing = relationship_by_key[key]
            existing["source_claim_ids"] = sorted(
                set(existing["source_claim_ids"] + updated["source_claim_ids"])
            )
            existing["confidence"] = max(existing.get("confidence", 0), updated.get("confidence", 0))
        else:
            relationship_by_key[key] = updated
    operator_relationships = sorted(
        relationship_by_key.values(), key=lambda item: item["relationship_id"]
    )

    collections = {
        "campus": base["collections"]["campus"],
        "facility": facilities,
        "operator": base["collections"]["operator"],
        "operator_relationship": operator_relationships,
        "facility_containment_relationship": sorted(
            containment_relationships, key=lambda item: item["relationship_id"]
        ),
        "review_decision": sorted(
            base["collections"]["review_decision"] + new_decisions,
            key=lambda item: item["review_decision_id"],
        ),
        "entity_resolution_candidate": sorted(
            updated_candidates, key=lambda item: item["resolution_candidate_id"]
        ),
        "source": evidence_sources_document["records"],
        "claim": sorted(external_claims, key=lambda item: item["claim_id"]),
    }

    outcomes_by_entity: dict[str, list[dict[str, str]]] = defaultdict(list)
    for adjudication in adjudications:
        candidate = candidate_by_id[adjudication["resolution_candidate_id"]]
        for subject in candidate["subject_refs"]:
            outcomes_by_entity[subject["entity_id"]].append(
                {
                    "resolution_candidate_id": adjudication["resolution_candidate_id"],
                    "decision": adjudication["decision"],
                }
            )
    containment_by_entity = {
        item["contained_facility_id"]: item["container_facility_id"]
        for item in containment_relationships
    }
    public_records = []
    for source_record in source_index:
        source_entity_id = source_record["entity_id"]
        outcomes = sorted(
            outcomes_by_entity.get(source_entity_id, []),
            key=lambda item: item["resolution_candidate_id"],
        )
        resolved_entity_id = merge_targets.get(source_entity_id, source_entity_id)
        if source_entity_id in merge_targets:
            identity_status = "merged"
        elif source_entity_id in containment_by_entity:
            identity_status = "distinct_within_building"
        elif any(item["decision"] == "escalate" for item in outcomes):
            identity_status = "review_pending"
        else:
            identity_status = "unchanged"
        record = {
            "schema_version": "1.0.0",
            "source_entity_id": source_entity_id,
            "resolved_entity_id": resolved_entity_id,
            "identity_status": identity_status,
            "candidate_outcomes": outcomes,
            "generated_at": generated_at,
        }
        if source_entity_id in containment_by_entity:
            record["container_facility_id"] = containment_by_entity[source_entity_id]
        facility = facility_by_id.get(resolved_entity_id)
        if facility and facility.get("campus_id"):
            record["campus_id"] = facility["campus_id"]
        public_records.append(record)

    coverage_by_fips: dict[str, dict[str, Any]] = {}
    for source in source_coverage:
        coverage_by_fips[source["county_fips"]] = {
            "schema_version": "1.0.0",
            "county_fips": source["county_fips"],
            "county_name": source["county_name"],
            "state_abbr": source["state_abbr"],
            "reviewed_candidate_count": 0,
            "pending_candidate_count": 0,
            "merged_source_record_count": 0,
            "distinct_contained_facility_count": 0,
            "campus_linked_facility_count": 0,
            "adjudication_status": "no_source_record" if source["source_record_count"] == 0 else "no_candidate",
            "generated_at": generated_at,
        }
    for adjudication in adjudications:
        candidate = candidate_by_id[adjudication["resolution_candidate_id"]]
        source_record = source_index_by_id[candidate["subject_refs"][0]["entity_id"]]
        county = coverage_by_fips[source_record["primary_county_fips"]]
        if adjudication["decision"] == "escalate":
            county["pending_candidate_count"] += 1
        else:
            county["reviewed_candidate_count"] += 1
        county["merged_source_record_count"] += int(adjudication["decision"] == "merge")
        county["distinct_contained_facility_count"] += int(
            adjudication["decision"] == "do_not_merge"
        )
    for facility in facilities:
        if facility["record_status"] == "superseded" or not facility.get("campus_id"):
            continue
        source_record = source_index_by_id[facility["facility_id"]]
        for county_fips in source_record["county_fipses"]:
            coverage_by_fips[county_fips]["campus_linked_facility_count"] += 1
    public_coverage = [coverage_by_fips[key] for key in sorted(coverage_by_fips)]
    for county in public_coverage:
        if county["pending_candidate_count"]:
            county["adjudication_status"] = "review_pending"
        elif county["reviewed_candidate_count"]:
            county["adjudication_status"] = "reviewed"

    counts = {
        "candidate_count": len(candidates),
        "accepted_candidate_count": sum(item["candidate_status"] == "accepted" for item in updated_candidates),
        "rejected_candidate_count": sum(item["candidate_status"] == "rejected" for item in updated_candidates),
        "pending_candidate_count": sum(item["candidate_status"] == "pending" for item in updated_candidates),
        "merged_source_record_count": len(merge_targets),
        "distinct_contained_facility_count": len(containment_relationships),
        "campus_linked_facility_count": sum(
            item.get("campus_id") is not None and item["record_status"] != "superseded"
            for item in facilities
        ),
        "canonical_non_superseded_facility_count": sum(
            item["record_status"] != "superseded" for item in facilities
        ),
        "external_evidence_source_count": len(evidence_sources_document["records"]),
        "external_evidence_claim_count": len(external_claims),
        "adjudication_decision_count": len(new_decisions),
    }
    report = {
        "schema_version": "1.0.0",
        "artifact_type": "candidate_adjudication_processing_report",
        "artifact_version": "2026.08.31",
        "generated_at": generated_at,
        "governed_rule_id": RULE_ID,
        "counts": counts,
        "decision_counts": dict(
            sorted(
                {
                    decision: sum(item["decision"] == decision for item in adjudications)
                    for decision in {item["decision"] for item in adjudications}
                }.items()
            )
        ),
        "notices": [
            "A located-within-building relationship is not an identity merge or ownership assertion.",
            "Superseded source records remain preserved and redirect to their reviewed canonical facility.",
            "Escalated candidates remain pending and do not change campus or facility identity.",
        ],
    }
    public_metadata = {
        **report,
        "artifact_type": "public_candidate_adjudication_summary",
    }
    public = {
        "records": public_records,
        "coverage": public_coverage,
        "queue": [
            item for item in updated_candidates if item["candidate_status"] == "pending"
        ],
        "decisions": new_decisions,
        "dossier": sorted(dossier, key=lambda item: item["resolution_candidate_id"]),
        "metadata": public_metadata,
    }
    return collections, report, public


def digest(payload: bytes) -> str:
    return hashlib.sha256(payload).hexdigest()


def main() -> int:
    collections, report, public = build_adjudication()
    generated_at = report["generated_at"]
    document = {
        "schema_version": "1.0.0",
        "artifact_type": "provisional_entity_adjudication",
        "artifact_version": "2026.08.31",
        "generated_at": generated_at,
        "record_count": sum(len(records) for records in collections.values()),
        "collections": collections,
    }
    outputs = [
        ("data/silver/infrastructure/im3-2026.02.09-entity-adjudication.json", document, True, document["record_count"], "silver", "adjudicated_entities"),
        ("data/silver/infrastructure/im3-2026.02.09-entity-adjudication.processing-report.json", report, False, 1, "silver", "processing_report"),
        ("site/public/data/v1/entity-resolution/adjudication-index.json", public["records"], True, len(public["records"]), "public", "adjudication_index"),
        ("site/public/data/v1/counties/entity-adjudication-coverage.json", public["coverage"], True, len(public["coverage"]), "public", "county_adjudication_coverage"),
        ("site/public/data/v1/entity-resolution/review-queue.json", public["queue"], True, len(public["queue"]), "public", "review_queue"),
        ("site/public/data/v1/entity-resolution/review-decisions.json", public["decisions"], True, len(public["decisions"]), "public", "review_decisions"),
        ("site/public/data/v1/entity-resolution/review-dossier.json", public["dossier"], True, len(public["dossier"]), "public", "review_dossier"),
        ("site/public/data/v1/entity-resolution/adjudication-metadata.json", public["metadata"], False, 1, "public", "adjudication_metadata"),
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
        "artifact_type": "provisional_entity_adjudication",
        "artifact_version": "2026.08.31",
        "generated_at": generated_at,
        "data_vintage": "2026-08-31",
        "record_schema": "https://dccio.org/schemas/v1/catalog.json",
        "format": "json",
        "parts": parts,
        "record_count": sum(part["record_count"] for part in parts),
        "input_dataset_ids": ["im3_entity_resolution_20260209"],
        "license_metadata": {
            "license": "Mixed source metadata; ODbL applies to IM3-derived records",
            "redistribution_status": "metadata_only",
            "attribution": ATTRIBUTION,
        },
    }
    write_json(
        ROOT / "data/silver/infrastructure/im3-2026.02.09-entity-adjudication.manifest.json",
        manifest,
    )
    print(json.dumps(report, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

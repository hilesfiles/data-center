#!/usr/bin/env python3
"""Resolve the two escalated IM3 campus-boundary candidates.

This creates a downstream snapshot. The initial adjudication remains immutable;
its two escalation decisions are retained as superseded review history.
"""

from __future__ import annotations

import hashlib
import json
from copy import deepcopy
from pathlib import Path
from typing import Any

from acquire_im3_facilities import ATTRIBUTION, write_json
from resolve_im3_entities import stable_id


ROOT = Path(__file__).resolve().parents[1]
RULE_ID = "im3_final_boundary_review_v1"
DATASET_ID = "im3_final_boundary_review_20260831"
ARTIFACT_VERSION = "2026.08.31"


def load(relative_path: str) -> Any:
    return json.loads((ROOT / relative_path).read_text(encoding="utf-8"))


def outcome_status(decision: str) -> str:
    return "accepted" if decision in {"merge", "accept"} else "rejected"


def make_claim(
    candidate: dict[str, Any],
    decision: dict[str, Any],
    evidence: dict[str, str],
    generated_at: str,
) -> dict[str, Any]:
    value = {
        "resolution_candidate_id": candidate["resolution_candidate_id"],
        "decision_context": decision["decision"],
        "finding": evidence["finding"],
    }
    return {
        "schema_version": "1.0.0",
        "claim_id": stable_id(
            "clm", "final_boundary_evidence", candidate["resolution_candidate_id"], evidence["source_id"]
        ),
        "source_id": evidence["source_id"],
        "subject": candidate["subject_refs"][0],
        "attribute_path": "identity.final_boundary_evidence",
        "raw_value": {"type": "json", "value": value},
        "normalized_value": {"type": "json", "value": value},
        "extraction_method": "manual",
        "extractor_version": RULE_ID,
        "source_quality_score": 0.9,
        "claim_confidence": 0.95,
        "review_status": "accepted",
        "notes": "Paraphrased finding retained with source metadata; no copyrighted page body is stored.",
        "created_at": generated_at,
        "updated_at": generated_at,
        "record_status": "provisional",
    }


def build_final_review() -> tuple[dict[str, Any], dict[str, Any], dict[str, Any]]:
    prior = load("data/silver/infrastructure/im3-2026.02.09-entity-adjudication.json")
    prior_public = load("site/public/data/v1/entity-resolution/adjudication-index.json")
    prior_coverage = load("site/public/data/v1/counties/entity-adjudication-coverage.json")
    prior_dossier = load("site/public/data/v1/entity-resolution/review-dossier.json")
    source_index = load("site/public/data/v1/facilities/index.json")
    history_acquisition = load("data/raw/openstreetmap/im3-final-boundary-way-history.acquisition.json")
    source_document = load("config/v1/im3-final-boundary-evidence-sources.json")
    decision_document = load("config/v1/im3-final-boundary-decisions.json")
    generated_at = history_acquisition["retrieved_at"]

    collections = deepcopy(prior["collections"])
    candidates_by_id = {
        item["resolution_candidate_id"]: item
        for item in collections["entity_resolution_candidate"]
    }
    decisions = decision_document["records"]
    if len(decisions) != 2 or any(
        candidates_by_id[item["resolution_candidate_id"]]["candidate_status"] != "pending"
        for item in decisions
    ):
        raise RuntimeError("Final boundary decisions must resolve exactly the two pending candidates")

    sources_by_id = {item["source_id"]: item for item in source_document["records"]}
    source_index_by_id = {item["entity_id"]: item for item in source_index}
    new_claims: list[dict[str, Any]] = []
    new_review_decisions: list[dict[str, Any]] = []
    replacement_decisions: dict[str, dict[str, Any]] = {}
    merge_targets: dict[str, str] = {}
    dossier_replacements: dict[str, dict[str, Any]] = {}

    review_decisions_by_id = {
        item["review_decision_id"]: item for item in collections["review_decision"]
    }
    for decision in decisions:
        candidate_id = decision["resolution_candidate_id"]
        candidate = candidates_by_id[candidate_id]
        previous_decision_id = stable_id("rev", "candidate_adjudication", candidate_id)
        previous_decision = review_decisions_by_id[previous_decision_id]
        if previous_decision["decision"] != "escalate":
            raise RuntimeError(f"Candidate {candidate_id} does not supersede an escalation")
        previous_decision["record_status"] = "superseded"
        previous_decision["updated_at"] = generated_at

        evidence_claim_ids = list(candidate["evidence_claim_ids"])
        evidence_details = []
        for evidence in decision["evidence"]:
            if evidence["source_id"] == "src_im3_atlas_20260209":
                evidence_details.append(
                    {
                        **evidence,
                        "title": "IM3 Open Source Data Center Atlas v2026.02.09",
                        "url": "https://doi.org/10.57931/3017294",
                    }
                )
                continue
            claim = make_claim(candidate, decision, evidence, generated_at)
            new_claims.append(claim)
            evidence_claim_ids.append(claim["claim_id"])
            source = sources_by_id[evidence["source_id"]]
            evidence_details.append({**evidence, "title": source["title"], "url": source["url"]})

        review_decision_id = stable_id("rev", "final_boundary_review", candidate_id)
        new_review_decisions.append(
            {
                "schema_version": "1.0.0",
                "review_decision_id": review_decision_id,
                "review_type": "entity_match",
                "subject_refs": candidate["subject_refs"],
                "decision": decision["decision"],
                "rationale": decision["rationale"],
                "evidence_claim_ids": sorted(set(evidence_claim_ids)),
                "reviewer": {"type": "governed_rule", "identifier": RULE_ID},
                "decided_at": generated_at,
                "supersedes_decision_id": previous_decision_id,
                "created_at": generated_at,
                "updated_at": generated_at,
                "record_status": "provisional",
            }
        )
        replacement_decisions[candidate_id] = decision

        updated_candidate = candidates_by_id[candidate_id]
        updated_candidate["candidate_status"] = outcome_status(decision["decision"])
        if decision["decision"] == "merge":
            canonical_id = decision["canonical_entity_id"]
            noncanonical = [
                ref["entity_id"] for ref in candidate["subject_refs"] if ref["entity_id"] != canonical_id
            ]
            if len(noncanonical) != 1:
                raise RuntimeError(f"Candidate {candidate_id} does not have one merge source")
            merge_targets[noncanonical[0]] = canonical_id

        prior_item = next(
            item for item in prior_dossier if item["resolution_candidate_id"] == candidate_id
        )
        dossier_replacements[candidate_id] = {
            **prior_item,
            "decision": decision["decision"],
            "rationale": decision["rationale"],
            "evidence": evidence_details,
            "review_decision_id": review_decision_id,
            "supersedes_review_decision_id": previous_decision_id,
            "generated_at": generated_at,
        }

    campus_by_id = {item["campus_id"]: item for item in collections["campus"]}
    facility_by_id = {item["facility_id"]: item for item in collections["facility"]}
    for source_id, canonical_id in merge_targets.items():
        if source_id in campus_by_id:
            campus_by_id[source_id]["record_status"] = "superseded"
            campus_by_id[source_id]["updated_at"] = generated_at
        elif source_id in facility_by_id:
            facility_by_id[source_id]["record_status"] = "superseded"
            facility_by_id[source_id]["updated_at"] = generated_at
        else:
            raise RuntimeError(f"Unknown merge source {source_id}")
        if canonical_id not in facility_by_id and canonical_id not in campus_by_id:
            raise RuntimeError(f"Unknown canonical entity {canonical_id}")

    collections["review_decision"] = sorted(
        collections["review_decision"] + new_review_decisions,
        key=lambda item: item["review_decision_id"],
    )
    collections["source"] = sorted(
        collections["source"] + source_document["records"], key=lambda item: item["source_id"]
    )
    collections["claim"] = sorted(
        collections["claim"] + new_claims, key=lambda item: item["claim_id"]
    )

    public_records = deepcopy(prior_public)
    public_by_id = {item["source_entity_id"]: item for item in public_records}
    for candidate_id, decision in replacement_decisions.items():
        candidate = candidates_by_id[candidate_id]
        for subject in candidate["subject_refs"]:
            record = public_by_id[subject["entity_id"]]
            for outcome in record["candidate_outcomes"]:
                if outcome["resolution_candidate_id"] == candidate_id:
                    outcome["decision"] = decision["decision"]
            if record["identity_status"] == "review_pending":
                record["identity_status"] = "unchanged"
            record["generated_at"] = generated_at
    for source_id, canonical_id in merge_targets.items():
        public_by_id[source_id]["resolved_entity_id"] = canonical_id
        public_by_id[source_id]["identity_status"] = "merged"

    coverage = deepcopy(prior_coverage)
    coverage_by_fips = {item["county_fips"]: item for item in coverage}
    for candidate_id, decision in replacement_decisions.items():
        candidate = candidates_by_id[candidate_id]
        subject_id = candidate["subject_refs"][0]["entity_id"]
        county = coverage_by_fips[source_index_by_id[subject_id]["primary_county_fips"]]
        county["pending_candidate_count"] -= 1
        county["reviewed_candidate_count"] += 1
        county["merged_source_record_count"] += int(decision["decision"] == "merge")
        county["adjudication_status"] = "reviewed"
        county["generated_at"] = generated_at

    dossier = [
        dossier_replacements.get(item["resolution_candidate_id"], item)
        for item in prior_dossier
    ]
    all_candidates = collections["entity_resolution_candidate"]
    counts = {
        "candidate_count": len(all_candidates),
        "accepted_candidate_count": sum(item["candidate_status"] == "accepted" for item in all_candidates),
        "rejected_candidate_count": sum(item["candidate_status"] == "rejected" for item in all_candidates),
        "pending_candidate_count": sum(item["candidate_status"] == "pending" for item in all_candidates),
        "merged_source_record_count": sum(
            item["identity_status"] == "merged" for item in public_records
        ),
        "distinct_contained_facility_count": len(collections["facility_containment_relationship"]),
        "campus_linked_facility_count": sum(
            item.get("campus_id") is not None and item["record_status"] != "superseded"
            for item in collections["facility"]
        ),
        "canonical_non_superseded_facility_count": sum(
            item["record_status"] != "superseded" for item in collections["facility"]
        ),
        "active_campus_count": sum(item["record_status"] != "superseded" for item in collections["campus"]),
        "final_evidence_source_count": len(source_document["records"]),
        "final_evidence_claim_count": len(new_claims),
        "final_review_decision_count": len(new_review_decisions),
        "total_review_decision_count": len(collections["review_decision"]),
    }
    report = {
        "schema_version": "1.0.0",
        "artifact_type": "final_boundary_review_processing_report",
        "artifact_version": ARTIFACT_VERSION,
        "generated_at": generated_at,
        "governed_rule_id": RULE_ID,
        "counts": counts,
        "final_decision_counts": {
            decision: sum(item["decision"] == decision for item in decisions)
            for decision in sorted({item["decision"] for item in decisions})
        },
        "notices": [
            "All sixteen first-pass spatial identity candidates now have evidence-backed outcomes.",
            "The smaller One Wilshire source polygon is a superseded building part, not a campus.",
            "The Lumen building and 4010 Data Center campus remain separate identities at different addresses.",
            "Source objects and superseded review decisions remain preserved for auditability.",
        ],
    }
    public = {
        "records": sorted(public_records, key=lambda item: item["source_entity_id"]),
        "coverage": sorted(coverage, key=lambda item: item["county_fips"]),
        "queue": [item for item in all_candidates if item["candidate_status"] == "pending"],
        "decisions": new_review_decisions,
        "dossier": sorted(dossier, key=lambda item: item["resolution_candidate_id"]),
        "metadata": {**report, "artifact_type": "public_final_boundary_review_summary"},
    }
    return collections, report, public


def digest(payload: bytes) -> str:
    return hashlib.sha256(payload).hexdigest()


def main() -> int:
    collections, report, public = build_final_review()
    document = {
        "schema_version": "1.0.0",
        "artifact_type": "provisional_final_boundary_review",
        "artifact_version": ARTIFACT_VERSION,
        "generated_at": report["generated_at"],
        "record_count": sum(len(records) for records in collections.values()),
        "collections": collections,
    }
    outputs = [
        ("data/silver/infrastructure/im3-2026.02.09-final-boundary-review.json", document, True, document["record_count"], "silver", "final_boundary_review"),
        ("data/silver/infrastructure/im3-2026.02.09-final-boundary-review.processing-report.json", report, False, 1, "silver", "processing_report"),
        ("site/public/data/v1/entity-resolution/final-index.json", public["records"], True, len(public["records"]), "public", "final_adjudication_index"),
        ("site/public/data/v1/counties/final-review-coverage.json", public["coverage"], True, len(public["coverage"]), "public", "final_review_coverage"),
        ("site/public/data/v1/entity-resolution/final-review-queue.json", public["queue"], True, len(public["queue"]), "public", "final_review_queue"),
        ("site/public/data/v1/entity-resolution/final-review-decisions.json", public["decisions"], True, len(public["decisions"]), "public", "final_review_decisions"),
        ("site/public/data/v1/entity-resolution/final-review-dossier.json", public["dossier"], True, len(public["dossier"]), "public", "final_review_dossier"),
        ("site/public/data/v1/entity-resolution/final-review-metadata.json", public["metadata"], False, 1, "public", "final_review_metadata"),
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
        "artifact_type": "provisional_final_boundary_review",
        "artifact_version": ARTIFACT_VERSION,
        "generated_at": report["generated_at"],
        "data_vintage": "2026-08-31",
        "record_schema": "https://dccio.org/schemas/v1/catalog.json",
        "format": "json",
        "parts": parts,
        "record_count": sum(part["record_count"] for part in parts),
        "input_dataset_ids": ["im3_entity_adjudication_20260831"],
        "license_metadata": {
            "license": "Mixed source metadata; ODbL applies to IM3 and OSM-derived records",
            "redistribution_status": "metadata_only",
            "attribution": ATTRIBUTION,
        },
    }
    write_json(
        ROOT / "data/silver/infrastructure/im3-2026.02.09-final-boundary-review.manifest.json",
        manifest,
    )
    print(json.dumps(report, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

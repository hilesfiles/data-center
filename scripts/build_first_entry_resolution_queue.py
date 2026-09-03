#!/usr/bin/env python3
"""Build the append-only successor queue for county first-entry resolution.

This builder promotes evidence into a new research candidate generation. It never
changes a prior adjudication, assigns a treatment date, or labels an unresolved
county as never treated.
"""

from __future__ import annotations

import hashlib
import json
import math
from collections import Counter
from pathlib import Path
from typing import Any

from acquire_census_counties import write_json


ROOT = Path(__file__).resolve().parents[1]
BUILD_VERSION = "first-entry-resolution-v1.0"
TREATMENT_ID = "trt_first_entry_v1"
PANEL_START_YEAR = 2001
PANEL_END_YEAR = 2024
MINIMUM_PRE_PERIODS = 7
MINIMUM_POST_PERIODS = 3
AUTHORITATIVE_SOURCE_TYPES = {
    "federal_dataset", "state_record", "local_government_record", "planning_record",
    "zoning_record", "permit_record", "assessor_record", "utility_filing",
    "regulatory_filing", "court_record", "sec_filing", "incentive_agreement",
    "operator_release", "legislative_record",
}
PRECISION_RANK = {
    "unknown": 0, "range": 0, "approximate_year": 1, "year": 2,
    "quarter": 3, "month": 4, "day": 5,
}
PRECISION_MULTIPLIER = {
    "unknown": 0.0, "range": 0.5, "approximate_year": 0.65, "year": 0.8,
    "quarter": 0.88, "month": 0.95, "day": 1.0,
}


def load_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def digest(payload: bytes) -> str:
    return hashlib.sha256(payload).hexdigest()


def stable_id(prefix: str, *parts: str) -> str:
    value = hashlib.sha256("\x1f".join(parts).encode("utf-8")).hexdigest()[:20]
    return f"{prefix}_{value}"


def temporal_year(when: dict[str, Any]) -> int:
    if "year" in when:
        return int(when["year"])
    if "date" in when:
        return int(str(when["date"])[:4])
    if "date_lower" in when:
        return int(str(when["date_lower"])[:4])
    raise RuntimeError(f"Temporal extent does not contain a usable year: {when}")


def temporal_sort_key(when: dict[str, Any]) -> tuple[int, str]:
    return (temporal_year(when), str(when.get("date", when.get("date_lower", ""))))


def tier_for(score: float, tiers: list[dict[str, Any]]) -> str:
    for tier in tiers:
        if float(tier["minimum_score"]) <= score <= float(tier["maximum_score"]):
            return tier["tier"]
    raise RuntimeError(f"Priority score {score} is outside the configured tiers")


def load_source_lookup() -> dict[str, dict[str, Any]]:
    lookup: dict[str, dict[str, Any]] = {}
    for path in sorted((ROOT / "config" / "v1").glob("*evidence-sources.json")):
        document = load_json(path)
        for source in document.get("records", document.get("sources", [])):
            source_id = source["source_id"]
            existing = lookup.get(source_id)
            if existing is not None and existing != source:
                raise RuntimeError(f"Conflicting evidence source definition {source_id}")
            lookup[source_id] = source
    return lookup


def source_summary(
    source_ids: list[str], source_lookup: dict[str, dict[str, Any]]
) -> tuple[int, float]:
    missing = sorted(set(source_ids) - set(source_lookup))
    if missing:
        raise RuntimeError(f"Resolution anchor references unknown sources: {missing}")
    sources = [source_lookup[source_id] for source_id in source_ids]
    authoritative_types = {
        source["source_type"] for source in sources
        if source["source_type"] in AUTHORITATIVE_SOURCE_TYPES
    }
    best_quality = max(float(source.get("source_quality_prior", 0.0)) for source in sources)
    return len(authoritative_types), best_quality


def gate_status_for(
    when: dict[str, Any], evidence_score: float, authoritative_type_count: int
) -> dict[str, Any]:
    year = temporal_year(when)
    pre_periods = max(0, min(24, year - PANEL_START_YEAR))
    post_periods = max(0, min(24, PANEL_END_YEAR - year))
    precision = when["precision"]
    evidence_pass = (
        evidence_score >= 80
        and PRECISION_RANK.get(precision, 0) >= PRECISION_RANK["year"]
        and authoritative_type_count >= 1
    )
    period_pass = pre_periods >= MINIMUM_PRE_PERIODS and post_periods >= MINIMUM_POST_PERIODS
    return {
        "evidence_threshold_status": "passed" if evidence_pass else "failed",
        "period_requirement_status": "passed" if period_pass else "failed",
        "both_model_gates_pass": evidence_pass and period_pass,
        "available_pre_periods": pre_periods,
        "available_post_periods": post_periods,
    }


def build() -> dict[str, Any]:
    policy = load_json(ROOT / "config" / "v1" / "first-entry-resolution-policy.json")
    generated_at = policy["updated_at"]
    weights = policy["scoring"]["weights"]
    if not math.isclose(sum(float(value) for value in weights.values()), 100.0, abs_tol=1e-9):
        raise RuntimeError("First-entry resolution scoring weights must sum to 100")

    predecessor_document = load_json(
        ROOT / "data" / "silver" / "treatments"
        / "county-first-entry-research-priority-v1.json"
    )
    predecessor_records = predecessor_document["collections"]["first_entry_research_candidate"]
    if len(predecessor_records) != 217:
        raise RuntimeError(f"Expected 217 predecessor candidates; found {len(predecessor_records)}")
    if any(record["research_status"] != policy["eligibility"]["predecessor_research_status"] for record in predecessor_records):
        raise RuntimeError("Every successor input must have completed predecessor research")

    treatment_document = load_json(
        ROOT / "data" / "silver" / "treatments" / "county-first-entry-v1.json"
    )
    evaluations = {
        record["treatment_event_evaluation_id"]: record
        for record in treatment_document["collections"]["treatment_event_evaluation"]
    }
    assessments = {
        record["county_fips"]: record
        for record in treatment_document["collections"]["county_treatment_assessment"]
    }
    adjudications = load_json(
        ROOT / "config" / "v1" / "first-entry-anchor-adjudications.json"
    )["records"]
    adjudication_by_fips = {record["county_fips"]: record for record in adjudications}
    if len(adjudication_by_fips) != len(adjudications):
        raise RuntimeError("Duplicate county in first-entry adjudications")
    source_lookup = load_source_lookup()

    if any(assessments[record["county_fips"]]["assessment_status"] == "eligible" for record in predecessor_records):
        raise RuntimeError("Already eligible treatments must not enter the successor queue")

    state_to_region = {
        state_abbr: frame["region"]
        for frame in policy["regional_frame"]
        for state_abbr in frame["state_abbrs"]
    }
    all_state_abbrs = sorted(state_to_region)
    max_facility_count = max(int(record["active_canonical_facility_count"]) for record in predecessor_records)
    required_findings = policy["research_protocol"]["required_findings"]

    candidates: list[dict[str, Any]] = []
    for predecessor in predecessor_records:
        county_fips = predecessor["county_fips"]
        adjudication = adjudication_by_fips.get(county_fips)
        anchor: dict[str, Any] | None = None
        prior_evaluation_id: str | None = None
        prior_adjudication_id: str | None = None
        authoritative_type_count = 0
        evidence_score = 0.0
        predecessor_count = 0

        if adjudication is None:
            track = "establish_anchor"
            generation = 1
            finding_status = {finding: "unresolved" for finding in required_findings}
            gate_status = {
                "evidence_threshold_status": "not_evaluated",
                "period_requirement_status": "not_evaluated",
                "both_model_gates_pass": False,
                "available_pre_periods": 0,
                "available_post_periods": 0,
            }
            research_summary = (
                "Completed predecessor research did not establish a dated exact-facility anchor. "
                "The successor search must establish that anchor before county inventory closure."
            )
        elif adjudication["resolution_state"] == "candidate_rejected_first_entry":
            track = "promote_predecessor"
            generation = 2
            findings = adjudication["earlier_operational_findings"]
            if not findings:
                raise RuntimeError(f"Rejected county {county_fips} has no predecessor finding")
            finding = min(
                findings,
                key=lambda item: (temporal_sort_key(item["when"]), item["facility_id"]),
            )
            source_ids = sorted(set(finding["source_ids"]))
            authoritative_type_count, best_source_quality = source_summary(source_ids, source_lookup)
            evidence_score = round(
                best_source_quality
                * float(finding["confidence"])
                * PRECISION_MULTIPLIER.get(finding["when"]["precision"], 0.0)
                * 100.0,
                2,
            )
            anchor = {
                "facility_id": finding["facility_id"],
                "canonical_name": finding["canonical_name"],
                "when": finding["when"],
                "source_ids": source_ids,
                "derivation": "promoted_earlier_finding",
                "confidence": float(finding["confidence"]),
                "evidence_score": evidence_score,
            }
            gate_status = gate_status_for(finding["when"], evidence_score, authoritative_type_count)
            finding_status = {
                "earliest_dated_operational_event": "partial",
                "exact_facility_identity_for_earliest_event": "resolved",
                "county_inventory_completeness": "unresolved",
                "documented_search_for_earlier_operations": "partial",
            }
            predecessor_count = len(findings)
            prior_adjudication_id = adjudication["county_first_entry_adjudication_id"]
            prior_evaluation_id = adjudication["candidate_event_evaluation_id"]
            research_summary = (
                "The prior candidate was rejected after an earlier operation was documented. "
                "That earliest documented predecessor is promoted as a new candidate; research "
                "must test it against any still-earlier operation and close the county inventory."
            )
        elif adjudication["resolution_state"] == "unresolved":
            track = "resolve_existing_anchor"
            generation = 1
            prior_adjudication_id = adjudication["county_first_entry_adjudication_id"]
            prior_evaluation_id = adjudication["candidate_event_evaluation_id"]
            evaluation = evaluations[prior_evaluation_id]
            source_ids = sorted(set(adjudication["source_ids"]))
            _, _ = source_summary(source_ids, source_lookup)
            authoritative_type_count = len({
                source_type for source_type in adjudication["authoritative_source_types"]
                if source_type in AUTHORITATIVE_SOURCE_TYPES
            })
            evidence_score = float(evaluation["data_quality_score"])
            anchor = {
                "facility_id": evaluation["facility_id"],
                "canonical_name": evaluation["canonical_name"],
                "when": evaluation["when"],
                "source_ids": source_ids,
                "derivation": "existing_dated_candidate",
                "confidence": float(evaluation["claim_confidence"]),
                "evidence_score": evidence_score,
            }
            gate_status = {
                "evidence_threshold_status": evaluation["evidence_threshold_status"],
                "period_requirement_status": evaluation["period_requirement_status"],
                "both_model_gates_pass": (
                    evaluation["evidence_threshold_status"] == "passed"
                    and evaluation["period_requirement_status"] == "passed"
                ),
                "available_pre_periods": int(evaluation["available_pre_periods"]),
                "available_post_periods": int(evaluation["available_post_periods"]),
            }
            finding_status = dict(adjudication["required_finding_status"])
            research_summary = (
                "A dated exact-facility anchor is retained from the prior adjudication. "
                "Research must complete the historical county inventory and conclusive "
                "earlier-operation search before first entry can be verified."
            )
        else:
            raise RuntimeError(
                f"Unsupported first-entry resolution state {adjudication['resolution_state']}"
            )

        facility_count = int(predecessor["active_canonical_facility_count"])
        audit_feasibility = (
            100.0 if max_facility_count <= 1
            else 100.0 * (1.0 - math.log(facility_count) / math.log(max_facility_count))
        )
        gates_passed = sum(
            gate_status[key] == "passed"
            for key in ("evidence_threshold_status", "period_requirement_status")
        )
        components = {
            "model_gate_readiness": float(gates_passed * 50),
            "predecessor_promotability": {
                "promote_predecessor": 100.0,
                "resolve_existing_anchor": 50.0,
                "establish_anchor": 0.0,
            }[track],
            "inventory_audit_feasibility": round(max(0.0, audit_feasibility), 2),
            "anchor_evidence_quality": round(evidence_score, 2),
            "authoritative_source_diversity": float(min(100, authoritative_type_count * 50)),
            "required_finding_closure": round(
                sum(status == "resolved" for status in finding_status.values())
                / len(required_findings) * 100.0,
                2,
            ),
        }
        priority_score = round(
            sum(components[name] * float(weights[name]) / 100.0 for name in weights), 2
        )
        remaining_findings = [
            finding for finding in required_findings if finding_status[finding] != "resolved"
        ]
        reasons = [f"resolution_track:{track}"]
        if gate_status["both_model_gates_pass"]:
            reasons.append("candidate_passes_model_evidence_and_period_gates")
        if facility_count <= 5:
            reasons.append("manageable_inventory_audit_scope")
        if authoritative_type_count >= 2:
            reasons.append("multiple_authoritative_source_types")
        if anchor is not None:
            reasons.append("dated_exact_facility_candidate_available")

        candidate = {
            "schema_version": "1.0.0",
            "resolution_candidate_id": stable_id(
                "frc", policy["policy_id"], county_fips, str(generation)
            ),
            "first_entry_research_candidate_id": predecessor["first_entry_research_candidate_id"],
            "treatment_definition_id": TREATMENT_ID,
            "county_fips": county_fips,
            "county_name": predecessor["county_name"],
            "state_abbr": predecessor["state_abbr"],
            "census_region": state_to_region[predecessor["state_abbr"]],
            "resolution_track": track,
            "candidate_generation": generation,
            "active_canonical_facility_count": facility_count,
            "predecessor_count": predecessor_count,
            "gate_status": gate_status,
            "authoritative_source_type_count": authoritative_type_count,
            "required_finding_status": finding_status,
            "remaining_findings": remaining_findings,
            "score_components": components,
            "priority_score": priority_score,
            "priority_tier": tier_for(priority_score, policy["priority_tiers"]),
            "national_rank": 0,
            "region_rank": 0,
            "queue_status": "national_backlog",
            "resolution_status": "queued",
            "resolution_objective": "verify_county_first_operational_entry",
            "selection_reasons": reasons,
            "research_summary": research_summary,
            "created_at": generated_at,
            "updated_at": generated_at,
            "record_status": "provisional",
        }
        if anchor is not None:
            candidate["candidate_anchor"] = anchor
            candidate["prior_adjudication_id"] = prior_adjudication_id
            candidate["prior_candidate_event_evaluation_id"] = prior_evaluation_id
        candidates.append(candidate)

    candidates.sort(key=lambda record: (-record["priority_score"], record["county_fips"]))
    region_ranks: Counter[str] = Counter()
    for national_rank, record in enumerate(candidates, start=1):
        record["national_rank"] = national_rank
        region_ranks[record["census_region"]] += 1
        record["region_rank"] = region_ranks[record["census_region"]]

    tranche_policy = policy["initial_tranche"]
    selected_ids: set[str] = set()
    for region in [frame["region"] for frame in policy["regional_frame"]]:
        state_counts: Counter[str] = Counter()
        selected_count = 0
        for record in candidates:
            if record["census_region"] != region:
                continue
            if record["priority_tier"] == tranche_policy["exclude_tier"]:
                continue
            if state_counts[record["state_abbr"]] >= int(tranche_policy["max_per_state"]):
                continue
            selected_ids.add(record["resolution_candidate_id"])
            state_counts[record["state_abbr"]] += 1
            selected_count += 1
            if selected_count == int(tranche_policy["per_region_quota"]):
                break
        if selected_count != int(tranche_policy["per_region_quota"]):
            raise RuntimeError(f"Could not satisfy the configured resolution quota for {region}")
    if len(selected_ids) != int(tranche_policy["size"]):
        raise RuntimeError("Resolution initial tranche size does not match policy")

    initial_tranche = [
        record for record in candidates if record["resolution_candidate_id"] in selected_ids
    ]
    for initial_rank, record in enumerate(initial_tranche, start=1):
        record["queue_status"] = "initial_tranche"
        record["initial_tranche_rank"] = initial_rank

    resolution_adjudication_path = (
        ROOT / "config" / "v1" / "first-entry-resolution-tranche-1-adjudications.json"
    )
    resolution_adjudication_document = load_json(resolution_adjudication_path)
    resolution_adjudications = resolution_adjudication_document["records"]
    if resolution_adjudication_document.get("record_count") != len(resolution_adjudications):
        raise RuntimeError("Resolution adjudication record count is inconsistent")
    adjudication_by_candidate_id = {
        record["resolution_candidate_id"]: record for record in resolution_adjudications
    }
    if len(adjudication_by_candidate_id) != len(resolution_adjudications):
        raise RuntimeError("Duplicate resolution candidate adjudication")
    expected_adjudicated_ids = {
        record["resolution_candidate_id"] for record in initial_tranche[:8]
    }
    if set(adjudication_by_candidate_id) != expected_adjudicated_ids:
        raise RuntimeError("Tranche-one adjudications must cover initial-tranche ranks 1-8")
    candidate_by_id = {record["resolution_candidate_id"]: record for record in candidates}
    for adjudication in resolution_adjudications:
        candidate = candidate_by_id[adjudication["resolution_candidate_id"]]
        if (
            adjudication["county_fips"] != candidate["county_fips"]
            or adjudication["county_name"] != candidate["county_name"]
            or adjudication["state_abbr"] != candidate["state_abbr"]
            or adjudication["candidate_generation"] != candidate["candidate_generation"]
            or adjudication["reviewed_anchor"] != candidate.get("candidate_anchor")
            or adjudication.get("prior_adjudication_id") != candidate.get("prior_adjudication_id")
        ):
            raise RuntimeError(
                f"Resolution adjudication lineage mismatch for {candidate['resolution_candidate_id']}"
            )
        candidate["resolution_status"] = "evidence_collected"
        candidate["resolution_adjudication_id"] = adjudication["resolution_adjudication_id"]
        candidate["latest_resolution_state"] = adjudication["resolution_state"]
        candidate["updated_at"] = adjudication["updated_at"]

    silver_document = {
        "schema_version": "1.0.0",
        "artifact_type": "county_first_entry_resolution_priority_registry",
        "artifact_version": BUILD_VERSION,
        "generated_at": generated_at,
        "policy_id": policy["policy_id"],
        "record_count": len(candidates),
        "collections": {"first_entry_resolution_candidate": candidates},
    }
    silver_path = ROOT / "data" / "silver" / "treatments" / "county-first-entry-resolution-priority-v1.json"
    silver_payload = write_json(silver_path, silver_document, compact=True)

    public_directory = (
        ROOT / "site" / "public" / "data" / "v1" / "treatments"
        / "county-first-entry-resolution"
    )
    public_parts: list[tuple[Path, bytes, int]] = []
    index_parts: list[dict[str, Any]] = []
    for state_abbr in all_state_abbrs:
        state_records = [record for record in candidates if record["state_abbr"] == state_abbr]
        state_path = public_directory / "by-state" / f"{state_abbr.lower()}.json"
        state_payload = write_json(state_path, state_records, compact=True)
        public_parts.append((state_path, state_payload, len(state_records)))
        index_parts.append({
            "state_abbr": state_abbr,
            "path": f"county-first-entry-resolution/by-state/{state_abbr.lower()}.json",
            "record_count": len(state_records),
            "byte_size": len(state_payload),
            "sha256": digest(state_payload),
        })

    track_counts = Counter(record["resolution_track"] for record in candidates)
    gate_counts = Counter(
        "both_passed" if record["gate_status"]["both_model_gates_pass"] else "not_both_passed"
        for record in candidates
    )
    tier_counts = Counter(record["priority_tier"] for record in candidates)
    region_counts = Counter(record["census_region"] for record in candidates)
    tranche_track_counts = Counter(record["resolution_track"] for record in initial_tranche)
    tranche_region_counts = Counter(record["census_region"] for record in initial_tranche)
    public_index = {
        "schema_version": "1.0.0",
        "artifact_type": "county_first_entry_resolution_public_index",
        "artifact_version": BUILD_VERSION,
        "generated_at": generated_at,
        "policy_id": policy["policy_id"],
        "partition_count": len(index_parts),
        "record_count": len(candidates),
        "initial_tranche_count": len(initial_tranche),
        "adjudication_count": len(resolution_adjudications),
        "adjudications_path": "county-first-entry-resolution/adjudications.json",
        "evidence_sources_path": "county-first-entry-resolution/evidence-sources.json",
        "resolution_track_counts": dict(sorted(track_counts.items())),
        "resolution_status_counts": dict(sorted(Counter(record["resolution_status"] for record in candidates).items())),
        "priority_tier_counts": dict(sorted(tier_counts.items())),
        "region_counts": dict(sorted(region_counts.items())),
        "initial_tranche_region_counts": dict(sorted(tranche_region_counts.items())),
        "partitions": index_parts,
    }
    index_path = public_directory / "index.json"
    index_payload = write_json(index_path, public_index)
    tranche_path = public_directory / "initial-tranche.json"
    tranche_payload = write_json(tranche_path, initial_tranche)
    public_adjudication_path = public_directory / "adjudications.json"
    public_adjudication_payload = write_json(
        public_adjudication_path, resolution_adjudication_document
    )
    referenced_source_ids = sorted({
        source_id
        for adjudication in resolution_adjudications
        for source_id in adjudication["source_ids"]
    })
    missing_public_sources = sorted(set(referenced_source_ids) - set(source_lookup))
    if missing_public_sources:
        raise RuntimeError(f"Resolution adjudications reference unknown sources: {missing_public_sources}")
    public_evidence_document = {
        "schema_version": "1.0.0",
        "artifact_type": "first_entry_resolution_evidence_sources",
        "generated_at": generated_at,
        "record_count": len(referenced_source_ids),
        "records": [source_lookup[source_id] for source_id in referenced_source_ids],
    }
    public_evidence_path = public_directory / "evidence-sources.json"
    public_evidence_payload = write_json(public_evidence_path, public_evidence_document)

    report = {
        "schema_version": "1.0.0",
        "artifact_type": "county_first_entry_resolution_processing_report",
        "artifact_version": BUILD_VERSION,
        "generated_at": generated_at,
        "policy_id": policy["policy_id"],
        "treatment_definition_id": TREATMENT_ID,
        "predecessor_candidate_count": len(predecessor_records),
        "resolution_candidate_count": len(candidates),
        "initial_tranche_count": len(initial_tranche),
        "national_backlog_count": len(candidates) - len(initial_tranche),
        "resolution_track_counts": dict(sorted(track_counts.items())),
        "model_gate_counts": dict(sorted(gate_counts.items())),
        "priority_tier_counts": dict(sorted(tier_counts.items())),
        "region_counts": dict(sorted(region_counts.items())),
        "initial_tranche_region_counts": dict(sorted(tranche_region_counts.items())),
        "initial_tranche_track_counts": dict(sorted(tranche_track_counts.items())),
        "resolution_status_counts": dict(sorted(Counter(record["resolution_status"] for record in candidates).items())),
        "adjudication_count": len(resolution_adjudications),
        "adjudication_resolution_counts": dict(sorted(Counter(record["resolution_state"] for record in resolution_adjudications).items())),
        "public_partition_count": len(index_parts),
        "treatment_effect": {
            "treatment_dates_assigned": 0,
            "eligible_treatment_count_changed": False,
            "model_run_authorized": False,
        },
        "notices": [
            "This append-only registry preserves every predecessor adjudication.",
            "A promoted predecessor is a new candidate, not a verified county first entry.",
            "Queue position does not assign treatment or never-treated status.",
        ],
    }
    report_path = ROOT / "data" / "silver" / "treatments" / "county-first-entry-resolution-priority-v1.processing-report.json"
    report_payload = write_json(report_path, report)

    parts: list[dict[str, Any]] = []
    for path, payload, count, zone, projection in [
        (silver_path, silver_payload, len(candidates), "silver", "resolution_priority_registry"),
        (index_path, index_payload, 1, "public", "partition_index"),
        (tranche_path, tranche_payload, len(initial_tranche), "public", "initial_tranche"),
        (public_adjudication_path, public_adjudication_payload, len(resolution_adjudications), "public", "resolution_adjudications"),
        (public_evidence_path, public_evidence_payload, len(referenced_source_ids), "public", "resolution_evidence_sources"),
        (report_path, report_payload, 1, "silver", "processing_report"),
    ]:
        parts.append({
            "path": path.relative_to(ROOT).as_posix(),
            "sha256": digest(payload),
            "byte_size": len(payload),
            "record_count": count,
            "partition_values": {"zone": zone, "projection": projection},
        })
    for path, payload, count in public_parts:
        parts.append({
            "path": path.relative_to(ROOT).as_posix(),
            "sha256": digest(payload),
            "byte_size": len(payload),
            "record_count": count,
            "partition_values": {
                "zone": "public",
                "projection": "first_entry_resolution_candidate",
                "state_abbr": path.stem.upper(),
            },
        })
    manifest = {
        "schema_version": "1.0.0",
        "dataset_id": "county_first_entry_resolution_priority_v1",
        "artifact_type": "resolution_priority_registry",
        "artifact_version": BUILD_VERSION,
        "generated_at": generated_at,
        "data_vintage": "resolution-baseline-2026-09-03",
        "record_schema": "https://dccio.org/schemas/v1/first-entry-resolution-candidate.schema.json",
        "format": "json",
        "parts": parts,
        "record_count": sum(part["record_count"] for part in parts),
        "input_dataset_ids": policy["input_dataset_ids"],
        "license_metadata": {
            "license": "Mixed public-source metadata; see input dataset manifests",
            "redistribution_status": "metadata_only",
            "attribution": "Derived prioritization from governed public evidence metadata",
        },
    }
    write_json(
        ROOT / "data" / "silver" / "treatments"
        / "county-first-entry-resolution-priority-v1.manifest.json",
        manifest,
    )
    return report


def main() -> int:
    print(json.dumps(build(), indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

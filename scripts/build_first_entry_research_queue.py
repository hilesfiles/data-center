#!/usr/bin/env python3
"""Build a governed county queue for first-operational-entry research.

Priority scores order research effort only. They never establish a facility date,
county first entry, treatment assignment, or never-treated comparison status.
"""

from __future__ import annotations

import hashlib
import json
import math
from collections import Counter, defaultdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from acquire_census_counties import write_json


ROOT = Path(__file__).resolve().parents[1]
BUILD_VERSION = "first-entry-research-v1.1"
TREATMENT_ID = "trt_first_entry_v1"


def load_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def digest(payload: bytes) -> str:
    return hashlib.sha256(payload).hexdigest()


def stable_id(prefix: str, *parts: str) -> str:
    value = hashlib.sha256("\x1f".join(parts).encode("utf-8")).hexdigest()[:20]
    return f"{prefix}_{value}"


def load_history() -> dict[str, dict[str, Any]]:
    records: dict[str, dict[str, Any]] = {}
    directory = ROOT / "site" / "public" / "data" / "v1" / "panels" / "county-economic-history" / "by-state"
    for path in sorted(directory.glob("*.json")):
        for record in load_json(path):
            county_fips = record["county_fips"]
            if county_fips in records:
                raise RuntimeError(f"Duplicate public history county {county_fips}")
            records[county_fips] = record
    if len(records) != 3144:
        raise RuntimeError(f"Expected 3,144 public county histories; found {len(records)}")
    return records


def load_reviewed_operational_counts() -> Counter[str]:
    directory = ROOT / "site" / "public" / "data" / "v1" / "lifecycle"
    facilities: dict[str, dict[str, Any]] = {}
    for path in sorted(directory.glob("*results.json")):
        for record in load_json(path):
            facility_id = record["facility_id"]
            existing = facilities.get(facility_id)
            if existing is not None:
                comparable_existing = {
                    key: existing.get(key)
                    for key in ("county_fips", "resolution_status", "resolved_current_status")
                }
                comparable_record = {
                    key: record.get(key)
                    for key in ("county_fips", "resolution_status", "resolved_current_status")
                }
                if comparable_existing != comparable_record:
                    raise RuntimeError(f"Conflicting reviewed lifecycle result {facility_id}")
            facilities[facility_id] = record
    counts: Counter[str] = Counter()
    for record in facilities.values():
        if (
            record.get("resolution_status") == "resolved"
            and record.get("resolved_current_status") in {"operational", "partially_operational"}
        ):
            counts[record["county_fips"]] += 1
    return counts


def tier_for(score: float, tiers: list[dict[str, Any]]) -> str:
    for tier in tiers:
        if float(tier["minimum_score"]) <= score <= float(tier["maximum_score"]):
            return tier["tier"]
    raise RuntimeError(f"Priority score {score} is outside the configured tiers")


def build() -> dict[str, Any]:
    generated_at = datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")
    policy = load_json(ROOT / "config" / "v1" / "first-entry-research-policy.json")
    weights = policy["scoring"]["weights"]
    if not math.isclose(sum(float(value) for value in weights.values()), 100.0, abs_tol=1e-9):
        raise RuntimeError("First-entry research scoring weights must sum to 100")

    lifecycle_coverage = load_json(
        ROOT / "site" / "public" / "data" / "v1" / "counties"
        / "lifecycle-national-tranche-6-coverage.json"
    )
    source_coverage = load_json(
        ROOT / "site" / "public" / "data" / "v1" / "counties"
        / "facility-source-coverage.json"
    )
    history = load_history()
    treatment_registry = load_json(
        ROOT / "data" / "silver" / "treatments" / "county-first-entry-v1.json"
    )
    treatment_assessments = {
        record["county_fips"]: record
        for record in treatment_registry["collections"]["county_treatment_assessment"]
    }
    first_entry_adjudications = load_json(
        ROOT / "config" / "v1" / "first-entry-anchor-adjudications.json"
    ).get("records", [])
    adjudication_by_fips = {
        record["county_fips"]: record for record in first_entry_adjudications
    }
    if len(adjudication_by_fips) != len(first_entry_adjudications):
        raise RuntimeError("Duplicate county in first-entry adjudications")
    national_index = load_json(
        ROOT / "site" / "public" / "data" / "v1" / "lifecycle" / "national-priority-index.json"
    )
    national_fips_by_id = {
        record["national_priority_id"]: record["primary_county_fips"]
        for record in national_index
    }
    lifecycle_anchor_adjudications = load_json(
        ROOT / "config" / "v1" / "first-entry-lifecycle-anchor-adjudications.json"
    ).get("records", [])
    rejected_seed_fips = {
        national_fips_by_id[record["national_priority_id"]]
        for record in lifecycle_anchor_adjudications
        if record.get("resolved_current_status") == "rejected"
    }
    source_by_fips = {record["county_fips"]: record for record in source_coverage}
    reviewed_operational_counts = load_reviewed_operational_counts()
    state_to_region = {
        state_abbr: frame["region"]
        for frame in policy["regional_frame"]
        for state_abbr in frame["state_abbrs"]
    }
    all_state_abbrs = sorted(state_to_region)

    if len(lifecycle_coverage) != 3144 or len(source_by_fips) != 3144 or len(treatment_assessments) != 3144:
        raise RuntimeError("First-entry research inputs must each cover 3,144 counties")

    required_history = int(policy["eligibility"]["complete_history_years_required"])
    eligible_inputs = [
        record for record in lifecycle_coverage
        if record["active_canonical_facility_count"] > 0
        and history[record["county_fips"]]["complete_year_count"] >= required_history
        and treatment_assessments[record["county_fips"]]["assessment_status"] != "eligible"
    ]
    if not eligible_inputs:
        raise RuntimeError("No counties satisfy the first-entry research eligibility policy")
    max_facility_count = max(record["active_canonical_facility_count"] for record in eligible_inputs)

    candidates: list[dict[str, Any]] = []
    for coverage in eligible_inputs:
        county_fips = coverage["county_fips"]
        facility_count = int(coverage["active_canonical_facility_count"])
        source = source_by_fips[county_fips]
        assessment = treatment_assessments[county_fips]
        first_entry_adjudication = adjudication_by_fips.get(county_fips)
        rejected_seed = county_fips in rejected_seed_fips
        reviewed_operational_count = reviewed_operational_counts[county_fips]
        dated_candidate_count = int(assessment["candidate_event_count"])
        complete_year_count = int(history[county_fips]["complete_year_count"])
        identity_coverage = (
            float(source["named_record_count"]) / float(source["source_record_count"])
            if source["source_record_count"] else 0.0
        )
        audit_feasibility = (
            100.0
            if max_facility_count <= 1
            else 100.0 * (1.0 - math.log(facility_count) / math.log(max_facility_count))
        )
        components = {
            "dated_event_anchor": 100.0 if dated_candidate_count else 0.0,
            "reviewed_operational_evidence": min(100.0, 50.0 * reviewed_operational_count),
            "inventory_audit_feasibility": round(max(0.0, audit_feasibility), 2),
            "panel_completeness": round(complete_year_count / 24.0 * 100.0, 2),
            "source_identity_coverage": round(identity_coverage * 100.0, 2),
        }
        priority_score = round(
            sum(components[name] * float(weights[name]) / 100.0 for name in weights), 2
        )
        reasons = ["complete_24_year_panel"]
        if dated_candidate_count:
            reasons.append("governed_dated_operational_candidate")
        if reviewed_operational_count:
            reasons.append("reviewed_current_operational_evidence")
        if facility_count <= 5:
            reasons.append("manageable_inventory_audit_scope")
        if identity_coverage >= 0.75:
            reasons.append("strong_source_identity_coverage")
        candidate = {
                "schema_version": "1.0.0",
                "first_entry_research_candidate_id": stable_id("fer", TREATMENT_ID, county_fips),
                "treatment_definition_id": TREATMENT_ID,
                "county_fips": county_fips,
                "county_name": coverage["county_name"],
                "state_abbr": coverage["state_abbr"],
                "census_region": state_to_region[coverage["state_abbr"]],
                "active_canonical_facility_count": facility_count,
                "reviewed_operational_facility_count": reviewed_operational_count,
                "dated_operational_candidate_count": dated_candidate_count,
                "panel_complete_year_count": complete_year_count,
                "source_record_count": int(source["source_record_count"]),
                "named_source_record_count": int(source["named_record_count"]),
                "score_components": components,
                "priority_score": priority_score,
                "priority_tier": tier_for(priority_score, policy["priority_tiers"]),
                "national_rank": 0,
                "region_rank": 0,
                "queue_status": "national_backlog",
                "research_status": "evidence_collected" if first_entry_adjudication or rejected_seed else "queued",
                "research_objective": "verify_county_first_operational_entry",
                "required_findings": policy["research_protocol"]["required_findings"],
                "suggested_source_types": policy["research_protocol"]["suggested_source_types"],
                "selection_reasons": reasons,
                "created_at": generated_at,
                "updated_at": generated_at,
                "record_status": "provisional",
            }
        if first_entry_adjudication is not None:
            candidate["county_first_entry_adjudication_id"] = (
                first_entry_adjudication["county_first_entry_adjudication_id"]
            )
            candidate["adjudication_status"] = first_entry_adjudication["resolution_state"]
            candidate["inventory_completeness_status"] = first_entry_adjudication[
                "inventory_completeness_status"
            ]
            if first_entry_adjudication["resolution_state"] == "unresolved":
                candidate["research_summary"] = (
                    "A dated exact-facility operation is documented, but the county's first entry remains unresolved. "
                    "Research must complete the historical inventory and search for earlier operations."
                )
            else:
                candidate["research_summary"] = (
                    "Earlier operation documented; dated anchor rejected. "
                    "County first entry remains unresolved pending a complete historical inventory."
                )
        elif rejected_seed:
            candidate["research_summary"] = (
                "The county's only mapped seed was adjudicated as a non-data-center false positive. "
                "County first entry remains unresolved pending a corrected historical facility inventory."
            )
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
        region_selected = 0
        for record in candidates:
            if record["census_region"] != region or record["priority_tier"] == "first_entry_deferred":
                continue
            if state_counts[record["state_abbr"]] >= int(tranche_policy["max_per_state"]):
                continue
            selected_ids.add(record["first_entry_research_candidate_id"])
            state_counts[record["state_abbr"]] += 1
            region_selected += 1
            if region_selected == int(tranche_policy["per_region_quota"]):
                break
        if region_selected != int(tranche_policy["per_region_quota"]):
            raise RuntimeError(f"Could not satisfy the configured first-entry quota for {region}")
    if len(selected_ids) != int(tranche_policy["size"]):
        raise RuntimeError("First-entry initial tranche size does not match the policy")

    initial_tranche = [
        record for record in candidates
        if record["first_entry_research_candidate_id"] in selected_ids
    ]
    for initial_rank, record in enumerate(initial_tranche, start=1):
        record["queue_status"] = "initial_tranche"
        record["initial_tranche_rank"] = initial_rank

    silver_document = {
        "schema_version": "1.0.0",
        "artifact_type": "county_first_entry_research_priority_registry",
        "artifact_version": BUILD_VERSION,
        "generated_at": generated_at,
        "policy_id": policy["policy_id"],
        "record_count": len(candidates),
        "collections": {"first_entry_research_candidate": candidates},
    }
    silver_path = ROOT / "data" / "silver" / "treatments" / "county-first-entry-research-priority-v1.json"
    silver_payload = write_json(silver_path, silver_document, compact=True)

    public_directory = (
        ROOT / "site" / "public" / "data" / "v1" / "treatments"
        / "county-first-entry-research"
    )
    public_parts: list[tuple[Path, bytes, int]] = []
    index_parts: list[dict[str, Any]] = []
    for state_abbr in all_state_abbrs:
        state_records = [record for record in candidates if record["state_abbr"] == state_abbr]
        state_path = public_directory / "by-state" / f"{state_abbr.lower()}.json"
        state_payload = write_json(state_path, state_records, compact=True)
        public_parts.append((state_path, state_payload, len(state_records)))
        index_parts.append(
            {
                "state_abbr": state_abbr,
                "path": f"county-first-entry-research/by-state/{state_abbr.lower()}.json",
                "record_count": len(state_records),
                "byte_size": len(state_payload),
                "sha256": digest(state_payload),
            }
        )

    tier_counts = Counter(record["priority_tier"] for record in candidates)
    region_counts = Counter(record["census_region"] for record in candidates)
    tranche_region_counts = Counter(record["census_region"] for record in initial_tranche)
    public_index = {
        "schema_version": "1.0.0",
        "artifact_type": "county_first_entry_research_public_index",
        "artifact_version": BUILD_VERSION,
        "generated_at": generated_at,
        "policy_id": policy["policy_id"],
        "partition_count": len(index_parts),
        "record_count": len(candidates),
        "initial_tranche_count": len(initial_tranche),
        "priority_tier_counts": dict(sorted(tier_counts.items())),
        "region_counts": dict(sorted(region_counts.items())),
        "initial_tranche_region_counts": dict(sorted(tranche_region_counts.items())),
        "partitions": index_parts,
    }
    index_path = public_directory / "index.json"
    index_payload = write_json(index_path, public_index)
    tranche_path = public_directory / "initial-tranche.json"
    tranche_payload = write_json(tranche_path, initial_tranche)

    active_facility_counties = sum(
        record["active_canonical_facility_count"] > 0 for record in lifecycle_coverage
    )
    incomplete_active = sum(
        record["active_canonical_facility_count"] > 0
        and history[record["county_fips"]]["complete_year_count"] < required_history
        for record in lifecycle_coverage
    )
    report = {
        "schema_version": "1.0.0",
        "artifact_type": "county_first_entry_research_processing_report",
        "artifact_version": BUILD_VERSION,
        "generated_at": generated_at,
        "policy_id": policy["policy_id"],
        "treatment_definition_id": TREATMENT_ID,
        "county_count": len(lifecycle_coverage),
        "active_facility_county_count": active_facility_counties,
        "eligible_research_candidate_count": len(candidates),
        "initial_tranche_count": len(initial_tranche),
        "national_backlog_count": len(candidates) - len(initial_tranche),
        "exclusion_counts": {
            "no_active_canonical_facility": len(lifecycle_coverage) - active_facility_counties,
            "incomplete_24_year_panel": incomplete_active,
            "already_eligible_treatment": sum(
                assessment["assessment_status"] == "eligible"
                for assessment in treatment_assessments.values()
            ),
        },
        "priority_tier_counts": dict(sorted(tier_counts.items())),
        "region_counts": dict(sorted(region_counts.items())),
        "initial_tranche_region_counts": dict(sorted(tranche_region_counts.items())),
        "public_partition_count": len(index_parts),
        "adjudication_status_counts": dict(sorted(Counter(
            record.get("adjudication_status", "not_adjudicated") for record in candidates
        ).items())),
        "treatment_effect": {
            "treatment_dates_assigned": 0,
            "eligible_treatment_count_changed": False,
            "model_run_authorized": False,
        },
        "notices": [
            "Priority scores order county research only and are not evidence of first entry.",
            "Initial-tranche membership does not assign a treatment date or comparison status.",
            "An unresolved county is not classified as never treated.",
        ],
    }
    report_path = ROOT / "data" / "silver" / "treatments" / "county-first-entry-research-priority-v1.processing-report.json"
    report_payload = write_json(report_path, report)

    parts: list[dict[str, Any]] = []
    for path, payload, count, zone, projection in [
        (silver_path, silver_payload, len(candidates), "silver", "research_priority_registry"),
        (index_path, index_payload, 1, "public", "partition_index"),
        (tranche_path, tranche_payload, len(initial_tranche), "public", "initial_tranche"),
        (report_path, report_payload, 1, "silver", "processing_report"),
    ]:
        parts.append(
            {
                "path": path.relative_to(ROOT).as_posix(),
                "sha256": digest(payload),
                "byte_size": len(payload),
                "record_count": count,
                "partition_values": {"zone": zone, "projection": projection},
            }
        )
    for path, payload, count in public_parts:
        parts.append(
            {
                "path": path.relative_to(ROOT).as_posix(),
                "sha256": digest(payload),
                "byte_size": len(payload),
                "record_count": count,
                "partition_values": {
                    "zone": "public",
                    "projection": "first_entry_research_candidate",
                    "state_abbr": path.stem.upper(),
                },
            }
        )
    manifest = {
        "schema_version": "1.0.0",
        "dataset_id": "county_first_entry_research_priority_v1",
        "artifact_type": "research_priority_registry",
        "artifact_version": BUILD_VERSION,
        "generated_at": generated_at,
        "data_vintage": "reviewed-through-2026-09-01",
        "record_schema": "https://dccio.org/schemas/v1/first-entry-research-candidate.schema.json",
        "format": "json",
        "parts": parts,
        "record_count": sum(part["record_count"] for part in parts),
        "input_dataset_ids": policy["input_dataset_ids"],
        "license_metadata": {
            "license": "Mixed public-source metadata; see input dataset manifests",
            "redistribution_status": "metadata_only",
            "attribution": "Derived prioritization from governed Census, BEA, BLS, and IM3 metadata",
        },
    }
    write_json(
        ROOT / "data" / "silver" / "treatments"
        / "county-first-entry-research-priority-v1.manifest.json",
        manifest,
    )
    return report


def main() -> int:
    print(json.dumps(build(), indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

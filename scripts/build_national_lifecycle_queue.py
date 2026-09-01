#!/usr/bin/env python3
"""Build the governed national lifecycle-verification priority queue."""

from __future__ import annotations

import hashlib
import json
from collections import Counter
from pathlib import Path
from typing import Any

from acquire_im3_facilities import ATTRIBUTION, write_json
from resolve_im3_entities import stable_id


ROOT = Path(__file__).resolve().parents[1]
DATASET_ID = "im3_lifecycle_national_priority_20260831"
ARTIFACT_VERSION = "2026.08.31"


def load(relative_path: str) -> Any:
    return json.loads((ROOT / relative_path).read_text(encoding="utf-8"))


def digest(payload: bytes) -> str:
    return hashlib.sha256(payload).hexdigest()


def classify_archetype(
    facility: dict[str, Any],
    source: dict[str, Any],
    operator_link: dict[str, Any] | None,
    prior_pilot_outcome: str,
    *,
    apply_prior_override: bool,
) -> str:
    if apply_prior_override and prior_pilot_outcome != "not_reviewed":
        return "prior_review_followup"
    if facility.get("campus_id"):
        return "campus_member_mapping"
    named = bool(source.get("source_name")) and not facility["canonical_name"].startswith("Unnamed IM3 ")
    building = source.get("source_layer") == "building"
    if building and source.get("source_ref"):
        return "exact_reference_building"
    if building and named and operator_link:
        return "named_operator_building"
    if building and named:
        return "named_building"
    if source.get("source_layer") == "point" and operator_link:
        return "operator_point"
    return "low_context"


def build_pilot_yield_analysis(
    results: list[dict[str, Any]],
    facility_by_id: dict[str, dict[str, Any]],
    source_by_id: dict[str, dict[str, Any]],
    operator_link_by_facility: dict[str, dict[str, Any]],
    generated_at: str,
) -> dict[str, Any]:
    outcome_counts = Counter(record["resolution_status"] for record in results)
    by_archetype: dict[str, Counter[str]] = {}
    for result in results:
        facility_id = result["facility_id"]
        archetype = classify_archetype(
            facility_by_id[facility_id],
            source_by_id[facility_id],
            operator_link_by_facility.get(facility_id),
            "not_reviewed",
            apply_prior_override=False,
        )
        by_archetype.setdefault(archetype, Counter())[result["resolution_status"]] += 1

    archetype_rows = []
    for archetype in sorted(by_archetype):
        counts = by_archetype[archetype]
        reviewed = sum(counts.values())
        archetype_rows.append(
            {
                "research_archetype": archetype,
                "reviewed_count": reviewed,
                "resolved_count": counts["resolved"],
                "unresolved_count": counts["unresolved"],
                "disputed_count": counts["disputed"],
                "resolution_rate": round(counts["resolved"] / reviewed, 4),
            }
        )

    reviewed_count = len(results)
    return {
        "schema_version": "1.0.0",
        "analysis_id": "ana_lifecycle_pilot_yield_20260831",
        "input_dataset_id": "im3_lifecycle_tranche_2_20260831",
        "generated_at": generated_at,
        "overall": {
            "reviewed_count": reviewed_count,
            "resolved_count": outcome_counts["resolved"],
            "unresolved_count": outcome_counts["unresolved"],
            "disputed_count": outcome_counts["disputed"],
            "resolution_rate": round(outcome_counts["resolved"] / reviewed_count, 4),
        },
        "by_research_archetype": archetype_rows,
        "failure_modes": [
            {
                "failure_mode": "building_identity_not_established",
                "count": outcome_counts["unresolved"],
                "policy_response": "Require two matching facility identifiers and stop without projecting campus or market evidence onto a building.",
            },
            {
                "failure_mode": "official_source_conflict",
                "count": outcome_counts["disputed"],
                "policy_response": "Retain all claims, prohibit majority voting, and route the facility to needs_review.",
            },
        ],
        "policy_implications": [
            "Prioritize named buildings with operator or exact source-reference context.",
            "Treat campus-member buildings as a distinct identity-mapping research archetype.",
            "Exclude completed unresolved and disputed pilot records from the next general-purpose tranche.",
            "Use regional, state, county, and operator caps so evidence yield is tested beyond the densest markets.",
        ],
    }


def build_queue() -> tuple[
    list[dict[str, Any]],
    list[dict[str, Any]],
    list[dict[str, Any]],
    dict[str, Any],
    dict[str, Any],
]:
    final_review = load("data/silver/infrastructure/im3-2026.02.09-final-boundary-review.json")
    source_index = load("site/public/data/v1/facilities/index.json")
    county_reference = load("site/public/data/v1/counties/facility-source-coverage.json")
    pilot_results = load("site/public/data/v1/lifecycle/tranche-2-results.json")
    policy = load("config/v1/lifecycle-national-expansion-policy.json")
    generated_at = policy["updated_at"]

    source_by_id = {item["entity_id"]: item for item in source_index}
    county_by_fips = {item["county_fips"]: item for item in county_reference}
    operators_by_id = {item["operator_id"]: item for item in final_review["collections"]["operator"]}
    operator_link_by_facility: dict[str, dict[str, Any]] = {}
    for relationship in final_review["collections"]["operator_relationship"]:
        if relationship["relationship_type"] == "operator":
            operator_link_by_facility.setdefault(relationship["subject_id"], relationship)

    active_facilities = [
        item
        for item in final_review["collections"]["facility"]
        if item["record_status"] != "superseded"
    ]
    facility_by_id = {item["facility_id"]: item for item in active_facilities}
    pilot_result_by_facility = {item["facility_id"]: item for item in pilot_results}
    resolved_facility_ids = {
        item["facility_id"] for item in pilot_results if item["resolution_status"] == "resolved"
    }

    eligible: list[tuple[dict[str, Any], dict[str, Any]]] = []
    for facility in active_facilities:
        if facility["facility_id"] in resolved_facility_ids:
            continue
        source = source_by_id.get(facility["facility_id"])
        if source and source.get("primary_county_fips"):
            eligible.append((facility, source))

    region_by_state: dict[str, str] = {}
    for frame in policy["regional_frame"]:
        for state_abbr in frame["state_abbrs"]:
            if state_abbr in region_by_state:
                raise RuntimeError(f"State {state_abbr} appears in multiple Census regions")
            region_by_state[state_abbr] = frame["region"]
    if len(region_by_state) != 51:
        raise RuntimeError("Regional frame must cover the 50 states and District of Columbia")

    state_abbr_counts = Counter(
        county_by_fips[source["primary_county_fips"]]["state_abbr"] for _, source in eligible
    )
    county_counts = Counter(source["primary_county_fips"] for _, source in eligible)
    maximum_state_count = max(state_abbr_counts.values())
    maximum_county_count = max(county_counts.values())
    weights = policy["scoring"]["weights"]
    if round(sum(weights.values()), 6) != 100:
        raise RuntimeError("National lifecycle scoring weights must sum to 100")

    strategies = {
        item["archetype"]: item["source_strategy"] for item in policy["research_archetypes"]
    }
    candidates: list[dict[str, Any]] = []
    for facility, source in eligible:
        facility_id = facility["facility_id"]
        county_fips = source["primary_county_fips"]
        county = county_by_fips[county_fips]
        state_abbr = county["state_abbr"]
        operator_link = operator_link_by_facility.get(facility_id)
        operator = operators_by_id.get(operator_link["operator_id"]) if operator_link else None
        pilot_result = pilot_result_by_facility.get(facility_id)
        prior_pilot_outcome = pilot_result["resolution_status"] if pilot_result else "not_reviewed"
        if prior_pilot_outcome == "resolved":
            raise RuntimeError("Resolved pilot facility entered the unknown-status queue")

        named = bool(source.get("source_name")) and not facility["canonical_name"].startswith("Unnamed IM3 ")
        building = source["source_layer"] == "building"
        source_reference = bool(source.get("source_ref"))
        non_campus = not bool(facility.get("campus_id"))
        source_quality = facility.get("data_quality", {}).get("score", 0) / 100
        state_coverage_need = 1 - state_abbr_counts[state_abbr] / maximum_state_count
        county_density = county_counts[county_fips] / maximum_county_count
        score_components = {
            "source_name_specificity": round(weights["source_name_specificity"] * int(named), 4),
            "operator_link": round(weights["operator_link"] * int(operator_link is not None), 4),
            "building_footprint": round(weights["building_footprint"] * int(building), 4),
            "source_reference": round(weights["source_reference"] * int(source_reference), 4),
            "non_campus_specificity": round(weights["non_campus_specificity"] * int(non_campus), 4),
            "source_quality": round(weights["source_quality"] * source_quality, 4),
            "state_coverage_need": round(weights["state_coverage_need"] * state_coverage_need, 4),
            "county_density": round(weights["county_density"] * county_density, 4),
        }
        priority_score = round(sum(score_components.values()), 2)
        if prior_pilot_outcome != "not_reviewed":
            priority_tier = "national_deferred"
        elif priority_score >= 75:
            priority_tier = "national_high"
        elif priority_score >= 50:
            priority_tier = "national_standard"
        else:
            priority_tier = "national_deferred"

        archetype = classify_archetype(
            facility,
            source,
            operator_link,
            prior_pilot_outcome,
            apply_prior_override=True,
        )
        reasons = []
        if prior_pilot_outcome != "not_reviewed":
            reasons.append(f"Completed pilot outcome is {prior_pilot_outcome}; retain for targeted follow-up outside the initial tranche.")
        if named:
            reasons.append("Source provides a facility name suitable for exact-identity research.")
        if operator_link:
            reasons.append("A source-backed normalized operator relationship is available.")
        if building:
            reasons.append("Mapped building geometry supports address, parcel, assessor, and permit matching.")
        if source_reference:
            reasons.append("The source record includes a reference suitable for exact-record lookup.")
        if facility.get("campus_id"):
            reasons.append("Campus membership requires explicit building-level evidence before lifecycle attribution.")
        if not reasons:
            reasons.append("Record remains in the national backlog but has limited identity context for efficient research.")

        candidate = {
            "schema_version": "1.0.0",
            "national_priority_id": stable_id("lnp", policy["policy_id"], facility_id),
            "facility_id": facility_id,
            "canonical_name": facility["canonical_name"],
            "primary_county_fips": county_fips,
            "county_name": county["county_name"],
            "state_abbr": state_abbr,
            "census_region": region_by_state[state_abbr],
            "source_layer": source["source_layer"],
            "research_archetype": archetype,
            "target_attributes": policy["target_attributes"],
            "suggested_source_types": strategies[archetype],
            "score_components": score_components,
            "priority_score": priority_score,
            "priority_tier": priority_tier,
            "national_rank": 0,
            "region_rank": 0,
            "queue_status": "national_backlog",
            "selection_reasons": reasons,
            "prior_pilot_outcome": prior_pilot_outcome,
            "lifecycle_status": "unknown",
            "created_at": generated_at,
            "updated_at": generated_at,
            "record_status": "active",
        }
        if source_reference and isinstance(source.get("source_ref"), str):
            candidate["source_ref"] = source["source_ref"]
        if facility.get("campus_id"):
            candidate["campus_id"] = facility["campus_id"]
        if operator_link and operator:
            candidate["operator_id"] = operator["operator_id"]
            candidate["operator_canonical_name"] = operator["canonical_name"]
        candidates.append(candidate)

    tier_order = {"national_high": 0, "national_standard": 1, "national_deferred": 2}
    candidates.sort(
        key=lambda item: (tier_order[item["priority_tier"]], -item["priority_score"], item["facility_id"])
    )
    for rank, candidate in enumerate(candidates, 1):
        candidate["national_rank"] = rank

    region_candidates: dict[str, list[dict[str, Any]]] = {}
    for frame in policy["regional_frame"]:
        region = frame["region"]
        ranked = [item for item in candidates if item["census_region"] == region]
        for rank, candidate in enumerate(ranked, 1):
            candidate["region_rank"] = rank
        region_candidates[region] = ranked

    tranche_policy = policy["initial_tranche"]
    if tranche_policy["size"] != tranche_policy["per_region_quota"] * len(region_candidates):
        raise RuntimeError("Initial tranche size must equal the per-region quota times four regions")
    eligible_tiers = set(tranche_policy["eligible_priority_tiers"])
    selected_ids: set[str] = set()
    selected: list[dict[str, Any]] = []
    state_selected: Counter[str] = Counter()
    county_selected: Counter[str] = Counter()
    operator_selected: Counter[str] = Counter()
    region_selected: Counter[str] = Counter()

    for _ in range(tranche_policy["per_region_quota"]):
        for frame in policy["regional_frame"]:
            region = frame["region"]
            chosen = None
            for candidate in region_candidates[region]:
                if candidate["facility_id"] in selected_ids:
                    continue
                if candidate["priority_tier"] not in eligible_tiers:
                    continue
                if candidate["prior_pilot_outcome"] != "not_reviewed":
                    continue
                if state_selected[candidate["state_abbr"]] >= tranche_policy["max_per_state"]:
                    continue
                if county_selected[candidate["primary_county_fips"]] >= tranche_policy["max_per_county"]:
                    continue
                operator_id = candidate.get("operator_id")
                if operator_id and operator_selected[operator_id] >= tranche_policy["max_per_operator"]:
                    continue
                chosen = candidate
                break
            if chosen is None:
                raise RuntimeError(
                    f"Unable to satisfy the initial-tranche diversity constraints for {region}; "
                    f"selected {region_selected[region]} of {tranche_policy['per_region_quota']}"
                )
            selected_ids.add(chosen["facility_id"])
            chosen["queue_status"] = "initial_tranche"
            chosen["initial_tranche_rank"] = len(selected) + 1
            selected.append(chosen)
            state_selected[chosen["state_abbr"]] += 1
            county_selected[chosen["primary_county_fips"]] += 1
            if chosen.get("operator_id"):
                operator_selected[chosen["operator_id"]] += 1
            region_selected[region] += 1

    if len(selected) != tranche_policy["size"]:
        raise RuntimeError("Initial national tranche size is inconsistent with policy")

    active_count_by_county = Counter(
        source_by_id[item["facility_id"]]["primary_county_fips"]
        for item in active_facilities
        if item["facility_id"] in source_by_id and source_by_id[item["facility_id"]].get("primary_county_fips")
    )
    verified_by_county = Counter(
        source_by_id[facility_id]["primary_county_fips"] for facility_id in resolved_facility_ids
    )
    in_research_by_county = Counter(
        item["county_fips"] for item in pilot_results if item["resolution_status"] == "unresolved"
    )
    needs_review_by_county = Counter(
        item["county_fips"] for item in pilot_results if item["resolution_status"] == "disputed"
    )
    queued_by_county = Counter(item["primary_county_fips"] for item in selected)
    coverage = []
    for county_fips in sorted(county_by_fips):
        county = county_by_fips[county_fips]
        active_count = active_count_by_county[county_fips]
        queued_count = queued_by_county[county_fips]
        reviewed_count = verified_by_county[county_fips] + in_research_by_county[county_fips] + needs_review_by_county[county_fips]
        if queued_count:
            coverage_status = "national_initial_tranche"
        elif reviewed_count:
            coverage_status = "pilot_reviewed"
        elif active_count:
            coverage_status = "national_backlog"
        else:
            coverage_status = "no_active_facility"
        coverage.append(
            {
                "schema_version": "1.0.0",
                "county_fips": county_fips,
                "county_name": county["county_name"],
                "state_abbr": county["state_abbr"],
                "active_canonical_facility_count": active_count,
                "queued_facility_count": queued_count,
                "in_research_facility_count": in_research_by_county[county_fips],
                "needs_review_facility_count": needs_review_by_county[county_fips],
                "verified_facility_count": verified_by_county[county_fips],
                "unknown_status_facility_count": active_count - verified_by_county[county_fips],
                "coverage_status": coverage_status,
                "generated_at": generated_at,
            }
        )

    pilot_analysis = build_pilot_yield_analysis(
        pilot_results,
        facility_by_id,
        source_by_id,
        operator_link_by_facility,
        generated_at,
    )
    summary = {
        "schema_version": "1.0.0",
        "artifact_type": "public_lifecycle_national_expansion_summary",
        "artifact_version": ARTIFACT_VERSION,
        "generated_at": generated_at,
        "policy_id": policy["policy_id"],
        "input_dataset_ids": policy["input_dataset_ids"],
        "counts": {
            "active_canonical_facility_count": len(active_facilities),
            "verified_facility_count": len(resolved_facility_ids),
            "unknown_status_facility_count": len(candidates),
            "national_priority_record_count": len(candidates),
            "initial_tranche_facility_count": len(selected),
            "national_backlog_facility_count": len(candidates) - len(selected),
            "represented_state_count": len({item["state_abbr"] for item in selected}),
            "represented_county_count": len({item["primary_county_fips"] for item in selected}),
            "represented_operator_count": len({item["operator_id"] for item in selected if item.get("operator_id")}),
        },
        "priority_tier_counts": dict(sorted(Counter(item["priority_tier"] for item in candidates).items())),
        "research_archetype_counts": dict(sorted(Counter(item["research_archetype"] for item in candidates).items())),
        "initial_tranche_by_region": dict(sorted(region_selected.items())),
        "initial_tranche_by_state": dict(sorted(state_selected.items())),
        "notices": [
            "Priority is a research-order decision and is not evidence of facility operation.",
            "The national index includes all 1,327 canonical facilities whose lifecycle status remains unknown after the pilot.",
            "The first national tranche is balanced across Census regions and capped by state, county, and operator.",
            "Completed unresolved and disputed pilot records remain in the backlog for targeted follow-up but are excluded from the initial national tranche.",
        ],
    }
    return candidates, selected, coverage, pilot_analysis, summary


def main() -> int:
    candidates, selected, coverage, pilot_analysis, summary = build_queue()
    document = {
        "schema_version": "1.0.0",
        "artifact_type": "lifecycle_national_priority_queue",
        "artifact_version": ARTIFACT_VERSION,
        "generated_at": summary["generated_at"],
        "record_count": len(candidates),
        "collections": {"lifecycle_national_priority_record": candidates},
    }
    outputs = [
        ("data/silver/infrastructure/im3-2026.02.09-lifecycle-national-priority.json", document, True, len(candidates), "silver", "national_priority_queue"),
        ("data/silver/infrastructure/im3-2026.02.09-lifecycle-national-priority.processing-report.json", summary, False, 1, "silver", "processing_report"),
        ("data/silver/infrastructure/im3-2026.02.09-lifecycle-pilot-yield-analysis.json", pilot_analysis, False, 1, "silver", "pilot_yield_analysis"),
        ("site/public/data/v1/lifecycle/national-priority-index.json", candidates, True, len(candidates), "public", "national_priority_index"),
        ("site/public/data/v1/lifecycle/national-initial-tranche.json", selected, True, len(selected), "public", "national_initial_tranche"),
        ("site/public/data/v1/lifecycle/national-pilot-yield-analysis.json", pilot_analysis, False, 1, "public", "pilot_yield_analysis"),
        ("site/public/data/v1/counties/lifecycle-national-expansion-coverage.json", coverage, True, len(coverage), "public", "national_lifecycle_coverage"),
        ("site/public/data/v1/lifecycle/national-expansion-metadata.json", summary, False, 1, "public", "national_expansion_metadata"),
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
        "artifact_type": "lifecycle_national_priority_queue",
        "artifact_version": ARTIFACT_VERSION,
        "generated_at": summary["generated_at"],
        "data_vintage": "2026-08-31",
        "record_schema": "https://dccio.org/schemas/v1/lifecycle-national-priority-record.schema.json",
        "format": "json",
        "parts": parts,
        "record_count": sum(part["record_count"] for part in parts),
        "input_dataset_ids": ["im3_final_boundary_review_20260831", "im3_lifecycle_tranche_2_20260831"],
        "license_metadata": {
            "license": "ODbL applies to IM3-derived records",
            "redistribution_status": "allowed",
            "attribution": ATTRIBUTION,
        },
    }
    write_json(
        ROOT / "data/silver/infrastructure/im3-2026.02.09-lifecycle-national-priority.manifest.json",
        manifest,
    )
    print(json.dumps(summary, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

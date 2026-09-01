#!/usr/bin/env python3
"""Build governed county first-entry treatment assessments from reviewed lifecycle events.

The builder never treats a current operational status, directory label, or dated opening
of one facility as proof of a county's first data-center entry. Candidate events are scored
against the configured evidence thresholds and remain excluded until the first-entry claim
itself is explicitly verified.
"""

from __future__ import annotations

import glob
import hashlib
import json
from collections import Counter, defaultdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from acquire_census_counties import write_json


ROOT = Path(__file__).resolve().parents[1]
BUILD_VERSION = "first-entry-v1.3"
TREATMENT_ID = "trt_first_entry_v1"
PANEL_YEARS = tuple(range(2001, 2025))
AUTHORITATIVE_SOURCE_TYPES = {
    "federal_dataset", "state_record", "local_government_record", "planning_record",
    "zoning_record", "permit_record", "assessor_record", "utility_filing",
    "regulatory_filing", "court_record", "sec_filing", "incentive_agreement",
    "operator_release", "legislative_record",
}
PRECISION_RANK = {
    "unknown": 0, "approximate_year": 1, "year": 2, "quarter": 3,
    "month": 4, "day": 5,
}


def stable_id(prefix: str, *parts: str) -> str:
    value = hashlib.sha256("\x1f".join(parts).encode("utf-8")).hexdigest()[:20]
    return f"{prefix}_{value}"


def digest(payload: bytes) -> str:
    return hashlib.sha256(payload).hexdigest()


def load_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def load_counties() -> dict[str, dict[str, Any]]:
    path = ROOT / "site" / "public" / "data" / "v1" / "maps" / "counties.geojson"
    document = load_json(path)
    counties = {
        feature["properties"]["county_fips"]: feature["properties"]
        for feature in document.get("features", [])
    }
    if len(counties) != 3144:
        raise RuntimeError(f"Expected 3,144 current Census counties; found {len(counties)}")
    return counties


def load_treatment_definition() -> dict[str, Any]:
    document = load_json(ROOT / "config" / "v1" / "treatment-definitions.json")
    matches = [
        record for record in document.get("treatments", [])
        if record.get("treatment_definition_id") == TREATMENT_ID
    ]
    if len(matches) != 1:
        raise RuntimeError(f"Expected one active treatment definition {TREATMENT_ID}")
    return matches[0]


def load_model_specification() -> dict[str, Any]:
    document = load_json(ROOT / "config" / "v1" / "model-specifications.json")
    matches = [
        record for record in document.get("models", [])
        if record.get("treatment_definition_id") == TREATMENT_ID
    ]
    if len(matches) != 1:
        raise RuntimeError(f"Expected one model specification for {TREATMENT_ID}")
    return matches[0]


def load_sources() -> dict[str, dict[str, Any]]:
    records: dict[str, dict[str, Any]] = {}
    pattern = str(ROOT / "config" / "v1" / "*evidence-sources.json")
    for filename in sorted(glob.glob(pattern)):
        for record in load_json(Path(filename)).get("records", []):
            source_id = record["source_id"]
            if source_id in records and records[source_id] != record:
                raise RuntimeError(f"Conflicting lifecycle source record {source_id}")
            records[source_id] = record
    return records


def load_first_entry_adjudications() -> list[dict[str, Any]]:
    path = ROOT / "config" / "v1" / "first-entry-anchor-adjudications.json"
    return load_json(path).get("records", [])


def load_candidate_results() -> dict[str, dict[str, Any]]:
    records: dict[str, dict[str, Any]] = {}
    directory = ROOT / "site" / "public" / "data" / "v1" / "lifecycle"
    for path in sorted(directory.glob("*results.json")):
        for record in load_json(path):
            candidate_id = record.get("verification_candidate_id") or record.get("national_priority_id")
            if candidate_id is None:
                continue
            if candidate_id in records and records[candidate_id] != record:
                raise RuntimeError(f"Conflicting lifecycle result {candidate_id}")
            records[candidate_id] = record
    return records


def load_adjudications() -> list[dict[str, Any]]:
    records: list[dict[str, Any]] = []
    pattern = str(ROOT / "config" / "v1" / "*lifecycle*adjudications.json")
    for filename in sorted(glob.glob(pattern)):
        records.extend(
            record
            for record in load_json(Path(filename)).get("records", [])
            if record.get("verification_candidate_id") is not None
            or record.get("national_priority_id") is not None
        )
    return records


def cohort_year(when: dict[str, Any]) -> int:
    if when.get("year") is not None:
        return int(when["year"])
    if when.get("date"):
        return int(str(when["date"])[:4])
    raise RuntimeError(f"Dated operational event lacks a cohort year: {when}")


def build() -> dict[str, Any]:
    generated_at = datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")
    counties = load_counties()
    treatment = load_treatment_definition()
    threshold = treatment["eligibility"]
    model_specification = load_model_specification()
    sample_definition = model_specification["sample_definition"]
    minimum_pre_periods = int(sample_definition["minimum_pre_periods"])
    minimum_post_periods = int(sample_definition["minimum_post_periods"])
    source_quality = load_json(ROOT / "config" / "v1" / "source-quality.json")
    precision_multipliers = source_quality["date_precision_multipliers"]
    sources = load_sources()
    candidate_results = load_candidate_results()
    adjudications = load_adjudications()
    first_entry_adjudications = load_first_entry_adjudications()
    first_entry_by_evaluation = {
        record["candidate_event_evaluation_id"]: record
        for record in first_entry_adjudications
    }
    if len(first_entry_by_evaluation) != len(first_entry_adjudications):
        raise RuntimeError("Duplicate candidate evaluation in first-entry adjudications")
    for record in first_entry_adjudications:
        unknown_sources = set(record["source_ids"]) - set(sources)
        if unknown_sources:
            raise RuntimeError(
                f"First-entry adjudication {record['county_first_entry_adjudication_id']} "
                f"references unknown sources: {sorted(unknown_sources)}"
            )

    events: list[dict[str, Any]] = []
    evaluations: list[dict[str, Any]] = []
    evaluations_by_county: dict[str, list[dict[str, Any]]] = defaultdict(list)

    for adjudication in adjudications:
        reference_type = (
            "facility_verification_candidate"
            if adjudication.get("verification_candidate_id") is not None
            else "national_priority"
        )
        candidate_id = (
            adjudication.get("verification_candidate_id")
            or adjudication["national_priority_id"]
        )
        result = candidate_results.get(candidate_id)
        if result is None:
            raise RuntimeError(f"Lifecycle adjudication has no public result: {candidate_id}")
        for event_candidate in adjudication.get("events", []):
            if event_candidate.get("event_type") != "operational":
                continue
            source_id = event_candidate["source_id"]
            source = sources.get(source_id)
            if source is None:
                raise RuntimeError(f"Operational event references unknown source {source_id}")
            when = event_candidate["when"]
            precision = when["precision"]
            source_quality_score = float(source.get("source_quality_prior", 0))
            claim_confidence = float(event_candidate["confidence"])
            precision_multiplier = float(precision_multipliers[precision])
            data_quality_score = round(
                source_quality_score * claim_confidence * precision_multiplier * 100, 2
            )
            authoritative_count = int(source["source_type"] in AUTHORITATIVE_SOURCE_TYPES)
            source_count = 1
            evidence_passed = (
                data_quality_score >= threshold["minimum_dqs"]
                and authoritative_count >= threshold["minimum_authoritative_sources"]
                and source_count >= threshold.get("minimum_source_count", 1)
                and PRECISION_RANK.get(precision, 0)
                >= PRECISION_RANK[threshold["minimum_date_precision"]]
            )
            year = cohort_year(when)
            available_pre = sum(panel_year < year for panel_year in PANEL_YEARS)
            available_post = sum(panel_year > year for panel_year in PANEL_YEARS)
            period_passed = (
                available_pre >= minimum_pre_periods
                and available_post >= minimum_post_periods
            )
            facility_id = result["facility_id"]
            event_id = stable_id("evt", facility_id, "operational", json.dumps(when, sort_keys=True))
            evaluation_id = stable_id("tev", TREATMENT_ID, event_id)
            first_entry_adjudication = first_entry_by_evaluation.get(evaluation_id)
            first_entry_verified = (
                first_entry_adjudication is not None
                and first_entry_adjudication["decision"] == "accept_candidate_as_first_entry"
            ) or adjudication.get("county_first_entry_verified") is True
            candidate_rejected = (
                first_entry_adjudication is not None
                and first_entry_adjudication["decision"] == "reject_candidate_as_first_entry"
            )
            exclusion_reasons: list[str] = []
            if not evidence_passed:
                exclusion_reasons.append("evidence_threshold_not_met")
            if not period_passed:
                exclusion_reasons.append("panel_period_requirement_not_met")
            if candidate_rejected:
                exclusion_reasons.append("candidate_event_not_county_first_entry")
            elif not first_entry_verified:
                exclusion_reasons.append("county_first_entry_not_verified")
            eligibility_status = "eligible" if not exclusion_reasons else "excluded"
            events.append(
                {
                    "schema_version": "1.0.0",
                    "event_id": event_id,
                    "event_type": "operational",
                    "subjects": [{"entity_type": "facility", "entity_id": facility_id}],
                    "when": when,
                    "resolution_status": "resolved",
                    "confidence": claim_confidence,
                    "notes": event_candidate["notes"],
                    "created_at": generated_at,
                    "updated_at": generated_at,
                    "record_status": "active",
                }
            )
            evaluation = {
                "schema_version": "1.0.0",
                "treatment_event_evaluation_id": evaluation_id,
                "event_id": event_id,
                "treatment_definition_id": TREATMENT_ID,
                "lifecycle_review_reference": {
                    "reference_type": reference_type,
                    "reference_id": candidate_id,
                },
                "facility_id": facility_id,
                "canonical_name": result["canonical_name"],
                "county_fips": result["county_fips"],
                "county_name": result["county_name"],
                "state_abbr": result["state_abbr"],
                "when": when,
                "source_id": source_id,
                "source_type": source["source_type"],
                "source_quality_score": source_quality_score,
                "claim_confidence": claim_confidence,
                "date_precision_multiplier": precision_multiplier,
                "data_quality_score": data_quality_score,
                "authoritative_source_count": authoritative_count,
                "source_count": source_count,
                "evidence_threshold_status": "passed" if evidence_passed else "failed",
                "first_entry_verification_status": (
                    "verified" if first_entry_verified
                    else "rejected_as_first_entry" if candidate_rejected
                    else "not_verified"
                ),
                "eligibility_status": eligibility_status,
                "exclusion_reasons": exclusion_reasons,
                "available_pre_periods": available_pre,
                "available_post_periods": available_post,
                "period_requirement_status": "passed" if period_passed else "failed",
                "created_at": generated_at,
                "updated_at": generated_at,
                "record_status": "active" if eligibility_status == "eligible" else "provisional",
            }
            if reference_type == "facility_verification_candidate":
                evaluation["verification_candidate_id"] = candidate_id
            else:
                evaluation["national_priority_id"] = candidate_id
            if first_entry_adjudication is not None:
                evaluation["county_first_entry_adjudication_id"] = (
                    first_entry_adjudication["county_first_entry_adjudication_id"]
                )
            evaluations.append(evaluation)
            evaluations_by_county[result["county_fips"]].append(evaluation)

    assessments: list[dict[str, Any]] = []
    for county_fips, county in sorted(counties.items()):
        candidate_evaluations = sorted(
            evaluations_by_county.get(county_fips, []),
            key=lambda record: (cohort_year(record["when"]), record["event_id"]),
        )
        eligible = [record for record in candidate_evaluations if record["eligibility_status"] == "eligible"]
        if eligible:
            earliest = eligible[0]
            assessment_status = "eligible"
        elif candidate_evaluations:
            earliest = None
            assessment_status = "candidate_events_not_first_entry"
        else:
            earliest = None
            assessment_status = "no_reviewed_dated_operational_event"
        assessment = {
            "schema_version": "1.0.0",
            "treatment_assessment_id": stable_id("tas", TREATMENT_ID, county_fips),
            "treatment_definition_id": TREATMENT_ID,
            "county_fips": county_fips,
            "county_name": county["county_name"],
            "state_abbr": county["state_abbr"],
            "assessment_status": assessment_status,
            "candidate_event_count": len(candidate_evaluations),
            "candidate_event_evaluation_ids": [
                record["treatment_event_evaluation_id"] for record in candidate_evaluations
            ],
            "first_entry_verified": bool(eligible),
            "review_scope": "reviewed_facility_events_only",
            "created_at": generated_at,
            "updated_at": generated_at,
            "record_status": "active" if eligible else "provisional",
        }
        adjudication_records = [
            first_entry_by_evaluation[record["treatment_event_evaluation_id"]]
            for record in candidate_evaluations
            if record["treatment_event_evaluation_id"] in first_entry_by_evaluation
        ]
        if adjudication_records:
            assessment["first_entry_adjudication_ids"] = [
                record["county_first_entry_adjudication_id"]
                for record in adjudication_records
            ]
            assessment["candidate_rejection_count"] = sum(
                record["decision"] == "reject_candidate_as_first_entry"
                for record in adjudication_records
            )
            assessment["inventory_completeness_status"] = adjudication_records[0][
                "inventory_completeness_status"
            ]
            if any(record["resolution_state"] == "unresolved" for record in adjudication_records):
                assessment["first_entry_research_summary"] = (
                    "A dated exact-facility operation is documented, but county first entry remains unresolved. "
                    "The complete historical county inventory and conclusive earlier-operations search are not established."
                )
            else:
                assessment["first_entry_research_summary"] = (
                    "Earlier operation documented; the dated anchor is rejected as county first entry. "
                    "The complete historical county inventory is not established."
                )
        if earliest:
            assessment["eligible_treatment_period"] = earliest["when"]
            assessment["eligible_cohort_year"] = cohort_year(earliest["when"])
        assessments.append(assessment)

    silver_document = {
        "schema_version": "1.0.0",
        "artifact_type": "county_first_entry_treatment_registry",
        "artifact_version": BUILD_VERSION,
        "generated_at": generated_at,
        "record_count": len(events) + len(evaluations) + len(assessments),
        "collections": {
            "event": events,
            "treatment_event_evaluation": evaluations,
            "county_treatment_assessment": assessments,
        },
    }
    silver_path = ROOT / "data" / "silver" / "treatments" / "county-first-entry-v1.json"
    silver_payload = write_json(silver_path, silver_document, compact=True)

    public_directory = (
        ROOT / "site" / "public" / "data" / "v1" / "treatments"
        / "county-first-entry" / "by-state"
    )
    public_parts: list[tuple[Path, bytes, int]] = []
    index_parts: list[dict[str, Any]] = []
    for state_abbr in sorted({record["state_abbr"] for record in assessments}):
        state_records = [record for record in assessments if record["state_abbr"] == state_abbr]
        state_path = public_directory / f"{state_abbr.lower()}.json"
        state_payload = write_json(state_path, state_records, compact=True)
        public_parts.append((state_path, state_payload, len(state_records)))
        index_parts.append(
            {
                "state_abbr": state_abbr,
                "path": f"county-first-entry/by-state/{state_abbr.lower()}.json",
                "record_count": len(state_records),
                "byte_size": len(state_payload),
                "sha256": digest(state_payload),
            }
        )
    public_index = {
        "schema_version": "1.0.0",
        "artifact_type": "county_first_entry_public_index",
        "artifact_version": BUILD_VERSION,
        "generated_at": generated_at,
        "partition_count": len(index_parts),
        "record_count": len(assessments),
        "adjudication_count": len(first_entry_adjudications),
        "adjudications_path": "county-first-entry/adjudications.json",
        "evidence_sources_path": "county-first-entry/evidence-sources.json",
        "partitions": index_parts,
    }
    index_path = (
        ROOT / "site" / "public" / "data" / "v1" / "treatments"
        / "county-first-entry" / "index.json"
    )
    index_payload = write_json(index_path, public_index)
    evaluation_path = (
        ROOT / "site" / "public" / "data" / "v1" / "treatments"
        / "county-first-entry" / "candidate-events.json"
    )
    evaluation_payload = write_json(evaluation_path, evaluations)
    public_adjudication_path = (
        ROOT / "site" / "public" / "data" / "v1" / "treatments"
        / "county-first-entry" / "adjudications.json"
    )
    public_adjudication_payload = write_json(
        public_adjudication_path, first_entry_adjudications
    )
    adjudication_source_ids = {
        source_id
        for record in first_entry_adjudications
        for source_id in record["source_ids"]
    }
    public_evidence_sources = [
        sources[source_id] for source_id in sorted(adjudication_source_ids)
    ]
    public_evidence_path = (
        ROOT / "site" / "public" / "data" / "v1" / "treatments"
        / "county-first-entry" / "evidence-sources.json"
    )
    public_evidence_payload = write_json(public_evidence_path, public_evidence_sources)

    assessment_counts = Counter(record["assessment_status"] for record in assessments)
    report = {
        "schema_version": "1.0.0",
        "artifact_type": "county_first_entry_treatment_processing_report",
        "artifact_version": BUILD_VERSION,
        "generated_at": generated_at,
        "treatment_definition_id": TREATMENT_ID,
        "model_specification_id": model_specification["model_specification_id"],
        "panel_years": {"start": PANEL_YEARS[0], "end": PANEL_YEARS[-1]},
        "period_requirements": {
            "minimum_pre_periods": minimum_pre_periods,
            "minimum_post_periods": minimum_post_periods,
        },
        "county_count": len(assessments),
        "reviewed_dated_operational_event_count": len(evaluations),
        "evidence_threshold_pass_count": sum(record["evidence_threshold_status"] == "passed" for record in evaluations),
        "period_requirement_pass_count": sum(record["period_requirement_status"] == "passed" for record in evaluations),
        "first_entry_verified_event_count": sum(record["first_entry_verification_status"] == "verified" for record in evaluations),
        "candidate_rejected_as_first_entry_count": sum(record["first_entry_verification_status"] == "rejected_as_first_entry" for record in evaluations),
        "eligible_treatment_event_count": sum(record["eligibility_status"] == "eligible" for record in evaluations),
        "eligible_county_count": assessment_counts.get("eligible", 0),
        "assessment_status_counts": dict(sorted(assessment_counts.items())),
        "public_partition_count": len(index_parts),
        "model_readiness": {
            "status": "insufficient_eligible_treatments",
            "governed_treatment_registry_available": True,
            "eligible_treatment_dates_available": assessment_counts.get("eligible", 0) > 0,
            "model_run_authorized": False,
        },
        "quality_formula": "source_quality_score * claim_confidence * date_precision_multiplier * 100",
        "authoritative_source_types": sorted(AUTHORITATIVE_SOURCE_TYPES),
        "notices": [
            "A dated facility opening is not treated as a county first entry unless the first-entry claim is explicitly verified.",
            "Current operational status without a governed operational date is not a treatment date.",
            "No county currently has an eligible first-entry treatment date; no model run is authorized.",
            "Never-treated status is not inferred from absence of a reviewed event.",
        ],
    }
    report_path = ROOT / "data" / "silver" / "treatments" / "county-first-entry-v1.processing-report.json"
    report_payload = write_json(report_path, report)

    parts = []
    for path, payload, count, zone, projection in [
        (silver_path, silver_payload, silver_document["record_count"], "silver", "treatment_registry"),
        (index_path, index_payload, 1, "public", "partition_index"),
        (evaluation_path, evaluation_payload, len(evaluations), "public", "candidate_events"),
        (public_adjudication_path, public_adjudication_payload, len(first_entry_adjudications), "public", "first_entry_adjudications"),
        (public_evidence_path, public_evidence_payload, len(public_evidence_sources), "public", "first_entry_evidence_sources"),
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
                    "zone": "public", "projection": "county_treatment_assessment",
                    "state_abbr": path.stem.upper(),
                },
            }
        )
    manifest = {
        "schema_version": "1.0.0",
        "dataset_id": "county_first_entry_treatment_registry_v1",
        "artifact_type": "treatment_registry",
        "artifact_version": BUILD_VERSION,
        "generated_at": generated_at,
        "data_vintage": "reviewed-through-2026-09-01",
        "record_schema": "https://dccio.org/schemas/v1/county-treatment-assessment.schema.json",
        "format": "json",
        "parts": parts,
        "record_count": sum(part["record_count"] for part in parts),
        "input_dataset_ids": [
            "im3_2026_02_09_lifecycle_review", "county_economic_core_panel_2001_2024"
        ],
        "license_metadata": {
            "license": "Mixed public-source metadata; see referenced source records",
            "redistribution_status": "metadata_only",
            "attribution": "Facility event metadata from reviewed government and first-party sources",
        },
    }
    write_json(
        ROOT / "data" / "silver" / "treatments" / "county-first-entry-v1.manifest.json",
        manifest,
    )
    return report


def main() -> int:
    print(json.dumps(build(), indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

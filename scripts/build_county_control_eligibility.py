"""Build the national county control-eligibility screening registry.

This is a screening product, not a donor pool. Inventory absence remains unresolved
until a county-specific negative-evidence audit is completed.
"""

from __future__ import annotations

import hashlib
import json
from collections import Counter, defaultdict
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
POLICY_PATH = ROOT / "config" / "v1" / "county-control-eligibility-policy.json"
HISTORY_DIR = ROOT / "site" / "public" / "data" / "v1" / "panels" / "county-economic-history" / "by-state"
LIFECYCLE_PATH = ROOT / "site" / "public" / "data" / "v1" / "counties" / "lifecycle-national-tranche-6-coverage.json"
TREATMENT_PATH = ROOT / "data" / "silver" / "treatments" / "county-first-entry-v1.json"
REJECTED_PATH = ROOT / "site" / "public" / "data" / "v1" / "study" / "rejected-projects" / "index.json"
STUDY_PATH = ROOT / "site" / "public" / "data" / "v1" / "study" / "index.json"
PUBLIC_DIR = ROOT / "site" / "public" / "data" / "v1" / "analysis" / "county-control-eligibility"
SILVER_DIR = ROOT / "data" / "silver" / "analysis" / "county-control-eligibility"
GENERATED_AT = "2026-09-09T00:00:00+00:00"


def read(path: Path):
    return json.loads(path.read_text(encoding="utf-8"))


def write(path: Path, value) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def stable_id(county_fips: str) -> str:
    digest = hashlib.sha256(f"county-control-eligibility-v1|{county_fips}".encode()).hexdigest()[:20]
    return f"ccs_{digest}"


def count_by(records: list[dict], field: str) -> dict[str, int]:
    return dict(sorted(Counter(record[field] for record in records).items()))


def load_history() -> list[dict]:
    records: list[dict] = []
    for path in sorted(HISTORY_DIR.glob("*.json")):
        records.extend(read(path))
    return sorted(records, key=lambda record: record["county_fips"])


def build_products(generated_at: str = GENERATED_AT) -> tuple[dict, dict[str, list[dict]], list[dict]]:
    policy = read(POLICY_PATH)
    history = load_history()
    lifecycle = {record["county_fips"]: record for record in read(LIFECYCLE_PATH)}
    treatment_document = read(TREATMENT_PATH)
    treatments = {record["county_fips"]: record for record in treatment_document["collections"]["county_treatment_assessment"]}
    rejected = defaultdict(list)
    for project in read(REJECTED_PATH)["projects"]:
        rejected[project["county_fips"]].append(project["project_id"])
    study = defaultdict(list)
    for project in read(STUDY_PATH)["projects"]:
        study[project["county_fips"]].append(project["project_id"])

    if len(history) != 3144 or len(lifecycle) != 3144 or len(treatments) != 3144:
        raise ValueError("history, lifecycle, and treatment inputs must each cover 3,144 unique counties")
    if len({record["county_fips"] for record in history}) != 3144:
        raise ValueError("county history contains duplicate FIPS records")

    records: list[dict] = []
    for county in history:
        fips = county["county_fips"]
        facility = lifecycle[fips]
        treatment = treatments[fips]
        active_count = facility["active_canonical_facility_count"]
        stopped_ids = sorted(rejected[fips])
        has_facility = active_count > 0
        has_stopped = bool(stopped_ids)
        if has_facility and has_stopped:
            exposure_status = "known_facility_and_stopped_proposal"
        elif has_facility:
            exposure_status = "known_facility_inventory"
        elif has_stopped:
            exposure_status = "known_stopped_proposal_only"
        else:
            exposure_status = "no_known_project_record"

        excluded = has_facility or has_stopped
        exclusion_reasons: list[str] = []
        if has_facility:
            exclusion_reasons.append("Known active canonical facility inventory record")
        if has_stopped:
            exclusion_reasons.append("Known stopped data-center proposal")
        latest = next((year for year in county["years"] if year["year"] == 2024), None)
        if latest is None:
            raise ValueError(f"county {fips} has no 2024 panel row")
        records.append({
            "schema_version": "1.0.0",
            "control_screening_id": stable_id(fips),
            "county_fips": fips,
            "county_name": county["county_name"],
            "state_abbr": county["state_abbr"],
            "as_of": policy["as_of"],
            "exposure_status": exposure_status,
            "control_eligibility": "excluded_known_exposure" if excluded else "unresolved_negative_evidence",
            "negative_evidence_status": "not_applicable" if excluded else "not_audited",
            "known_evidence": {
                "active_canonical_facility_count": active_count,
                "facility_review_status": facility["coverage_status"],
                "first_entry_candidate_event_count": treatment["candidate_event_count"],
                "first_entry_verified": treatment["first_entry_verified"],
                "stopped_proposal_ids": stopped_ids,
                "study_project_ids": sorted(study[fips]),
            },
            "panel": {
                "start_year": county["start_year"],
                "end_year": county["end_year"],
                "complete_year_count": county["complete_year_count"],
                "coverage_status": county["coverage_status"],
                "history_path": f"panels/county-economic-history/by-state/{county['state_abbr']}.json",
            },
            "latest_metrics": {
                "year": 2024,
                "real_gdp_usd": latest["real_gdp_usd"],
                "population": latest["population"],
                "annual_avg_covered_employment": latest["annual_avg_covered_employment"],
                "annual_avg_weekly_wage_nominal_usd": latest["annual_avg_weekly_wage_nominal_usd"],
            },
            "matching_readiness": "predictor_panel_available" if county["coverage_status"] == "complete" else "panel_incomplete",
            "exclusion_reasons": exclusion_reasons,
            "required_next_step": (
                "Excluded from donor pools unless a future treatment-year design establishes a valid pre-exposure window."
                if excluded else
                "Complete all policy negative-evidence domains, spillover screening, and treatment-year-specific pre-trend diagnostics."
            ),
            "policy_id": policy["policy_id"],
        })

    by_state: dict[str, list[dict]] = defaultdict(list)
    for record in records:
        by_state[record["state_abbr"]].append(record)
    partitions = {state: sorted(items, key=lambda record: record["county_fips"]) for state, items in sorted(by_state.items())}
    states = [{
        "state_abbr": state,
        "path": f"by-state/{state}.json",
        "records": len(items),
        "by_exposure_status": count_by(items, "exposure_status"),
        "by_control_eligibility": count_by(items, "control_eligibility"),
    } for state, items in partitions.items()]
    index = {
        "schema_version": "1.0.0",
        "release_id": "county-control-eligibility-1.0.0",
        "generated_at": generated_at,
        "as_of": policy["as_of"],
        "policy_id": policy["policy_id"],
        "scope": policy["review_scope"],
        "interpretation_warning": policy["negative_evidence_rule"],
        "counts": {
            "counties": len(records),
            "states": len(partitions),
            "by_exposure_status": count_by(records, "exposure_status"),
            "by_control_eligibility": count_by(records, "control_eligibility"),
            "by_matching_readiness": count_by(records, "matching_readiness"),
        },
        "required_negative_search_domains": policy["required_negative_search_domains"],
        "future_matching_requirements": policy["future_matching_requirements"],
        "states": states,
    }
    return index, partitions, records


def main() -> int:
    index, partitions, records = build_products()
    write(PUBLIC_DIR / "index.json", index)
    for state, state_records in partitions.items():
        write(PUBLIC_DIR / "by-state" / f"{state}.json", state_records)
    write(SILVER_DIR / "county-control-screening.json", {
        "schema_version": "1.0.0",
        "release_id": index["release_id"],
        "generated_at": index["generated_at"],
        "record_count": len(records),
        "records": records,
    })
    print(json.dumps(index["counts"], indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

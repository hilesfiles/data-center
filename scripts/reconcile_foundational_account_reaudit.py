"""Apply the independently reviewed foundational-account removal directives.

The three workers were intentionally limited to append-only project fragments.  This
release migration removes the superseded base claims and legacy syntheses atomically
before the normal publication builder merges the accepted replacement fragments.
"""

from __future__ import annotations

import json
from collections import Counter
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
EVIDENCE = ROOT / "config/v1/study-economic-evidence.json"
SYNTHESIS = ROOT / "config/v1/study-modeled-synthesis.json"
SWITCH_FRAGMENT = (
    ROOT
    / "config/v1/study-economic-evidence.projects"
    / "prj_study_im3_point_06685432442.json"
)

APPLE = "prj_study_im3_building_00300974499"
SWITCH = "prj_study_im3_point_06685432442"
HAMMOND = "prj_study_im3_building_00978934687"

SWITCH_RETAIN = {
    "est_study_switch_citadel_combined_property_tax_paid_fy2024_25",
    "est_study_switch_citadel_combined_property_tax_paid_fy2025_26",
    "est_study_switch_citadel_cumulative_tax_paid_fy2025_26",
    "est_study_full_switch_storey_annual_local_service_cost_break_even",
}

SUPERSEDED_CLAIMS = {
    "clm_study_switch_storey_audit_jobs_2020",
    "clm_study_switch_storey_audit_wage_2020",
    "clm_study_switch_storey_audit_capex_2020",
    "clm_study_dx_permitted_water_withdrawal_capacity_2018",
}


def read(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def write(path: Path, payload: dict) -> None:
    path.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")


def reconcile_evidence() -> None:
    payload = read(EVIDENCE)
    present = SUPERSEDED_CLAIMS & {row["claim_id"] for row in payload["records"]}
    if present not in (set(), SUPERSEDED_CLAIMS):
        raise RuntimeError(f"Partial evidence reconciliation detected: {sorted(present)}")
    payload["records"] = [
        row for row in payload["records"] if row["claim_id"] not in SUPERSEDED_CLAIMS
    ]
    if present:
        write(EVIDENCE, payload)


def reconcile_synthesis() -> None:
    payload = read(SYNTHESIS)
    before = Counter(row["project_id"] for row in payload["estimates"])
    expected_before = Counter({APPLE: 27, SWITCH: 34, HAMMOND: 43})
    expected_after = Counter({SWITCH: 4})
    observed = Counter({key: before[key] for key in expected_before})
    if observed not in (expected_before, expected_after):
        raise RuntimeError(f"Unexpected foundational model counts: {dict(observed)}")

    payload["estimates"] = [
        row
        for row in payload["estimates"]
        if row["project_id"] not in {APPLE, HAMMOND}
        and not (row["project_id"] == SWITCH and row["estimate_id"] not in SWITCH_RETAIN)
    ]
    payload["synthesis_version"] = "study-modeled-synthesis-3.3.0"
    payload["reviewed_on"] = "2026-09-06"
    payload["scope_note"] = (
        "Foundational accounts re-audited under study-modeling-policy 1.3.0 after renewed "
        "direct-evidence searches. Apple Mesa retains three narrowly scoped business-personal-"
        "property FTZ counterfactuals from its project fragment; Switch Citadel retains four "
        "exact fiscal arithmetic or break-even syntheses; Digital Crossroad Hammond retains two "
        "two-account paid-tax arithmetic or break-even syntheses from its project fragment. All "
        "other legacy foundational estimates were removed because direct inputs, project scope, "
        "time profiles, local allocation, causal identification, or decision relevance were not "
        "defensible. Reported observations, forecasts, and remaining models stay separate."
    )
    if observed == expected_before:
        write(SYNTHESIS, payload)


def reconcile_switch_audit_trail() -> None:
    payload = read(SWITCH_FRAGMENT)
    original_scope = payload["scope_note"]
    revised_scope = original_scope.replace(
        "No synthesis fragment is added: one legacy capital-floor model requires revision, "
        "four exact fiscal arithmetic models remain eligible, and twenty-nine legacy models "
        "require removal.",
        "No synthesis fragment is added: four exact fiscal arithmetic or break-even models "
        "remain eligible, and thirty legacy models require removal. The single-claim capital-"
        "floor restatement is removed because the revised GOED capital observation is already "
        "published directly and a duplicate modeled record adds no decision-useful information.",
    )
    if revised_scope == original_scope and "thirty legacy models require removal" not in original_scope:
        raise RuntimeError("Switch scope-note reconciliation marker was not found")
    payload["scope_note"] = revised_scope

    update = next(
        row
        for row in payload["project_updates"]
        if row["title"].startswith("Legacy synthesis disposition")
    )
    original_notes = update["notes"]
    revised_notes = original_notes.replace(
        "01 est_study_switch_storey_documented_capital_floor_2021_q2 — REVISE to "
        "$452,372,959 using only clm_study_switch_storey_audit_capex_2020_rev2025; "
        "rename/relabel as an unallocated Storey-agreement capital floor through 2020 and do "
        "not add 2021 mixed-facility SEC flows.",
        "01 est_study_switch_storey_documented_capital_floor_2021_q2 — REMOVE; the revised "
        "$452,372,959 GOED capital observation is published directly, so a single-claim modeled "
        "restatement adds no decision-useful information.",
    ).replace(
        "TALLY: RETAIN 4, REVISE 1, REMOVE 29.",
        "TALLY: RETAIN 4, REVISE 0, REMOVE 30.",
    )
    if revised_notes == original_notes and "REVISE 0, REMOVE 30" not in original_notes:
        raise RuntimeError("Switch model-decision reconciliation marker was not found")
    update["notes"] = revised_notes
    if revised_scope != original_scope or revised_notes != original_notes:
        write(SWITCH_FRAGMENT, payload)


def main() -> None:
    reconcile_evidence()
    reconcile_synthesis()
    reconcile_switch_audit_trail()


if __name__ == "__main__":
    main()

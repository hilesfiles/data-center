"""Validate the county control-eligibility registry and its semantic guardrails."""

from __future__ import annotations

from pathlib import Path

if __package__:
    from .build_county_control_eligibility import POLICY_PATH, PUBLIC_DIR, SILVER_DIR, build_products, read
else:
    from build_county_control_eligibility import POLICY_PATH, PUBLIC_DIR, SILVER_DIR, build_products, read


ROOT = Path(__file__).resolve().parents[1]
SCHEMAS = ROOT / "schemas" / "v1"


def validate_control_registry(validator) -> list[str]:
    issues: list[str] = []
    try:
        index, partitions, records = build_products()
    except (KeyError, TypeError, ValueError) as error:
        return [f"county control registry: {error}"]

    for issue in validator.validate_record(read(POLICY_PATH), SCHEMAS / "county-control-eligibility-policy.schema.json"):
        issues.append(f"control policy{issue.path}: {issue.message}")
    for issue in validator.validate_record(index, SCHEMAS / "public-county-control-index.schema.json"):
        issues.append(f"control index{issue.path}: {issue.message}")
    for record in records:
        for issue in validator.validate_record(record, SCHEMAS / "public-county-control-eligibility.schema.json"):
            issues.append(f"{record['county_fips']}{issue.path}: {issue.message}")
        if record["control_eligibility"] == "eligible_verified_no_known_project":
            issues.append(f"{record['county_fips']}: v1 cannot assign verified control eligibility before negative-evidence audits")
        if record["exposure_status"] == "no_known_project_record" and record["control_eligibility"] != "unresolved_negative_evidence":
            issues.append(f"{record['county_fips']}: inventory absence must remain unresolved")

    if not (PUBLIC_DIR / "index.json").is_file() or read(PUBLIC_DIR / "index.json") != index:
        issues.append("published county control index is missing or stale; run build_county_control_eligibility.py")
    for state, expected in partitions.items():
        path = PUBLIC_DIR / "by-state" / f"{state}.json"
        if not path.is_file() or read(path) != expected:
            issues.append(f"published county control partition is missing or stale: {state}")
    silver_path = SILVER_DIR / "county-control-screening.json"
    if not silver_path.is_file():
        issues.append("silver county control registry is missing")
    elif read(silver_path).get("records") != records:
        issues.append("silver county control registry is stale")
    return issues

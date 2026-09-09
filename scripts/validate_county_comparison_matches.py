"""Validate comparison-county matching output and publication guardrails."""

from __future__ import annotations

from pathlib import Path

if __package__:
    from .build_county_comparison_matches import POLICY_PATH, PUBLIC_PATH, SILVER_PATH, build_products, read
else:
    from build_county_comparison_matches import POLICY_PATH, PUBLIC_PATH, SILVER_PATH, build_products, read

ROOT = Path(__file__).resolve().parents[1]
SCHEMAS = ROOT / "schemas" / "v1"


def validate_comparison_matches(validator) -> list[str]:
    issues: list[str] = []
    try:
        product = build_products()
    except (KeyError, TypeError, ValueError) as error:
        return [f"county comparison matches: {error}"]
    for value, schema, label in [
        (read(POLICY_PATH), "county-comparison-matching-policy.schema.json", "comparison policy"),
        (product, "public-county-comparison-match-index.schema.json", "comparison index"),
    ]:
        for issue in validator.validate_record(value, SCHEMAS / schema):
            issues.append(f"{label}{issue.path}: {issue.message}")
    host_fips = {host["county_fips"] for host in product["hosts"]}
    for host in product["hosts"]:
        ranks = [candidate["rank"] for candidate in host["comparison_candidates"]]
        if ranks != [1, 2, 3, 4, 5]:
            issues.append(f"{host['county_fips']}: candidate ranks are not 1-5")
        for candidate in host["comparison_candidates"]:
            if candidate["county_fips"] in host_fips:
                issues.append(f"{host['county_fips']}: host county entered candidate pool")
            if candidate["facility_screen_status"] != "zero_known_records_across_two_national_registries":
                issues.append(f"{host['county_fips']}: candidate failed active-facility screen")
            if candidate["verification_status"] != "local_facility_absence_review_required":
                issues.append(f"{host['county_fips']}: candidate was presented as locally verified")
    if not PUBLIC_PATH.is_file() or read(PUBLIC_PATH) != product:
        issues.append("published county comparison index is missing or stale; run build_county_comparison_matches.py")
    if not SILVER_PATH.is_file() or read(SILVER_PATH) != product:
        issues.append("silver county comparison output is missing or stale")
    return issues

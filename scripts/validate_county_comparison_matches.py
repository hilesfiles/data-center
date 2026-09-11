"""Validate comparison-county matching output and publication guardrails."""

from __future__ import annotations

from pathlib import Path

if __package__:
    from .build_county_comparison_matches import ABSENCE_ADJUDICATIONS_PATH, EXPOSURE_FINDINGS_PATH, POLICY_PATH, PUBLIC_PATH, SILVER_PATH, VERIFICATION_QUEUE_PUBLIC_PATH, VERIFICATION_QUEUE_SILVER_PATH, build_products, build_verification_queue, read
    from .build_county_treatment_anchor_review import ADJUDICATIONS_PATH, EXPOSURE_POLICY_PATH, EXPOSURE_POLICY_PUBLIC_PATH, PUBLIC_PATH as ANCHOR_PUBLIC_PATH, SILVER_PATH as ANCHOR_SILVER_PATH, build_product as build_anchor_product
else:
    from build_county_comparison_matches import ABSENCE_ADJUDICATIONS_PATH, EXPOSURE_FINDINGS_PATH, POLICY_PATH, PUBLIC_PATH, SILVER_PATH, VERIFICATION_QUEUE_PUBLIC_PATH, VERIFICATION_QUEUE_SILVER_PATH, build_products, build_verification_queue, read
    from build_county_treatment_anchor_review import ADJUDICATIONS_PATH, EXPOSURE_POLICY_PATH, EXPOSURE_POLICY_PUBLIC_PATH, PUBLIC_PATH as ANCHOR_PUBLIC_PATH, SILVER_PATH as ANCHOR_SILVER_PATH, build_product as build_anchor_product

ROOT = Path(__file__).resolve().parents[1]
SCHEMAS = ROOT / "schemas" / "v1"


def validate_comparison_matches(validator) -> list[str]:
    issues: list[str] = []
    try:
        product = build_products()
        queue = build_verification_queue(product)
        anchor_product = build_anchor_product()
    except (KeyError, TypeError, ValueError) as error:
        return [f"county comparison matches: {error}"]
    for value, schema, label in [
        (read(POLICY_PATH), "county-comparison-matching-policy.schema.json", "comparison policy"),
        (read(EXPOSURE_FINDINGS_PATH), "county-comparison-exposure-findings.schema.json", "comparison exposure findings"),
        (read(ABSENCE_ADJUDICATIONS_PATH), "county-comparison-absence-adjudications.schema.json", "comparison absence adjudications"),
        (read(EXPOSURE_POLICY_PATH), "county-data-center-exposure-policy.schema.json", "county exposure policy"),
        (read(ADJUDICATIONS_PATH), "county-treatment-anchor-adjudications.schema.json", "county treatment-anchor adjudications"),
        (product, "public-county-comparison-match-index.schema.json", "comparison index"),
        (queue, "public-county-comparison-verification-queue.schema.json", "comparison verification queue"),
        (anchor_product, "public-county-treatment-anchor-review.schema.json", "county treatment anchor review"),
    ]:
        for issue in validator.validate_record(value, SCHEMAS / schema):
            issues.append(f"{label}{issue.path}: {issue.message}")
    host_fips = {host["county_fips"] for host in product["hosts"]}
    positive_exposure_fips = {finding["county_fips"] for finding in read(EXPOSURE_FINDINGS_PATH)["findings"]}
    absence_adjudications = {record["county_fips"]: record for record in read(ABSENCE_ADJUDICATIONS_PATH)["adjudications"]}
    for host in product["hosts"]:
        ranks = [candidate["rank"] for candidate in host["comparison_candidates"]]
        if ranks != list(range(1, 13)):
            issues.append(f"{host['county_fips']}: candidate ranks are not 1-12")
        for candidate in host["comparison_candidates"]:
            if candidate["county_fips"] in host_fips:
                issues.append(f"{host['county_fips']}: host county entered candidate pool")
            if candidate["county_fips"] in positive_exposure_fips:
                issues.append(f"{host['county_fips']}: documented positive-exposure county entered candidate pool")
            if candidate["facility_screen_status"] != "zero_known_records_across_three_national_registries":
                issues.append(f"{host['county_fips']}: candidate failed active-facility screen")
            adjudication = absence_adjudications.get(candidate["county_fips"])
            expected_status = (
                "eligible_verified_no_known_project"
                if adjudication and adjudication["review_status"] == "verified_no_qualifying_exposure_found"
                else "local_facility_absence_review_required"
            )
            if candidate["verification_status"] != expected_status:
                issues.append(f"{host['county_fips']}: candidate verification status disagrees with its governed absence adjudication")
    if not PUBLIC_PATH.is_file() or read(PUBLIC_PATH) != product:
        issues.append("published county comparison index is missing or stale; run build_county_comparison_matches.py")
    if not SILVER_PATH.is_file() or read(SILVER_PATH) != product:
        issues.append("silver county comparison output is missing or stale")
    if not VERIFICATION_QUEUE_PUBLIC_PATH.is_file() or read(VERIFICATION_QUEUE_PUBLIC_PATH) != queue:
        issues.append("published comparison verification queue is missing or stale; run build_county_comparison_matches.py")
    if not VERIFICATION_QUEUE_SILVER_PATH.is_file() or read(VERIFICATION_QUEUE_SILVER_PATH) != queue:
        issues.append("silver comparison verification queue is missing or stale")
    if not ANCHOR_PUBLIC_PATH.is_file() or read(ANCHOR_PUBLIC_PATH) != anchor_product:
        issues.append("published county treatment anchor review is missing or stale; run build_county_treatment_anchor_review.py")
    if not ANCHOR_SILVER_PATH.is_file() or read(ANCHOR_SILVER_PATH) != anchor_product:
        issues.append("silver county treatment anchor review is missing or stale")
    if not EXPOSURE_POLICY_PUBLIC_PATH.is_file() or read(EXPOSURE_POLICY_PUBLIC_PATH) != read(EXPOSURE_POLICY_PATH):
        issues.append("published county exposure policy is missing or stale; run build_county_treatment_anchor_review.py")
    return issues

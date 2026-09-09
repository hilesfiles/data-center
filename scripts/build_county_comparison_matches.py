"""Build explainable comparison-county candidates for the 35 study host counties."""

from __future__ import annotations

import hashlib
import json
import math
import statistics
from collections import defaultdict
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
POLICY_PATH = ROOT / "config" / "v1" / "county-comparison-matching-policy.json"
EXPOSURE_FINDINGS_PATH = ROOT / "config" / "v1" / "county-comparison-exposure-findings.json"
ABSENCE_ADJUDICATIONS_PATH = ROOT / "config" / "v1" / "county-comparison-absence-adjudications.json"
CONTROL_POLICY_PATH = ROOT / "config" / "v1" / "county-control-eligibility-policy.json"
HISTORY_DIR = ROOT / "site" / "public" / "data" / "v1" / "panels" / "county-economic-history" / "by-state"
LIFECYCLE_PATH = ROOT / "site" / "public" / "data" / "v1" / "counties" / "lifecycle-national-tranche-6-coverage.json"
COUNTY_MAP_PATH = ROOT / "site" / "public" / "data" / "v1" / "maps" / "counties.geojson"
EXTERNAL_REGISTRY_PATHS = [
    ROOT / "data" / "bronze" / "external" / "suedatacenters-data-centers-v1.32.0.json",
    ROOT / "data" / "bronze" / "external" / "deploy-data-center-facilities-2026-09-09.json",
]
STUDY_DIR = ROOT / "site" / "public" / "data" / "v1" / "study"
PUBLIC_PATH = ROOT / "site" / "public" / "data" / "v1" / "analysis" / "county-comparison-matches" / "index.json"
SILVER_PATH = ROOT / "data" / "silver" / "analysis" / "county-comparison-matches.json"
VERIFICATION_QUEUE_PUBLIC_PATH = ROOT / "site" / "public" / "data" / "v1" / "analysis" / "county-comparison-matches" / "verification-queue.json"
VERIFICATION_QUEUE_SILVER_PATH = ROOT / "data" / "silver" / "analysis" / "county-comparison-verification-queue.json"
GENERATED_AT = "2026-09-09T00:00:00+00:00"


REGIONS = {
    "New England": "Northeast", "Middle Atlantic": "Northeast",
    "East North Central": "Midwest", "West North Central": "Midwest",
    "South Atlantic": "South", "East South Central": "South", "West South Central": "South",
    "Mountain": "West", "Pacific": "West",
}
DIVISIONS = {
    "New England": "CT ME MA NH RI VT".split(),
    "Middle Atlantic": "NJ NY PA".split(),
    "East North Central": "IN IL MI OH WI".split(),
    "West North Central": "IA KS MN MO NE ND SD".split(),
    "South Atlantic": "DE DC FL GA MD NC SC VA WV".split(),
    "East South Central": "AL KY MS TN".split(),
    "West South Central": "AR LA OK TX".split(),
    "Mountain": "AZ CO ID MT NV NM UT WY".split(),
    "Pacific": "AK CA HI OR WA".split(),
}
STATE_DIVISION = {state: division for division, states in DIVISIONS.items() for state in states}


def read(path: Path):
    return json.loads(path.read_text(encoding="utf-8"))


def write(path: Path, value) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def load_history() -> dict[str, dict]:
    records = {}
    for path in sorted(HISTORY_DIR.glob("*.json")):
        for record in read(path):
            records[record["county_fips"]] = record
    return records


def geography(state: str) -> tuple[str, str]:
    division = STATE_DIVISION[state]
    return REGIONS[division], division


def ring_contains(ring: list[list[float]], longitude: float, latitude: float) -> bool:
    inside = False
    previous = ring[-1]
    for current in ring:
        x1, y1 = previous[:2]
        x2, y2 = current[:2]
        if (y1 > latitude) != (y2 > latitude):
            crossing = (x2 - x1) * (latitude - y1) / (y2 - y1) + x1
            if longitude < crossing:
                inside = not inside
        previous = current
    return inside


def geometry_contains(geometry: dict, longitude: float, latitude: float) -> bool:
    polygons = geometry["coordinates"] if geometry["type"] == "MultiPolygon" else [geometry["coordinates"]]
    return any(ring_contains(polygon[0], longitude, latitude) and not any(ring_contains(hole, longitude, latitude) for hole in polygon[1:]) for polygon in polygons)


def geometry_bbox(geometry: dict) -> tuple[float, float, float, float]:
    polygons = geometry["coordinates"] if geometry["type"] == "MultiPolygon" else [geometry["coordinates"]]
    points = [point for polygon in polygons for ring in polygon for point in ring]
    xs = [point[0] for point in points]
    ys = [point[1] for point in points]
    return min(xs), min(ys), max(xs), max(ys)


def normalize_county_name(value: str) -> str:
    normalized = value.strip().lower().replace(".", "")
    for suffix in (" census area", " municipality", " county", " parish", " borough"):
        if normalized.endswith(suffix):
            normalized = normalized[: -len(suffix)]
            break
    return " ".join(normalized.split())


def external_registry_counties() -> tuple[dict[str, int], dict]:
    county_map = read(COUNTY_MAP_PATH)
    boundaries = [(feature["properties"]["county_fips"], geometry_bbox(feature["geometry"]), feature["geometry"]) for feature in county_map["features"]]
    names = {(feature["properties"]["state_abbr"], normalize_county_name(feature["properties"]["county_name"])): feature["properties"]["county_fips"] for feature in county_map["features"]}
    counts: dict[str, int] = defaultdict(int)
    unmatched = []
    registries = []
    for registry_path in EXTERNAL_REGISTRY_PATHS:
        registry = read(registry_path)
        registry_key = registry_path.stem
        matched_count = 0
        direct_matches: dict[str, str] = {}
        location_counties: dict[str, set[str]] = defaultdict(set)
        for facility in registry["facilities"]:
            longitude = facility.get("longitude", facility.get("lng"))
            latitude = facility.get("latitude", facility.get("lat"))
            matched = None
            if longitude is not None and latitude is not None:
                for fips, (min_x, min_y, max_x, max_y), geometry in boundaries:
                    if min_x <= longitude <= max_x and min_y <= latitude <= max_y and geometry_contains(geometry, longitude, latitude):
                        matched = fips
                        break
            if not matched and facility.get("county") and facility.get("state"):
                matched = names.get((facility["state"], normalize_county_name(facility["county"])))
            if matched:
                direct_matches[facility["id"]] = matched
                if facility.get("locationId"):
                    location_counties[facility["locationId"]].add(matched)
        for facility in registry["facilities"]:
            matched_fips = set()
            if facility["id"] in direct_matches:
                matched_fips.add(direct_matches[facility["id"]])
            elif facility.get("locationId"):
                matched_fips.update(location_counties.get(facility["locationId"], set()))
            if matched_fips:
                for matched in matched_fips:
                    counts[matched] += 1
                matched_count += 1
            else:
                unmatched.append(f"{registry_key}:{facility['id']}")
        registries.append({"path": registry_path, "document": registry, "matched_count": matched_count})
    return counts, {"registries": registries, "unmatched_ids": unmatched}


def growth(first: float, last: float, periods: int) -> float:
    return (last / first) ** (1 / periods) - 1 if first > 0 and last >= 0 else 0.0


def make_features(county: dict, start_year: int, end_year: int) -> dict | None:
    rows = [row for row in county["years"] if start_year <= row["year"] <= end_year]
    fields = ["population", "real_gdp_usd", "annual_avg_covered_employment", "annual_avg_weekly_wage_nominal_usd"]
    if len(rows) != end_year - start_year + 1 or any(row[field] is None for row in rows for field in fields):
        return None
    population = [row["population"] for row in rows]
    gdp = [row["real_gdp_usd"] for row in rows]
    employment = [row["annual_avg_covered_employment"] for row in rows]
    wage = [row["annual_avg_weekly_wage_nominal_usd"] for row in rows]
    periods = len(rows) - 1
    return {
        "population_mean": round(statistics.fmean(population), 2),
        "real_gdp_usd_mean": round(statistics.fmean(gdp), 2),
        "covered_employment_mean": round(statistics.fmean(employment), 2),
        "weekly_wage_usd_mean": round(statistics.fmean(wage), 2),
        "real_gdp_per_capita_mean": round(statistics.fmean(g / p for g, p in zip(gdp, population)), 2),
        "covered_employment_per_100_residents_mean": round(statistics.fmean(e / p * 100 for e, p in zip(employment, population)), 4),
        "population_growth_rate": round(growth(population[0], population[-1], periods), 6),
        "real_gdp_growth_rate": round(growth(gdp[0], gdp[-1], periods), 6),
        "covered_employment_growth_rate": round(growth(employment[0], employment[-1], periods), 6),
        "weekly_wage_growth_rate": round(growth(wage[0], wage[-1], periods), 6),
    }


def transformed(features: dict) -> dict[str, float]:
    return {
        "log_population_mean": math.log1p(features["population_mean"]),
        "log_real_gdp_mean": math.log1p(features["real_gdp_usd_mean"]),
        "log_covered_employment_mean": math.log1p(features["covered_employment_mean"]),
        "log_weekly_wage_mean": math.log1p(features["weekly_wage_usd_mean"]),
        "real_gdp_per_capita_mean": features["real_gdp_per_capita_mean"],
        "covered_employment_per_100_residents_mean": features["covered_employment_per_100_residents_mean"],
        "population_growth_rate": features["population_growth_rate"],
        "real_gdp_growth_rate": features["real_gdp_growth_rate"],
        "covered_employment_growth_rate": features["covered_employment_growth_rate"],
        "weekly_wage_growth_rate": features["weekly_wage_growth_rate"],
    }


def robust_scales(vectors: list[dict[str, float]], keys: list[str]) -> dict[str, float]:
    result = {}
    for key in keys:
        values = sorted(vector[key] for vector in vectors)
        quartiles = statistics.quantiles(values, n=4, method="inclusive")
        scale = quartiles[2] - quartiles[0]
        if scale <= 0:
            scale = statistics.pstdev(values) or 1.0
        result[key] = scale
    return result


def load_absence_adjudications(history: dict[str, dict], exposure_findings: dict, control_policy: dict) -> tuple[dict[str, dict], dict]:
    document = read(ABSENCE_ADJUDICATIONS_PATH)
    if document["as_of"] != control_policy["as_of"]:
        raise ValueError("absence adjudication and control-policy as-of dates must match")
    required_domains = [domain["code"] for domain in control_policy["required_negative_search_domains"]]
    exposure_ids = {finding["finding_id"] for finding in exposure_findings["findings"]}
    records: dict[str, dict] = {}
    for adjudication in document["adjudications"]:
        fips = adjudication["county_fips"]
        if fips in records:
            raise ValueError(f"duplicate absence adjudication for county {fips}")
        if fips not in history:
            raise ValueError(f"absence adjudication references unknown county {fips}")
        county = history[fips]
        if county["county_name"] != adjudication["county_name"] or county["state_abbr"] != adjudication["state_abbr"]:
            raise ValueError(f"absence adjudication has inconsistent county identity for {fips}")
        domain_codes = [domain["code"] for domain in adjudication["domain_reviews"]]
        if domain_codes != required_domains:
            raise ValueError(f"absence adjudication domains must follow policy order for {fips}")
        statuses = [domain["status"] for domain in adjudication["domain_reviews"]]
        status = adjudication["review_status"]
        eligibility = adjudication["control_eligibility"]
        if status == "verified_no_qualifying_exposure_found":
            if eligibility != "eligible_verified_no_known_project":
                raise ValueError(f"verified absence adjudication has inconsistent eligibility for {fips}")
            if adjudication["record_status"] != "final" or not adjudication["completed_on"]:
                raise ValueError(f"verified absence adjudication must be final and completed for {fips}")
            if adjudication["reviewed_through"] < document["as_of"]:
                raise ValueError(f"verified absence adjudication is stale for {fips}")
            if set(statuses) != {"reviewed_no_qualifying_evidence"}:
                raise ValueError(f"verified absence adjudication must clear all domains for {fips}")
            if adjudication["exposure_finding_ids"]:
                raise ValueError(f"verified absence adjudication cannot reference positive findings for {fips}")
            for domain in adjudication["domain_reviews"]:
                if not domain["repositories"] or not domain["queries"] or not domain["sources"]:
                    raise ValueError(f"verified domain review lacks documented search evidence for {fips}:{domain['code']}")
        elif status == "qualifying_exposure_found":
            if eligibility != "excluded_known_exposure" or "qualifying_evidence_found" not in statuses:
                raise ValueError(f"positive absence adjudication has inconsistent decision for {fips}")
            if not adjudication["exposure_finding_ids"] or not set(adjudication["exposure_finding_ids"]).issubset(exposure_ids):
                raise ValueError(f"positive absence adjudication lacks governed exposure finding for {fips}")
        elif eligibility != "unresolved_negative_evidence":
            raise ValueError(f"unresolved absence adjudication has inconsistent eligibility for {fips}")
        records[fips] = adjudication
    return records, document


def build_products(generated_at: str = GENERATED_AT) -> dict:
    policy = read(POLICY_PATH)
    exposure_findings = read(EXPOSURE_FINDINGS_PATH)
    control_policy = read(CONTROL_POLICY_PATH)
    history = load_history()
    absence_adjudications, absence_document = load_absence_adjudications(history, exposure_findings, control_policy)
    lifecycle = {record["county_fips"]: record for record in read(LIFECYCLE_PATH)}
    external_counts, external_meta = external_registry_counties()
    study = read(STUDY_DIR / "index.json")
    projects_by_county: dict[str, list[dict]] = defaultdict(list)
    anchors_by_county: dict[str, list[int]] = defaultdict(list)
    for project in study["projects"]:
        projects_by_county[project["county_fips"]].append(project)
        detail = read(STUDY_DIR / project["detail_path"])
        anchor = detail["history"].get("anchor")
        if anchor:
            year = int(anchor.get("date", "")[:4]) if anchor.get("date") else anchor.get("year")
            if year:
                anchors_by_county[project["county_fips"]].append(year)
    host_fips = set(projects_by_county)
    if len(host_fips) != 35 or len(study["projects"]) != 36:
        raise ValueError("study register must contain 36 projects across 35 host counties")
    candidate_count = policy["candidate_count_per_host"]
    weights = policy["feature_weights"]
    geography_adjustments = policy["geography_adjustments"]
    positive_exposure_fips = set()
    for finding in exposure_findings["findings"]:
        fips = finding["county_fips"]
        if fips not in history:
            raise ValueError(f"positive exposure finding references unknown county {fips}")
        county = history[fips]
        if county["county_name"] != finding["county_name"] or county["state_abbr"] != finding["state_abbr"]:
            raise ValueError(f"positive exposure finding has inconsistent county identity for {fips}")
        positive_exposure_fips.add(fips)
    candidate_fips = sorted(
        fips for fips, record in lifecycle.items()
        if record["active_canonical_facility_count"] == 0
        and external_counts.get(fips, 0) == 0
        and fips not in positive_exposure_fips
        and fips not in host_fips
    )

    hosts = []
    for fips in sorted(host_fips):
        projects = sorted(projects_by_county[fips], key=lambda item: item["project_id"])
        anchor_year = min(anchors_by_county[fips]) if anchors_by_county[fips] else None
        if anchor_year is not None and anchor_year - policy["baseline_year_count"] >= 2001:
            end_year = anchor_year - 1
            start_year = end_year - policy["baseline_year_count"] + 1
            strategy = "pre_documented_project_anchor"
            note = "Five calendar years immediately preceding the earliest documented study-project anchor in this host county. The anchor is not asserted to be the county's first data center."
        else:
            start_year = policy["fallback_baseline"]["start_year"]
            end_year = policy["fallback_baseline"]["end_year"]
            strategy = "common_early_panel_window"
            note = "Structural comparison uses the first five available panel years because no sufficiently early documented study-project anchor is stored. It is not a verified pre-data-center period."
        host_features = make_features(history[fips], start_year, end_year)
        if host_features is None:
            raise ValueError(f"host county {fips} lacks complete baseline features")
        eligible = []
        for candidate in candidate_fips:
            features = make_features(history[candidate], start_year, end_year)
            if features is not None:
                eligible.append((candidate, features, transformed(features)))
        keys = list(weights)
        scales = robust_scales([vector for _, _, vector in eligible], keys)
        host_vector = transformed(host_features)
        host_region, host_division = geography(history[fips]["state_abbr"])
        scored = []
        for candidate, features, vector in eligible:
            candidate_record = history[candidate]
            candidate_region, candidate_division = geography(candidate_record["state_abbr"])
            distance = math.sqrt(sum(weights[key] * ((host_vector[key] - vector[key]) / scales[key]) ** 2 for key in keys))
            if candidate_region != host_region:
                distance += geography_adjustments["different_census_region_penalty"]
            elif candidate_division != host_division:
                distance += geography_adjustments["different_census_division_penalty"]
            scored.append((distance, candidate, candidate_record, candidate_region, candidate_division, features))
        scored.sort(key=lambda item: (item[0], item[1]))
        comparisons = []
        for rank, (distance, candidate, record, region, division, features) in enumerate(scored[:candidate_count], 1):
            adjudication = absence_adjudications.get(candidate)
            verified = bool(adjudication and adjudication["review_status"] == "verified_no_qualifying_exposure_found")
            comparisons.append({
                "rank": rank, "county_fips": candidate, "county_name": record["county_name"], "state_abbr": record["state_abbr"],
                "census_region": region, "census_division": division, "same_census_region": region == host_region, "same_census_division": division == host_division,
                "match_score": round(100 / (1 + distance), 2), "standardized_distance": round(distance, 6),
                "facility_screen_status": "zero_known_records_across_three_national_registries", "verification_status": "eligible_verified_no_known_project" if verified else "local_facility_absence_review_required",
                "absence_adjudication_id": adjudication["adjudication_id"] if adjudication else None,
                "absence_reviewed_through": adjudication["reviewed_through"] if adjudication else None,
                "features": features, "history_path": f"panels/county-economic-history/by-state/{record['state_abbr']}.json",
            })
        county = history[fips]
        hosts.append({
            "county_fips": fips, "county_name": county["county_name"], "state_abbr": county["state_abbr"],
            "census_region": host_region, "census_division": host_division,
            "project_ids": [project["project_id"] for project in projects], "project_names": [project["name"] for project in projects],
            "baseline": {"start_year": start_year, "end_year": end_year, "strategy": strategy, "anchor_year": anchor_year, "note": note},
            "features": host_features, "comparison_candidates": comparisons,
        })
    unique_comparisons = {candidate["county_fips"] for host in hosts for candidate in host["comparison_candidates"]}
    verified_comparisons = {fips for fips in unique_comparisons if fips in absence_adjudications and absence_adjudications[fips]["review_status"] == "verified_no_qualifying_exposure_found"}
    return {
        "schema_version": "1.0.0", "release_id": "county-comparison-matches-1.0.0", "generated_at": generated_at,
        "as_of": policy["as_of"], "policy_id": policy["policy_id"], "scope": policy["purpose"],
        "counts": {"host_counties": len(hosts), "host_projects": len(study["projects"]), "comparison_candidates": sum(len(host["comparison_candidates"]) for host in hosts), "analytical_candidates_per_host": candidate_count, "presentation_candidates_per_host": policy["presentation_candidate_count"], "unique_comparison_counties": len(unique_comparisons), "screened_candidate_pool_count": len(candidate_fips), "candidate_specific_positive_exclusions": len(positive_exposure_fips), "externally_verified_absent": len(verified_comparisons)},
        "screening_sources": [
            {"source_id": "repository_active_canonical_facility_inventory", "title": "DCCIO active canonical-facility inventory", "version": "lifecycle-national-tranche-6", "record_count": len(lifecycle), "url": None, "license": None, "retrieved_on": policy["as_of"], "sha256": hashlib.sha256(LIFECYCLE_PATH.read_bytes()).hexdigest()},
            {"source_id": "suedatacenters_registry_v1_32_0", "title": external_meta["registries"][0]["document"]["name"], "version": external_meta["registries"][0]["document"]["basedOn"]["version"], "record_count": external_meta["registries"][0]["document"]["count"], "url": external_meta["registries"][0]["document"]["documentation"], "license": external_meta["registries"][0]["document"]["license"], "retrieved_on": external_meta["registries"][0]["document"]["retrieved"], "sha256": hashlib.sha256(EXTERNAL_REGISTRY_PATHS[0].read_bytes()).hexdigest()},
            {"source_id": "deploy_facility_registry_2026_09_09", "title": external_meta["registries"][1]["document"]["name"], "version": "2026-09-09 snapshot", "record_count": external_meta["registries"][1]["document"]["count"], "url": external_meta["registries"][1]["document"]["documentation"], "license": external_meta["registries"][1]["document"]["license"], "retrieved_on": external_meta["registries"][1]["document"]["retrieved"], "sha256": hashlib.sha256(EXTERNAL_REGISTRY_PATHS[1].read_bytes()).hexdigest()},
        ],
        "positive_exposure_findings": {
            "dataset_id": exposure_findings["dataset_id"],
            "path": "config/v1/county-comparison-exposure-findings.json",
            "record_count": len(exposure_findings["findings"]),
            "excluded_count": len(positive_exposure_fips),
            "qualifying_rule": exposure_findings["qualifying_rule"],
            "interpretation_note": exposure_findings["interpretation_note"],
            "sha256": hashlib.sha256(EXPOSURE_FINDINGS_PATH.read_bytes()).hexdigest(),
        },
        "absence_adjudications": {
            "dataset_id": absence_document["dataset_id"],
            "path": "config/v1/county-comparison-absence-adjudications.json",
            "record_count": len(absence_document["adjudications"]),
            "verified_candidate_count": len(verified_comparisons),
            "decision_rule": absence_document["decision_rule"],
            "sha256": hashlib.sha256(ABSENCE_ADJUDICATIONS_PATH.read_bytes()).hexdigest(),
        },
        "external_registry_unmatched_coordinate_ids": external_meta["unmatched_ids"],
        "method": {
            "candidate_pool": "Counties outside the 35-host cohort with zero linked records in the repository active-facility inventory and two pinned external national registries, no governed candidate-specific positive exposure finding, and complete baseline features.",
            "distance": "Square root of the weighted sum of squared feature differences standardized by candidate-pool interquartile ranges, plus disclosed Census-geography penalties.",
            "score": "100 / (1 + standardized distance). Scores rank candidates within a host specification and are not probabilities.",
            "baseline_rule": "Use five years before the earliest documented study-project anchor when available; otherwise use the labeled 2001–2005 structural window.",
            "features": list(weights), "feature_weights": weights, "geography_adjustments": geography_adjustments,
        },
        "interpretation_limits": policy["interpretation_limits"], "hosts": hosts,
    }


def build_verification_queue(product: dict) -> dict:
    control_policy = read(CONTROL_POLICY_PATH)
    absence_document = read(ABSENCE_ADJUDICATIONS_PATH)
    adjudications = {record["county_fips"]: record for record in absence_document["adjudications"]}
    candidates: dict[str, dict] = {}
    for host in product["hosts"]:
        for candidate in host["comparison_candidates"]:
            record = candidates.setdefault(candidate["county_fips"], {
                "county_fips": candidate["county_fips"],
                "county_name": candidate["county_name"],
                "state_abbr": candidate["state_abbr"],
                "host_matches": [],
            })
            record["host_matches"].append({
                "host_county_fips": host["county_fips"],
                "host_county_name": host["county_name"],
                "host_state_abbr": host["state_abbr"],
                "candidate_rank": candidate["rank"],
                "match_score": candidate["match_score"],
            })
    ordered = sorted(
        candidates.values(),
        key=lambda item: (
            -len(item["host_matches"]),
            min(match["candidate_rank"] for match in item["host_matches"]),
            -max(match["match_score"] for match in item["host_matches"]),
            item["county_fips"],
        ),
    )
    domains = control_policy["required_negative_search_domains"]
    for priority, record in enumerate(ordered, 1):
        adjudication = adjudications.get(record["county_fips"])
        record["priority"] = priority
        record["candidate_slot_count"] = len(record["host_matches"])
        record["best_match_rank"] = min(match["candidate_rank"] for match in record["host_matches"])
        record["best_match_score"] = max(match["match_score"] for match in record["host_matches"])
        record["mean_match_score"] = round(statistics.fmean(match["match_score"] for match in record["host_matches"]), 2)
        record["host_matches"].sort(key=lambda match: (match["candidate_rank"], -match["match_score"], match["host_county_fips"]))
        verified = bool(adjudication and adjudication["review_status"] == "verified_no_qualifying_exposure_found")
        record["review_status"] = "eligible_verified_no_known_project" if verified else "local_facility_absence_review_required"
        record["absence_adjudication_id"] = adjudication["adjudication_id"] if adjudication else None
        record["absence_reviewed_through"] = adjudication["reviewed_through"] if adjudication else None
        if adjudication:
            reviews = {domain["code"]: domain for domain in adjudication["domain_reviews"]}
            record["domain_reviews"] = [
                {**reviews[domain["code"]], "code": domain["code"], "label": domain["label"]}
                for domain in domains
            ]
        else:
            record["domain_reviews"] = [
                {"code": domain["code"], "label": domain["label"], "status": "not_reviewed", "repositories": [], "queries": [], "coverage_statement": "Not reviewed.", "finding": "No determination.", "limitations": ["Required county-specific review has not been completed."], "sources": []}
                for domain in domains
            ]
        record["required_next_step"] = "Run treatment-year-specific spillover and pre-trend diagnostics before causal use." if verified else "Audit every required domain through each linked host county's treatment year; record dated sources and spillover checks before any causal use."
    verified_count = sum(record["review_status"] == "eligible_verified_no_known_project" for record in ordered)
    return {
        "schema_version": "1.0.0",
        "release_id": "county-comparison-verification-queue-1.0.0",
        "generated_at": product["generated_at"],
        "as_of": product["as_of"],
        "policy_id": control_policy["policy_id"],
        "scope": "Prioritized local absence-verification queue for the unique counties appearing in the current expanded host-to-comparison analytical reserve.",
        "counts": {
            "unique_candidates": len(ordered),
            "candidate_slots": sum(record["candidate_slot_count"] for record in ordered),
            "locally_verified_absent": verified_count,
            "local_absence_review_required": len(ordered) - verified_count,
        },
        "priority_rule": "Audit counties used by the most host matches first, then best candidate rank, best match score, and county FIPS.",
        "required_negative_search_domains": domains,
        "candidates": ordered,
    }


def main() -> int:
    product = build_products()
    queue = build_verification_queue(product)
    write(PUBLIC_PATH, product)
    write(SILVER_PATH, product)
    write(VERIFICATION_QUEUE_PUBLIC_PATH, queue)
    write(VERIFICATION_QUEUE_SILVER_PATH, queue)
    print(json.dumps(product["counts"], indent=2, sort_keys=True))
    print(json.dumps(queue["counts"], indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

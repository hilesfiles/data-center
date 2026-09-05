"""Validate scoped economic evidence and materialize existing source/claim contracts.

Claims stay separate from harmonized observations until their subject and period can
support those accounts. A source-checked amount is not automatically an impact result.
"""
from __future__ import annotations

import json
import math
from collections import defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
EVIDENCE = ROOT / "config/v1/study-economic-evidence.json"
ANNUAL_PERIODS = ("fiscal_year", "calendar_year", "tax_year", "source_year")


def validate_evidence(evidence, candidates):
    if __package__:
        from .validate_data_contract import ContractValidator
    else:
        from validate_data_contract import ContractValidator
    issues = ContractValidator(ROOT / "schemas/v1").validate_record(
        evidence, ROOT / "schemas/v1/study-economic-evidence.schema.json")
    if issues:
        raise ValueError("Economic evidence schema: " + "; ".join(str(i) for i in issues))
    projects = {r["project_id"]: r for r in candidates}
    metrics = {m["metric_code"]: m for m in evidence["metrics"]}
    sources = {s["source_id"]: s for s in evidence["sources"]}
    if len(metrics) != len(evidence["metrics"]) or len(sources) != len(evidence["sources"]):
        raise ValueError("Duplicate economic metric or source")
    update_keys = set()
    for update in evidence.get("project_updates", []):
        if update["project_id"] not in projects or update["source_id"] not in sources:
            raise ValueError("Unknown research-update project or source")
        key = (update["project_id"], update["source_id"], update["as_of"])
        if key in update_keys:
            raise ValueError("Duplicate research update")
        update_keys.add(key)
    ids, source_facts, series_signatures, series_years, annual_points = set(), set(), {}, set(), set()
    for r in evidence["records"]:
        if r["claim_id"] in ids:
            raise ValueError("Duplicate economic claim")
        ids.add(r["claim_id"])
        if r["project_id"] not in projects or r["metric_code"] not in metrics or r["source_id"] not in sources:
            raise ValueError("Unknown economic project, metric or source")
        if r["scope"]["county_fips"] != projects[r["project_id"]]["county_fips"]:
            raise ValueError("Economic evidence host county mismatch")
        if not math.isfinite(r["value"]):
            raise ValueError("Economic value must be finite")
        pdf_source = sources[r["source_id"]]["review_method"] in ("pdf_text_and_page_image", "web_pdf_text")
        if pdf_source != ("pdf_page" in r and "printed_page" in r) or (not pdf_source and ("pdf_page" in r or "printed_page" in r)):
            raise ValueError("PDF sources require page locators; web pages use section locators; structured data uses field locators")
        period = r["period"]
        if (r["basis"] == "source_projection") != (period["kind"] == "projection_horizon"):
            raise ValueError("Projection basis and horizon must agree")
        if (metrics[r["metric_code"]]["measure_type"] == "peak") != (period["kind"] == "historical_peak"):
            raise ValueError("Peak workforce requires historical-peak timing")
        if period["kind"] == "cumulative" and metrics[r["metric_code"]]["measure_type"] != "flow":
            raise ValueError("Cumulative spending requires a flow measure")
        # Repeating a campus/company fact on another building would inflate coverage.
        fact = (r["source_id"], r["metric_code"], json.dumps(period, sort_keys=True),
                json.dumps(r["scope"], sort_keys=True))
        if fact in source_facts:
            raise ValueError("Duplicate scoped source fact")
        source_facts.add(fact)
        if key := r.get("annual_series_key"):
            if r["basis"] != "reported_actual" or period["kind"] not in ANNUAL_PERIODS or r.get("value_qualifier", "exact") != "exact":
                raise ValueError("Annual series requires exact reported actual fiscal, calendar, tax or source-year evidence")
            signature = (r["project_id"], r["metric_code"], json.dumps(r["scope"], sort_keys=True), period["kind"])
            if key in series_signatures and series_signatures[key] != signature:
                raise ValueError("Annual series mixes metrics or subject scopes or year bases")
            series_signatures[key] = signature
            point = (*signature, period["year"])
            if (key, period["year"]) in series_years or point in annual_points:
                raise ValueError("Annual series repeats a year; reconcile source revisions first")
            series_years.add((key, period["year"]))
            annual_points.add(point)
    return metrics, sources


def economic_products(evidence, candidates, stamp):
    metrics, sources = validate_evidence(evidence, candidates)
    by_project = defaultdict(list)
    claims = []
    for record in evidence["records"]:
        metric = metrics[record["metric_code"]]
        row = {**record, **{k: metric[k] for k in ("label", "category", "unit", "measure_type", "aggregation")}}
        by_project[row["project_id"]].append(row)
        value = {"type": "quantity", "value": row["value"], "unit": row["unit"]}
        if row["unit"].startswith("USD"):
            value.update(currency="USD", price_basis="nominal")
        # The canonical quantity contract has no bound/approximation field. Keep
        # qualified values structured rather than emitting an exact threshold.
        if row.get("value_qualifier", "exact") != "exact":
            value = {"type": "json", "value": {**value, "qualifier": row["value_qualifier"]}}
        # A candidate key represents the source's wider subject, without asserting
        # that an entire campus or county taxpayer account is one mapped building.
        claims.append({
            "schema_version": "1.0.0", "claim_id": row["claim_id"], "source_id": row["source_id"],
            "subject": {"entity_type": "campus" if row["scope"]["level"] == "campus" else "geography",
                        "candidate_key": row["scope"]["label"]},
            "attribute_path": row["metric_code"], "raw_value": value,
            "source_excerpt_reference": {"section": row["source_locator"], **({"page": row["pdf_page"]} if "pdf_page" in row else {})},
            "claim_date": {"precision": "year", "year": row["period"]["year"]} if row["period"]["kind"] in (*ANNUAL_PERIODS, "source_year") else {"precision": "unknown"},
            "extraction_method": "llm_structured_output", "extractor_version": evidence["evidence_version"],
            "claim_confidence": 0.9, "review_status": "accepted", "record_status": "provisional",
            "notes": f"Source transcription checked; independent measurement not verified. {row['basis']}; {row['period']['label']}. Study link: {row['project_id']}. {row['notes']}",
            "created_at": stamp, "updated_at": stamp,
        })
    canonical_sources = [{
        **{k: s[k] for k in ("source_id", "source_type", "publisher", "title", "url", "publication_date")},
        "schema_version": "1.0.0", "copyright_policy": "metadata_only",
        "created_at": stamp, "updated_at": stamp, "record_status": "active",
    } for s in sources.values()]
    return by_project, claims, canonical_sources


def category_coverage(records, category):
    matching = [r for r in records if r["category"] == category]
    if not matching:
        return "not_yet_collected"
    return "partial" if any(r["basis"] == "reported_actual" for r in matching) else "projections_only"

"""Validate and group governed modeled syntheses without creating source claims."""
from __future__ import annotations

import json
import math
from collections import defaultdict
from datetime import date
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SYNTHESIS = ROOT / "config/v1/study-modeled-synthesis.json"
MODELING_POLICY = ROOT / "config/v1/study-modeling-policy.json"
CAUSAL_METHODS = {"difference_in_differences", "event_study", "synthetic_control"}
MULTIPLIER_METHODS = {"input_output_multiplier", "contribution_analysis"}


def _read(path):
    return json.loads(path.read_text(encoding="utf-8"))


def _finite(values, estimate_id):
    if not all(isinstance(value, (int, float)) and math.isfinite(value) for value in values):
        raise ValueError(f"Non-finite modeled value: {estimate_id}")


def modeled_products(payload, candidates, evidence, policy=None):
    """Return project-grouped estimates after semantic and anti-overlap checks."""
    policy = _read(MODELING_POLICY) if policy is None else policy
    if payload["modeling_policy_version"] != policy["policy_version"]:
        raise ValueError("Modeled synthesis policy version mismatch")
    if any(row.get("basis") == "modeled_synthesis" for row in evidence["records"]):
        raise ValueError("Modeled values cannot enter canonical source evidence")

    project_ids = {row["project_id"] for row in candidates}
    claim_ids = {row["claim_id"] for row in evidence["records"]}
    source_ids = {row["source_id"] for row in evidence["sources"]} | {row["source_id"] for row in payload["sources"]}
    estimate_ids = {row["estimate_id"] for row in payload["estimates"]}
    if len(estimate_ids) != len(payload["estimates"]):
        raise ValueError("Duplicate modeled estimate")

    keys = set()
    grouped = {project_id: [] for project_id in project_ids}
    aggregation_rows = defaultdict(list)
    component_owners = {}
    for row in payload["estimates"]:
        estimate_id = row["estimate_id"]
        if row["project_id"] not in project_ids:
            raise ValueError(f"Unknown modeled project: {row['project_id']}")
        interval = row["interval"]
        _finite([row["value"], interval["low"], interval["central"], interval["high"]], estimate_id)
        if not interval["low"] <= interval["central"] <= interval["high"] or row["value"] != interval["central"]:
            raise ValueError(f"Invalid modeled interval ordering: {estimate_id}")
        if interval["kind"] in {"point_estimate", "deterministic_counterfactual"} and not interval["low"] == interval["central"] == interval["high"]:
            raise ValueError(f"Non-degenerate deterministic interval: {estimate_id}")

        period = row["period"]
        if period["kind"] == "construction_period" and date.fromisoformat(period["start_date"]) > date.fromisoformat(period["end_date"]):
            raise ValueError(f"Invalid modeled period ordering: {estimate_id}")
        if row["scope"]["inventory_allocation"] == "allocated" and row["derivation"]["method"] != "allocation":
            raise ValueError(f"Allocated modeled value lacks allocation method: {estimate_id}")

        derivation = row["derivation"]
        missing_claims = set(derivation["input_claim_ids"]) - claim_ids
        missing_sources = set(derivation["input_source_ids"]) - source_ids
        if missing_claims or missing_sources:
            raise ValueError(f"Unknown modeled inputs: {estimate_id}")
        parameter_names = [parameter["name"] for parameter in row["parameters"]]
        if len(parameter_names) != len(set(parameter_names)):
            raise ValueError(f"Duplicate modeled parameter: {estimate_id}")
        for parameter in row["parameters"]:
            _finite([parameter["value"]], estimate_id)
            provenance = parameter["provenance"]
            reference = provenance.get("reference_id")
            if provenance["kind"] == "claim" and (reference not in claim_ids or reference not in derivation["input_claim_ids"]):
                raise ValueError(f"Unknown or undeclared parameter claim: {estimate_id}")
            if provenance["kind"] == "source" and (reference not in source_ids or reference not in derivation["input_source_ids"]):
                raise ValueError(f"Unknown or undeclared parameter source: {estimate_id}")

        method = derivation["method"]
        if method in CAUSAL_METHODS and "causal_design" not in row:
            raise ValueError(f"Missing causal-design metadata: {estimate_id}")
        if method in MULTIPLIER_METHODS:
            multiplier = row.get("multiplier_provenance")
            if not multiplier or multiplier["source_id"] not in derivation["input_source_ids"]:
                raise ValueError(f"Incomplete multiplier provenance: {estimate_id}")

        key = (row["project_id"], row["metric_code"], json.dumps(period, sort_keys=True), row["scope"]["label"], row["contribution_channel"])
        if key in keys:
            raise ValueError(f"Duplicate modeled project/metric/period/scope/channel: {estimate_id}")
        keys.add(key)
        aggregation_rows[row["aggregation"]["aggregation_id"]].append(row)
        grouped[row["project_id"]].append(row)

    for aggregation_id, rows in aggregation_rows.items():
        standalone = [row for row in rows if row["aggregation"]["role"] == "standalone"]
        if len(rows) > 1 and standalone:
            raise ValueError(f"Overlapping standalone aggregation: {aggregation_id}")
        totals = [row for row in rows if row["aggregation"]["role"] == "total"]
        for total in totals:
            if total["contribution_channel"] != "total":
                raise ValueError(f"Aggregation total lacks total channel: {total['estimate_id']}")
            for component_id in total["aggregation"]["component_estimate_ids"]:
                component = next((row for row in rows if row["estimate_id"] == component_id), None)
                if not component or component["aggregation"]["role"] != "component":
                    raise ValueError(f"Unknown or invalid aggregation component: {total['estimate_id']}")
                if component_id in component_owners:
                    raise ValueError(f"Overlapping aggregation component: {component_id}")
                component_owners[component_id] = total["estimate_id"]
    return grouped, payload["sources"]

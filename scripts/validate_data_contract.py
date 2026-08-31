#!/usr/bin/env python3
"""Validate DCCIO Draft 2020-12 schemas and scenario fixtures without dependencies.

The validator implements the JSON Schema keywords used by this repository. It is not a
general replacement for a standards-compliant JSON Schema implementation. CI may run a
full validator in addition to this deterministic baseline.
"""

from __future__ import annotations

import hashlib
import json
import math
import re
import sys
from collections import Counter
from dataclasses import dataclass
from datetime import date, datetime
from pathlib import Path
from typing import Any
from urllib.parse import urlparse


ROOT = Path(__file__).resolve().parents[1]
SCHEMA_DIR = ROOT / "schemas" / "v1"
VALID_FIXTURE_DIR = ROOT / "fixtures" / "v1" / "valid"
INVALID_FIXTURE_DIR = ROOT / "fixtures" / "v1" / "invalid"
CONFIG_DIR = ROOT / "config" / "v1"
PUBLIC_DATA_DIR = ROOT / "site" / "public" / "data" / "v1"
DATA_DIR = ROOT / "data"
CORE_STATE_FIPS = {
    "01", "02", "04", "05", "06", "08", "09", "10", "11", "12", "13",
    "15", "16", "17", "18", "19", "20", "21", "22", "23", "24", "25",
    "26", "27", "28", "29", "30", "31", "32", "33", "34", "35", "36",
    "37", "38", "39", "40", "41", "42", "44", "45", "46", "47", "48",
    "49", "50", "51", "53", "54", "55", "56",
}


@dataclass(frozen=True)
class Issue:
    code: str
    path: str
    message: str

    def __str__(self) -> str:
        return f"[{self.code}] {self.path}: {self.message}"


def load_json(path: Path) -> Any:
    with path.open("r", encoding="utf-8") as handle:
        return json.load(handle)


class ContractValidator:
    """Small validator for the subset of Draft 2020-12 used by DCCIO schemas."""

    def __init__(self, schema_dir: Path) -> None:
        self.schema_dir = schema_dir
        self.schemas_by_path: dict[Path, dict[str, Any]] = {}
        self.schemas_by_id: dict[str, tuple[Path, dict[str, Any]]] = {}
        for path in sorted(schema_dir.glob("*.schema.json")):
            schema = load_json(path)
            resolved = path.resolve()
            self.schemas_by_path[resolved] = schema
            schema_id = schema.get("$id")
            if schema_id:
                self.schemas_by_id[schema_id] = (resolved, schema)

    def validate_record(self, record: Any, schema_path: Path) -> list[Issue]:
        resolved = schema_path.resolve()
        schema = self.schemas_by_path[resolved]
        return self._validate(record, schema, resolved, "$", schema)

    def _resolve_ref(
        self, reference: str, current_path: Path, root_schema: dict[str, Any]
    ) -> tuple[dict[str, Any], Path, dict[str, Any]]:
        document_ref, _, fragment = reference.partition("#")
        if not document_ref:
            target_path = current_path
            target_root = root_schema
        elif document_ref in self.schemas_by_id:
            target_path, target_root = self.schemas_by_id[document_ref]
        else:
            target_path = (current_path.parent / document_ref).resolve()
            if target_path not in self.schemas_by_path:
                raise KeyError(f"unresolvable schema reference {reference!r}")
            target_root = self.schemas_by_path[target_path]

        target: Any = target_root
        if fragment:
            if not fragment.startswith("/"):
                raise KeyError(f"unsupported non-pointer fragment in {reference!r}")
            for token in fragment.lstrip("/").split("/"):
                token = token.replace("~1", "/").replace("~0", "~")
                target = target[token]
        if not isinstance(target, dict):
            raise KeyError(f"schema reference {reference!r} did not resolve to an object")
        return target, target_path, target_root

    @staticmethod
    def _is_type(instance: Any, expected: str) -> bool:
        checks = {
            "object": lambda x: isinstance(x, dict),
            "array": lambda x: isinstance(x, list),
            "string": lambda x: isinstance(x, str),
            "number": lambda x: isinstance(x, (int, float)) and not isinstance(x, bool),
            "integer": lambda x: isinstance(x, int) and not isinstance(x, bool),
            "boolean": lambda x: isinstance(x, bool),
            "null": lambda x: x is None,
        }
        return checks[expected](instance)

    def _validate(
        self,
        instance: Any,
        schema: dict[str, Any],
        current_path: Path,
        instance_path: str,
        root_schema: dict[str, Any],
    ) -> list[Issue]:
        issues: list[Issue] = []

        if "$ref" in schema:
            try:
                target, target_path, target_root = self._resolve_ref(
                    schema["$ref"], current_path, root_schema
                )
            except (KeyError, TypeError) as exc:
                return [Issue("schema_reference", instance_path, str(exc))]
            return self._validate(instance, target, target_path, instance_path, target_root)

        if "allOf" in schema:
            for child in schema["allOf"]:
                issues.extend(
                    self._validate(instance, child, current_path, instance_path, root_schema)
                )

        if "anyOf" in schema:
            branches = [
                self._validate(instance, child, current_path, instance_path, root_schema)
                for child in schema["anyOf"]
            ]
            if all(branch for branch in branches):
                issues.append(Issue("schema_validation", instance_path, "does not satisfy anyOf"))

        if "oneOf" in schema:
            branches = [
                self._validate(instance, child, current_path, instance_path, root_schema)
                for child in schema["oneOf"]
            ]
            successes = sum(not branch for branch in branches)
            if successes != 1:
                issues.append(
                    Issue(
                        "schema_validation",
                        instance_path,
                        f"must satisfy exactly one oneOf branch; satisfied {successes}",
                    )
                )

        if "if" in schema:
            condition_issues = self._validate(
                instance, schema["if"], current_path, instance_path, root_schema
            )
            branch_name = "then" if not condition_issues else "else"
            if branch_name in schema:
                issues.extend(
                    self._validate(
                        instance,
                        schema[branch_name],
                        current_path,
                        instance_path,
                        root_schema,
                    )
                )

        expected_type = schema.get("type")
        if expected_type is not None:
            valid_type = (
                any(self._is_type(instance, item) for item in expected_type)
                if isinstance(expected_type, list)
                else self._is_type(instance, expected_type)
            )
            if not valid_type:
                return issues + [
                    Issue(
                        "schema_validation",
                        instance_path,
                        f"expected type {expected_type!r}, got {type(instance).__name__}",
                    )
                ]

        if "const" in schema and instance != schema["const"]:
            issues.append(
                Issue("schema_validation", instance_path, f"must equal {schema['const']!r}")
            )
        if "enum" in schema and instance not in schema["enum"]:
            issues.append(
                Issue("schema_validation", instance_path, f"value {instance!r} is not allowed")
            )

        if isinstance(instance, dict):
            for field in schema.get("required", []):
                if field not in instance:
                    issues.append(
                        Issue("schema_validation", instance_path, f"missing required property {field!r}")
                    )
            declared = schema.get("properties", {})
            for key, value in instance.items():
                child_path = f"{instance_path}.{key}"
                if key in declared:
                    issues.extend(
                        self._validate(value, declared[key], current_path, child_path, root_schema)
                    )
                elif schema.get("additionalProperties") is False:
                    issues.append(
                        Issue("schema_validation", child_path, "additional property is not allowed")
                    )
                elif isinstance(schema.get("additionalProperties"), dict):
                    issues.extend(
                        self._validate(
                            value,
                            schema["additionalProperties"],
                            current_path,
                            child_path,
                            root_schema,
                        )
                    )

        if isinstance(instance, list):
            if len(instance) < schema.get("minItems", 0):
                issues.append(Issue("schema_validation", instance_path, "array is too short"))
            if "maxItems" in schema and len(instance) > schema["maxItems"]:
                issues.append(Issue("schema_validation", instance_path, "array is too long"))
            if schema.get("uniqueItems"):
                serialized = [json.dumps(item, sort_keys=True) for item in instance]
                if len(serialized) != len(set(serialized)):
                    issues.append(Issue("schema_validation", instance_path, "array items are not unique"))
            item_schema = schema.get("items")
            if isinstance(item_schema, dict):
                for index, value in enumerate(instance):
                    issues.extend(
                        self._validate(
                            value,
                            item_schema,
                            current_path,
                            f"{instance_path}[{index}]",
                            root_schema,
                        )
                    )

        if isinstance(instance, str):
            if len(instance) < schema.get("minLength", 0):
                issues.append(Issue("schema_validation", instance_path, "string is too short"))
            if "maxLength" in schema and len(instance) > schema["maxLength"]:
                issues.append(Issue("schema_validation", instance_path, "string is too long"))
            if "pattern" in schema and re.search(schema["pattern"], instance) is None:
                issues.append(
                    Issue(
                        "schema_validation",
                        instance_path,
                        f"does not match pattern {schema['pattern']!r}",
                    )
                )
            if "format" in schema and not self._valid_format(instance, schema["format"]):
                issues.append(
                    Issue(
                        "schema_validation",
                        instance_path,
                        f"is not a valid {schema['format']}",
                    )
                )

        if isinstance(instance, (int, float)) and not isinstance(instance, bool):
            if not math.isfinite(instance):
                issues.append(Issue("schema_validation", instance_path, "number must be finite"))
            if "minimum" in schema and instance < schema["minimum"]:
                issues.append(Issue("schema_validation", instance_path, "number is below minimum"))
            if "maximum" in schema and instance > schema["maximum"]:
                issues.append(Issue("schema_validation", instance_path, "number is above maximum"))
            if "exclusiveMinimum" in schema and instance <= schema["exclusiveMinimum"]:
                issues.append(
                    Issue("schema_validation", instance_path, "number is not above exclusive minimum")
                )
            if "exclusiveMaximum" in schema and instance >= schema["exclusiveMaximum"]:
                issues.append(
                    Issue("schema_validation", instance_path, "number is not below exclusive maximum")
                )

        return issues

    @staticmethod
    def _valid_format(value: str, format_name: str) -> bool:
        try:
            if format_name == "date":
                date.fromisoformat(value)
                return bool(re.fullmatch(r"\d{4}-\d{2}-\d{2}", value))
            if format_name == "date-time":
                datetime.fromisoformat(value.replace("Z", "+00:00"))
                return "T" in value
            if format_name == "uri":
                parsed = urlparse(value)
                return bool(parsed.scheme and (parsed.netloc or parsed.scheme == "urn"))
        except ValueError:
            return False
        return True


ID_FIELDS = {
    "campus": "campus_id",
    "facility": "facility_id",
    "operator": "operator_id",
    "operator_relationship": "relationship_id",
    "project": "project_id",
    "project_phase": "phase_id",
    "event": "event_id",
    "source": "source_id",
    "source_artifact": "artifact_id",
    "claim": "claim_id",
    "claim_resolution": "resolution_id",
    "review_decision": "review_decision_id",
    "observation": "observation_id",
    "panel_row": "panel_row_id",
    "acquisition_manifest": "manifest_id",
    "treatment_definition": "treatment_definition_id",
    "model_specification": "model_specification_id",
    "model_run": "model_run_id",
    "analysis_unit": "analysis_unit_id",
    "model_estimate": "estimate_id",
    "model_diagnostic": "diagnostic_id",
    "donor_weight": "donor_weight_id",
    "index_score": "index_score_id",
}


def collect_ids(fixture: dict[str, Any]) -> tuple[set[str], list[Issue]]:
    identifiers: set[str] = set()
    issues: list[Issue] = []
    for collection, id_field in ID_FIELDS.items():
        for index, record in enumerate(fixture.get(collection, [])):
            identifier = record.get(id_field)
            if not identifier:
                continue
            if identifier in identifiers:
                issues.append(
                    Issue(
                        "referential_integrity",
                        f"$.{collection}[{index}].{id_field}",
                        f"duplicate identifier {identifier!r}",
                    )
                )
            identifiers.add(identifier)
    return identifiers, issues


def check_reference(
    reference: str | None, identifiers: set[str], path: str, issues: list[Issue]
) -> None:
    if reference and reference not in identifiers:
        issues.append(
            Issue("referential_integrity", path, f"reference {reference!r} does not exist")
        )


def validate_references(fixture: dict[str, Any]) -> list[Issue]:
    ids, issues = collect_ids(fixture)
    geography_ids = {row["geography_id"] for row in fixture.get("geography_reference", [])}
    metric_codes = {row["metric_code"] for row in fixture.get("metric_definition", [])}

    for i, record in enumerate(fixture.get("campus", [])):
        for j, assignment in enumerate(record.get("geography_assignments", [])):
            if assignment["geography_id"] not in geography_ids:
                issues.append(Issue("referential_integrity", f"$.campus[{i}].geography_assignments[{j}]", "unknown geography"))
    for i, record in enumerate(fixture.get("facility", [])):
        check_reference(record.get("campus_id"), ids, f"$.facility[{i}].campus_id", issues)
        for j, assignment in enumerate(record.get("geography_assignments", [])):
            if assignment["geography_id"] not in geography_ids:
                issues.append(Issue("referential_integrity", f"$.facility[{i}].geography_assignments[{j}]", "unknown geography"))
    for i, record in enumerate(fixture.get("operator", [])):
        check_reference(record.get("parent_operator_id"), ids, f"$.operator[{i}].parent_operator_id", issues)
    for i, record in enumerate(fixture.get("operator_relationship", [])):
        check_reference(record.get("operator_id"), ids, f"$.operator_relationship[{i}].operator_id", issues)
        check_reference(record.get("subject_id"), ids, f"$.operator_relationship[{i}].subject_id", issues)
        for j, claim_id in enumerate(record.get("source_claim_ids", [])):
            check_reference(claim_id, ids, f"$.operator_relationship[{i}].source_claim_ids[{j}]", issues)
    for i, record in enumerate(fixture.get("project", [])):
        for j, target in enumerate(record.get("target_refs", [])):
            check_reference(target.get("entity_id"), ids, f"$.project[{i}].target_refs[{j}]", issues)
    for i, record in enumerate(fixture.get("project_phase", [])):
        check_reference(record.get("project_id"), ids, f"$.project_phase[{i}].project_id", issues)
        check_reference(record.get("facility_id"), ids, f"$.project_phase[{i}].facility_id", issues)
    for i, record in enumerate(fixture.get("event", [])):
        for j, subject in enumerate(record.get("subjects", [])):
            check_reference(subject.get("entity_id"), ids, f"$.event[{i}].subjects[{j}]", issues)
        for j, claim_id in enumerate(record.get("source_claim_ids", [])):
            check_reference(claim_id, ids, f"$.event[{i}].source_claim_ids[{j}]", issues)
    for i, record in enumerate(fixture.get("source_artifact", [])):
        check_reference(record.get("source_id"), ids, f"$.source_artifact[{i}].source_id", issues)
    for i, record in enumerate(fixture.get("claim", [])):
        check_reference(record.get("source_id"), ids, f"$.claim[{i}].source_id", issues)
        check_reference(record.get("source_artifact_id"), ids, f"$.claim[{i}].source_artifact_id", issues)
        check_reference(record.get("subject", {}).get("entity_id"), ids, f"$.claim[{i}].subject.entity_id", issues)
    for i, record in enumerate(fixture.get("claim_resolution", [])):
        check_reference(record.get("subject", {}).get("entity_id"), ids, f"$.claim_resolution[{i}].subject.entity_id", issues)
        refs = record.get("claim_refs", {})
        check_reference(refs.get("winning"), ids, f"$.claim_resolution[{i}].claim_refs.winning", issues)
        for group in ("supporting", "conflicting"):
            for j, claim_id in enumerate(refs.get(group, [])):
                check_reference(claim_id, ids, f"$.claim_resolution[{i}].claim_refs.{group}[{j}]", issues)
    for i, record in enumerate(fixture.get("observation", [])):
        subject = record.get("subject", {})
        if subject.get("subject_type") in {"campus", "facility", "project", "project_phase"}:
            check_reference(subject.get("subject_id"), ids, f"$.observation[{i}].subject.subject_id", issues)
        elif subject.get("subject_type") in {"county", "state", "cbsa", "utility_territory", "balancing_authority", "nation"} and subject.get("subject_id") not in geography_ids:
            issues.append(Issue("referential_integrity", f"$.observation[{i}].subject.subject_id", "unknown geography"))
        if record.get("metric_code") not in metric_codes:
            issues.append(Issue("referential_integrity", f"$.observation[{i}].metric_code", "unknown metric"))
        for field in ("source_ids", "source_claim_ids"):
            for j, reference in enumerate(record.get(field, [])):
                check_reference(reference, ids, f"$.observation[{i}].{field}[{j}]", issues)
        for j, reference in enumerate(record.get("derivation", {}).get("input_observation_ids", [])):
            check_reference(reference, ids, f"$.observation[{i}].derivation.input_observation_ids[{j}]", issues)
    for i, record in enumerate(fixture.get("panel_row", [])):
        if record.get("geography", {}).get("geography_id") not in geography_ids:
            issues.append(Issue("referential_integrity", f"$.panel_row[{i}].geography.geography_id", "unknown geography"))
        for j, reference in enumerate(record.get("observation_refs", [])):
            check_reference(reference.get("observation_id"), ids, f"$.panel_row[{i}].observation_refs[{j}].observation_id", issues)
            if reference.get("metric_code") not in metric_codes:
                issues.append(Issue("referential_integrity", f"$.panel_row[{i}].observation_refs[{j}].metric_code", "unknown metric"))
    for i, record in enumerate(fixture.get("model_specification", [])):
        check_reference(record.get("treatment_definition_id"), ids, f"$.model_specification[{i}].treatment_definition_id", issues)
        if record.get("outcome_metric_code") not in metric_codes:
            issues.append(Issue("referential_integrity", f"$.model_specification[{i}].outcome_metric_code", "unknown metric"))
    for i, record in enumerate(fixture.get("model_run", [])):
        check_reference(record.get("model_specification_id"), ids, f"$.model_run[{i}].model_specification_id", issues)
    for i, record in enumerate(fixture.get("analysis_unit", [])):
        check_reference(record.get("model_run_id"), ids, f"$.analysis_unit[{i}].model_run_id", issues)
        check_reference(record.get("panel_row_id"), ids, f"$.analysis_unit[{i}].panel_row_id", issues)
        check_reference(record.get("treatment_definition_id"), ids, f"$.analysis_unit[{i}].treatment_definition_id", issues)
        if record.get("geography", {}).get("geography_id") not in geography_ids:
            issues.append(Issue("referential_integrity", f"$.analysis_unit[{i}].geography.geography_id", "unknown geography"))
    for collection in ("model_estimate", "model_diagnostic", "donor_weight"):
        for i, record in enumerate(fixture.get(collection, [])):
            check_reference(record.get("model_run_id"), ids, f"$.{collection}[{i}].model_run_id", issues)
    for i, record in enumerate(fixture.get("index_score", [])):
        for j, component in enumerate(record.get("components", [])):
            for field in ("estimate_id", "observation_id", "input_index_score_id"):
                check_reference(component.get(field), ids, f"$.index_score[{i}].components[{j}].{field}", issues)
    for i, record in enumerate(fixture.get("public_county_summary", [])):
        if record.get("county_fips") not in geography_ids:
            issues.append(Issue("referential_integrity", f"$.public_county_summary[{i}].county_fips", "unknown geography"))
        for code, value in record.get("indices", {}).items():
            check_reference(value.get("index_score_id"), ids, f"$.public_county_summary[{i}].indices.{code}.index_score_id", issues)

    return issues


def validate_schema_catalog(validator: ContractValidator) -> list[Issue]:
    issues: list[Issue] = []
    catalog_path = SCHEMA_DIR / "catalog.json"
    catalog = load_json(catalog_path)
    catalog_paths = {entry["path"] for entry in catalog["schemas"]}
    actual_paths = {path.name for path in SCHEMA_DIR.glob("*.schema.json")}
    for missing in sorted(actual_paths - catalog_paths):
        issues.append(Issue("schema_catalog", "$.schemas", f"schema {missing!r} is not cataloged"))
    for missing in sorted(catalog_paths - actual_paths):
        issues.append(Issue("schema_catalog", "$.schemas", f"catalog path {missing!r} does not exist"))
    names = [entry["name"] for entry in catalog["schemas"]]
    if len(names) != len(set(names)):
        issues.append(Issue("schema_catalog", "$.schemas", "schema names are not unique"))

    for path, schema in validator.schemas_by_path.items():
        if schema.get("$schema") != "https://json-schema.org/draft/2020-12/schema":
            issues.append(Issue("schema_catalog", path.name, "schema draft must be 2020-12"))
        if not schema.get("$id"):
            issues.append(Issue("schema_catalog", path.name, "schema is missing $id"))
        issues.extend(check_schema_refs(schema, path, validator, "$"))
    return issues


def check_schema_refs(
    node: Any, current_path: Path, validator: ContractValidator, path: str
) -> list[Issue]:
    issues: list[Issue] = []
    if isinstance(node, dict):
        if "$ref" in node:
            try:
                validator._resolve_ref(node["$ref"], current_path, validator.schemas_by_path[current_path])
            except (KeyError, TypeError) as exc:
                issues.append(Issue("schema_reference", f"{current_path.name}:{path}.$ref", str(exc)))
        for key, value in node.items():
            issues.extend(check_schema_refs(value, current_path, validator, f"{path}.{key}"))
    elif isinstance(node, list):
        for index, value in enumerate(node):
            issues.extend(check_schema_refs(value, current_path, validator, f"{path}[{index}]"))
    return issues


def validate_fixture(
    path: Path, validator: ContractValidator, schema_paths: dict[str, Path]
) -> list[Issue]:
    fixture = load_json(path)
    issues: list[Issue] = []
    ignored = {"fixture_version", "description", "expected_error_codes"}
    for collection, records in fixture.items():
        if collection in ignored:
            continue
        if collection not in schema_paths:
            issues.append(Issue("schema_catalog", f"$.{collection}", "fixture collection has no schema"))
            continue
        if not isinstance(records, list):
            issues.append(Issue("schema_validation", f"$.{collection}", "fixture collection must be an array"))
            continue
        for index, record in enumerate(records):
            for issue in validator.validate_record(record, schema_paths[collection]):
                issues.append(Issue(issue.code, f"{path.name}:{collection}[{index}]{issue.path[1:]}", issue.message))
    if not any(issue.code == "schema_validation" for issue in issues):
        issues.extend(validate_references(fixture))
    return issues


def validate_project_config(
    validator: ContractValidator, schema_paths: dict[str, Path]
) -> list[Issue]:
    issues: list[Issue] = []
    config_files = {
        path.stem: load_json(path) for path in sorted(CONFIG_DIR.glob("*.json"))
    }
    required = {
        "event-taxonomy",
        "index-methodology",
        "metric-registry",
        "model-specifications",
        "opposition-taxonomy",
        "source-quality",
        "source-registry",
        "treatment-definitions",
    }
    for name in sorted(required - config_files.keys()):
        issues.append(Issue("config_validation", f"config/{name}.json", "required config is missing"))

    if issues:
        return issues

    events = config_files["event-taxonomy"]["events"]
    event_codes = [row["code"] for row in events]
    if len(event_codes) != len(set(event_codes)):
        issues.append(Issue("config_validation", "event-taxonomy.events", "event codes are not unique"))
    event_schema = load_json(schema_paths["event"])
    schema_event_codes = set(event_schema["properties"]["event_type"]["enum"])
    if set(event_codes) != schema_event_codes:
        issues.append(Issue("config_validation", "event-taxonomy.events", "taxonomy and event schema enums differ"))

    metrics = config_files["metric-registry"]["metrics"]
    metric_codes = [row["metric_code"] for row in metrics]
    metric_code_set = set(metric_codes)
    if len(metric_codes) != len(metric_code_set):
        issues.append(Issue("config_validation", "metric-registry.metrics", "metric codes are not unique"))
    for index, metric in enumerate(metrics):
        denominator = metric.get("denominator_metric_code")
        if denominator and denominator not in metric_code_set:
            issues.append(Issue("config_validation", f"metric-registry.metrics[{index}]", f"unknown denominator {denominator!r}"))

    treatments = config_files["treatment-definitions"]["treatments"]
    treatment_ids: set[str] = set()
    for index, record in enumerate(treatments):
        treatment_ids.add(record.get("treatment_definition_id", ""))
        for issue in validator.validate_record(record, schema_paths["treatment_definition"]):
            issues.append(Issue("config_validation", f"treatment-definitions.treatments[{index}]{issue.path[1:]}", issue.message))
        for event_type in record.get("qualifying_event_types", []):
            if event_type not in schema_event_codes:
                issues.append(Issue("config_validation", f"treatment-definitions.treatments[{index}]", f"unknown event type {event_type!r}"))
        for metric_code in record.get("exposure_metric_codes", []):
            if metric_code not in metric_code_set:
                issues.append(Issue("config_validation", f"treatment-definitions.treatments[{index}]", f"unknown exposure metric {metric_code!r}"))

    for index, record in enumerate(config_files["model-specifications"]["models"]):
        for issue in validator.validate_record(record, schema_paths["model_specification"]):
            issues.append(Issue("config_validation", f"model-specifications.models[{index}]{issue.path[1:]}", issue.message))
        if record.get("treatment_definition_id") not in treatment_ids:
            issues.append(Issue("config_validation", f"model-specifications.models[{index}]", "unknown treatment definition"))
        for metric_code in [record.get("outcome_metric_code"), *record.get("covariate_metric_codes", [])]:
            if metric_code not in metric_code_set:
                issues.append(Issue("config_validation", f"model-specifications.models[{index}]", f"unknown metric {metric_code!r}"))

    for code, definition in config_files["index-methodology"]["indices"].items():
        components = definition.get("components")
        if components and not math.isclose(sum(components.values()), 1.0, abs_tol=1e-9):
            issues.append(Issue("config_validation", f"index-methodology.indices.{code}.components", "weights must sum to 1"))

    source_codes = [row["code"] for row in config_files["source-registry"]["sources"]]
    if len(source_codes) != len(set(source_codes)):
        issues.append(Issue("config_validation", "source-registry.sources", "source codes are not unique"))
    return issues


def validate_public_data(
    validator: ContractValidator, schema_paths: dict[str, Path]
) -> list[Issue]:
    issues: list[Issue] = []
    counties_path = PUBLIC_DATA_DIR / "maps" / "counties.geojson"
    counties_geojson = load_json(counties_path)
    if counties_geojson.get("type") != "FeatureCollection":
        issues.append(Issue("public_data_validation", "maps/counties.geojson", "must be a FeatureCollection"))
    features = counties_geojson.get("features", [])
    feature_fips_list = [
        feature.get("properties", {}).get("county_fips") for feature in features
    ]
    feature_fips = set(feature_fips_list)
    if len(features) != 3144:
        issues.append(Issue("public_data_validation", "maps/counties.geojson", f"expected 3,144 Census 2025 counties; found {len(features)}"))
    if len(feature_fips_list) != len(feature_fips):
        issues.append(Issue("public_data_validation", "maps/counties.geojson", "county FIPS values must be unique"))
    if any(not isinstance(fips, str) or re.fullmatch(r"\d{5}", fips) is None for fips in feature_fips):
        issues.append(Issue("public_data_validation", "maps/counties.geojson", "every feature must have a five-digit county FIPS"))
    states_present = {
        feature.get("properties", {}).get("state_fips") for feature in features
    }
    if states_present != CORE_STATE_FIPS:
        issues.append(Issue("public_data_validation", "maps/counties.geojson", "scope must be the 50 states and District of Columbia"))
    metadata = counties_geojson.get("metadata", {})
    if metadata.get("record_count") != len(features) or metadata.get("reference_vintage") != "2025-01-01":
        issues.append(Issue("public_data_validation", "maps/counties.geojson.metadata", "record count or Census reference vintage is inconsistent"))

    features_by_fips = {
        feature["properties"]["county_fips"]: feature["properties"]
        for feature in features
        if feature.get("properties", {}).get("county_fips")
    }
    geography_path = DATA_DIR / "silver" / "geography" / "counties-2025.json"
    geography_document = load_json(geography_path)
    geography_records = geography_document.get("records", [])
    geography_fips = {record.get("county_fips") for record in geography_records}
    if geography_document.get("record_count") != len(geography_records) or geography_fips != feature_fips:
        issues.append(Issue("public_data_validation", "data/silver/geography/counties-2025.json", "geography collection and public map must contain the same counties"))
    for index, record in enumerate(geography_records):
        for issue in validator.validate_record(record, schema_paths["geography_reference"]):
            issues.append(Issue("public_data_validation", f"counties-2025.json.records[{index}]{issue.path[1:]}", issue.message))

    acquisition_path = DATA_DIR / "raw" / "census-tigerweb" / "2025-counties-5m.acquisition.json"
    acquisition = load_json(acquisition_path)
    for issue in validator.validate_record(acquisition, schema_paths["acquisition_manifest"]):
        issues.append(Issue("public_data_validation", f"2025-counties-5m.acquisition.json{issue.path[1:]}", issue.message))

    dataset_manifest_path = DATA_DIR / "silver" / "geography" / "counties-2025.manifest.json"
    dataset_manifest = load_json(dataset_manifest_path)
    for issue in validator.validate_record(dataset_manifest, schema_paths["dataset_manifest"]):
        issues.append(Issue("public_data_validation", f"counties-2025.manifest.json{issue.path[1:]}", issue.message))
    map_part = dataset_manifest.get("parts", [{}])[0]
    actual_map_payload = counties_path.read_bytes()
    actual_map_hash = hashlib.sha256(actual_map_payload).hexdigest()
    if (
        dataset_manifest.get("record_count") != len(features)
        or map_part.get("record_count") != len(features)
        or map_part.get("byte_size") != len(actual_map_payload)
        or map_part.get("sha256") != actual_map_hash
    ):
        issues.append(Issue("public_data_validation", "counties-2025.manifest.json", "map count, byte size, or SHA-256 does not match the artifact"))

    coverage_path = PUBLIC_DATA_DIR / "counties" / "facility-source-coverage.json"
    coverage_records = load_json(coverage_path)
    coverage_fips = [record.get("county_fips") for record in coverage_records]
    if len(coverage_records) != 3144 or set(coverage_fips) != feature_fips:
        issues.append(Issue("public_data_validation", "counties/facility-source-coverage.json", "coverage must contain every Census county exactly once"))
    if len(coverage_fips) != len(set(coverage_fips)):
        issues.append(Issue("public_data_validation", "counties/facility-source-coverage.json", "coverage county FIPS values must be unique"))
    coverage_by_fips: dict[str, dict[str, Any]] = {}
    for index, record in enumerate(coverage_records):
        county_fips = record.get("county_fips", "")
        coverage_by_fips[county_fips] = record
        for issue in validator.validate_record(
            record, schema_paths["public_facility_source_coverage"]
        ):
            issues.append(Issue("public_data_validation", f"facility-source-coverage.json[{index}]{issue.path[1:]}", issue.message))
        boundary = features_by_fips.get(county_fips, {})
        if record.get("county_name") != boundary.get("county_name") or record.get("state_abbr") != boundary.get("state_abbr"):
            issues.append(Issue("public_data_validation", f"facility-source-coverage.json[{index}]", "county identity does not match the Census boundary"))
        expected_status = "source_records_present" if record.get("source_record_count", 0) > 0 else "no_source_record"
        if record.get("coverage_status") != expected_status:
            issues.append(Issue("public_data_validation", f"facility-source-coverage.json[{index}]", "coverage status and source record count disagree"))

    facilities_map_path = PUBLIC_DATA_DIR / "maps" / "facilities.geojson"
    facilities_geojson = load_json(facilities_map_path)
    facility_features = facilities_geojson.get("features", [])
    facility_ids = [feature.get("properties", {}).get("entity_id") for feature in facility_features]
    if facilities_geojson.get("type") != "FeatureCollection" or len(facility_features) != 1472:
        issues.append(Issue("public_data_validation", "maps/facilities.geojson", "must contain 1,472 IM3 source-object points"))
    if len(facility_ids) != len(set(facility_ids)):
        issues.append(Issue("public_data_validation", "maps/facilities.geojson", "entity IDs must be unique"))
    facility_metadata = facilities_geojson.get("metadata", {})
    if (
        facility_metadata.get("record_count") != len(facility_features)
        or facility_metadata.get("release_vintage") != "2026.02.09"
        or facility_metadata.get("license") != "ODbL 1.0"
    ):
        issues.append(Issue("public_data_validation", "maps/facilities.geojson.metadata", "record count, release, or ODbL metadata is inconsistent"))

    expected_coverage: dict[str, Counter[str]] = {
        fips: Counter() for fips in feature_fips if isinstance(fips, str)
    }
    expected_footprint: Counter[str] = Counter()
    for index, feature in enumerate(facility_features):
        properties = feature.get("properties", {})
        counties = properties.get("county_fipses", [])
        primary = properties.get("primary_county_fips")
        layer = properties.get("source_layer")
        if feature.get("geometry", {}).get("type") != "Point":
            issues.append(Issue("public_data_validation", f"maps/facilities.geojson.features[{index}]", "public facility geometry must be a centroid point"))
        if not counties or any(county not in feature_fips for county in counties):
            issues.append(Issue("public_data_validation", f"maps/facilities.geojson.features[{index}]", "county assignment is missing from Census geography"))
        if primary not in counties:
            issues.append(Issue("public_data_validation", f"maps/facilities.geojson.features[{index}]", "primary county must be one of the assigned counties"))
        if layer not in {"point", "building", "campus"}:
            issues.append(Issue("public_data_validation", f"maps/facilities.geojson.features[{index}]", "unknown IM3 source layer"))
            continue
        for county_fips in counties:
            expected_coverage[county_fips]["source_record_count"] += 1
            expected_coverage[county_fips][f"{layer}_record_count"] += 1
            expected_coverage[county_fips]["named_record_count"] += int(bool(properties.get("source_name")))
            expected_coverage[county_fips]["operator_named_record_count"] += int(bool(properties.get("source_operator")))
            expected_coverage[county_fips]["cross_county_source_record_count"] += int(len(counties) > 1)
            if len(counties) == 1 and isinstance(properties.get("footprint_sqft"), (int, float)):
                expected_footprint[county_fips] += properties["footprint_sqft"]

    for county_fips, expected in expected_coverage.items():
        actual = coverage_by_fips.get(county_fips, {})
        for field, value in expected.items():
            if actual.get(field) != value:
                issues.append(Issue("public_data_validation", f"facility-source-coverage.json[{county_fips}]", f"{field} does not match facility source records"))
        if actual.get("observed_footprint_sqft") != expected_footprint[county_fips]:
            issues.append(Issue("public_data_validation", f"facility-source-coverage.json[{county_fips}]", "observed footprint does not match single-county source records"))

    facility_index_path = PUBLIC_DATA_DIR / "facilities" / "index.json"
    facility_index = load_json(facility_index_path)
    index_ids = [record.get("entity_id") for record in facility_index]
    if len(facility_index) != 1472 or set(index_ids) != set(facility_ids):
        issues.append(Issue("public_data_validation", "facilities/index.json", "facility index and map must contain the same 1,472 source objects"))

    im3_acquisition_path = DATA_DIR / "raw" / "im3-atlas" / "2026.02.09.acquisition.json"
    im3_acquisition = load_json(im3_acquisition_path)
    for issue in validator.validate_record(im3_acquisition, schema_paths["acquisition_manifest"]):
        issues.append(Issue("public_data_validation", f"2026.02.09.acquisition.json{issue.path[1:]}", issue.message))
    if im3_acquisition.get("sha256") != "1c0d8c206eb2070785e594784fda90f615e6ed7fd9646d67e1a9de237b8cc9f4":
        issues.append(Issue("public_data_validation", "2026.02.09.acquisition.json", "pinned IM3 artifact hash changed"))

    bronze_path = DATA_DIR / "bronze" / "im3-atlas" / "2026.02.09-source-rows.json"
    bronze = load_json(bronze_path)
    source_rows = bronze.get("records", [])
    source_row_ids = [record.get("source_row_id") for record in source_rows]
    layer_counts = Counter(record.get("source_layer") for record in source_rows)
    if (
        bronze.get("record_count") != 1479
        or bronze.get("in_scope_row_count") != 1477
        or bronze.get("excluded_from_public_scope_count") != 2
        or layer_counts != Counter({"point": 105, "building": 1239, "campus": 135})
        or len(source_row_ids) != len(set(source_row_ids))
    ):
        issues.append(Issue("public_data_validation", "2026.02.09-source-rows.json", "source row counts, layers, scope, or row IDs are inconsistent"))
    for index, record in enumerate(source_rows):
        for issue in validator.validate_record(record, schema_paths["facility_seed_source_record"]):
            issues.append(Issue("public_data_validation", f"2026.02.09-source-rows.json.records[{index}]{issue.path[1:]}", issue.message))

    silver_path = DATA_DIR / "silver" / "infrastructure" / "im3-2026.02.09.json"
    silver = load_json(silver_path)
    collections = silver.get("collections", {})
    expected_collection_counts = {
        "source": 1,
        "source_artifact": 1,
        "campus": 132,
        "facility": 1340,
        "claim": 1472,
        "claim_resolution": 1472,
        "observation": 1472,
    }
    actual_collection_counts = {name: len(collections.get(name, [])) for name in expected_collection_counts}
    if actual_collection_counts != expected_collection_counts or silver.get("record_count") != sum(expected_collection_counts.values()):
        issues.append(Issue("public_data_validation", "im3-2026.02.09.json", "silver collection counts are inconsistent"))
    for collection, expected_count in expected_collection_counts.items():
        if expected_count == 0:
            continue
        for index, record in enumerate(collections.get(collection, [])):
            for issue in validator.validate_record(record, schema_paths[collection]):
                issues.append(Issue("public_data_validation", f"im3-2026.02.09.json.{collection}[{index}]{issue.path[1:]}", issue.message))

    reference_fixture = {
        **collections,
        "geography_reference": geography_records,
        "metric_definition": load_json(CONFIG_DIR / "metric-registry.json")["metrics"],
    }
    for issue in validate_references(reference_fixture):
        issues.append(Issue("public_data_validation", f"im3-2026.02.09.json:{issue.path}", issue.message))

    processing_report = load_json(
        DATA_DIR / "silver" / "infrastructure" / "im3-2026.02.09.processing-report.json"
    )
    if (
        processing_report.get("source_row_count") != 1479
        or processing_report.get("distinct_in_scope_source_record_count") != 1472
        or processing_report.get("cross_county_source_record_count") != 5
        or processing_report.get("centroid_county_mismatch_count") != 4
        or processing_report.get("county_name_mismatch_count") != 0
    ):
        issues.append(Issue("public_data_validation", "im3-2026.02.09.processing-report.json", "expected scope, cross-county, or geography diagnostics changed"))

    im3_manifest_path = DATA_DIR / "silver" / "infrastructure" / "im3-2026.02.09.manifest.json"
    im3_manifest = load_json(im3_manifest_path)
    for issue in validator.validate_record(im3_manifest, schema_paths["dataset_manifest"]):
        issues.append(Issue("public_data_validation", f"im3-2026.02.09.manifest.json{issue.path[1:]}", issue.message))
    total_manifest_records = 0
    for index, part in enumerate(im3_manifest.get("parts", [])):
        part_path = (ROOT / part.get("path", "")).resolve()
        if not part_path.is_relative_to(ROOT) or not part_path.is_file():
            issues.append(Issue("public_data_validation", f"im3-2026.02.09.manifest.json.parts[{index}]", "part path is missing or outside the repository"))
            continue
        payload = part_path.read_bytes()
        total_manifest_records += part.get("record_count", 0)
        if part.get("byte_size") != len(payload) or part.get("sha256") != hashlib.sha256(payload).hexdigest():
            issues.append(Issue("public_data_validation", f"im3-2026.02.09.manifest.json.parts[{index}]", "byte size or SHA-256 does not match the artifact"))
    if im3_manifest.get("record_count") != total_manifest_records:
        issues.append(Issue("public_data_validation", "im3-2026.02.09.manifest.json", "manifest record count does not equal its parts"))
    return issues


def main() -> int:
    validator = ContractValidator(SCHEMA_DIR)
    catalog = load_json(SCHEMA_DIR / "catalog.json")
    schema_paths = {
        entry["name"]: SCHEMA_DIR / entry["path"]
        for entry in catalog["schemas"]
        if entry["record_kind"] != "definitions"
    }

    failures: list[str] = []
    catalog_issues = validate_schema_catalog(validator)
    if catalog_issues:
        failures.extend(str(issue) for issue in catalog_issues)

    valid_count = 0
    for fixture_path in sorted(VALID_FIXTURE_DIR.glob("*.json")):
        valid_count += 1
        issues = validate_fixture(fixture_path, validator, schema_paths)
        if issues:
            failures.append(f"Valid fixture {fixture_path.name} failed:")
            failures.extend(f"  {issue}" for issue in issues)

    invalid_count = 0
    for fixture_path in sorted(INVALID_FIXTURE_DIR.glob("*.json")):
        invalid_count += 1
        fixture = load_json(fixture_path)
        expected = set(fixture.get("expected_error_codes", []))
        issues = validate_fixture(fixture_path, validator, schema_paths)
        actual = {issue.code for issue in issues}
        if not issues:
            failures.append(f"Invalid fixture {fixture_path.name} unexpectedly passed")
        elif not expected.issubset(actual):
            failures.append(
                f"Invalid fixture {fixture_path.name} expected {sorted(expected)}, got {sorted(actual)}"
            )

    if valid_count == 0 or invalid_count == 0:
        failures.append("At least one valid and one invalid fixture are required")

    project_issues = validate_project_config(validator, schema_paths)
    project_issues.extend(validate_public_data(validator, schema_paths))
    if project_issues:
        failures.append("Project configuration or public data failed:")
        failures.extend(f"  {issue}" for issue in project_issues)

    if failures:
        print("Data contract validation FAILED")
        print("\n".join(failures))
        return 1

    print(
        "Data contract validation passed: "
        f"{len(validator.schemas_by_path)} schemas, "
        f"{valid_count} valid fixture(s), {invalid_count} invalid fixture(s), "
        "configuration and public JSON."
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())

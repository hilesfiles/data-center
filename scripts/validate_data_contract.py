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
    "facility_containment_relationship": "relationship_id",
    "project": "project_id",
    "project_phase": "phase_id",
    "event": "event_id",
    "source": "source_id",
    "source_artifact": "artifact_id",
    "claim": "claim_id",
    "claim_resolution": "resolution_id",
    "review_decision": "review_decision_id",
    "entity_resolution_candidate": "resolution_candidate_id",
    "lifecycle_verification_candidate": "verification_candidate_id",
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
    for i, record in enumerate(fixture.get("facility_containment_relationship", [])):
        check_reference(record.get("contained_facility_id"), ids, f"$.facility_containment_relationship[{i}].contained_facility_id", issues)
        check_reference(record.get("container_facility_id"), ids, f"$.facility_containment_relationship[{i}].container_facility_id", issues)
        check_reference(record.get("review_decision_id"), ids, f"$.facility_containment_relationship[{i}].review_decision_id", issues)
        for j, claim_id in enumerate(record.get("source_claim_ids", [])):
            check_reference(claim_id, ids, f"$.facility_containment_relationship[{i}].source_claim_ids[{j}]", issues)
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
    for i, record in enumerate(fixture.get("review_decision", [])):
        for j, subject in enumerate(record.get("subject_refs", [])):
            check_reference(subject.get("entity_id"), ids, f"$.review_decision[{i}].subject_refs[{j}].entity_id", issues)
        for j, claim_id in enumerate(record.get("evidence_claim_ids", [])):
            check_reference(claim_id, ids, f"$.review_decision[{i}].evidence_claim_ids[{j}]", issues)
    for i, record in enumerate(fixture.get("entity_resolution_candidate", [])):
        for j, subject in enumerate(record.get("subject_refs", [])):
            check_reference(subject.get("entity_id"), ids, f"$.entity_resolution_candidate[{i}].subject_refs[{j}].entity_id", issues)
        for j, claim_id in enumerate(record.get("evidence_claim_ids", [])):
            check_reference(claim_id, ids, f"$.entity_resolution_candidate[{i}].evidence_claim_ids[{j}]", issues)
    for i, record in enumerate(fixture.get("lifecycle_verification_candidate", [])):
        check_reference(record.get("facility_id"), ids, f"$.lifecycle_verification_candidate[{i}].facility_id", issues)
        check_reference(record.get("campus_id"), ids, f"$.lifecycle_verification_candidate[{i}].campus_id", issues)
        check_reference(record.get("operator_id"), ids, f"$.lifecycle_verification_candidate[{i}].operator_id", issues)
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

    first_entry_policy_path = CONFIG_DIR / "first-entry-research-policy.json"
    first_entry_policy = load_json(first_entry_policy_path)
    for issue in validator.validate_record(first_entry_policy, schema_paths["first_entry_research_policy"]):
        issues.append(Issue("config_validation", f"{first_entry_policy_path.name}{issue.path[1:]}", issue.message))
    first_entry_weights = first_entry_policy.get("scoring", {}).get("weights", {})
    first_entry_regions = first_entry_policy.get("regional_frame", [])
    first_entry_states = [state for frame in first_entry_regions for state in frame.get("state_abbrs", [])]
    first_entry_tranche = first_entry_policy.get("initial_tranche", {})
    if (
        not math.isclose(sum(first_entry_weights.values()), 100.0, abs_tol=1e-9)
        or {frame.get("region") for frame in first_entry_regions} != {"Northeast", "Midwest", "South", "West"}
        or len(first_entry_states) != 51
        or len(first_entry_states) != len(set(first_entry_states))
        or first_entry_tranche.get("size") != 24
        or first_entry_tranche.get("per_region_quota") != 6
        or first_entry_tranche.get("max_per_state") != 2
        or first_entry_tranche.get("size") != first_entry_tranche.get("per_region_quota") * 4
    ):
        issues.append(Issue("config_validation", first_entry_policy_path.name, "first-entry research weights, regional frame, or tranche constraints are inconsistent"))

    first_entry_source_path = CONFIG_DIR / "first-entry-anchor-evidence-sources.json"
    first_entry_source_document = load_json(first_entry_source_path)
    first_entry_sources = first_entry_source_document.get("records", [])
    if first_entry_source_document.get("record_count") != len(first_entry_sources):
        issues.append(Issue("config_validation", first_entry_source_path.name, "record count is inconsistent"))
    for index, record in enumerate(first_entry_sources):
        for issue in validator.validate_record(record, schema_paths["source"]):
            issues.append(Issue("config_validation", f"{first_entry_source_path.name}.records[{index}]{issue.path[1:]}", issue.message))

    first_entry_adjudication_path = CONFIG_DIR / "first-entry-anchor-adjudications.json"
    first_entry_adjudication_document = load_json(first_entry_adjudication_path)
    first_entry_adjudications = first_entry_adjudication_document.get("records", [])
    if first_entry_adjudication_document.get("record_count") != len(first_entry_adjudications):
        issues.append(Issue("config_validation", first_entry_adjudication_path.name, "record count is inconsistent"))
    all_evidence_source_ids: set[str] = set()
    for evidence_path in CONFIG_DIR.glob("*evidence-sources.json"):
        all_evidence_source_ids.update(
            record.get("source_id", "") for record in load_json(evidence_path).get("records", [])
        )
    for index, record in enumerate(first_entry_adjudications):
        for issue in validator.validate_record(record, schema_paths["county_first_entry_adjudication"]):
            issues.append(Issue("config_validation", f"{first_entry_adjudication_path.name}.records[{index}]{issue.path[1:]}", issue.message))
        if not set(record.get("source_ids", [])).issubset(all_evidence_source_ids):
            issues.append(Issue("referential_integrity", f"{first_entry_adjudication_path.name}.records[{index}]", "adjudication references an unknown evidence source"))
    if (
        {record.get("county_fips") for record in first_entry_adjudications} != {"04013", "06085", "13121", "17031", "18105", "26125", "32003", "34017"}
        or {
            record.get("county_fips"): record.get("decision")
            for record in first_entry_adjudications
        } != {
            "04013": "reject_candidate_as_first_entry",
            "06085": "reject_candidate_as_first_entry",
            "13121": "reject_candidate_as_first_entry",
            "17031": "reject_candidate_as_first_entry",
            "18105": "reject_candidate_as_first_entry",
            "26125": "reject_candidate_as_first_entry",
            "32003": "reject_candidate_as_first_entry",
            "34017": "continue_research",
        }
        or any(record.get("inventory_completeness_status") != "not_established" for record in first_entry_adjudications)
    ):
        issues.append(Issue("config_validation", first_entry_adjudication_path.name, "anchor adjudication outcomes are inconsistent"))
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

    bea_acquisition_specs = {
        "2024-cagdp1.acquisition.json": "95b49283df20772ded04ea53e1142955b8ade5e7f93047c0a3dfaf403b166fe1",
        "2024-cainc1.acquisition.json": "e1465c8b0e7e75f541241fe2fa64364b784dd6d2223901f9d576c4c5d49480b5",
    }
    for filename, expected_sha in bea_acquisition_specs.items():
        bea_acquisition_path = DATA_DIR / "raw" / "bea-regional" / filename
        bea_acquisition = load_json(bea_acquisition_path)
        for issue in validator.validate_record(bea_acquisition, schema_paths["acquisition_manifest"]):
            issues.append(Issue("public_data_validation", f"{filename}{issue.path[1:]}", issue.message))
        if bea_acquisition.get("sha256") != expected_sha:
            issues.append(Issue("public_data_validation", filename, "pinned BEA release hash changed"))

    bea_bronze_path = DATA_DIR / "bronze" / "economic" / "bea-county-2024-source-rows.json"
    bea_bronze = load_json(bea_bronze_path)
    bea_source_rows = bea_bronze.get("records", [])
    bea_source_fips = [record.get("county_fips") for record in bea_source_rows]
    if (
        bea_bronze.get("record_count") != 3144
        or len(bea_source_rows) != 3144
        or set(bea_source_fips) != feature_fips
        or len(bea_source_fips) != len(set(bea_source_fips))
        or any(record.get("year") != 2024 for record in bea_source_rows)
    ):
        issues.append(Issue("public_data_validation", bea_bronze_path.name, "BEA bronze rows must cover every Census county exactly once for 2024"))

    bea_silver_path = DATA_DIR / "silver" / "economic" / "bea-county-2024.json"
    bea_silver = load_json(bea_silver_path)
    bea_collections = bea_silver.get("collections", {})
    bea_sources = bea_collections.get("source", [])
    bea_observations = bea_collections.get("observation", [])
    bea_source_ids = {record.get("source_id") for record in bea_sources}
    expected_bea_metric_codes = {
        "economic.gdp.real",
        "economic.personal_income.nominal",
        "economic.personal_income.per_capita.nominal",
        "demographic.population",
    }
    if (
        len(bea_sources) != 2
        or len(bea_observations) != 12576
        or bea_silver.get("record_count") != 12578
        or bea_source_ids != {"src_bea_cagdp1_2024", "src_bea_cainc1_2024"}
        or {record.get("metric_code") for record in bea_observations} != expected_bea_metric_codes
    ):
        issues.append(Issue("public_data_validation", bea_silver_path.name, "BEA source or observation counts and metric coverage are inconsistent"))
    for index, record in enumerate(bea_sources):
        for issue in validator.validate_record(record, schema_paths["source"]):
            issues.append(Issue("public_data_validation", f"{bea_silver_path.name}.source[{index}]{issue.path[1:]}", issue.message))
    bea_observation_keys: set[tuple[str, str]] = set()
    bea_observations_by_key: dict[tuple[str, str], dict[str, Any]] = {}
    for index, record in enumerate(bea_observations):
        for issue in validator.validate_record(record, schema_paths["observation"]):
            issues.append(Issue("public_data_validation", f"{bea_silver_path.name}.observation[{index}]{issue.path[1:]}", issue.message))
        subject = record.get("subject", {})
        key = (subject.get("subject_id", ""), record.get("metric_code", ""))
        bea_observation_keys.add(key)
        bea_observations_by_key[key] = record
        if (
            subject.get("subject_type") != "county"
            or subject.get("subject_id") not in feature_fips
            or not set(record.get("source_ids", [])).issubset(bea_source_ids)
            or record.get("period") != {"year": 2024, "precision": "year"}
        ):
            issues.append(Issue("referential_integrity", f"{bea_silver_path.name}.observation[{index}]", "BEA observation has an invalid county, source, or period"))
    if len(bea_observation_keys) != 12576:
        issues.append(Issue("public_data_validation", bea_silver_path.name, "BEA county-metric observation keys must be unique"))

    bea_public_path = PUBLIC_DATA_DIR / "counties" / "economic-baseline-2024.json"
    bea_public = load_json(bea_public_path)
    bea_public_fips = [record.get("county_fips") for record in bea_public]
    bea_status_counts = Counter(record.get("coverage_status") for record in bea_public)
    bea_public_fields = {
        "economic.gdp.real": "real_gdp_usd",
        "economic.personal_income.nominal": "personal_income_nominal_usd",
        "demographic.population": "population",
        "economic.personal_income.per_capita.nominal": "per_capita_personal_income_nominal_usd",
    }
    if (
        len(bea_public) != 3144
        or set(bea_public_fips) != feature_fips
        or len(bea_public_fips) != len(set(bea_public_fips))
        or bea_status_counts != Counter({"complete": 3091, "unavailable": 53})
    ):
        issues.append(Issue("public_data_validation", bea_public_path.name, "BEA public baseline county coverage or statuses are inconsistent"))
    for index, record in enumerate(bea_public):
        for issue in validator.validate_record(record, schema_paths["public_county_economic_baseline"]):
            issues.append(Issue("public_data_validation", f"{bea_public_path.name}[{index}]{issue.path[1:]}", issue.message))
        fips = record.get("county_fips", "")
        boundary = features_by_fips.get(fips, {})
        if record.get("county_name") != boundary.get("county_name") or record.get("state_abbr") != boundary.get("state_abbr"):
            issues.append(Issue("public_data_validation", f"{bea_public_path.name}[{index}]", "county identity does not match the Census boundary"))
        for metric_code, field in bea_public_fields.items():
            observation = bea_observations_by_key.get((fips, metric_code), {})
            expected_value = observation.get("value", {}).get("value")
            if record.get(field) != expected_value:
                issues.append(Issue("public_data_validation", f"{bea_public_path.name}[{index}].{field}", "public value does not match the governed observation"))

    bea_report_path = DATA_DIR / "silver" / "economic" / "bea-county-2024.processing-report.json"
    bea_report = load_json(bea_report_path)
    if (
        bea_report.get("county_count") != 3144
        or bea_report.get("observation_count") != 12576
        or bea_report.get("missing_value_count") != 212
        or bea_report.get("complete_county_count") != 3091
    ):
        issues.append(Issue("public_data_validation", bea_report_path.name, "BEA processing diagnostics are inconsistent"))

    bea_manifest_path = DATA_DIR / "silver" / "economic" / "bea-county-2024.manifest.json"
    bea_manifest = load_json(bea_manifest_path)
    for issue in validator.validate_record(bea_manifest, schema_paths["dataset_manifest"]):
        issues.append(Issue("public_data_validation", f"{bea_manifest_path.name}{issue.path[1:]}", issue.message))
    bea_manifest_total = 0
    for index, part in enumerate(bea_manifest.get("parts", [])):
        part_path = (ROOT / part.get("path", "")).resolve()
        if not part_path.is_relative_to(ROOT) or not part_path.is_file():
            issues.append(Issue("public_data_validation", f"{bea_manifest_path.name}.parts[{index}]", "part path is missing or outside the repository"))
            continue
        payload = part_path.read_bytes()
        bea_manifest_total += part.get("record_count", 0)
        if part.get("byte_size") != len(payload) or part.get("sha256") != hashlib.sha256(payload).hexdigest():
            issues.append(Issue("public_data_validation", f"{bea_manifest_path.name}.parts[{index}]", "byte size or SHA-256 does not match the artifact"))
    if bea_manifest.get("record_count") != 18867 or bea_manifest_total != 18867:
        issues.append(Issue("public_data_validation", bea_manifest_path.name, "BEA manifest record count is inconsistent"))

    qcew_acquisition_path = DATA_DIR / "raw" / "bls-qcew" / "2025-annual-by-area.acquisition.json"
    qcew_acquisition = load_json(qcew_acquisition_path)
    for issue in validator.validate_record(qcew_acquisition, schema_paths["acquisition_manifest"]):
        issues.append(Issue("public_data_validation", f"{qcew_acquisition_path.name}{issue.path[1:]}", issue.message))
    if qcew_acquisition.get("sha256") != "b2f6ed3b854af15bea207c1ef5ab8f1c22ee5b7abf79687505292beb44585921":
        issues.append(Issue("public_data_validation", qcew_acquisition_path.name, "pinned BLS QCEW release hash changed"))

    qcew_bronze_path = DATA_DIR / "bronze" / "economic" / "bls-qcew-county-2025-source-rows.json"
    qcew_bronze = load_json(qcew_bronze_path)
    qcew_source_rows = qcew_bronze.get("records", [])
    qcew_source_fips = [record.get("county_fips") for record in qcew_source_rows]
    if (
        qcew_bronze.get("record_count") != 3144
        or len(qcew_source_rows) != 3144
        or set(qcew_source_fips) != feature_fips
        or len(qcew_source_fips) != len(set(qcew_source_fips))
        or any(record.get("year") != 2025 for record in qcew_source_rows)
    ):
        issues.append(Issue("public_data_validation", qcew_bronze_path.name, "QCEW bronze rows must cover every Census county exactly once for 2025"))

    qcew_silver_path = DATA_DIR / "silver" / "economic" / "bls-qcew-county-2025.json"
    qcew_silver = load_json(qcew_silver_path)
    qcew_collections = qcew_silver.get("collections", {})
    qcew_sources = qcew_collections.get("source", [])
    qcew_observations = qcew_collections.get("observation", [])
    qcew_source_ids = {record.get("source_id") for record in qcew_sources}
    expected_qcew_metric_codes = {
        "economic.employment.total",
        "economic.establishments.total",
        "economic.wages.total.nominal",
        "economic.wages.average_weekly.nominal",
        "economic.employment.construction.private",
    }
    if (
        len(qcew_sources) != 1
        or len(qcew_observations) != 15720
        or qcew_silver.get("record_count") != 15721
        or qcew_source_ids != {"src_bls_qcew_annual_by_area_2025"}
        or {record.get("metric_code") for record in qcew_observations} != expected_qcew_metric_codes
    ):
        issues.append(Issue("public_data_validation", qcew_silver_path.name, "QCEW source or observation counts and metric coverage are inconsistent"))
    for index, record in enumerate(qcew_sources):
        for issue in validator.validate_record(record, schema_paths["source"]):
            issues.append(Issue("public_data_validation", f"{qcew_silver_path.name}.source[{index}]{issue.path[1:]}", issue.message))
    qcew_observation_keys: set[tuple[str, str]] = set()
    qcew_observations_by_key: dict[tuple[str, str], dict[str, Any]] = {}
    qcew_value_status_counts: Counter[str] = Counter()
    for index, record in enumerate(qcew_observations):
        for issue in validator.validate_record(record, schema_paths["observation"]):
            issues.append(Issue("public_data_validation", f"{qcew_silver_path.name}.observation[{index}]{issue.path[1:]}", issue.message))
        subject = record.get("subject", {})
        key = (subject.get("subject_id", ""), record.get("metric_code", ""))
        qcew_observation_keys.add(key)
        qcew_observations_by_key[key] = record
        qcew_value_status_counts[record.get("value_status", "")] += 1
        if (
            subject.get("subject_type") != "county"
            or subject.get("subject_id") not in feature_fips
            or not set(record.get("source_ids", [])).issubset(qcew_source_ids)
            or record.get("period") != {"year": 2025, "precision": "year"}
        ):
            issues.append(Issue("referential_integrity", f"{qcew_silver_path.name}.observation[{index}]", "QCEW observation has an invalid county, source, or period"))
    if len(qcew_observation_keys) != 15720:
        issues.append(Issue("public_data_validation", qcew_silver_path.name, "QCEW county-metric observation keys must be unique"))
    if qcew_value_status_counts != Counter({"observed": 14779, "suppressed": 922, "not_available": 19}):
        issues.append(Issue("public_data_validation", qcew_silver_path.name, "QCEW observed, suppressed, and unavailable counts are inconsistent"))

    qcew_public_path = PUBLIC_DATA_DIR / "counties" / "employment-wages-baseline-2025.json"
    qcew_public = load_json(qcew_public_path)
    qcew_public_fips = [record.get("county_fips") for record in qcew_public]
    qcew_status_counts = Counter(record.get("coverage_status") for record in qcew_public)
    qcew_public_fields = {
        "economic.employment.total": "annual_avg_covered_employment",
        "economic.establishments.total": "annual_avg_establishments",
        "economic.wages.total.nominal": "total_annual_wages_nominal_usd",
        "economic.wages.average_weekly.nominal": "annual_avg_weekly_wage_nominal_usd",
        "economic.employment.construction.private": "private_construction_annual_avg_employment",
    }
    if (
        len(qcew_public) != 3144
        or set(qcew_public_fips) != feature_fips
        or len(qcew_public_fips) != len(set(qcew_public_fips))
        or qcew_status_counts != Counter({"complete": 2207, "partial": 936, "unavailable": 1})
    ):
        issues.append(Issue("public_data_validation", qcew_public_path.name, "QCEW public baseline county coverage or statuses are inconsistent"))
    for index, record in enumerate(qcew_public):
        for issue in validator.validate_record(record, schema_paths["public_county_employment_wages_baseline"]):
            issues.append(Issue("public_data_validation", f"{qcew_public_path.name}[{index}]{issue.path[1:]}", issue.message))
        fips = record.get("county_fips", "")
        boundary = features_by_fips.get(fips, {})
        if record.get("county_name") != boundary.get("county_name") or record.get("state_abbr") != boundary.get("state_abbr"):
            issues.append(Issue("public_data_validation", f"{qcew_public_path.name}[{index}]", "county identity does not match the Census boundary"))
        populated = 0
        for metric_code, field in qcew_public_fields.items():
            observation = qcew_observations_by_key.get((fips, metric_code), {})
            expected_value = observation.get("value", {}).get("value")
            if record.get(field) != expected_value:
                issues.append(Issue("public_data_validation", f"{qcew_public_path.name}[{index}].{field}", "public value does not match the governed observation"))
            populated += int(record.get(field) is not None)
        expected_status = "complete" if populated == 5 else "unavailable" if populated == 0 else "partial"
        if record.get("coverage_status") != expected_status:
            issues.append(Issue("public_data_validation", f"{qcew_public_path.name}[{index}].coverage_status", "coverage status does not match populated QCEW values"))
    unavailable_qcew_fips = {record.get("county_fips") for record in qcew_public if record.get("coverage_status") == "unavailable"}
    if unavailable_qcew_fips != {"15005"}:
        issues.append(Issue("public_data_validation", qcew_public_path.name, "only Kalawao County should be unavailable in the pinned QCEW release"))

    qcew_report_path = DATA_DIR / "silver" / "economic" / "bls-qcew-county-2025.processing-report.json"
    qcew_report = load_json(qcew_report_path)
    if (
        qcew_report.get("county_count") != 3144
        or qcew_report.get("observation_count") != 15720
        or qcew_report.get("missing_value_count") != 941
        or qcew_report.get("suppressed_value_count") != 922
        or qcew_report.get("coverage_counts") != {"complete": 2207, "partial": 936, "unavailable": 1}
    ):
        issues.append(Issue("public_data_validation", qcew_report_path.name, "QCEW processing diagnostics are inconsistent"))

    qcew_manifest_path = DATA_DIR / "silver" / "economic" / "bls-qcew-county-2025.manifest.json"
    qcew_manifest = load_json(qcew_manifest_path)
    for issue in validator.validate_record(qcew_manifest, schema_paths["dataset_manifest"]):
        issues.append(Issue("public_data_validation", f"{qcew_manifest_path.name}{issue.path[1:]}", issue.message))
    qcew_manifest_total = 0
    for index, part in enumerate(qcew_manifest.get("parts", [])):
        part_path = (ROOT / part.get("path", "")).resolve()
        if not part_path.is_relative_to(ROOT) or not part_path.is_file():
            issues.append(Issue("public_data_validation", f"{qcew_manifest_path.name}.parts[{index}]", "part path is missing or outside the repository"))
            continue
        payload = part_path.read_bytes()
        qcew_manifest_total += part.get("record_count", 0)
        if part.get("byte_size") != len(payload) or part.get("sha256") != hashlib.sha256(payload).hexdigest():
            issues.append(Issue("public_data_validation", f"{qcew_manifest_path.name}.parts[{index}]", "byte size or SHA-256 does not match the artifact"))
    if qcew_manifest.get("record_count") != 22010 or qcew_manifest_total != 22010:
        issues.append(Issue("public_data_validation", qcew_manifest_path.name, "QCEW manifest record count is inconsistent"))

    panel_acquisition_specs = {
        "2021-total-all-industries.acquisition.json": "331d81786235e57217ef1498efc64d5e3abf39f1cbca1cf841ea10533920db51",
        "2022-total-all-industries.acquisition.json": "9a95487df1dd1ded3f2dc712b5d19747e2aacfc30102869cd3a0b985501e739a",
        "2023-total-all-industries.acquisition.json": "0115a20a201b821d29f731340976aad8fc8dac16cb6a0c13df0f7f52afe108b1",
        "2024-total-all-industries.acquisition.json": "e73da8f6b2b415180b1910351327faa51183589021357535fd880f8761e12a12",
    }
    for filename, expected_sha in panel_acquisition_specs.items():
        panel_acquisition_path = DATA_DIR / "raw" / "bls-qcew" / "history" / filename
        panel_acquisition = load_json(panel_acquisition_path)
        for issue in validator.validate_record(panel_acquisition, schema_paths["acquisition_manifest"]):
            issues.append(Issue("public_data_validation", f"{filename}{issue.path[1:]}", issue.message))
        if panel_acquisition.get("sha256") != expected_sha:
            issues.append(Issue("public_data_validation", filename, "pinned historical BLS QCEW slice hash changed"))

    for year in range(2001, 2021):
        filename = f"{year}-total-all-industries.acquisition.json"
        panel_acquisition_path = DATA_DIR / "raw" / "bls-qcew" / "history" / filename
        panel_acquisition = load_json(panel_acquisition_path)
        for issue in validator.validate_record(panel_acquisition, schema_paths["acquisition_manifest"]):
            issues.append(Issue("public_data_validation", f"{filename}{issue.path[1:]}", issue.message))
        if (
            panel_acquisition.get("source_id") != f"src_bls_qcew_total_{year}"
            or panel_acquisition.get("archive_byte_size", 0) < 1
            or panel_acquisition.get("member_byte_size", 0) < 1
            or not str(panel_acquisition.get("source_member", "")).endswith(".csv")
            or not re.fullmatch(r"[a-f0-9]{8}", str(panel_acquisition.get("member_crc32", "")))
            or not re.fullmatch(r"[a-f0-9]{64}", str(panel_acquisition.get("sha256", "")))
        ):
            issues.append(Issue("public_data_validation", filename, "historical BLS archive-member pin is incomplete"))

    panel_bronze_path = DATA_DIR / "bronze" / "economic" / "county-history-2001-2024-source-rows.json"
    panel_bronze = load_json(panel_bronze_path)
    panel_bronze_rows = panel_bronze.get("records", [])
    panel_bronze_keys = {
        (record.get("county_fips"), record.get("year")) for record in panel_bronze_rows
    }
    expected_panel_keys = {(fips, year) for fips in feature_fips for year in range(2001, 2025)}
    if (
        panel_bronze.get("record_count") != 75456
        or len(panel_bronze_rows) != 75456
        or panel_bronze_keys != expected_panel_keys
    ):
        issues.append(Issue("public_data_validation", panel_bronze_path.name, "historical panel bronze rows must cover every county-year from 2001 through 2024 exactly once"))

    panel_silver_path = DATA_DIR / "silver" / "panels" / "county-economic-core-2001-2024.sources.json"
    panel_sources = load_json(panel_silver_path).get("collections", {}).get("source", [])
    panel_observations: list[dict[str, Any]] = []
    panel_rows: list[dict[str, Any]] = []
    for start_year, end_year in ((2001, 2008), (2009, 2016), (2017, 2024)):
        partition_path = DATA_DIR / "silver" / "panels" / f"county-economic-core-{start_year}-{end_year}.json"
        partition = load_json(partition_path)
        collections = partition.get("collections", {})
        partition_observations = collections.get("observation", [])
        partition_rows = collections.get("panel_row", [])
        if (
            partition.get("partition") != {"start_year": start_year, "end_year": end_year}
            or partition.get("record_count") != 125760
            or len(partition_observations) != 100608
            or len(partition_rows) != 25152
        ):
            issues.append(Issue("public_data_validation", partition_path.name, "historical silver partition counts or bounds are inconsistent"))
        panel_observations.extend(partition_observations)
        panel_rows.extend(partition_rows)
    panel_source_ids = {record.get("source_id") for record in panel_sources}
    expected_panel_source_ids = {
        "src_bea_cagdp1_2024", "src_bea_cainc1_2024",
        *(f"src_bls_qcew_total_{year}" for year in range(2001, 2025)),
    }
    expected_panel_metric_codes = {
        "economic.gdp.real",
        "demographic.population",
        "economic.employment.total",
        "economic.wages.average_weekly.nominal",
    }
    if (
        len(panel_sources) != 26
        or len(panel_observations) != 301824
        or len(panel_rows) != 75456
        or panel_source_ids != expected_panel_source_ids
        or {record.get("metric_code") for record in panel_observations} != expected_panel_metric_codes
    ):
        issues.append(Issue("public_data_validation", panel_silver_path.name, "historical panel source, observation, or row counts are inconsistent"))
    for index, record in enumerate(panel_sources):
        for issue in validator.validate_record(record, schema_paths["source"]):
            issues.append(Issue("public_data_validation", f"{panel_silver_path.name}.source[{index}]{issue.path[1:]}", issue.message))
    panel_observation_ids: set[str] = set()
    panel_observations_by_key: dict[tuple[str, int, str], dict[str, Any]] = {}
    panel_value_status_counts: Counter[str] = Counter()
    for index, record in enumerate(panel_observations):
        if index % 1000 == 0 or index == len(panel_observations) - 1:
            for issue in validator.validate_record(record, schema_paths["observation"]):
                issues.append(Issue("public_data_validation", f"{panel_silver_path.name}.observation[{index}]{issue.path[1:]}", issue.message))
        subject = record.get("subject", {})
        period = record.get("period", {})
        observation_id = record.get("observation_id", "")
        key = (subject.get("subject_id", ""), period.get("year", 0), record.get("metric_code", ""))
        panel_observation_ids.add(observation_id)
        panel_observations_by_key[key] = record
        panel_value_status_counts[record.get("value_status", "")] += 1
        if (
            subject.get("subject_type") != "county"
            or subject.get("subject_id") not in feature_fips
            or period.get("year") not in range(2001, 2025)
            or period.get("precision") != "year"
            or not set(record.get("source_ids", [])).issubset(panel_source_ids)
        ):
            issues.append(Issue("referential_integrity", f"{panel_silver_path.name}.observation[{index}]", "historical observation has an invalid county, source, or period"))
    if len(panel_observation_ids) != 301824 or len(panel_observations_by_key) != 301824:
        issues.append(Issue("public_data_validation", panel_silver_path.name, "historical observation IDs and county-year-metric keys must be unique"))
    if panel_value_status_counts != Counter({"observed": 298024, "not_available": 3774, "suppressed": 26}):
        issues.append(Issue("public_data_validation", panel_silver_path.name, "historical observation value-status counts are inconsistent"))

    panel_row_ids: set[str] = set()
    panel_rows_by_key: dict[tuple[str, int], dict[str, Any]] = {}
    for index, record in enumerate(panel_rows):
        if index % 1000 == 0 or index == len(panel_rows) - 1:
            for issue in validator.validate_record(record, schema_paths["panel_row"]):
                issues.append(Issue("public_data_validation", f"{panel_silver_path.name}.panel_row[{index}]{issue.path[1:]}", issue.message))
        geography = record.get("geography", {})
        period = record.get("period", {})
        key = (geography.get("geography_id", ""), period.get("year", 0))
        panel_row_ids.add(record.get("panel_row_id", ""))
        panel_rows_by_key[key] = record
        references = record.get("observation_refs", [])
        if (
            geography.get("geography_type") != "county"
            or key not in expected_panel_keys
            or len(references) != 4
            or {reference.get("metric_code") for reference in references} != expected_panel_metric_codes
            or any(reference.get("observation_id") not in panel_observation_ids for reference in references)
        ):
            issues.append(Issue("referential_integrity", f"{panel_silver_path.name}.panel_row[{index}]", "historical panel row has invalid geography, metrics, or observation references"))
        available = sum(
            panel_observations_by_key.get((key[0], key[1], reference.get("metric_code", "")), {}).get("value") is not None
            for reference in references
        )
        completeness = record.get("completeness", {})
        if (
            completeness.get("required_metric_count") != 4
            or completeness.get("available_metric_count") != available
            or completeness.get("coverage") != available / 4
        ):
            issues.append(Issue("public_data_validation", f"{panel_silver_path.name}.panel_row[{index}].completeness", "panel completeness does not match referenced observations"))
    if len(panel_row_ids) != 75456 or set(panel_rows_by_key) != expected_panel_keys:
        issues.append(Issue("public_data_validation", panel_silver_path.name, "historical panel row IDs and county-year keys must be unique"))

    panel_public_path = PUBLIC_DATA_DIR / "panels" / "county-economic-history" / "index.json"
    panel_public_index = load_json(panel_public_path)
    panel_public: list[dict[str, Any]] = []
    if (
        panel_public_index.get("partition_count") != 51
        or panel_public_index.get("record_count") != 3144
        or len(panel_public_index.get("partitions", [])) != 51
    ):
        issues.append(Issue("public_data_validation", panel_public_path.name, "public historical partition index counts are inconsistent"))
    for partition in panel_public_index.get("partitions", []):
        partition_path = (PUBLIC_DATA_DIR / "panels" / partition.get("path", "")).resolve()
        if not partition_path.is_relative_to(PUBLIC_DATA_DIR) or not partition_path.is_file():
            issues.append(Issue("public_data_validation", panel_public_path.name, "public historical partition is missing or outside the public data directory"))
            continue
        payload = partition_path.read_bytes()
        records = json.loads(payload)
        if (
            partition.get("byte_size") != len(payload)
            or partition.get("sha256") != hashlib.sha256(payload).hexdigest()
            or partition.get("record_count") != len(records)
            or any(record.get("state_abbr") != partition.get("state_abbr") for record in records)
        ):
            issues.append(Issue("public_data_validation", partition_path.name, "public historical partition metadata or state scope is inconsistent"))
        panel_public.extend(records)
    panel_public_fips = [record.get("county_fips") for record in panel_public]
    panel_public_status_counts = Counter(record.get("coverage_status") for record in panel_public)
    panel_public_fields = {
        "economic.gdp.real": "real_gdp_usd",
        "demographic.population": "population",
        "economic.employment.total": "annual_avg_covered_employment",
        "economic.wages.average_weekly.nominal": "annual_avg_weekly_wage_nominal_usd",
    }
    if (
        len(panel_public) != 3144
        or set(panel_public_fips) != feature_fips
        or len(panel_public_fips) != len(set(panel_public_fips))
        or panel_public_status_counts != Counter({"complete": 3064, "partial": 79, "unavailable": 1})
    ):
        issues.append(Issue("public_data_validation", panel_public_path.name, "public historical panel county coverage or statuses are inconsistent"))
    for index, record in enumerate(panel_public):
        if index % 100 == 0 or index == len(panel_public) - 1:
            for issue in validator.validate_record(record, schema_paths["public_county_economic_history"]):
                issues.append(Issue("public_data_validation", f"{panel_public_path.name}[{index}]{issue.path[1:]}", issue.message))
        fips = record.get("county_fips", "")
        boundary = features_by_fips.get(fips, {})
        if record.get("county_name") != boundary.get("county_name") or record.get("state_abbr") != boundary.get("state_abbr"):
            issues.append(Issue("public_data_validation", f"{panel_public_path.name}[{index}]", "county identity does not match the Census boundary"))
        complete_year_count = 0
        populated_year_count = 0
        if [year.get("year") for year in record.get("years", [])] != list(range(2001, 2025)):
            issues.append(Issue("public_data_validation", f"{panel_public_path.name}[{index}].years", "public panel years must be ordered 2001 through 2024"))
        for public_year in record.get("years", []):
            year = public_year.get("year", 0)
            populated = 0
            for metric_code, field in panel_public_fields.items():
                observation = panel_observations_by_key.get((fips, year, metric_code), {})
                expected_value = observation.get("value", {}).get("value")
                if public_year.get(field) != expected_value:
                    issues.append(Issue("public_data_validation", f"{panel_public_path.name}[{index}].years[{year}].{field}", "public panel value does not match governed observation"))
                populated += int(public_year.get(field) is not None)
            expected_year_status = "complete" if populated == 4 else "unavailable" if populated == 0 else "partial"
            if public_year.get("coverage_status") != expected_year_status:
                issues.append(Issue("public_data_validation", f"{panel_public_path.name}[{index}].years[{year}].coverage_status", "year coverage status does not match populated values"))
            complete_year_count += int(expected_year_status == "complete")
            populated_year_count += int(expected_year_status != "unavailable")
        expected_county_status = "complete" if complete_year_count == 24 else "unavailable" if populated_year_count == 0 else "partial"
        if record.get("complete_year_count") != complete_year_count or record.get("coverage_status") != expected_county_status:
            issues.append(Issue("public_data_validation", f"{panel_public_path.name}[{index}]", "county historical coverage does not match year records"))

    panel_report_path = DATA_DIR / "silver" / "panels" / "county-economic-core-2001-2024.processing-report.json"
    panel_report = load_json(panel_report_path)
    if (
        panel_report.get("county_count") != 3144
        or panel_report.get("year_count") != 24
        or panel_report.get("panel_row_count") != 75456
        or panel_report.get("observation_count") != 301824
        or panel_report.get("value_status_counts") != {"observed": 298024, "not_available": 3774, "suppressed": 26}
        or panel_report.get("public_coverage_counts") != {"complete": 3064, "partial": 79, "unavailable": 1}
        or panel_report.get("public_partition_count") != 51
        or panel_report.get("model_readiness", {}).get("status") != "missing_treatment_dates"
        or panel_report.get("model_readiness", {}).get("history_span_can_satisfy_period_requirements") is not True
        or panel_report.get("model_readiness", {}).get("treatment_dates_available") is not False
    ):
        issues.append(Issue("public_data_validation", panel_report_path.name, "historical panel processing diagnostics are inconsistent"))

    panel_manifest_path = DATA_DIR / "silver" / "panels" / "county-economic-core-2001-2024.manifest.json"
    panel_manifest = load_json(panel_manifest_path)
    for issue in validator.validate_record(panel_manifest, schema_paths["dataset_manifest"]):
        issues.append(Issue("public_data_validation", f"{panel_manifest_path.name}{issue.path[1:]}", issue.message))
    panel_manifest_total = 0
    for index, part in enumerate(panel_manifest.get("parts", [])):
        part_path = (ROOT / part.get("path", "")).resolve()
        if not part_path.is_relative_to(ROOT) or not part_path.is_file():
            issues.append(Issue("public_data_validation", f"{panel_manifest_path.name}.parts[{index}]", "part path is missing or outside the repository"))
            continue
        payload = part_path.read_bytes()
        panel_manifest_total += part.get("record_count", 0)
        if part.get("byte_size") != len(payload) or part.get("sha256") != hashlib.sha256(payload).hexdigest():
            issues.append(Issue("public_data_validation", f"{panel_manifest_path.name}.parts[{index}]", "byte size or SHA-256 does not match the artifact"))
    if panel_manifest.get("record_count") != 455908 or panel_manifest_total != 455908:
        issues.append(Issue("public_data_validation", panel_manifest_path.name, "historical panel manifest record count is inconsistent"))

    treatment_path = DATA_DIR / "silver" / "treatments" / "county-first-entry-v1.json"
    treatment_registry = load_json(treatment_path)
    treatment_collections = treatment_registry.get("collections", {})
    treatment_events = treatment_collections.get("event", [])
    treatment_evaluations = treatment_collections.get("treatment_event_evaluation", [])
    treatment_assessments = treatment_collections.get("county_treatment_assessment", [])
    if (
        treatment_registry.get("record_count") != 3160
        or len(treatment_events) != 8
        or len(treatment_evaluations) != 8
        or len(treatment_assessments) != 3144
    ):
        issues.append(Issue("public_data_validation", treatment_path.name, "county first-entry registry collection counts are inconsistent"))
    for index, record in enumerate(treatment_events):
        for issue in validator.validate_record(record, schema_paths["event"]):
            issues.append(Issue("public_data_validation", f"{treatment_path.name}.event[{index}]{issue.path[1:]}", issue.message))
    for index, record in enumerate(treatment_evaluations):
        for issue in validator.validate_record(record, schema_paths["treatment_event_evaluation"]):
            issues.append(Issue("public_data_validation", f"{treatment_path.name}.treatment_event_evaluation[{index}]{issue.path[1:]}", issue.message))
    for index, record in enumerate(treatment_assessments):
        for issue in validator.validate_record(record, schema_paths["county_treatment_assessment"]):
            issues.append(Issue("public_data_validation", f"{treatment_path.name}.county_treatment_assessment[{index}]{issue.path[1:]}", issue.message))

    treatment_evaluation_ids = [record.get("treatment_event_evaluation_id") for record in treatment_evaluations]
    treatment_event_ids = [record.get("event_id") for record in treatment_events]
    treatment_assessment_fips = [record.get("county_fips") for record in treatment_assessments]
    assessment_status_counts = Counter(record.get("assessment_status") for record in treatment_assessments)
    if (
        len(treatment_evaluation_ids) != len(set(treatment_evaluation_ids))
        or len(treatment_event_ids) != len(set(treatment_event_ids))
        or set(record.get("event_id") for record in treatment_evaluations) != set(treatment_event_ids)
        or len(treatment_assessment_fips) != len(set(treatment_assessment_fips))
        or set(treatment_assessment_fips) != feature_fips
        or assessment_status_counts != Counter({"candidate_events_not_first_entry": 8, "no_reviewed_dated_operational_event": 3136})
        or any(record.get("first_entry_verified") is not False for record in treatment_assessments)
        or any("eligible_treatment_period" in record or "eligible_cohort_year" in record for record in treatment_assessments)
    ):
        issues.append(Issue("public_data_validation", treatment_path.name, "county treatment identity, status, or eligibility invariants are inconsistent"))
    for index, record in enumerate(treatment_assessments):
        boundary = features_by_fips.get(record.get("county_fips", ""), {})
        if record.get("county_name") != boundary.get("county_name") or record.get("state_abbr") != boundary.get("state_abbr"):
            issues.append(Issue("public_data_validation", f"{treatment_path.name}.county_treatment_assessment[{index}]", "county identity does not match the Census boundary"))
        if not set(record.get("candidate_event_evaluation_ids", [])).issubset(set(treatment_evaluation_ids)):
            issues.append(Issue("referential_integrity", f"{treatment_path.name}.county_treatment_assessment[{index}]", "assessment references an unknown treatment event evaluation"))
    adjudicated_assessments = [record for record in treatment_assessments if record.get("first_entry_adjudication_ids")]
    if (
        {record.get("county_fips") for record in adjudicated_assessments} != {"04013", "06085", "13121", "17031", "18105", "26125", "32003", "34017"}
        or {
            record.get("county_fips"): record.get("candidate_rejection_count")
            for record in adjudicated_assessments
        } != {"04013": 1, "06085": 1, "13121": 1, "17031": 1, "18105": 1, "26125": 1, "32003": 1, "34017": 0}
        or any(record.get("inventory_completeness_status") != "not_established" for record in adjudicated_assessments)
    ):
        issues.append(Issue("public_data_validation", treatment_path.name, "county first-entry adjudication summaries are inconsistent"))

    evaluations_by_fips = {record.get("county_fips"): record for record in treatment_evaluations}
    expected_treatment_evaluations = {
        "06085": {
            "facility_id": "fac_im3_building_00888253616",
            "source_id": "src_ntt_sv1_opening_20210413",
            "when": {"date": "2021-04-13", "precision": "day"},
            "data_quality_score": 93.1,
            "available_pre_periods": 20,
            "available_post_periods": 3,
            "evidence_threshold_status": "passed",
            "period_requirement_status": "passed",
            "exclusion_reasons": ["candidate_event_not_county_first_entry"],
        },
        "04013": {
            "facility_id": "fac_im3_building_00300974499",
            "source_id": "src_apple_environment_report_2019",
            "when": {"date": "2017-03-01", "precision": "month"},
            "data_quality_score": 85.74,
            "available_pre_periods": 16,
            "available_post_periods": 7,
            "evidence_threshold_status": "passed",
            "period_requirement_status": "passed",
            "exclusion_reasons": ["candidate_event_not_county_first_entry"],
        },
        "13121": {
            "facility_id": "fac_im3_building_00269847438",
            "source_id": "src_dck_qts_atlanta_acquisition_20061003",
            "when": {"date": "2006-10-03", "precision": "day"},
            "data_quality_score": 84.6,
            "available_pre_periods": 5,
            "available_post_periods": 18,
            "evidence_threshold_status": "failed",
            "period_requirement_status": "failed",
            "exclusion_reasons": [
                "evidence_threshold_not_met",
                "panel_period_requirement_not_met",
                "candidate_event_not_county_first_entry",
            ],
        },
        "17031": {
            "facility_id": "fac_im3_building_00149379943",
            "source_id": "src_fibernet_2002_10k_600_federal_20030328",
            "when": {"date": "2003-03-28", "precision": "day"},
            "data_quality_score": 95.06,
            "available_pre_periods": 2,
            "available_post_periods": 21,
            "evidence_threshold_status": "passed",
            "period_requirement_status": "failed",
            "exclusion_reasons": [
                "panel_period_requirement_not_met",
                "candidate_event_not_county_first_entry",
            ],
        },
        "34017": {
            "facility_id": "fac_im3_building_00095782052",
            "source_id": "src_sungard_2001_10k_north_bergen_20020327",
            "when": {"date": "2002-03-27", "precision": "day"},
            "data_quality_score": 95.06,
            "available_pre_periods": 1,
            "available_post_periods": 22,
            "evidence_threshold_status": "passed",
            "period_requirement_status": "failed",
            "exclusion_reasons": [
                "panel_period_requirement_not_met",
                "county_first_entry_not_verified",
            ],
        },
        "32003": {
            "facility_id": "fac_im3_building_00172739953",
            "source_id": "src_switch_supernap_debut_2009",
            "when": {"year": 2009, "precision": "year"},
            "data_quality_score": 72.96,
            "available_pre_periods": 8,
            "available_post_periods": 15,
            "evidence_threshold_status": "failed",
            "period_requirement_status": "passed",
            "exclusion_reasons": [
                "evidence_threshold_not_met",
                "candidate_event_not_county_first_entry",
            ],
        },
        "18105": {
            "facility_id": "fac_im3_building_00203432103",
            "source_id": "src_iu_data_center_dedication_20091105",
            "when": {"date": "2009-11-05", "precision": "day"},
            "data_quality_score": 96.04,
            "available_pre_periods": 8,
            "available_post_periods": 15,
            "evidence_threshold_status": "passed",
            "period_requirement_status": "passed",
            "exclusion_reasons": ["candidate_event_not_county_first_entry"],
        },
        "26125": {
            "facility_id": "fac_im3_building_00377585075",
            "source_id": "src_edgeconnex_det01_fibertech_20150311",
            "when": {"date": "2015-03-11", "precision": "day"},
            "data_quality_score": 96.04,
            "available_pre_periods": 14,
            "available_post_periods": 9,
            "evidence_threshold_status": "passed",
            "period_requirement_status": "passed",
            "exclusion_reasons": ["candidate_event_not_county_first_entry"],
        },
    }
    if set(evaluations_by_fips) != set(expected_treatment_evaluations):
        issues.append(Issue("public_data_validation", treatment_path.name, "reviewed treatment candidate counties changed"))
    for county_fips, expected in expected_treatment_evaluations.items():
        actual = evaluations_by_fips.get(county_fips, {})
        if (
            any(actual.get(key) != value for key, value in expected.items())
            or actual.get("evidence_threshold_status") != expected["evidence_threshold_status"]
            or actual.get("period_requirement_status") != expected["period_requirement_status"]
            or actual.get("first_entry_verification_status") != (
                "not_verified" if county_fips == "34017" else "rejected_as_first_entry"
            )
            or actual.get("eligibility_status") != "excluded"
            or actual.get("exclusion_reasons") != expected["exclusion_reasons"]
            or actual.get("county_first_entry_adjudication_id") is None
        ):
            issues.append(Issue("public_data_validation", f"{treatment_path.name}.treatment_event_evaluation[{county_fips}]", "candidate evidence score, history window, or exclusion state changed"))

    treatment_public_path = PUBLIC_DATA_DIR / "treatments" / "county-first-entry" / "index.json"
    treatment_public_index = load_json(treatment_public_path)
    treatment_public_assessments: list[dict[str, Any]] = []
    if (
        treatment_public_index.get("partition_count") != 51
        or treatment_public_index.get("record_count") != 3144
        or treatment_public_index.get("adjudication_count") != 8
        or len(treatment_public_index.get("partitions", [])) != 51
    ):
        issues.append(Issue("public_data_validation", treatment_public_path.name, "county treatment partition index counts are inconsistent"))
    for partition in treatment_public_index.get("partitions", []):
        partition_path = (PUBLIC_DATA_DIR / "treatments" / partition.get("path", "")).resolve()
        if not partition_path.is_relative_to(PUBLIC_DATA_DIR) or not partition_path.is_file():
            issues.append(Issue("public_data_validation", treatment_public_path.name, "county treatment partition is missing or outside the public data directory"))
            continue
        payload = partition_path.read_bytes()
        records = json.loads(payload)
        if (
            partition.get("byte_size") != len(payload)
            or partition.get("sha256") != hashlib.sha256(payload).hexdigest()
            or partition.get("record_count") != len(records)
            or any(record.get("state_abbr") != partition.get("state_abbr") for record in records)
        ):
            issues.append(Issue("public_data_validation", partition_path.name, "county treatment partition metadata or state scope is inconsistent"))
        treatment_public_assessments.extend(records)
    treatment_public_by_fips = {
        record.get("county_fips"): record for record in treatment_public_assessments
    }
    treatment_governed_by_fips = {
        record.get("county_fips"): record for record in treatment_assessments
    }
    if (
        len(treatment_public_assessments) != len(treatment_public_by_fips)
        or treatment_public_by_fips != treatment_governed_by_fips
    ):
        issues.append(Issue("public_data_validation", treatment_public_path.name, "public county treatment partitions must match the governed assessment collection"))
    treatment_candidate_public_path = PUBLIC_DATA_DIR / "treatments" / "county-first-entry" / "candidate-events.json"
    if load_json(treatment_candidate_public_path) != treatment_evaluations:
        issues.append(Issue("public_data_validation", treatment_candidate_public_path.name, "public treatment candidates must match the governed evaluation collection"))
    governed_first_entry_adjudications = load_json(
        CONFIG_DIR / "first-entry-anchor-adjudications.json"
    ).get("records", [])
    public_first_entry_adjudications = load_json(
        PUBLIC_DATA_DIR / "treatments" / "county-first-entry" / "adjudications.json"
    )
    if public_first_entry_adjudications != governed_first_entry_adjudications:
        issues.append(Issue("public_data_validation", "county-first-entry/adjudications.json", "public adjudications must match governed records"))
    public_first_entry_sources = load_json(
        PUBLIC_DATA_DIR / "treatments" / "county-first-entry" / "evidence-sources.json"
    )
    expected_first_entry_source_ids = {
        source_id for record in governed_first_entry_adjudications for source_id in record.get("source_ids", [])
    }
    if {record.get("source_id") for record in public_first_entry_sources} != expected_first_entry_source_ids:
        issues.append(Issue("public_data_validation", "county-first-entry/evidence-sources.json", "public evidence-source coverage is inconsistent"))

    treatment_report_path = DATA_DIR / "silver" / "treatments" / "county-first-entry-v1.processing-report.json"
    treatment_report = load_json(treatment_report_path)
    if (
        treatment_report.get("county_count") != 3144
        or treatment_report.get("model_specification_id") != "msp_employment_entry_v1"
        or treatment_report.get("panel_years") != {"start": 2001, "end": 2024}
        or treatment_report.get("period_requirements") != {"minimum_pre_periods": 7, "minimum_post_periods": 3}
        or treatment_report.get("reviewed_dated_operational_event_count") != 8
        or treatment_report.get("evidence_threshold_pass_count") != 6
        or treatment_report.get("period_requirement_pass_count") != 5
        or treatment_report.get("first_entry_verified_event_count") != 0
        or treatment_report.get("candidate_rejected_as_first_entry_count") != 7
        or treatment_report.get("eligible_treatment_event_count") != 0
        or treatment_report.get("eligible_county_count") != 0
        or treatment_report.get("assessment_status_counts") != {"candidate_events_not_first_entry": 8, "no_reviewed_dated_operational_event": 3136}
        or treatment_report.get("model_readiness", {}).get("status") != "insufficient_eligible_treatments"
        or treatment_report.get("model_readiness", {}).get("governed_treatment_registry_available") is not True
        or treatment_report.get("model_readiness", {}).get("eligible_treatment_dates_available") is not False
        or treatment_report.get("model_readiness", {}).get("model_run_authorized") is not False
    ):
        issues.append(Issue("public_data_validation", treatment_report_path.name, "county first-entry processing diagnostics are inconsistent"))

    treatment_manifest_path = DATA_DIR / "silver" / "treatments" / "county-first-entry-v1.manifest.json"
    treatment_manifest = load_json(treatment_manifest_path)
    for issue in validator.validate_record(treatment_manifest, schema_paths["dataset_manifest"]):
        issues.append(Issue("public_data_validation", f"{treatment_manifest_path.name}{issue.path[1:]}", issue.message))
    treatment_manifest_total = 0
    for index, part in enumerate(treatment_manifest.get("parts", [])):
        part_path = (ROOT / part.get("path", "")).resolve()
        if not part_path.is_relative_to(ROOT) or not part_path.is_file():
            issues.append(Issue("public_data_validation", f"{treatment_manifest_path.name}.parts[{index}]", "part path is missing or outside the repository"))
            continue
        payload = part_path.read_bytes()
        treatment_manifest_total += part.get("record_count", 0)
        if part.get("byte_size") != len(payload) or part.get("sha256") != hashlib.sha256(payload).hexdigest():
            issues.append(Issue("public_data_validation", f"{treatment_manifest_path.name}.parts[{index}]", "byte size or SHA-256 does not match the artifact"))
    if treatment_manifest.get("record_count") != 6350 or treatment_manifest_total != 6350:
        issues.append(Issue("public_data_validation", treatment_manifest_path.name, "county first-entry manifest record count is inconsistent"))

    research_path = DATA_DIR / "silver" / "treatments" / "county-first-entry-research-priority-v1.json"
    research_registry = load_json(research_path)
    research_candidates = research_registry.get("collections", {}).get("first_entry_research_candidate", [])
    if research_registry.get("record_count") != 217 or len(research_candidates) != 217:
        issues.append(Issue("public_data_validation", research_path.name, "first-entry research registry count is inconsistent"))
    for index, record in enumerate(research_candidates):
        for issue in validator.validate_record(record, schema_paths["first_entry_research_candidate"]):
            issues.append(Issue("public_data_validation", f"{research_path.name}.first_entry_research_candidate[{index}]{issue.path[1:]}", issue.message))

    research_ids = [record.get("first_entry_research_candidate_id") for record in research_candidates]
    research_fips = [record.get("county_fips") for record in research_candidates]
    research_queue_counts = Counter(record.get("queue_status") for record in research_candidates)
    research_tier_counts = Counter(record.get("priority_tier") for record in research_candidates)
    research_region_counts = Counter(record.get("census_region") for record in research_candidates)
    research_initial = [record for record in research_candidates if record.get("queue_status") == "initial_tranche"]
    research_initial_region_counts = Counter(record.get("census_region") for record in research_initial)
    research_initial_state_counts = Counter(record.get("state_abbr") for record in research_initial)
    if (
        len(research_ids) != len(set(research_ids))
        or len(research_fips) != len(set(research_fips))
        or [record.get("national_rank") for record in research_candidates] != list(range(1, 218))
        or research_queue_counts != Counter({"national_backlog": 193, "initial_tranche": 24})
        or research_tier_counts != Counter({"first_entry_deferred": 124, "first_entry_standard": 85, "first_entry_high": 8})
        or research_region_counts != Counter({"South": 67, "Midwest": 63, "West": 58, "Northeast": 29})
        or research_initial_region_counts != Counter({"Northeast": 6, "Midwest": 6, "South": 6, "West": 6})
        or max(research_initial_state_counts.values(), default=0) > 2
        or sum(record.get("reviewed_operational_facility_count", 0) for record in research_candidates) != 44
        or sum(record.get("dated_operational_candidate_count", 0) for record in research_candidates) != 8
    ):
        issues.append(Issue("public_data_validation", research_path.name, "first-entry research identity, rank, tier, or balanced-tranche invariants are inconsistent"))

    expected_research_initial_fips = [
        "13121", "34017", "32003", "18105", "26125", "17031", "04013", "06085",
        "12001", "23005", "25017", "12057", "42091", "37119", "13067", "33015",
        "36087", "53061", "51107", "35001", "31153", "06037", "17043", "18089",
    ]
    if (
        [record.get("county_fips") for record in research_initial] != expected_research_initial_fips
        or [record.get("initial_tranche_rank") for record in research_initial] != list(range(1, 25))
    ):
        issues.append(Issue("public_data_validation", research_path.name, "first-entry initial tranche membership or rank changed"))

    research_lifecycle_coverage = load_json(
        PUBLIC_DATA_DIR / "counties" / "lifecycle-national-tranche-6-coverage.json"
    )
    research_lifecycle_by_fips = {
        record.get("county_fips"): record for record in research_lifecycle_coverage
    }
    research_history_by_fips = {record.get("county_fips"): record for record in panel_public}
    research_source_coverage = load_json(PUBLIC_DATA_DIR / "counties" / "facility-source-coverage.json")
    research_source_by_fips = {
        record.get("county_fips"): record for record in research_source_coverage
    }
    expected_research_fips = {
        county_fips for county_fips, coverage in research_lifecycle_by_fips.items()
        if coverage.get("active_canonical_facility_count", 0) > 0
        and research_history_by_fips.get(county_fips, {}).get("complete_year_count") == 24
        and next(
            assessment for assessment in treatment_assessments
            if assessment.get("county_fips") == county_fips
        ).get("assessment_status") != "eligible"
    }
    if set(research_fips) != expected_research_fips:
        issues.append(Issue("public_data_validation", research_path.name, "first-entry research eligibility does not match facility, panel, and treatment inputs"))

    research_max_facilities = max(
        (record.get("active_canonical_facility_count", 0) for record in research_candidates),
        default=1,
    )
    for index, record in enumerate(research_candidates):
        county_fips = record.get("county_fips", "")
        boundary = features_by_fips.get(county_fips, {})
        source = research_source_by_fips.get(county_fips, {})
        facility_count = record.get("active_canonical_facility_count", 0)
        expected_components = {
            "dated_event_anchor": 100.0 if record.get("dated_operational_candidate_count", 0) else 0.0,
            "reviewed_operational_evidence": min(100.0, 50.0 * record.get("reviewed_operational_facility_count", 0)),
            "inventory_audit_feasibility": round(
                100.0 * (1.0 - math.log(facility_count) / math.log(research_max_facilities)), 2
            ),
            "panel_completeness": round(record.get("panel_complete_year_count", 0) / 24.0 * 100.0, 2),
            "source_identity_coverage": round(
                record.get("named_source_record_count", 0) / record.get("source_record_count", 1) * 100.0, 2
            ),
        }
        weights = {
            "dated_event_anchor": 30,
            "reviewed_operational_evidence": 25,
            "inventory_audit_feasibility": 20,
            "panel_completeness": 15,
            "source_identity_coverage": 10,
        }
        expected_score = round(sum(expected_components[name] * weight / 100.0 for name, weight in weights.items()), 2)
        if (
            record.get("county_name") != boundary.get("county_name")
            or record.get("state_abbr") != boundary.get("state_abbr")
            or facility_count != research_lifecycle_by_fips.get(county_fips, {}).get("active_canonical_facility_count")
            or record.get("panel_complete_year_count") != 24
            or record.get("source_record_count") != source.get("source_record_count")
            or record.get("named_source_record_count") != source.get("named_record_count")
            or record.get("score_components") != expected_components
            or record.get("priority_score") != expected_score
            or record.get("research_status") != ("evidence_collected" if county_fips in {"04013", "06085", "13121", "17031", "18105", "26125", "32003", "34017"} else "queued")
            or record.get("research_objective") != "verify_county_first_operational_entry"
        ):
            issues.append(Issue("public_data_validation", f"{research_path.name}.first_entry_research_candidate[{index}]", "first-entry research identity, input metrics, or score is inconsistent"))

    research_public_index_path = PUBLIC_DATA_DIR / "treatments" / "county-first-entry-research" / "index.json"
    research_public_index = load_json(research_public_index_path)
    research_public_candidates: list[dict[str, Any]] = []
    if (
        research_public_index.get("partition_count") != 51
        or research_public_index.get("record_count") != 217
        or research_public_index.get("initial_tranche_count") != 24
        or len(research_public_index.get("partitions", [])) != 51
    ):
        issues.append(Issue("public_data_validation", research_public_index_path.name, "first-entry research public index counts are inconsistent"))
    for partition in research_public_index.get("partitions", []):
        partition_path = (PUBLIC_DATA_DIR / "treatments" / partition.get("path", "")).resolve()
        if not partition_path.is_relative_to(PUBLIC_DATA_DIR) or not partition_path.is_file():
            issues.append(Issue("public_data_validation", research_public_index_path.name, "first-entry research partition is missing or outside public data"))
            continue
        payload = partition_path.read_bytes()
        records = json.loads(payload)
        if (
            partition.get("byte_size") != len(payload)
            or partition.get("sha256") != hashlib.sha256(payload).hexdigest()
            or partition.get("record_count") != len(records)
            or any(record.get("state_abbr") != partition.get("state_abbr") for record in records)
        ):
            issues.append(Issue("public_data_validation", partition_path.name, "first-entry research partition metadata or state scope is inconsistent"))
        research_public_candidates.extend(records)
    if {
        record.get("county_fips"): record for record in research_public_candidates
    } != {
        record.get("county_fips"): record for record in research_candidates
    }:
        issues.append(Issue("public_data_validation", research_public_index_path.name, "public first-entry research partitions must match the governed registry"))
    research_public_tranche_path = PUBLIC_DATA_DIR / "treatments" / "county-first-entry-research" / "initial-tranche.json"
    if load_json(research_public_tranche_path) != research_initial:
        issues.append(Issue("public_data_validation", research_public_tranche_path.name, "public first-entry tranche must match governed initial-tranche records"))

    research_report_path = DATA_DIR / "silver" / "treatments" / "county-first-entry-research-priority-v1.processing-report.json"
    research_report = load_json(research_report_path)
    if (
        research_report.get("county_count") != 3144
        or research_report.get("active_facility_county_count") != 226
        or research_report.get("eligible_research_candidate_count") != 217
        or research_report.get("initial_tranche_count") != 24
        or research_report.get("national_backlog_count") != 193
        or research_report.get("exclusion_counts") != {"no_active_canonical_facility": 2918, "incomplete_24_year_panel": 9, "already_eligible_treatment": 0}
        or research_report.get("priority_tier_counts") != {"first_entry_deferred": 124, "first_entry_high": 8, "first_entry_standard": 85}
        or research_report.get("initial_tranche_region_counts") != {"Midwest": 6, "Northeast": 6, "South": 6, "West": 6}
        or research_report.get("adjudication_status_counts") != {"candidate_rejected_first_entry": 7, "not_adjudicated": 209, "unresolved": 1}
        or research_report.get("treatment_effect") != {"treatment_dates_assigned": 0, "eligible_treatment_count_changed": False, "model_run_authorized": False}
    ):
        issues.append(Issue("public_data_validation", research_report_path.name, "first-entry research processing diagnostics are inconsistent"))

    research_manifest_path = DATA_DIR / "silver" / "treatments" / "county-first-entry-research-priority-v1.manifest.json"
    research_manifest = load_json(research_manifest_path)
    for issue in validator.validate_record(research_manifest, schema_paths["dataset_manifest"]):
        issues.append(Issue("public_data_validation", f"{research_manifest_path.name}{issue.path[1:]}", issue.message))
    research_manifest_total = 0
    for index, part in enumerate(research_manifest.get("parts", [])):
        part_path = (ROOT / part.get("path", "")).resolve()
        if not part_path.is_relative_to(ROOT) or not part_path.is_file():
            issues.append(Issue("public_data_validation", f"{research_manifest_path.name}.parts[{index}]", "part path is missing or outside the repository"))
            continue
        payload = part_path.read_bytes()
        research_manifest_total += part.get("record_count", 0)
        if part.get("byte_size") != len(payload) or part.get("sha256") != hashlib.sha256(payload).hexdigest():
            issues.append(Issue("public_data_validation", f"{research_manifest_path.name}.parts[{index}]", "byte size or SHA-256 does not match the artifact"))
    if research_manifest.get("record_count") != 460 or research_manifest_total != 460:
        issues.append(Issue("public_data_validation", research_manifest_path.name, "first-entry research manifest record count is inconsistent"))

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

    resolution_path = DATA_DIR / "silver" / "infrastructure" / "im3-2026.02.09-entity-resolution.json"
    resolution = load_json(resolution_path)
    resolution_collections = resolution.get("collections", {})
    expected_resolution_counts = {
        "campus": 132,
        "facility": 1340,
        "operator": 161,
        "operator_relationship": 953,
        "review_decision": 414,
        "entity_resolution_candidate": 16,
    }
    actual_resolution_counts = {
        name: len(resolution_collections.get(name, []))
        for name in expected_resolution_counts
    }
    if (
        actual_resolution_counts != expected_resolution_counts
        or resolution.get("record_count") != sum(expected_resolution_counts.values())
    ):
        issues.append(Issue("public_data_validation", resolution_path.name, "entity-resolution collection counts are inconsistent"))
    for collection, expected_count in expected_resolution_counts.items():
        if expected_count == 0:
            continue
        for index, record in enumerate(resolution_collections.get(collection, [])):
            for issue in validator.validate_record(record, schema_paths[collection]):
                issues.append(Issue("public_data_validation", f"{resolution_path.name}.{collection}[{index}]{issue.path[1:]}", issue.message))

    resolution_reference_fixture = {
        **resolution_collections,
        "claim": collections.get("claim", []),
        "source": collections.get("source", []),
        "source_artifact": collections.get("source_artifact", []),
        "geography_reference": geography_records,
        "metric_definition": load_json(CONFIG_DIR / "metric-registry.json")["metrics"],
    }
    for issue in validate_references(resolution_reference_fixture):
        issues.append(Issue("public_data_validation", f"{resolution_path.name}:{issue.path}", issue.message))

    resolution_report_path = DATA_DIR / "silver" / "infrastructure" / "im3-2026.02.09-entity-resolution.processing-report.json"
    resolution_report = load_json(resolution_report_path)
    expected_report_counts = {
        "source_object_count": 1472,
        "facility_count": 1340,
        "campus_count": 132,
        "campus_linked_facility_count": 253,
        "campus_linked_building_count": 252,
        "campus_linked_point_count": 1,
        "operator_source_record_count": 953,
        "normalized_operator_count": 161,
        "raw_operator_variant_count": 163,
        "operator_groups_with_multiple_raw_variants": 2,
        "pending_candidate_count": 16,
        "point_building_candidate_count": 11,
        "campus_membership_candidate_count": 5,
        "governed_review_decision_count": 414,
    }
    if resolution_report.get("counts") != expected_report_counts:
        issues.append(Issue("public_data_validation", resolution_report_path.name, "entity-resolution diagnostics changed"))

    public_resolution_path = PUBLIC_DATA_DIR / "entity-resolution" / "index.json"
    public_resolution = load_json(public_resolution_path)
    resolution_ids = [record.get("entity_id") for record in public_resolution]
    if len(public_resolution) != 1472 or set(resolution_ids) != set(facility_ids):
        issues.append(Issue("public_data_validation", "entity-resolution/index.json", "resolution index and map must contain the same source objects"))
    for index, record in enumerate(public_resolution):
        for issue in validator.validate_record(record, schema_paths["public_entity_resolution_record"]):
            issues.append(Issue("public_data_validation", f"entity-resolution/index.json[{index}]{issue.path[1:]}", issue.message))

    resolution_coverage_path = PUBLIC_DATA_DIR / "counties" / "entity-resolution-coverage.json"
    resolution_coverage = load_json(resolution_coverage_path)
    resolution_coverage_fips = [record.get("county_fips") for record in resolution_coverage]
    if len(resolution_coverage) != 3144 or set(resolution_coverage_fips) != feature_fips:
        issues.append(Issue("public_data_validation", "counties/entity-resolution-coverage.json", "resolution coverage must contain every Census county exactly once"))
    if len(resolution_coverage_fips) != len(set(resolution_coverage_fips)):
        issues.append(Issue("public_data_validation", "counties/entity-resolution-coverage.json", "resolution coverage county FIPS values must be unique"))
    for index, record in enumerate(resolution_coverage):
        for issue in validator.validate_record(record, schema_paths["public_entity_resolution_coverage"]):
            issues.append(Issue("public_data_validation", f"entity-resolution-coverage.json[{index}]{issue.path[1:]}", issue.message))
        boundary = features_by_fips.get(record.get("county_fips", ""), {})
        if record.get("county_name") != boundary.get("county_name") or record.get("state_abbr") != boundary.get("state_abbr"):
            issues.append(Issue("public_data_validation", f"entity-resolution-coverage.json[{index}]", "county identity does not match the Census boundary"))
        if record.get("source_record_count") != coverage_by_fips.get(record.get("county_fips", ""), {}).get("source_record_count"):
            issues.append(Issue("public_data_validation", f"entity-resolution-coverage.json[{index}]", "source record count does not match source coverage"))
    if (
        sum(record.get("campus_linked_facility_count", 0) for record in resolution_coverage) < 253
        or sum(record.get("operator_linked_record_count", 0) for record in resolution_coverage) < 953
        or sum(record.get("pending_candidate_count", 0) for record in resolution_coverage) != 16
    ):
        issues.append(Issue("public_data_validation", "counties/entity-resolution-coverage.json", "national entity-resolution totals are inconsistent"))

    resolution_manifest_path = DATA_DIR / "silver" / "infrastructure" / "im3-2026.02.09-entity-resolution.manifest.json"
    resolution_manifest = load_json(resolution_manifest_path)
    for issue in validator.validate_record(resolution_manifest, schema_paths["dataset_manifest"]):
        issues.append(Issue("public_data_validation", f"{resolution_manifest_path.name}{issue.path[1:]}", issue.message))
    total_resolution_manifest_records = 0
    for index, part in enumerate(resolution_manifest.get("parts", [])):
        part_path = (ROOT / part.get("path", "")).resolve()
        if not part_path.is_relative_to(ROOT) or not part_path.is_file():
            issues.append(Issue("public_data_validation", f"{resolution_manifest_path.name}.parts[{index}]", "part path is missing or outside the repository"))
            continue
        payload = part_path.read_bytes()
        total_resolution_manifest_records += part.get("record_count", 0)
        if part.get("byte_size") != len(payload) or part.get("sha256") != hashlib.sha256(payload).hexdigest():
            issues.append(Issue("public_data_validation", f"{resolution_manifest_path.name}.parts[{index}]", "byte size or SHA-256 does not match the artifact"))
    if resolution_manifest.get("record_count") != total_resolution_manifest_records:
        issues.append(Issue("public_data_validation", resolution_manifest_path.name, "manifest record count does not equal its parts"))

    evidence_sources_path = CONFIG_DIR / "im3-candidate-evidence-sources.json"
    evidence_sources_document = load_json(evidence_sources_path)
    evidence_sources = evidence_sources_document.get("records", [])
    if evidence_sources_document.get("record_count") != 10 or len(evidence_sources) != 10:
        issues.append(Issue("public_data_validation", evidence_sources_path.name, "expected ten curated evidence sources"))
    for index, record in enumerate(evidence_sources):
        for issue in validator.validate_record(record, schema_paths["source"]):
            issues.append(Issue("public_data_validation", f"{evidence_sources_path.name}.records[{index}]{issue.path[1:]}", issue.message))

    adjudication_config_path = CONFIG_DIR / "im3-candidate-adjudications.json"
    adjudication_config_document = load_json(adjudication_config_path)
    adjudication_config = adjudication_config_document.get("records", [])
    if adjudication_config_document.get("record_count") != 16 or len(adjudication_config) != 16:
        issues.append(Issue("public_data_validation", adjudication_config_path.name, "every candidate must have one adjudication"))
    configured_candidate_ids = [record.get("resolution_candidate_id") for record in adjudication_config]
    resolution_candidate_ids = [record.get("resolution_candidate_id") for record in resolution_collections.get("entity_resolution_candidate", [])]
    if len(configured_candidate_ids) != len(set(configured_candidate_ids)) or set(configured_candidate_ids) != set(resolution_candidate_ids):
        issues.append(Issue("public_data_validation", adjudication_config_path.name, "configured adjudications must map one-to-one to resolution candidates"))
    configured_source_ids = {record.get("source_id") for record in evidence_sources} | {"src_im3_atlas_20260209"}
    for index, record in enumerate(adjudication_config):
        for issue in validator.validate_record(record, schema_paths["candidate_adjudication"]):
            issues.append(Issue("public_data_validation", f"{adjudication_config_path.name}.records[{index}]{issue.path[1:]}", issue.message))
        for evidence in record.get("evidence", []):
            if evidence.get("source_id") not in configured_source_ids:
                issues.append(Issue("referential_integrity", f"{adjudication_config_path.name}.records[{index}].evidence", "unknown adjudication evidence source"))

    adjudicated_path = DATA_DIR / "silver" / "infrastructure" / "im3-2026.02.09-entity-adjudication.json"
    adjudicated = load_json(adjudicated_path)
    adjudicated_collections = adjudicated.get("collections", {})
    expected_adjudicated_counts = {
        "campus": 132,
        "facility": 1340,
        "operator": 161,
        "operator_relationship": 953,
        "facility_containment_relationship": 8,
        "review_decision": 430,
        "entity_resolution_candidate": 16,
        "source": 10,
        "claim": 10,
    }
    actual_adjudicated_counts = {
        name: len(adjudicated_collections.get(name, []))
        for name in expected_adjudicated_counts
    }
    if actual_adjudicated_counts != expected_adjudicated_counts or adjudicated.get("record_count") != sum(expected_adjudicated_counts.values()):
        issues.append(Issue("public_data_validation", adjudicated_path.name, "adjudicated collection counts are inconsistent"))
    for collection, expected_count in expected_adjudicated_counts.items():
        if expected_count == 0:
            continue
        for index, record in enumerate(adjudicated_collections.get(collection, [])):
            for issue in validator.validate_record(record, schema_paths[collection]):
                issues.append(Issue("public_data_validation", f"{adjudicated_path.name}.{collection}[{index}]{issue.path[1:]}", issue.message))

    adjudicated_reference_fixture = {
        **adjudicated_collections,
        "claim": collections.get("claim", []) + adjudicated_collections.get("claim", []),
        "source": collections.get("source", []) + adjudicated_collections.get("source", []),
        "source_artifact": collections.get("source_artifact", []),
        "geography_reference": geography_records,
        "metric_definition": load_json(CONFIG_DIR / "metric-registry.json")["metrics"],
    }
    for issue in validate_references(adjudicated_reference_fixture):
        issues.append(Issue("public_data_validation", f"{adjudicated_path.name}:{issue.path}", issue.message))

    adjudication_report_path = DATA_DIR / "silver" / "infrastructure" / "im3-2026.02.09-entity-adjudication.processing-report.json"
    adjudication_report = load_json(adjudication_report_path)
    expected_adjudication_counts = {
        "candidate_count": 16,
        "accepted_candidate_count": 5,
        "rejected_candidate_count": 9,
        "pending_candidate_count": 2,
        "merged_source_record_count": 3,
        "distinct_contained_facility_count": 8,
        "campus_linked_facility_count": 255,
        "canonical_non_superseded_facility_count": 1337,
        "external_evidence_source_count": 10,
        "external_evidence_claim_count": 10,
        "adjudication_decision_count": 16,
    }
    if adjudication_report.get("counts") != expected_adjudication_counts or adjudication_report.get("decision_counts") != {"accept": 2, "do_not_merge": 8, "escalate": 2, "merge": 3, "reject": 1}:
        issues.append(Issue("public_data_validation", adjudication_report_path.name, "candidate adjudication diagnostics changed"))

    public_adjudication_path = PUBLIC_DATA_DIR / "entity-resolution" / "adjudication-index.json"
    public_adjudication = load_json(public_adjudication_path)
    public_adjudication_ids = [record.get("source_entity_id") for record in public_adjudication]
    if len(public_adjudication) != 1472 or set(public_adjudication_ids) != set(facility_ids):
        issues.append(Issue("public_data_validation", "entity-resolution/adjudication-index.json", "adjudication index and map must contain the same source objects"))
    for index, record in enumerate(public_adjudication):
        for issue in validator.validate_record(record, schema_paths["public_entity_adjudication_record"]):
            issues.append(Issue("public_data_validation", f"adjudication-index.json[{index}]{issue.path[1:]}", issue.message))

    adjudication_coverage_path = PUBLIC_DATA_DIR / "counties" / "entity-adjudication-coverage.json"
    adjudication_coverage = load_json(adjudication_coverage_path)
    adjudication_coverage_fips = [record.get("county_fips") for record in adjudication_coverage]
    if len(adjudication_coverage) != 3144 or set(adjudication_coverage_fips) != feature_fips or len(adjudication_coverage_fips) != len(set(adjudication_coverage_fips)):
        issues.append(Issue("public_data_validation", "counties/entity-adjudication-coverage.json", "adjudication coverage must contain every Census county exactly once"))
    for index, record in enumerate(adjudication_coverage):
        for issue in validator.validate_record(record, schema_paths["public_entity_adjudication_coverage"]):
            issues.append(Issue("public_data_validation", f"entity-adjudication-coverage.json[{index}]{issue.path[1:]}", issue.message))
        boundary = features_by_fips.get(record.get("county_fips", ""), {})
        if record.get("county_name") != boundary.get("county_name") or record.get("state_abbr") != boundary.get("state_abbr"):
            issues.append(Issue("public_data_validation", f"entity-adjudication-coverage.json[{index}]", "county identity does not match the Census boundary"))
    if (
        sum(record.get("reviewed_candidate_count", 0) for record in adjudication_coverage) != 14
        or sum(record.get("pending_candidate_count", 0) for record in adjudication_coverage) != 2
        or sum(record.get("merged_source_record_count", 0) for record in adjudication_coverage) != 3
        or sum(record.get("distinct_contained_facility_count", 0) for record in adjudication_coverage) != 8
    ):
        issues.append(Issue("public_data_validation", "counties/entity-adjudication-coverage.json", "national adjudication totals are inconsistent"))

    review_queue = load_json(PUBLIC_DATA_DIR / "entity-resolution" / "review-queue.json")
    if len(review_queue) != 2 or any(record.get("candidate_status") != "pending" for record in review_queue):
        issues.append(Issue("public_data_validation", "entity-resolution/review-queue.json", "review queue must contain the two escalated candidates"))
    for index, record in enumerate(review_queue):
        for issue in validator.validate_record(record, schema_paths["entity_resolution_candidate"]):
            issues.append(Issue("public_data_validation", f"review-queue.json[{index}]{issue.path[1:]}", issue.message))

    public_review_decisions = load_json(PUBLIC_DATA_DIR / "entity-resolution" / "review-decisions.json")
    if len(public_review_decisions) != 16:
        issues.append(Issue("public_data_validation", "entity-resolution/review-decisions.json", "public review decisions must contain all adjudications"))
    for index, record in enumerate(public_review_decisions):
        for issue in validator.validate_record(record, schema_paths["review_decision"]):
            issues.append(Issue("public_data_validation", f"review-decisions.json[{index}]{issue.path[1:]}", issue.message))
    dossier = load_json(PUBLIC_DATA_DIR / "entity-resolution" / "review-dossier.json")
    if len(dossier) != 16 or {record.get("resolution_candidate_id") for record in dossier} != set(resolution_candidate_ids):
        issues.append(Issue("public_data_validation", "entity-resolution/review-dossier.json", "review dossier must cover all candidates"))

    adjudication_manifest_path = DATA_DIR / "silver" / "infrastructure" / "im3-2026.02.09-entity-adjudication.manifest.json"
    adjudication_manifest = load_json(adjudication_manifest_path)
    for issue in validator.validate_record(adjudication_manifest, schema_paths["dataset_manifest"]):
        issues.append(Issue("public_data_validation", f"{adjudication_manifest_path.name}{issue.path[1:]}", issue.message))
    total_adjudication_manifest_records = 0
    for index, part in enumerate(adjudication_manifest.get("parts", [])):
        part_path = (ROOT / part.get("path", "")).resolve()
        if not part_path.is_relative_to(ROOT) or not part_path.is_file():
            issues.append(Issue("public_data_validation", f"{adjudication_manifest_path.name}.parts[{index}]", "part path is missing or outside the repository"))
            continue
        payload = part_path.read_bytes()
        total_adjudication_manifest_records += part.get("record_count", 0)
        if part.get("byte_size") != len(payload) or part.get("sha256") != hashlib.sha256(payload).hexdigest():
            issues.append(Issue("public_data_validation", f"{adjudication_manifest_path.name}.parts[{index}]", "byte size or SHA-256 does not match the artifact"))
    if adjudication_manifest.get("record_count") != total_adjudication_manifest_records:
        issues.append(Issue("public_data_validation", adjudication_manifest_path.name, "manifest record count does not equal its parts"))

    osm_history_path = DATA_DIR / "raw" / "openstreetmap" / "im3-final-boundary-way-history.json"
    osm_history = load_json(osm_history_path)
    osm_records = osm_history.get("records", [])
    expected_osm_way_ids = {428021816, 495115494, 151179323, 1052182309}
    if (
        osm_history.get("record_count") != 4
        or len(osm_records) != 4
        or {record.get("way_id") for record in osm_records} != expected_osm_way_ids
        or any(record.get("version_count") != len(record.get("elements", [])) for record in osm_records)
    ):
        issues.append(Issue("public_data_validation", osm_history_path.name, "OSM boundary history collection is incomplete"))
    osm_acquisition_path = DATA_DIR / "raw" / "openstreetmap" / "im3-final-boundary-way-history.acquisition.json"
    osm_acquisition = load_json(osm_acquisition_path)
    for issue in validator.validate_record(osm_acquisition, schema_paths["acquisition_manifest"]):
        issues.append(Issue("public_data_validation", f"{osm_acquisition_path.name}{issue.path[1:]}", issue.message))
    if (
        osm_acquisition.get("local_path") != osm_history_path.relative_to(ROOT).as_posix()
        or osm_acquisition.get("sha256") != hashlib.sha256(osm_history_path.read_bytes()).hexdigest()
    ):
        issues.append(Issue("public_data_validation", osm_acquisition_path.name, "OSM acquisition hash or local path is inconsistent"))

    final_sources_path = CONFIG_DIR / "im3-final-boundary-evidence-sources.json"
    final_sources_document = load_json(final_sources_path)
    final_sources = final_sources_document.get("records", [])
    if final_sources_document.get("record_count") != 3 or len(final_sources) != 3:
        issues.append(Issue("public_data_validation", final_sources_path.name, "expected three final boundary evidence sources"))
    for index, record in enumerate(final_sources):
        for issue in validator.validate_record(record, schema_paths["source"]):
            issues.append(Issue("public_data_validation", f"{final_sources_path.name}.records[{index}]{issue.path[1:]}", issue.message))

    final_decisions_path = CONFIG_DIR / "im3-final-boundary-decisions.json"
    final_decisions_document = load_json(final_decisions_path)
    final_decisions = final_decisions_document.get("records", [])
    expected_final_candidate_ids = {
        "erc_im3_62102081f4bf6466a9af",
        "erc_im3_705961754a8de416cb06",
    }
    if (
        final_decisions_document.get("record_count") != 2
        or len(final_decisions) != 2
        or {record.get("resolution_candidate_id") for record in final_decisions} != expected_final_candidate_ids
    ):
        issues.append(Issue("public_data_validation", final_decisions_path.name, "final decisions must resolve the two escalated candidates"))
    final_source_ids = {record.get("source_id") for record in final_sources} | {"src_im3_atlas_20260209"}
    for index, record in enumerate(final_decisions):
        for issue in validator.validate_record(record, schema_paths["candidate_adjudication"]):
            issues.append(Issue("public_data_validation", f"{final_decisions_path.name}.records[{index}]{issue.path[1:]}", issue.message))
        for evidence in record.get("evidence", []):
            if evidence.get("source_id") not in final_source_ids:
                issues.append(Issue("referential_integrity", f"{final_decisions_path.name}.records[{index}].evidence", "unknown final boundary evidence source"))

    final_path = DATA_DIR / "silver" / "infrastructure" / "im3-2026.02.09-final-boundary-review.json"
    final_review = load_json(final_path)
    final_collections = final_review.get("collections", {})
    expected_final_counts = {
        "campus": 132,
        "facility": 1340,
        "operator": 161,
        "operator_relationship": 953,
        "facility_containment_relationship": 8,
        "review_decision": 432,
        "entity_resolution_candidate": 16,
        "source": 13,
        "claim": 14,
    }
    actual_final_counts = {name: len(final_collections.get(name, [])) for name in expected_final_counts}
    if actual_final_counts != expected_final_counts or final_review.get("record_count") != sum(expected_final_counts.values()):
        issues.append(Issue("public_data_validation", final_path.name, "final boundary review collection counts are inconsistent"))
    for collection, expected_count in expected_final_counts.items():
        if expected_count == 0:
            continue
        for index, record in enumerate(final_collections.get(collection, [])):
            for issue in validator.validate_record(record, schema_paths[collection]):
                issues.append(Issue("public_data_validation", f"{final_path.name}.{collection}[{index}]{issue.path[1:]}", issue.message))
    final_reference_fixture = {
        **final_collections,
        "claim": collections.get("claim", []) + final_collections.get("claim", []),
        "source": collections.get("source", []) + final_collections.get("source", []),
        "source_artifact": collections.get("source_artifact", []),
        "geography_reference": geography_records,
        "metric_definition": load_json(CONFIG_DIR / "metric-registry.json")["metrics"],
    }
    for issue in validate_references(final_reference_fixture):
        issues.append(Issue("public_data_validation", f"{final_path.name}:{issue.path}", issue.message))
    active_campus_ids = {
        item.get("campus_id")
        for item in final_collections.get("campus", [])
        if item.get("record_status") != "superseded"
    }
    if len(active_campus_ids) != 131 or "cam_im3_campus_00495115494" in active_campus_ids:
        issues.append(Issue("public_data_validation", final_path.name, "One Wilshire building part must be the only newly superseded campus"))

    final_report_path = DATA_DIR / "silver" / "infrastructure" / "im3-2026.02.09-final-boundary-review.processing-report.json"
    final_report = load_json(final_report_path)
    expected_final_report_counts = {
        "candidate_count": 16,
        "accepted_candidate_count": 6,
        "rejected_candidate_count": 10,
        "pending_candidate_count": 0,
        "merged_source_record_count": 4,
        "distinct_contained_facility_count": 8,
        "campus_linked_facility_count": 255,
        "canonical_non_superseded_facility_count": 1337,
        "active_campus_count": 131,
        "final_evidence_source_count": 3,
        "final_evidence_claim_count": 4,
        "final_review_decision_count": 2,
        "total_review_decision_count": 432,
    }
    if final_report.get("counts") != expected_final_report_counts or final_report.get("final_decision_counts") != {"merge": 1, "reject": 1}:
        issues.append(Issue("public_data_validation", final_report_path.name, "final boundary review diagnostics changed"))

    final_public_path = PUBLIC_DATA_DIR / "entity-resolution" / "final-index.json"
    final_public = load_json(final_public_path)
    final_public_ids = [record.get("source_entity_id") for record in final_public]
    if len(final_public) != 1472 or set(final_public_ids) != set(facility_ids):
        issues.append(Issue("public_data_validation", "entity-resolution/final-index.json", "final index and map must contain the same source objects"))
    for index, record in enumerate(final_public):
        for issue in validator.validate_record(record, schema_paths["public_entity_adjudication_record"]):
            issues.append(Issue("public_data_validation", f"final-index.json[{index}]{issue.path[1:]}", issue.message))
    if (
        sum(record.get("identity_status") == "merged" for record in final_public) != 4
        or any(record.get("identity_status") == "review_pending" for record in final_public)
    ):
        issues.append(Issue("public_data_validation", "entity-resolution/final-index.json", "final identity outcomes are inconsistent"))

    final_coverage_path = PUBLIC_DATA_DIR / "counties" / "final-review-coverage.json"
    final_coverage = load_json(final_coverage_path)
    final_coverage_fips = [record.get("county_fips") for record in final_coverage]
    if len(final_coverage) != 3144 or set(final_coverage_fips) != feature_fips or len(final_coverage_fips) != len(set(final_coverage_fips)):
        issues.append(Issue("public_data_validation", "counties/final-review-coverage.json", "final review coverage must contain every Census county exactly once"))
    for index, record in enumerate(final_coverage):
        for issue in validator.validate_record(record, schema_paths["public_entity_adjudication_coverage"]):
            issues.append(Issue("public_data_validation", f"final-review-coverage.json[{index}]{issue.path[1:]}", issue.message))
        boundary = features_by_fips.get(record.get("county_fips", ""), {})
        if record.get("county_name") != boundary.get("county_name") or record.get("state_abbr") != boundary.get("state_abbr"):
            issues.append(Issue("public_data_validation", f"final-review-coverage.json[{index}]", "county identity does not match the Census boundary"))
    if (
        sum(record.get("reviewed_candidate_count", 0) for record in final_coverage) != 16
        or sum(record.get("pending_candidate_count", 0) for record in final_coverage) != 0
        or sum(record.get("merged_source_record_count", 0) for record in final_coverage) != 4
        or sum(record.get("distinct_contained_facility_count", 0) for record in final_coverage) != 8
        or sum(record.get("campus_linked_facility_count", 0) for record in final_coverage) != 256
    ):
        issues.append(Issue("public_data_validation", "counties/final-review-coverage.json", "national final review totals are inconsistent"))

    final_queue = load_json(PUBLIC_DATA_DIR / "entity-resolution" / "final-review-queue.json")
    if final_queue != []:
        issues.append(Issue("public_data_validation", "entity-resolution/final-review-queue.json", "final review queue must be empty"))
    final_public_decisions = load_json(PUBLIC_DATA_DIR / "entity-resolution" / "final-review-decisions.json")
    if len(final_public_decisions) != 2 or any(not record.get("supersedes_decision_id") for record in final_public_decisions):
        issues.append(Issue("public_data_validation", "entity-resolution/final-review-decisions.json", "final decisions must supersede both escalations"))
    for index, record in enumerate(final_public_decisions):
        for issue in validator.validate_record(record, schema_paths["review_decision"]):
            issues.append(Issue("public_data_validation", f"final-review-decisions.json[{index}]{issue.path[1:]}", issue.message))
    final_dossier = load_json(PUBLIC_DATA_DIR / "entity-resolution" / "final-review-dossier.json")
    if len(final_dossier) != 16 or {record.get("resolution_candidate_id") for record in final_dossier} != set(resolution_candidate_ids):
        issues.append(Issue("public_data_validation", "entity-resolution/final-review-dossier.json", "final dossier must cover all candidates"))

    final_manifest_path = DATA_DIR / "silver" / "infrastructure" / "im3-2026.02.09-final-boundary-review.manifest.json"
    final_manifest = load_json(final_manifest_path)
    for issue in validator.validate_record(final_manifest, schema_paths["dataset_manifest"]):
        issues.append(Issue("public_data_validation", f"{final_manifest_path.name}{issue.path[1:]}", issue.message))
    total_final_manifest_records = 0
    for index, part in enumerate(final_manifest.get("parts", [])):
        part_path = (ROOT / part.get("path", "")).resolve()
        if not part_path.is_relative_to(ROOT) or not part_path.is_file():
            issues.append(Issue("public_data_validation", f"{final_manifest_path.name}.parts[{index}]", "part path is missing or outside the repository"))
            continue
        payload = part_path.read_bytes()
        total_final_manifest_records += part.get("record_count", 0)
        if part.get("byte_size") != len(payload) or part.get("sha256") != hashlib.sha256(payload).hexdigest():
            issues.append(Issue("public_data_validation", f"{final_manifest_path.name}.parts[{index}]", "byte size or SHA-256 does not match the artifact"))
    if final_manifest.get("record_count") != total_final_manifest_records:
        issues.append(Issue("public_data_validation", final_manifest_path.name, "manifest record count does not equal its parts"))

    lifecycle_policy_path = CONFIG_DIR / "lifecycle-pilot-policy.json"
    lifecycle_policy = load_json(lifecycle_policy_path)
    for issue in validator.validate_record(lifecycle_policy, schema_paths["lifecycle_verification_policy"]):
        issues.append(Issue("public_data_validation", f"{lifecycle_policy_path.name}{issue.path[1:]}", issue.message))
    if (
        lifecycle_policy.get("pilot_size") != 24
        or lifecycle_policy.get("county_count") != 8
        or lifecycle_policy.get("per_county_quota") != 3
        or sum(lifecycle_policy.get("scoring_weights", {}).values()) != 100
    ):
        issues.append(Issue("public_data_validation", lifecycle_policy_path.name, "lifecycle pilot policy size, quota, or scoring weights are inconsistent"))

    lifecycle_path = DATA_DIR / "silver" / "infrastructure" / "im3-2026.02.09-lifecycle-pilot.json"
    lifecycle_pilot = load_json(lifecycle_path)
    lifecycle_candidates = lifecycle_pilot.get("collections", {}).get("lifecycle_verification_candidate", [])
    active_final_facility_ids = {
        item.get("facility_id")
        for item in final_collections.get("facility", [])
        if item.get("record_status") != "superseded"
    }
    lifecycle_candidate_ids = [item.get("verification_candidate_id") for item in lifecycle_candidates]
    lifecycle_facility_ids = [item.get("facility_id") for item in lifecycle_candidates]
    lifecycle_counties = Counter(item.get("primary_county_fips") for item in lifecycle_candidates)
    if (
        lifecycle_pilot.get("record_count") != 24
        or len(lifecycle_candidates) != 24
        or len(lifecycle_candidate_ids) != len(set(lifecycle_candidate_ids))
        or len(lifecycle_facility_ids) != len(set(lifecycle_facility_ids))
        or not set(lifecycle_facility_ids).issubset(active_final_facility_ids)
        or len(lifecycle_counties) != 8
        or set(lifecycle_counties.values()) != {3}
        or any(item.get("review_status") != "queued" or item.get("evidence_status") != "no_external_evidence" for item in lifecycle_candidates)
    ):
        issues.append(Issue("public_data_validation", lifecycle_path.name, "lifecycle pilot selection, identity, or initial state is inconsistent"))
    for index, record in enumerate(lifecycle_candidates):
        for issue in validator.validate_record(record, schema_paths["lifecycle_verification_candidate"]):
            issues.append(Issue("public_data_validation", f"{lifecycle_path.name}.lifecycle_verification_candidate[{index}]{issue.path[1:]}", issue.message))
    lifecycle_reference_fixture = {
        "facility": final_collections.get("facility", []),
        "campus": final_collections.get("campus", []),
        "operator": final_collections.get("operator", []),
        "lifecycle_verification_candidate": lifecycle_candidates,
        "geography_reference": geography_records,
        "metric_definition": load_json(CONFIG_DIR / "metric-registry.json")["metrics"],
    }
    for issue in validate_references(lifecycle_reference_fixture):
        issues.append(Issue("public_data_validation", f"{lifecycle_path.name}:{issue.path}", issue.message))

    lifecycle_report_path = DATA_DIR / "silver" / "infrastructure" / "im3-2026.02.09-lifecycle-pilot.processing-report.json"
    lifecycle_report = load_json(lifecycle_report_path)
    expected_lifecycle_counts = {
        "active_canonical_facility_count": 1337,
        "eligible_facility_count": 1337,
        "unknown_status_facility_count": 1337,
        "pilot_facility_count": 24,
        "pilot_county_count": 8,
        "verified_facility_count": 0,
    }
    if lifecycle_report.get("counts") != expected_lifecycle_counts or len(lifecycle_report.get("pilot_counties", [])) != 8:
        issues.append(Issue("public_data_validation", lifecycle_report_path.name, "lifecycle pilot diagnostics changed"))

    public_lifecycle_queue_path = PUBLIC_DATA_DIR / "lifecycle" / "pilot-queue.json"
    public_lifecycle_queue = load_json(public_lifecycle_queue_path)
    if public_lifecycle_queue != lifecycle_candidates:
        issues.append(Issue("public_data_validation", "lifecycle/pilot-queue.json", "public lifecycle queue must match the governed silver queue"))
    for index, record in enumerate(public_lifecycle_queue):
        for issue in validator.validate_record(record, schema_paths["lifecycle_verification_candidate"]):
            issues.append(Issue("public_data_validation", f"pilot-queue.json[{index}]{issue.path[1:]}", issue.message))

    lifecycle_coverage_path = PUBLIC_DATA_DIR / "counties" / "lifecycle-verification-coverage.json"
    lifecycle_coverage = load_json(lifecycle_coverage_path)
    lifecycle_coverage_fips = [record.get("county_fips") for record in lifecycle_coverage]
    if len(lifecycle_coverage) != 3144 or set(lifecycle_coverage_fips) != feature_fips or len(lifecycle_coverage_fips) != len(set(lifecycle_coverage_fips)):
        issues.append(Issue("public_data_validation", "counties/lifecycle-verification-coverage.json", "lifecycle coverage must contain every Census county exactly once"))
    for index, record in enumerate(lifecycle_coverage):
        for issue in validator.validate_record(record, schema_paths["public_lifecycle_verification_coverage"]):
            issues.append(Issue("public_data_validation", f"lifecycle-verification-coverage.json[{index}]{issue.path[1:]}", issue.message))
        boundary = features_by_fips.get(record.get("county_fips", ""), {})
        if record.get("county_name") != boundary.get("county_name") or record.get("state_abbr") != boundary.get("state_abbr"):
            issues.append(Issue("public_data_validation", f"lifecycle-verification-coverage.json[{index}]", "county identity does not match the Census boundary"))
    if (
        sum(record.get("active_canonical_facility_count", 0) for record in lifecycle_coverage) != 1337
        or sum(record.get("queued_facility_count", 0) for record in lifecycle_coverage) != 24
        or sum(record.get("verified_facility_count", 0) for record in lifecycle_coverage) != 0
        or sum(record.get("unknown_status_facility_count", 0) for record in lifecycle_coverage) != 1337
        or sum(record.get("coverage_status") == "pilot_queued" for record in lifecycle_coverage) != 8
    ):
        issues.append(Issue("public_data_validation", "counties/lifecycle-verification-coverage.json", "national lifecycle coverage totals are inconsistent"))

    lifecycle_manifest_path = DATA_DIR / "silver" / "infrastructure" / "im3-2026.02.09-lifecycle-pilot.manifest.json"
    lifecycle_manifest = load_json(lifecycle_manifest_path)
    for issue in validator.validate_record(lifecycle_manifest, schema_paths["dataset_manifest"]):
        issues.append(Issue("public_data_validation", f"{lifecycle_manifest_path.name}{issue.path[1:]}", issue.message))
    total_lifecycle_manifest_records = 0
    for index, part in enumerate(lifecycle_manifest.get("parts", [])):
        part_path = (ROOT / part.get("path", "")).resolve()
        if not part_path.is_relative_to(ROOT) or not part_path.is_file():
            issues.append(Issue("public_data_validation", f"{lifecycle_manifest_path.name}.parts[{index}]", "part path is missing or outside the repository"))
            continue
        payload = part_path.read_bytes()
        total_lifecycle_manifest_records += part.get("record_count", 0)
        if part.get("byte_size") != len(payload) or part.get("sha256") != hashlib.sha256(payload).hexdigest():
            issues.append(Issue("public_data_validation", f"{lifecycle_manifest_path.name}.parts[{index}]", "byte size or SHA-256 does not match the artifact"))
    if lifecycle_manifest.get("record_count") != total_lifecycle_manifest_records:
        issues.append(Issue("public_data_validation", lifecycle_manifest_path.name, "manifest record count does not equal its parts"))

    tranche_sources_path = CONFIG_DIR / "lifecycle-tranche-1-evidence-sources.json"
    tranche_sources_document = load_json(tranche_sources_path)
    tranche_sources = tranche_sources_document.get("records", [])
    if tranche_sources_document.get("record_count") != 14 or len(tranche_sources) != 14:
        issues.append(Issue("public_data_validation", tranche_sources_path.name, "expected fourteen governed evidence sources"))
    for index, record in enumerate(tranche_sources):
        for issue in validator.validate_record(record, schema_paths["source"]):
            issues.append(Issue("public_data_validation", f"{tranche_sources_path.name}.records[{index}]{issue.path[1:]}", issue.message))

    tranche_adjudications_path = CONFIG_DIR / "lifecycle-tranche-1-adjudications.json"
    tranche_adjudications_document = load_json(tranche_adjudications_path)
    tranche_adjudications = tranche_adjudications_document.get("records", [])
    if tranche_adjudications_document.get("record_count") != 8 or len(tranche_adjudications) != 8:
        issues.append(Issue("public_data_validation", tranche_adjudications_path.name, "expected one adjudication per pilot county"))
    tranche_source_ids = {record.get("source_id") for record in tranche_sources}
    for index, record in enumerate(tranche_adjudications):
        for issue in validator.validate_record(record, schema_paths["lifecycle_evidence_adjudication"]):
            issues.append(Issue("public_data_validation", f"{tranche_adjudications_path.name}.records[{index}]{issue.path[1:]}", issue.message))
        if record.get("verification_candidate_id") not in set(lifecycle_candidate_ids):
            issues.append(Issue("referential_integrity", f"{tranche_adjudications_path.name}.records[{index}]", "unknown lifecycle candidate"))
        for evidence in record.get("evidence", []):
            if evidence.get("source_id") not in tranche_source_ids:
                issues.append(Issue("referential_integrity", f"{tranche_adjudications_path.name}.records[{index}]", "unknown evidence source"))

    pwc_acquisition_path = DATA_DIR / "raw" / "prince-william-county" / "lifecycle-tranche-1-iad14.acquisition.json"
    pwc_acquisition = load_json(pwc_acquisition_path)
    for issue in validator.validate_record(pwc_acquisition, schema_paths["acquisition_manifest"]):
        issues.append(Issue("public_data_validation", f"{pwc_acquisition_path.name}{issue.path[1:]}", issue.message))
    pwc_raw_path = ROOT / pwc_acquisition.get("local_path", "")
    if not pwc_raw_path.is_file() or pwc_acquisition.get("sha256") != hashlib.sha256(pwc_raw_path.read_bytes()).hexdigest():
        issues.append(Issue("public_data_validation", pwc_acquisition_path.name, "raw GIS response is missing or its SHA-256 changed"))
    else:
        pwc_features = load_json(pwc_raw_path).get("features", [])
        iad14 = [item.get("attributes", {}) for item in pwc_features if item.get("attributes", {}).get("BuildingID") == "IAD14"]
        if len(iad14) != 1 or iad14[0].get("BuildingStatus") != "Planned" or iad14[0].get("PermitStatus") != "Planned":
            issues.append(Issue("public_data_validation", pwc_raw_path.name, "governed IAD14 conflict evidence changed"))

    tranche_path = DATA_DIR / "silver" / "infrastructure" / "im3-2026.02.09-lifecycle-tranche-1.json"
    tranche = load_json(tranche_path)
    tranche_collections = tranche.get("collections", {})
    expected_tranche_collection_counts = {
        "source": 14,
        "claim": 16,
        "claim_resolution": 8,
        "review_decision": 8,
        "event": 3,
        "observation": 2,
        "facility": 6,
    }
    if {name: len(tranche_collections.get(name, [])) for name in expected_tranche_collection_counts} != expected_tranche_collection_counts:
        issues.append(Issue("public_data_validation", tranche_path.name, "lifecycle tranche collection counts changed"))
    if tranche.get("record_count") != sum(expected_tranche_collection_counts.values()):
        issues.append(Issue("public_data_validation", tranche_path.name, "lifecycle tranche record count is inconsistent"))
    for collection, expected_count in expected_tranche_collection_counts.items():
        for index, record in enumerate(tranche_collections.get(collection, [])):
            for issue in validator.validate_record(record, schema_paths[collection]):
                issues.append(Issue("public_data_validation", f"{tranche_path.name}.{collection}[{index}]{issue.path[1:]}", issue.message))

    updated_facility_by_id = {item["facility_id"]: item for item in tranche_collections.get("facility", [])}
    reference_facilities = [updated_facility_by_id.get(item["facility_id"], item) for item in final_collections.get("facility", [])]
    tranche_reference_fixture = {
        **tranche_collections,
        "facility": reference_facilities,
        "campus": final_collections.get("campus", []),
        "operator": final_collections.get("operator", []),
        "lifecycle_verification_candidate": lifecycle_candidates,
        "geography_reference": geography_records,
        "metric_definition": load_json(CONFIG_DIR / "metric-registry.json")["metrics"],
    }
    for issue in validate_references(tranche_reference_fixture):
        issues.append(Issue("public_data_validation", f"{tranche_path.name}:{issue.path}", issue.message))
    review_ids = {record.get("review_decision_id") for record in tranche_collections.get("review_decision", [])}
    if any(record.get("review_decision_id") not in review_ids for record in tranche_collections.get("claim_resolution", [])):
        issues.append(Issue("referential_integrity", tranche_path.name, "claim resolution references an unknown review decision"))

    tranche_queue_path = PUBLIC_DATA_DIR / "lifecycle" / "tranche-1-queue.json"
    tranche_queue = load_json(tranche_queue_path)
    queue_status_counts = Counter(record.get("review_status") for record in tranche_queue)
    if len(tranche_queue) != 24 or queue_status_counts != Counter({"queued": 16, "verified": 6, "in_research": 1, "needs_review": 1}):
        issues.append(Issue("public_data_validation", tranche_queue_path.name, "lifecycle tranche queue states changed"))
    for index, record in enumerate(tranche_queue):
        for issue in validator.validate_record(record, schema_paths["lifecycle_verification_candidate"]):
            issues.append(Issue("public_data_validation", f"{tranche_queue_path.name}[{index}]{issue.path[1:]}", issue.message))

    tranche_results_path = PUBLIC_DATA_DIR / "lifecycle" / "tranche-1-results.json"
    tranche_results = load_json(tranche_results_path)
    result_status_counts = Counter(record.get("resolution_status") for record in tranche_results)
    if len(tranche_results) != 8 or result_status_counts != Counter({"resolved": 6, "unresolved": 1, "disputed": 1}):
        issues.append(Issue("public_data_validation", tranche_results_path.name, "public lifecycle result states changed"))
    for index, record in enumerate(tranche_results):
        for issue in validator.validate_record(record, schema_paths["public_lifecycle_verification_record"]):
            issues.append(Issue("public_data_validation", f"{tranche_results_path.name}[{index}]{issue.path[1:]}", issue.message))
        if record.get("facility_id") not in active_final_facility_ids or record.get("verification_candidate_id") not in set(lifecycle_candidate_ids):
            issues.append(Issue("referential_integrity", f"{tranche_results_path.name}[{index}]", "public lifecycle result references an unknown facility or candidate"))

    tranche_coverage_path = PUBLIC_DATA_DIR / "counties" / "lifecycle-tranche-1-coverage.json"
    tranche_coverage = load_json(tranche_coverage_path)
    tranche_coverage_fips = [record.get("county_fips") for record in tranche_coverage]
    if len(tranche_coverage) != 3144 or set(tranche_coverage_fips) != feature_fips or len(tranche_coverage_fips) != len(set(tranche_coverage_fips)):
        issues.append(Issue("public_data_validation", tranche_coverage_path.name, "tranche coverage must contain every Census county exactly once"))
    for index, record in enumerate(tranche_coverage):
        for issue in validator.validate_record(record, schema_paths["public_lifecycle_verification_coverage"]):
            issues.append(Issue("public_data_validation", f"{tranche_coverage_path.name}[{index}]{issue.path[1:]}", issue.message))
    if (
        sum(record.get("active_canonical_facility_count", 0) for record in tranche_coverage) != 1337
        or sum(record.get("queued_facility_count", 0) for record in tranche_coverage) != 16
        or sum(record.get("in_research_facility_count", 0) for record in tranche_coverage) != 1
        or sum(record.get("needs_review_facility_count", 0) for record in tranche_coverage) != 1
        or sum(record.get("verified_facility_count", 0) for record in tranche_coverage) != 6
        or sum(record.get("unknown_status_facility_count", 0) for record in tranche_coverage) != 1331
        or sum(record.get("coverage_status") == "pilot_in_progress" for record in tranche_coverage) != 8
    ):
        issues.append(Issue("public_data_validation", tranche_coverage_path.name, "national lifecycle tranche totals are inconsistent"))

    tranche_manifest_path = DATA_DIR / "silver" / "infrastructure" / "im3-2026.02.09-lifecycle-tranche-1.manifest.json"
    tranche_manifest = load_json(tranche_manifest_path)
    for issue in validator.validate_record(tranche_manifest, schema_paths["dataset_manifest"]):
        issues.append(Issue("public_data_validation", f"{tranche_manifest_path.name}{issue.path[1:]}", issue.message))
    total_tranche_manifest_records = 0
    for index, part in enumerate(tranche_manifest.get("parts", [])):
        part_path = (ROOT / part.get("path", "")).resolve()
        if not part_path.is_relative_to(ROOT) or not part_path.is_file():
            issues.append(Issue("public_data_validation", f"{tranche_manifest_path.name}.parts[{index}]", "part path is missing or outside the repository"))
            continue
        payload = part_path.read_bytes()
        total_tranche_manifest_records += part.get("record_count", 0)
        if part.get("byte_size") != len(payload) or part.get("sha256") != hashlib.sha256(payload).hexdigest():
            issues.append(Issue("public_data_validation", f"{tranche_manifest_path.name}.parts[{index}]", "byte size or SHA-256 does not match the artifact"))
    if tranche_manifest.get("record_count") != total_tranche_manifest_records:
        issues.append(Issue("public_data_validation", tranche_manifest_path.name, "manifest record count does not equal its parts"))

    tranche_2_sources_path = CONFIG_DIR / "lifecycle-tranche-2-evidence-sources.json"
    tranche_2_sources_document = load_json(tranche_2_sources_path)
    tranche_2_sources = tranche_2_sources_document.get("records", [])
    if tranche_2_sources_document.get("record_count") != 15 or len(tranche_2_sources) != 15:
        issues.append(Issue("public_data_validation", tranche_2_sources_path.name, "expected fifteen governed evidence sources"))
    for index, record in enumerate(tranche_2_sources):
        for issue in validator.validate_record(record, schema_paths["source"]):
            issues.append(Issue("public_data_validation", f"{tranche_2_sources_path.name}.records[{index}]{issue.path[1:]}", issue.message))

    tranche_2_adjudications_path = CONFIG_DIR / "lifecycle-tranche-2-adjudications.json"
    tranche_2_adjudications_document = load_json(tranche_2_adjudications_path)
    tranche_2_adjudications = tranche_2_adjudications_document.get("records", [])
    tranche_2_source_ids = {record.get("source_id") for record in tranche_2_sources}
    if tranche_2_adjudications_document.get("record_count") != 16 or len(tranche_2_adjudications) != 16:
        issues.append(Issue("public_data_validation", tranche_2_adjudications_path.name, "expected sixteen distinct adjudications"))
    for index, record in enumerate(tranche_2_adjudications):
        for issue in validator.validate_record(record, schema_paths["lifecycle_evidence_adjudication"]):
            issues.append(Issue("public_data_validation", f"{tranche_2_adjudications_path.name}.records[{index}]{issue.path[1:]}", issue.message))
        if record.get("verification_candidate_id") not in set(lifecycle_candidate_ids):
            issues.append(Issue("referential_integrity", f"{tranche_2_adjudications_path.name}.records[{index}]", "unknown lifecycle candidate"))
        for evidence in record.get("evidence", []):
            if evidence.get("source_id") not in tranche_2_source_ids:
                issues.append(Issue("referential_integrity", f"{tranche_2_adjudications_path.name}.records[{index}]", "unknown evidence source"))

    tranche_2_path = DATA_DIR / "silver" / "infrastructure" / "im3-2026.02.09-lifecycle-tranche-2.json"
    tranche_2 = load_json(tranche_2_path)
    tranche_2_collections = tranche_2.get("collections", {})
    expected_tranche_2_collection_counts = {
        "source": 15,
        "claim": 25,
        "claim_resolution": 16,
        "review_decision": 16,
        "event": 0,
        "observation": 2,
        "facility": 4,
    }
    if {name: len(tranche_2_collections.get(name, [])) for name in expected_tranche_2_collection_counts} != expected_tranche_2_collection_counts:
        issues.append(Issue("public_data_validation", tranche_2_path.name, "lifecycle tranche two collection counts changed"))
    if tranche_2.get("record_count") != sum(expected_tranche_2_collection_counts.values()):
        issues.append(Issue("public_data_validation", tranche_2_path.name, "lifecycle tranche two record count is inconsistent"))
    for collection in expected_tranche_2_collection_counts:
        for index, record in enumerate(tranche_2_collections.get(collection, [])):
            for issue in validator.validate_record(record, schema_paths[collection]):
                issues.append(Issue("public_data_validation", f"{tranche_2_path.name}.{collection}[{index}]{issue.path[1:]}", issue.message))

    all_updated_facilities = {
        item["facility_id"]: item
        for item in tranche_collections.get("facility", []) + tranche_2_collections.get("facility", [])
    }
    tranche_2_reference_facilities = [all_updated_facilities.get(item["facility_id"], item) for item in final_collections.get("facility", [])]
    tranche_2_reference_fixture = {
        **tranche_2_collections,
        "facility": tranche_2_reference_facilities,
        "campus": final_collections.get("campus", []),
        "operator": final_collections.get("operator", []),
        "lifecycle_verification_candidate": lifecycle_candidates,
        "geography_reference": geography_records,
        "metric_definition": load_json(CONFIG_DIR / "metric-registry.json")["metrics"],
    }
    for issue in validate_references(tranche_2_reference_fixture):
        issues.append(Issue("public_data_validation", f"{tranche_2_path.name}:{issue.path}", issue.message))
    tranche_2_review_ids = {record.get("review_decision_id") for record in tranche_2_collections.get("review_decision", [])}
    if any(record.get("review_decision_id") not in tranche_2_review_ids for record in tranche_2_collections.get("claim_resolution", [])):
        issues.append(Issue("referential_integrity", tranche_2_path.name, "claim resolution references an unknown review decision"))

    tranche_2_queue_path = PUBLIC_DATA_DIR / "lifecycle" / "tranche-2-queue.json"
    tranche_2_queue = load_json(tranche_2_queue_path)
    tranche_2_queue_status_counts = Counter(record.get("review_status") for record in tranche_2_queue)
    if len(tranche_2_queue) != 24 or tranche_2_queue_status_counts != Counter({"verified": 10, "in_research": 11, "needs_review": 3}):
        issues.append(Issue("public_data_validation", tranche_2_queue_path.name, "completed lifecycle pilot states changed"))
    for index, record in enumerate(tranche_2_queue):
        for issue in validator.validate_record(record, schema_paths["lifecycle_verification_candidate"]):
            issues.append(Issue("public_data_validation", f"{tranche_2_queue_path.name}[{index}]{issue.path[1:]}", issue.message))

    tranche_2_results_path = PUBLIC_DATA_DIR / "lifecycle" / "tranche-2-results.json"
    tranche_2_results = load_json(tranche_2_results_path)
    tranche_2_result_status_counts = Counter(record.get("resolution_status") for record in tranche_2_results)
    if len(tranche_2_results) != 24 or tranche_2_result_status_counts != Counter({"resolved": 10, "unresolved": 11, "disputed": 3}):
        issues.append(Issue("public_data_validation", tranche_2_results_path.name, "completed public lifecycle result states changed"))
    if len({record.get("verification_candidate_id") for record in tranche_2_results}) != 24:
        issues.append(Issue("public_data_validation", tranche_2_results_path.name, "public lifecycle results must contain every pilot candidate exactly once"))
    for index, record in enumerate(tranche_2_results):
        for issue in validator.validate_record(record, schema_paths["public_lifecycle_verification_record"]):
            issues.append(Issue("public_data_validation", f"{tranche_2_results_path.name}[{index}]{issue.path[1:]}", issue.message))

    tranche_2_coverage_path = PUBLIC_DATA_DIR / "counties" / "lifecycle-tranche-2-coverage.json"
    tranche_2_coverage = load_json(tranche_2_coverage_path)
    tranche_2_coverage_fips = [record.get("county_fips") for record in tranche_2_coverage]
    if len(tranche_2_coverage) != 3144 or set(tranche_2_coverage_fips) != feature_fips or len(tranche_2_coverage_fips) != len(set(tranche_2_coverage_fips)):
        issues.append(Issue("public_data_validation", tranche_2_coverage_path.name, "tranche coverage must contain every Census county exactly once"))
    for index, record in enumerate(tranche_2_coverage):
        for issue in validator.validate_record(record, schema_paths["public_lifecycle_verification_coverage"]):
            issues.append(Issue("public_data_validation", f"{tranche_2_coverage_path.name}[{index}]{issue.path[1:]}", issue.message))
    if (
        sum(record.get("active_canonical_facility_count", 0) for record in tranche_2_coverage) != 1337
        or sum(record.get("queued_facility_count", 0) for record in tranche_2_coverage) != 0
        or sum(record.get("in_research_facility_count", 0) for record in tranche_2_coverage) != 11
        or sum(record.get("needs_review_facility_count", 0) for record in tranche_2_coverage) != 3
        or sum(record.get("verified_facility_count", 0) for record in tranche_2_coverage) != 10
        or sum(record.get("unknown_status_facility_count", 0) for record in tranche_2_coverage) != 1327
        or sum(record.get("coverage_status") == "pilot_in_progress" for record in tranche_2_coverage) != 0
        or sum(record.get("coverage_status") == "pilot_reviewed" for record in tranche_2_coverage) != 8
    ):
        issues.append(Issue("public_data_validation", tranche_2_coverage_path.name, "completed national lifecycle pilot totals are inconsistent"))

    tranche_2_manifest_path = DATA_DIR / "silver" / "infrastructure" / "im3-2026.02.09-lifecycle-tranche-2.manifest.json"
    tranche_2_manifest = load_json(tranche_2_manifest_path)
    for issue in validator.validate_record(tranche_2_manifest, schema_paths["dataset_manifest"]):
        issues.append(Issue("public_data_validation", f"{tranche_2_manifest_path.name}{issue.path[1:]}", issue.message))
    total_tranche_2_manifest_records = 0
    for index, part in enumerate(tranche_2_manifest.get("parts", [])):
        part_path = (ROOT / part.get("path", "")).resolve()
        if not part_path.is_relative_to(ROOT) or not part_path.is_file():
            issues.append(Issue("public_data_validation", f"{tranche_2_manifest_path.name}.parts[{index}]", "part path is missing or outside the repository"))
            continue
        payload = part_path.read_bytes()
        total_tranche_2_manifest_records += part.get("record_count", 0)
        if part.get("byte_size") != len(payload) or part.get("sha256") != hashlib.sha256(payload).hexdigest():
            issues.append(Issue("public_data_validation", f"{tranche_2_manifest_path.name}.parts[{index}]", "byte size or SHA-256 does not match the artifact"))
    if tranche_2_manifest.get("record_count") != total_tranche_2_manifest_records:
        issues.append(Issue("public_data_validation", tranche_2_manifest_path.name, "manifest record count does not equal its parts"))

    national_policy_path = CONFIG_DIR / "lifecycle-national-expansion-policy.json"
    national_policy = load_json(national_policy_path)
    for issue in validator.validate_record(national_policy, schema_paths["lifecycle_national_expansion_policy"]):
        issues.append(Issue("public_data_validation", f"{national_policy_path.name}{issue.path[1:]}", issue.message))
    regional_states = [
        state_abbr
        for frame in national_policy.get("regional_frame", [])
        for state_abbr in frame.get("state_abbrs", [])
    ]
    national_tranche_policy = national_policy.get("initial_tranche", {})
    if (
        sum(national_policy.get("scoring", {}).get("weights", {}).values()) != 100
        or len(regional_states) != 51
        or len(regional_states) != len(set(regional_states))
        or national_tranche_policy.get("size") != 48
        or national_tranche_policy.get("per_region_quota") != 12
    ):
        issues.append(Issue("public_data_validation", national_policy_path.name, "national scoring, regional frame, or tranche quota is inconsistent"))

    national_path = DATA_DIR / "silver" / "infrastructure" / "im3-2026.02.09-lifecycle-national-priority.json"
    national_document = load_json(national_path)
    national_candidates = national_document.get("collections", {}).get("lifecycle_national_priority_record", [])
    resolved_pilot_facility_ids = {
        record.get("facility_id")
        for record in tranche_2_results
        if record.get("resolution_status") == "resolved"
    }
    expected_unknown_facility_ids = active_final_facility_ids - resolved_pilot_facility_ids
    national_ids = [record.get("national_priority_id") for record in national_candidates]
    national_facility_ids = [record.get("facility_id") for record in national_candidates]
    if (
        national_document.get("record_count") != 1327
        or len(national_candidates) != 1327
        or len(national_ids) != len(set(national_ids))
        or len(national_facility_ids) != len(set(national_facility_ids))
        or set(national_facility_ids) != expected_unknown_facility_ids
        or sorted(record.get("national_rank") for record in national_candidates) != list(range(1, 1328))
        or Counter(record.get("queue_status") for record in national_candidates) != Counter({"national_backlog": 1279, "initial_tranche": 48})
    ):
        issues.append(Issue("public_data_validation", national_path.name, "national lifecycle priority identity, ranks, or queue states are inconsistent"))
    for index, record in enumerate(national_candidates):
        for issue in validator.validate_record(record, schema_paths["lifecycle_national_priority_record"]):
            issues.append(Issue("public_data_validation", f"{national_path.name}.lifecycle_national_priority_record[{index}]{issue.path[1:]}", issue.message))

    national_public_path = PUBLIC_DATA_DIR / "lifecycle" / "national-priority-index.json"
    national_public = load_json(national_public_path)
    if national_public != national_candidates:
        issues.append(Issue("public_data_validation", national_public_path.name, "public national priority index must match the governed silver queue"))

    national_initial_path = PUBLIC_DATA_DIR / "lifecycle" / "national-initial-tranche.json"
    national_initial = load_json(national_initial_path)
    initial_region_counts = Counter(record.get("census_region") for record in national_initial)
    initial_state_counts = Counter(record.get("state_abbr") for record in national_initial)
    initial_county_counts = Counter(record.get("primary_county_fips") for record in national_initial)
    initial_operator_counts = Counter(record.get("operator_id") for record in national_initial if record.get("operator_id"))
    if (
        len(national_initial) != 48
        or set(record.get("facility_id") for record in national_initial)
        != {record.get("facility_id") for record in national_candidates if record.get("queue_status") == "initial_tranche"}
        or sorted(record.get("initial_tranche_rank") for record in national_initial) != list(range(1, 49))
        or initial_region_counts != Counter({"Northeast": 12, "Midwest": 12, "South": 12, "West": 12})
        or max(initial_state_counts.values()) > 3
        or max(initial_county_counts.values()) > 2
        or max(initial_operator_counts.values()) > 4
        or any(record.get("prior_pilot_outcome") != "not_reviewed" for record in national_initial)
    ):
        issues.append(Issue("public_data_validation", national_initial_path.name, "initial national tranche violates size, balance, diversity, or pilot-exclusion rules"))
    for index, record in enumerate(national_initial):
        for issue in validator.validate_record(record, schema_paths["lifecycle_national_priority_record"]):
            issues.append(Issue("public_data_validation", f"{national_initial_path.name}[{index}]{issue.path[1:]}", issue.message))

    pilot_yield_path = PUBLIC_DATA_DIR / "lifecycle" / "national-pilot-yield-analysis.json"
    pilot_yield = load_json(pilot_yield_path)
    for issue in validator.validate_record(pilot_yield, schema_paths["lifecycle_pilot_yield_analysis"]):
        issues.append(Issue("public_data_validation", f"{pilot_yield_path.name}{issue.path[1:]}", issue.message))
    if pilot_yield.get("overall") != {
        "reviewed_count": 24,
        "resolved_count": 10,
        "unresolved_count": 11,
        "disputed_count": 3,
        "resolution_rate": 0.4167,
    }:
        issues.append(Issue("public_data_validation", pilot_yield_path.name, "pilot yield totals changed"))

    national_coverage_path = PUBLIC_DATA_DIR / "counties" / "lifecycle-national-expansion-coverage.json"
    national_coverage = load_json(national_coverage_path)
    national_coverage_fips = [record.get("county_fips") for record in national_coverage]
    if len(national_coverage) != 3144 or set(national_coverage_fips) != feature_fips or len(national_coverage_fips) != len(set(national_coverage_fips)):
        issues.append(Issue("public_data_validation", national_coverage_path.name, "national expansion coverage must contain every Census county exactly once"))
    for index, record in enumerate(national_coverage):
        for issue in validator.validate_record(record, schema_paths["public_lifecycle_verification_coverage"]):
            issues.append(Issue("public_data_validation", f"{national_coverage_path.name}[{index}]{issue.path[1:]}", issue.message))
    if (
        sum(record.get("active_canonical_facility_count", 0) for record in national_coverage) != 1337
        or sum(record.get("queued_facility_count", 0) for record in national_coverage) != 48
        or sum(record.get("in_research_facility_count", 0) for record in national_coverage) != 11
        or sum(record.get("needs_review_facility_count", 0) for record in national_coverage) != 3
        or sum(record.get("verified_facility_count", 0) for record in national_coverage) != 10
        or sum(record.get("unknown_status_facility_count", 0) for record in national_coverage) != 1327
    ):
        issues.append(Issue("public_data_validation", national_coverage_path.name, "national expansion coverage totals are inconsistent"))

    national_metadata_path = PUBLIC_DATA_DIR / "lifecycle" / "national-expansion-metadata.json"
    national_metadata = load_json(national_metadata_path)
    for issue in validator.validate_record(national_metadata, schema_paths["lifecycle_national_expansion_summary"]):
        issues.append(Issue("public_data_validation", f"{national_metadata_path.name}{issue.path[1:]}", issue.message))
    if national_metadata.get("counts", {}).get("national_priority_record_count") != 1327 or national_metadata.get("counts", {}).get("initial_tranche_facility_count") != 48:
        issues.append(Issue("public_data_validation", national_metadata_path.name, "national expansion summary counts are inconsistent"))

    national_manifest_path = DATA_DIR / "silver" / "infrastructure" / "im3-2026.02.09-lifecycle-national-priority.manifest.json"
    national_manifest = load_json(national_manifest_path)
    for issue in validator.validate_record(national_manifest, schema_paths["dataset_manifest"]):
        issues.append(Issue("public_data_validation", f"{national_manifest_path.name}{issue.path[1:]}", issue.message))
    total_national_manifest_records = 0
    for index, part in enumerate(national_manifest.get("parts", [])):
        part_path = (ROOT / part.get("path", "")).resolve()
        if not part_path.is_relative_to(ROOT) or not part_path.is_file():
            issues.append(Issue("public_data_validation", f"{national_manifest_path.name}.parts[{index}]", "part path is missing or outside the repository"))
            continue
        payload = part_path.read_bytes()
        total_national_manifest_records += part.get("record_count", 0)
        if part.get("byte_size") != len(payload) or part.get("sha256") != hashlib.sha256(payload).hexdigest():
            issues.append(Issue("public_data_validation", f"{national_manifest_path.name}.parts[{index}]", "byte size or SHA-256 does not match the artifact"))
    if national_manifest.get("record_count") != total_national_manifest_records:
        issues.append(Issue("public_data_validation", national_manifest_path.name, "manifest record count does not equal its parts"))

    national_tranche_sources_path = CONFIG_DIR / "national-lifecycle-tranche-1-evidence-sources.json"
    national_tranche_sources_document = load_json(national_tranche_sources_path)
    national_tranche_sources = national_tranche_sources_document.get("records", [])
    national_tranche_source_ids = {record.get("source_id") for record in national_tranche_sources}
    if national_tranche_sources_document.get("record_count") != 10 or len(national_tranche_sources) != 10:
        issues.append(Issue("public_data_validation", national_tranche_sources_path.name, "expected ten governed evidence sources"))
    for index, record in enumerate(national_tranche_sources):
        for issue in validator.validate_record(record, schema_paths["source"]):
            issues.append(Issue("public_data_validation", f"{national_tranche_sources_path.name}.records[{index}]{issue.path[1:]}", issue.message))

    national_tranche_adjudications_path = CONFIG_DIR / "national-lifecycle-tranche-1-adjudications.json"
    national_tranche_adjudications_document = load_json(national_tranche_adjudications_path)
    national_tranche_adjudications = national_tranche_adjudications_document.get("records", [])
    expected_reviewed_priority_ids = {
        record.get("national_priority_id")
        for record in national_initial
        if record.get("initial_tranche_rank") in range(1, 9)
    }
    adjudicated_priority_ids = {record.get("national_priority_id") for record in national_tranche_adjudications}
    if (
        national_tranche_adjudications_document.get("record_count") != 8
        or len(national_tranche_adjudications) != 8
        or adjudicated_priority_ids != expected_reviewed_priority_ids
    ):
        issues.append(Issue("public_data_validation", national_tranche_adjudications_path.name, "adjudications must cover national initial-tranche ranks one through eight exactly once"))
    for index, record in enumerate(national_tranche_adjudications):
        for issue in validator.validate_record(record, schema_paths["national_lifecycle_evidence_adjudication"]):
            issues.append(Issue("public_data_validation", f"{national_tranche_adjudications_path.name}.records[{index}]{issue.path[1:]}", issue.message))
        for evidence in record.get("evidence", []):
            if evidence.get("source_id") not in national_tranche_source_ids:
                issues.append(Issue("referential_integrity", f"{national_tranche_adjudications_path.name}.records[{index}]", "unknown evidence source"))

    national_tranche_path = DATA_DIR / "silver" / "infrastructure" / "im3-2026.02.09-lifecycle-national-tranche-1.json"
    national_tranche = load_json(national_tranche_path)
    national_tranche_collections = national_tranche.get("collections", {})
    expected_national_tranche_collection_counts = {
        "source": 10,
        "claim": 17,
        "claim_resolution": 8,
        "review_decision": 8,
        "event": 2,
        "observation": 4,
        "facility": 8,
    }
    if {
        name: len(national_tranche_collections.get(name, []))
        for name in expected_national_tranche_collection_counts
    } != expected_national_tranche_collection_counts:
        issues.append(Issue("public_data_validation", national_tranche_path.name, "national lifecycle tranche collection counts changed"))
    if national_tranche.get("record_count") != sum(expected_national_tranche_collection_counts.values()):
        issues.append(Issue("public_data_validation", national_tranche_path.name, "national lifecycle tranche record count is inconsistent"))
    for collection in expected_national_tranche_collection_counts:
        for index, record in enumerate(national_tranche_collections.get(collection, [])):
            for issue in validator.validate_record(record, schema_paths[collection]):
                issues.append(Issue("public_data_validation", f"{national_tranche_path.name}.{collection}[{index}]{issue.path[1:]}", issue.message))
    national_tranche_review_ids = {
        record.get("review_decision_id")
        for record in national_tranche_collections.get("review_decision", [])
    }
    if any(
        record.get("review_decision_id") not in national_tranche_review_ids
        for record in national_tranche_collections.get("claim_resolution", [])
    ):
        issues.append(Issue("referential_integrity", national_tranche_path.name, "claim resolution references an unknown review decision"))

    national_tranche_results_path = PUBLIC_DATA_DIR / "lifecycle" / "national-tranche-1-results.json"
    national_tranche_results = load_json(national_tranche_results_path)
    result_priority_ids = {record.get("national_priority_id") for record in national_tranche_results}
    if (
        len(national_tranche_results) != 8
        or result_priority_ids != expected_reviewed_priority_ids
        or sorted(record.get("initial_tranche_rank") for record in national_tranche_results) != list(range(1, 9))
        or any(record.get("resolution_status") != "resolved" for record in national_tranche_results)
        or any(record.get("review_status") != "verified" for record in national_tranche_results)
        or any(record.get("resolved_current_status") != "operational" for record in national_tranche_results)
    ):
        issues.append(Issue("public_data_validation", national_tranche_results_path.name, "national tranche results must resolve ranks one through eight as verified operational facilities"))
    for index, record in enumerate(national_tranche_results):
        for issue in validator.validate_record(record, schema_paths["public_national_lifecycle_verification_record"]):
            issues.append(Issue("public_data_validation", f"{national_tranche_results_path.name}[{index}]{issue.path[1:]}", issue.message))
        if not set(record.get("evidence_source_ids", [])).issubset(national_tranche_source_ids):
            issues.append(Issue("referential_integrity", f"{national_tranche_results_path.name}[{index}]", "result references an unknown evidence source"))

    national_remaining_path = PUBLIC_DATA_DIR / "lifecycle" / "national-tranche-1-remaining-queue.json"
    national_remaining = load_json(national_remaining_path)
    initial_priority_ids = {record.get("national_priority_id") for record in national_initial}
    remaining_priority_ids = {record.get("national_priority_id") for record in national_remaining}
    if (
        len(national_remaining) != 40
        or len(remaining_priority_ids) != 40
        or remaining_priority_ids & result_priority_ids
        or remaining_priority_ids | result_priority_ids != initial_priority_ids
    ):
        issues.append(Issue("public_data_validation", national_remaining_path.name, "remaining queue must be the forty unreviewed records from the initial national tranche"))
    for index, record in enumerate(national_remaining):
        for issue in validator.validate_record(record, schema_paths["lifecycle_national_priority_record"]):
            issues.append(Issue("public_data_validation", f"{national_remaining_path.name}[{index}]{issue.path[1:]}", issue.message))

    national_tranche_coverage_path = PUBLIC_DATA_DIR / "counties" / "lifecycle-national-tranche-1-coverage.json"
    national_tranche_coverage = load_json(national_tranche_coverage_path)
    national_tranche_coverage_fips = [record.get("county_fips") for record in national_tranche_coverage]
    if (
        len(national_tranche_coverage) != 3144
        or set(national_tranche_coverage_fips) != feature_fips
        or len(national_tranche_coverage_fips) != len(set(national_tranche_coverage_fips))
    ):
        issues.append(Issue("public_data_validation", national_tranche_coverage_path.name, "national tranche coverage must contain every Census county exactly once"))
    for index, record in enumerate(national_tranche_coverage):
        for issue in validator.validate_record(record, schema_paths["public_lifecycle_verification_coverage"]):
            issues.append(Issue("public_data_validation", f"{national_tranche_coverage_path.name}[{index}]{issue.path[1:]}", issue.message))
    if (
        sum(record.get("active_canonical_facility_count", 0) for record in national_tranche_coverage) != 1337
        or sum(record.get("queued_facility_count", 0) for record in national_tranche_coverage) != 40
        or sum(record.get("in_research_facility_count", 0) for record in national_tranche_coverage) != 11
        or sum(record.get("needs_review_facility_count", 0) for record in national_tranche_coverage) != 3
        or sum(record.get("verified_facility_count", 0) for record in national_tranche_coverage) != 18
        or sum(record.get("unknown_status_facility_count", 0) for record in national_tranche_coverage) != 1319
    ):
        issues.append(Issue("public_data_validation", national_tranche_coverage_path.name, "national tranche coverage totals are inconsistent"))

    national_tranche_metadata_path = PUBLIC_DATA_DIR / "lifecycle" / "national-tranche-1-metadata.json"
    national_tranche_metadata = load_json(national_tranche_metadata_path)
    for issue in validator.validate_record(national_tranche_metadata, schema_paths["public_national_lifecycle_tranche_summary"]):
        issues.append(Issue("public_data_validation", f"{national_tranche_metadata_path.name}{issue.path[1:]}", issue.message))
    expected_national_tranche_counts = {
        "active_canonical_facility_count": 1337,
        "initial_tranche_facility_count": 48,
        "reviewed_facility_count": 8,
        "tranche_verified_facility_count": 8,
        "cumulative_verified_facility_count": 18,
        "in_research_facility_count": 11,
        "needs_review_facility_count": 3,
        "remaining_queue_facility_count": 40,
        "unknown_status_facility_count": 1319,
        "source_count": 10,
        "claim_count": 17,
        "event_count": 2,
        "observation_count": 4,
    }
    if national_tranche_metadata.get("counts") != expected_national_tranche_counts:
        issues.append(Issue("public_data_validation", national_tranche_metadata_path.name, "national tranche summary counts are inconsistent"))

    national_tranche_manifest_path = DATA_DIR / "silver" / "infrastructure" / "im3-2026.02.09-lifecycle-national-tranche-1.manifest.json"
    national_tranche_manifest = load_json(national_tranche_manifest_path)
    for issue in validator.validate_record(national_tranche_manifest, schema_paths["dataset_manifest"]):
        issues.append(Issue("public_data_validation", f"{national_tranche_manifest_path.name}{issue.path[1:]}", issue.message))
    total_national_tranche_manifest_records = 0
    for index, part in enumerate(national_tranche_manifest.get("parts", [])):
        part_path = (ROOT / part.get("path", "")).resolve()
        if not part_path.is_relative_to(ROOT) or not part_path.is_file():
            issues.append(Issue("public_data_validation", f"{national_tranche_manifest_path.name}.parts[{index}]", "part path is missing or outside the repository"))
            continue
        payload = part_path.read_bytes()
        total_national_tranche_manifest_records += part.get("record_count", 0)
        if part.get("byte_size") != len(payload) or part.get("sha256") != hashlib.sha256(payload).hexdigest():
            issues.append(Issue("public_data_validation", f"{national_tranche_manifest_path.name}.parts[{index}]", "byte size or SHA-256 does not match the artifact"))
    if national_tranche_manifest.get("record_count") != total_national_tranche_manifest_records:
        issues.append(Issue("public_data_validation", national_tranche_manifest_path.name, "manifest record count does not equal its parts"))

    national_tranche_2_sources_path = CONFIG_DIR / "national-lifecycle-tranche-2-evidence-sources.json"
    national_tranche_2_sources_document = load_json(national_tranche_2_sources_path)
    national_tranche_2_sources = national_tranche_2_sources_document.get("records", [])
    national_tranche_2_source_ids = {record.get("source_id") for record in national_tranche_2_sources}
    if national_tranche_2_sources_document.get("record_count") != 11 or len(national_tranche_2_sources) != 11:
        issues.append(Issue("public_data_validation", national_tranche_2_sources_path.name, "expected eleven governed evidence sources"))
    for index, record in enumerate(national_tranche_2_sources):
        for issue in validator.validate_record(record, schema_paths["source"]):
            issues.append(Issue("public_data_validation", f"{national_tranche_2_sources_path.name}.records[{index}]{issue.path[1:]}", issue.message))

    national_tranche_2_adjudications_path = CONFIG_DIR / "national-lifecycle-tranche-2-adjudications.json"
    national_tranche_2_adjudications_document = load_json(national_tranche_2_adjudications_path)
    national_tranche_2_adjudications = national_tranche_2_adjudications_document.get("records", [])
    expected_reviewed_2_priority_ids = {
        record.get("national_priority_id")
        for record in national_remaining
        if record.get("initial_tranche_rank") in range(9, 17)
    }
    adjudicated_2_priority_ids = {record.get("national_priority_id") for record in national_tranche_2_adjudications}
    if (
        national_tranche_2_adjudications_document.get("record_count") != 8
        or len(national_tranche_2_adjudications) != 8
        or adjudicated_2_priority_ids != expected_reviewed_2_priority_ids
    ):
        issues.append(Issue("public_data_validation", national_tranche_2_adjudications_path.name, "adjudications must cover national initial-tranche ranks nine through sixteen exactly once"))
    for index, record in enumerate(national_tranche_2_adjudications):
        for issue in validator.validate_record(record, schema_paths["national_lifecycle_evidence_adjudication"]):
            issues.append(Issue("public_data_validation", f"{national_tranche_2_adjudications_path.name}.records[{index}]{issue.path[1:]}", issue.message))
        for evidence in record.get("evidence", []):
            if evidence.get("source_id") not in national_tranche_2_source_ids:
                issues.append(Issue("referential_integrity", f"{national_tranche_2_adjudications_path.name}.records[{index}]", "unknown evidence source"))

    national_tranche_2_path = DATA_DIR / "silver" / "infrastructure" / "im3-2026.02.09-lifecycle-national-tranche-2.json"
    national_tranche_2 = load_json(national_tranche_2_path)
    national_tranche_2_collections = national_tranche_2.get("collections", {})
    expected_national_tranche_2_collection_counts = {
        "source": 11,
        "claim": 21,
        "claim_resolution": 8,
        "review_decision": 8,
        "event": 0,
        "observation": 5,
        "facility": 6,
    }
    if {
        name: len(national_tranche_2_collections.get(name, []))
        for name in expected_national_tranche_2_collection_counts
    } != expected_national_tranche_2_collection_counts:
        issues.append(Issue("public_data_validation", national_tranche_2_path.name, "second national lifecycle tranche collection counts changed"))
    if national_tranche_2.get("record_count") != sum(expected_national_tranche_2_collection_counts.values()):
        issues.append(Issue("public_data_validation", national_tranche_2_path.name, "second national lifecycle tranche record count is inconsistent"))
    for collection in expected_national_tranche_2_collection_counts:
        for index, record in enumerate(national_tranche_2_collections.get(collection, [])):
            for issue in validator.validate_record(record, schema_paths[collection]):
                issues.append(Issue("public_data_validation", f"{national_tranche_2_path.name}.{collection}[{index}]{issue.path[1:]}", issue.message))
    national_tranche_2_review_ids = {
        record.get("review_decision_id")
        for record in national_tranche_2_collections.get("review_decision", [])
    }
    if any(
        record.get("review_decision_id") not in national_tranche_2_review_ids
        for record in national_tranche_2_collections.get("claim_resolution", [])
    ):
        issues.append(Issue("referential_integrity", national_tranche_2_path.name, "claim resolution references an unknown review decision"))

    national_tranche_2_results_path = PUBLIC_DATA_DIR / "lifecycle" / "national-tranche-2-results.json"
    national_tranche_2_results = load_json(national_tranche_2_results_path)
    result_2_priority_ids = {record.get("national_priority_id") for record in national_tranche_2_results}
    result_2_resolution_counts = Counter(record.get("resolution_status") for record in national_tranche_2_results)
    result_2_review_counts = Counter(record.get("review_status") for record in national_tranche_2_results)
    if (
        len(national_tranche_2_results) != 8
        or result_2_priority_ids != expected_reviewed_2_priority_ids
        or sorted(record.get("initial_tranche_rank") for record in national_tranche_2_results) != list(range(9, 17))
        or result_2_resolution_counts != Counter({"resolved": 6, "unresolved": 2})
        or result_2_review_counts != Counter({"verified": 6, "in_research": 2})
        or any(
            record.get("resolved_current_status") != "operational"
            for record in national_tranche_2_results
            if record.get("resolution_status") == "resolved"
        )
    ):
        issues.append(Issue("public_data_validation", national_tranche_2_results_path.name, "second national tranche result states or ranks are inconsistent"))
    for index, record in enumerate(national_tranche_2_results):
        for issue in validator.validate_record(record, schema_paths["public_national_lifecycle_verification_record"]):
            issues.append(Issue("public_data_validation", f"{national_tranche_2_results_path.name}[{index}]{issue.path[1:]}", issue.message))
        if not set(record.get("evidence_source_ids", [])).issubset(national_tranche_2_source_ids):
            issues.append(Issue("referential_integrity", f"{national_tranche_2_results_path.name}[{index}]", "result references an unknown evidence source"))

    national_remaining_2_path = PUBLIC_DATA_DIR / "lifecycle" / "national-tranche-2-remaining-queue.json"
    national_remaining_2 = load_json(national_remaining_2_path)
    prior_remaining_priority_ids = {record.get("national_priority_id") for record in national_remaining}
    remaining_2_priority_ids = {record.get("national_priority_id") for record in national_remaining_2}
    if (
        len(national_remaining_2) != 32
        or len(remaining_2_priority_ids) != 32
        or remaining_2_priority_ids & result_2_priority_ids
        or remaining_2_priority_ids | result_2_priority_ids != prior_remaining_priority_ids
    ):
        issues.append(Issue("public_data_validation", national_remaining_2_path.name, "remaining queue must be the thirty-two unreviewed records after ranks nine through sixteen"))
    for index, record in enumerate(national_remaining_2):
        for issue in validator.validate_record(record, schema_paths["lifecycle_national_priority_record"]):
            issues.append(Issue("public_data_validation", f"{national_remaining_2_path.name}[{index}]{issue.path[1:]}", issue.message))

    national_tranche_2_coverage_path = PUBLIC_DATA_DIR / "counties" / "lifecycle-national-tranche-2-coverage.json"
    national_tranche_2_coverage = load_json(national_tranche_2_coverage_path)
    national_tranche_2_coverage_fips = [record.get("county_fips") for record in national_tranche_2_coverage]
    if (
        len(national_tranche_2_coverage) != 3144
        or set(national_tranche_2_coverage_fips) != feature_fips
        or len(national_tranche_2_coverage_fips) != len(set(national_tranche_2_coverage_fips))
    ):
        issues.append(Issue("public_data_validation", national_tranche_2_coverage_path.name, "second national tranche coverage must contain every Census county exactly once"))
    for index, record in enumerate(national_tranche_2_coverage):
        for issue in validator.validate_record(record, schema_paths["public_lifecycle_verification_coverage"]):
            issues.append(Issue("public_data_validation", f"{national_tranche_2_coverage_path.name}[{index}]{issue.path[1:]}", issue.message))
    if (
        sum(record.get("active_canonical_facility_count", 0) for record in national_tranche_2_coverage) != 1337
        or sum(record.get("queued_facility_count", 0) for record in national_tranche_2_coverage) != 32
        or sum(record.get("in_research_facility_count", 0) for record in national_tranche_2_coverage) != 13
        or sum(record.get("needs_review_facility_count", 0) for record in national_tranche_2_coverage) != 3
        or sum(record.get("verified_facility_count", 0) for record in national_tranche_2_coverage) != 24
        or sum(record.get("unknown_status_facility_count", 0) for record in national_tranche_2_coverage) != 1313
    ):
        issues.append(Issue("public_data_validation", national_tranche_2_coverage_path.name, "second national tranche coverage totals are inconsistent"))

    national_tranche_2_metadata_path = PUBLIC_DATA_DIR / "lifecycle" / "national-tranche-2-metadata.json"
    national_tranche_2_metadata = load_json(national_tranche_2_metadata_path)
    for issue in validator.validate_record(national_tranche_2_metadata, schema_paths["public_national_lifecycle_tranche_summary"]):
        issues.append(Issue("public_data_validation", f"{national_tranche_2_metadata_path.name}{issue.path[1:]}", issue.message))
    expected_national_tranche_2_counts = {
        "active_canonical_facility_count": 1337,
        "initial_tranche_facility_count": 48,
        "reviewed_facility_count": 8,
        "tranche_verified_facility_count": 6,
        "cumulative_verified_facility_count": 24,
        "in_research_facility_count": 13,
        "needs_review_facility_count": 3,
        "remaining_queue_facility_count": 32,
        "unknown_status_facility_count": 1313,
        "source_count": 11,
        "claim_count": 21,
        "event_count": 0,
        "observation_count": 5,
    }
    if national_tranche_2_metadata.get("counts") != expected_national_tranche_2_counts:
        issues.append(Issue("public_data_validation", national_tranche_2_metadata_path.name, "second national tranche summary counts are inconsistent"))

    national_tranche_2_manifest_path = DATA_DIR / "silver" / "infrastructure" / "im3-2026.02.09-lifecycle-national-tranche-2.manifest.json"
    national_tranche_2_manifest = load_json(national_tranche_2_manifest_path)
    for issue in validator.validate_record(national_tranche_2_manifest, schema_paths["dataset_manifest"]):
        issues.append(Issue("public_data_validation", f"{national_tranche_2_manifest_path.name}{issue.path[1:]}", issue.message))
    total_national_tranche_2_manifest_records = 0
    for index, part in enumerate(national_tranche_2_manifest.get("parts", [])):
        part_path = (ROOT / part.get("path", "")).resolve()
        if not part_path.is_relative_to(ROOT) or not part_path.is_file():
            issues.append(Issue("public_data_validation", f"{national_tranche_2_manifest_path.name}.parts[{index}]", "part path is missing or outside the repository"))
            continue
        payload = part_path.read_bytes()
        total_national_tranche_2_manifest_records += part.get("record_count", 0)
        if part.get("byte_size") != len(payload) or part.get("sha256") != hashlib.sha256(payload).hexdigest():
            issues.append(Issue("public_data_validation", f"{national_tranche_2_manifest_path.name}.parts[{index}]", "byte size or SHA-256 does not match the artifact"))
    if national_tranche_2_manifest.get("record_count") != total_national_tranche_2_manifest_records:
        issues.append(Issue("public_data_validation", national_tranche_2_manifest_path.name, "manifest record count does not equal its parts"))

    national_tranche_3_sources_path = CONFIG_DIR / "national-lifecycle-tranche-3-evidence-sources.json"
    national_tranche_3_sources_document = load_json(national_tranche_3_sources_path)
    national_tranche_3_sources = national_tranche_3_sources_document.get("records", [])
    national_tranche_3_source_ids = {record.get("source_id") for record in national_tranche_3_sources}
    if national_tranche_3_sources_document.get("record_count") != 17 or len(national_tranche_3_sources) != 17:
        issues.append(Issue("public_data_validation", national_tranche_3_sources_path.name, "expected seventeen governed evidence sources"))
    for index, record in enumerate(national_tranche_3_sources):
        for issue in validator.validate_record(record, schema_paths["source"]):
            issues.append(Issue("public_data_validation", f"{national_tranche_3_sources_path.name}.records[{index}]{issue.path[1:]}", issue.message))

    national_tranche_3_adjudications_path = CONFIG_DIR / "national-lifecycle-tranche-3-adjudications.json"
    national_tranche_3_adjudications_document = load_json(national_tranche_3_adjudications_path)
    national_tranche_3_adjudications = national_tranche_3_adjudications_document.get("records", [])
    expected_reviewed_3_priority_ids = {
        record.get("national_priority_id")
        for record in national_remaining_2
        if record.get("initial_tranche_rank") in range(17, 25)
    }
    adjudicated_3_priority_ids = {record.get("national_priority_id") for record in national_tranche_3_adjudications}
    if (
        national_tranche_3_adjudications_document.get("record_count") != 8
        or len(national_tranche_3_adjudications) != 8
        or adjudicated_3_priority_ids != expected_reviewed_3_priority_ids
    ):
        issues.append(Issue("public_data_validation", national_tranche_3_adjudications_path.name, "adjudications must cover national initial-tranche ranks seventeen through twenty-four exactly once"))
    for index, record in enumerate(national_tranche_3_adjudications):
        for issue in validator.validate_record(record, schema_paths["national_lifecycle_evidence_adjudication"]):
            issues.append(Issue("public_data_validation", f"{national_tranche_3_adjudications_path.name}.records[{index}]{issue.path[1:]}", issue.message))
        for evidence in record.get("evidence", []):
            if evidence.get("source_id") not in national_tranche_3_source_ids:
                issues.append(Issue("referential_integrity", f"{national_tranche_3_adjudications_path.name}.records[{index}]", "unknown evidence source"))

    national_tranche_3_path = DATA_DIR / "silver" / "infrastructure" / "im3-2026.02.09-lifecycle-national-tranche-3.json"
    national_tranche_3 = load_json(national_tranche_3_path)
    national_tranche_3_collections = national_tranche_3.get("collections", {})
    expected_national_tranche_3_collection_counts = {
        "source": 17,
        "claim": 24,
        "claim_resolution": 8,
        "review_decision": 8,
        "event": 1,
        "observation": 7,
        "facility": 7,
    }
    if {
        name: len(national_tranche_3_collections.get(name, []))
        for name in expected_national_tranche_3_collection_counts
    } != expected_national_tranche_3_collection_counts:
        issues.append(Issue("public_data_validation", national_tranche_3_path.name, "third national lifecycle tranche collection counts changed"))
    if national_tranche_3.get("record_count") != sum(expected_national_tranche_3_collection_counts.values()):
        issues.append(Issue("public_data_validation", national_tranche_3_path.name, "third national lifecycle tranche record count is inconsistent"))
    for collection in expected_national_tranche_3_collection_counts:
        for index, record in enumerate(national_tranche_3_collections.get(collection, [])):
            for issue in validator.validate_record(record, schema_paths[collection]):
                issues.append(Issue("public_data_validation", f"{national_tranche_3_path.name}.{collection}[{index}]{issue.path[1:]}", issue.message))
    national_tranche_3_review_ids = {
        record.get("review_decision_id")
        for record in national_tranche_3_collections.get("review_decision", [])
    }
    if any(
        record.get("review_decision_id") not in national_tranche_3_review_ids
        for record in national_tranche_3_collections.get("claim_resolution", [])
    ):
        issues.append(Issue("referential_integrity", national_tranche_3_path.name, "claim resolution references an unknown review decision"))

    national_tranche_3_results_path = PUBLIC_DATA_DIR / "lifecycle" / "national-tranche-3-results.json"
    national_tranche_3_results = load_json(national_tranche_3_results_path)
    result_3_priority_ids = {record.get("national_priority_id") for record in national_tranche_3_results}
    result_3_resolution_counts = Counter(record.get("resolution_status") for record in national_tranche_3_results)
    result_3_review_counts = Counter(record.get("review_status") for record in national_tranche_3_results)
    if (
        len(national_tranche_3_results) != 8
        or result_3_priority_ids != expected_reviewed_3_priority_ids
        or sorted(record.get("initial_tranche_rank") for record in national_tranche_3_results) != list(range(17, 25))
        or result_3_resolution_counts != Counter({"resolved": 7, "unresolved": 1})
        or result_3_review_counts != Counter({"verified": 7, "in_research": 1})
        or any(
            record.get("resolved_current_status") != "operational"
            for record in national_tranche_3_results
            if record.get("resolution_status") == "resolved"
        )
    ):
        issues.append(Issue("public_data_validation", national_tranche_3_results_path.name, "third national tranche result states or ranks are inconsistent"))
    for index, record in enumerate(national_tranche_3_results):
        for issue in validator.validate_record(record, schema_paths["public_national_lifecycle_verification_record"]):
            issues.append(Issue("public_data_validation", f"{national_tranche_3_results_path.name}[{index}]{issue.path[1:]}", issue.message))
        if not set(record.get("evidence_source_ids", [])).issubset(national_tranche_3_source_ids):
            issues.append(Issue("referential_integrity", f"{national_tranche_3_results_path.name}[{index}]", "result references an unknown evidence source"))

    national_remaining_3_path = PUBLIC_DATA_DIR / "lifecycle" / "national-tranche-3-remaining-queue.json"
    national_remaining_3 = load_json(national_remaining_3_path)
    prior_remaining_2_priority_ids = {record.get("national_priority_id") for record in national_remaining_2}
    remaining_3_priority_ids = {record.get("national_priority_id") for record in national_remaining_3}
    if (
        len(national_remaining_3) != 24
        or len(remaining_3_priority_ids) != 24
        or remaining_3_priority_ids & result_3_priority_ids
        or remaining_3_priority_ids | result_3_priority_ids != prior_remaining_2_priority_ids
    ):
        issues.append(Issue("public_data_validation", national_remaining_3_path.name, "remaining queue must be the twenty-four unreviewed records after ranks seventeen through twenty-four"))
    for index, record in enumerate(national_remaining_3):
        for issue in validator.validate_record(record, schema_paths["lifecycle_national_priority_record"]):
            issues.append(Issue("public_data_validation", f"{national_remaining_3_path.name}[{index}]{issue.path[1:]}", issue.message))

    national_tranche_3_coverage_path = PUBLIC_DATA_DIR / "counties" / "lifecycle-national-tranche-3-coverage.json"
    national_tranche_3_coverage = load_json(national_tranche_3_coverage_path)
    national_tranche_3_coverage_fips = [record.get("county_fips") for record in national_tranche_3_coverage]
    if (
        len(national_tranche_3_coverage) != 3144
        or set(national_tranche_3_coverage_fips) != feature_fips
        or len(national_tranche_3_coverage_fips) != len(set(national_tranche_3_coverage_fips))
    ):
        issues.append(Issue("public_data_validation", national_tranche_3_coverage_path.name, "third national tranche coverage must contain every Census county exactly once"))
    for index, record in enumerate(national_tranche_3_coverage):
        for issue in validator.validate_record(record, schema_paths["public_lifecycle_verification_coverage"]):
            issues.append(Issue("public_data_validation", f"{national_tranche_3_coverage_path.name}[{index}]{issue.path[1:]}", issue.message))
    if (
        sum(record.get("active_canonical_facility_count", 0) for record in national_tranche_3_coverage) != 1337
        or sum(record.get("queued_facility_count", 0) for record in national_tranche_3_coverage) != 24
        or sum(record.get("in_research_facility_count", 0) for record in national_tranche_3_coverage) != 14
        or sum(record.get("needs_review_facility_count", 0) for record in national_tranche_3_coverage) != 3
        or sum(record.get("verified_facility_count", 0) for record in national_tranche_3_coverage) != 31
        or sum(record.get("unknown_status_facility_count", 0) for record in national_tranche_3_coverage) != 1306
    ):
        issues.append(Issue("public_data_validation", national_tranche_3_coverage_path.name, "third national tranche coverage totals are inconsistent"))

    national_tranche_3_metadata_path = PUBLIC_DATA_DIR / "lifecycle" / "national-tranche-3-metadata.json"
    national_tranche_3_metadata = load_json(national_tranche_3_metadata_path)
    for issue in validator.validate_record(national_tranche_3_metadata, schema_paths["public_national_lifecycle_tranche_summary"]):
        issues.append(Issue("public_data_validation", f"{national_tranche_3_metadata_path.name}{issue.path[1:]}", issue.message))
    expected_national_tranche_3_counts = {
        "active_canonical_facility_count": 1337,
        "initial_tranche_facility_count": 48,
        "reviewed_facility_count": 8,
        "tranche_verified_facility_count": 7,
        "cumulative_verified_facility_count": 31,
        "in_research_facility_count": 14,
        "needs_review_facility_count": 3,
        "remaining_queue_facility_count": 24,
        "unknown_status_facility_count": 1306,
        "source_count": 17,
        "claim_count": 24,
        "event_count": 1,
        "observation_count": 7,
    }
    if national_tranche_3_metadata.get("counts") != expected_national_tranche_3_counts:
        issues.append(Issue("public_data_validation", national_tranche_3_metadata_path.name, "third national tranche summary counts are inconsistent"))

    national_tranche_3_manifest_path = DATA_DIR / "silver" / "infrastructure" / "im3-2026.02.09-lifecycle-national-tranche-3.manifest.json"
    national_tranche_3_manifest = load_json(national_tranche_3_manifest_path)
    for issue in validator.validate_record(national_tranche_3_manifest, schema_paths["dataset_manifest"]):
        issues.append(Issue("public_data_validation", f"{national_tranche_3_manifest_path.name}{issue.path[1:]}", issue.message))
    total_national_tranche_3_manifest_records = 0
    for index, part in enumerate(national_tranche_3_manifest.get("parts", [])):
        part_path = (ROOT / part.get("path", "")).resolve()
        if not part_path.is_relative_to(ROOT) or not part_path.is_file():
            issues.append(Issue("public_data_validation", f"{national_tranche_3_manifest_path.name}.parts[{index}]", "part path is missing or outside the repository"))
            continue
        payload = part_path.read_bytes()
        total_national_tranche_3_manifest_records += part.get("record_count", 0)
        if part.get("byte_size") != len(payload) or part.get("sha256") != hashlib.sha256(payload).hexdigest():
            issues.append(Issue("public_data_validation", f"{national_tranche_3_manifest_path.name}.parts[{index}]", "byte size or SHA-256 does not match the artifact"))
    if national_tranche_3_manifest.get("record_count") != total_national_tranche_3_manifest_records:
        issues.append(Issue("public_data_validation", national_tranche_3_manifest_path.name, "manifest record count does not equal its parts"))

    national_tranche_4_sources_path = CONFIG_DIR / "national-lifecycle-tranche-4-evidence-sources.json"
    national_tranche_4_sources_document = load_json(national_tranche_4_sources_path)
    national_tranche_4_sources = national_tranche_4_sources_document.get("records", [])
    national_tranche_4_source_ids = {record.get("source_id") for record in national_tranche_4_sources}
    if national_tranche_4_sources_document.get("record_count") != 16 or len(national_tranche_4_sources) != 16:
        issues.append(Issue("public_data_validation", national_tranche_4_sources_path.name, "expected sixteen governed evidence sources"))
    for index, record in enumerate(national_tranche_4_sources):
        for issue in validator.validate_record(record, schema_paths["source"]):
            issues.append(Issue("public_data_validation", f"{national_tranche_4_sources_path.name}.records[{index}]{issue.path[1:]}", issue.message))

    national_tranche_4_adjudications_path = CONFIG_DIR / "national-lifecycle-tranche-4-adjudications.json"
    national_tranche_4_adjudications_document = load_json(national_tranche_4_adjudications_path)
    national_tranche_4_adjudications = national_tranche_4_adjudications_document.get("records", [])
    expected_reviewed_4_priority_ids = {
        record.get("national_priority_id")
        for record in national_remaining_3
        if record.get("initial_tranche_rank") in range(25, 33)
    }
    adjudicated_4_priority_ids = {record.get("national_priority_id") for record in national_tranche_4_adjudications}
    if (
        national_tranche_4_adjudications_document.get("record_count") != 8
        or len(national_tranche_4_adjudications) != 8
        or adjudicated_4_priority_ids != expected_reviewed_4_priority_ids
    ):
        issues.append(Issue("public_data_validation", national_tranche_4_adjudications_path.name, "adjudications must cover national initial-tranche ranks twenty-five through thirty-two exactly once"))
    for index, record in enumerate(national_tranche_4_adjudications):
        for issue in validator.validate_record(record, schema_paths["national_lifecycle_evidence_adjudication"]):
            issues.append(Issue("public_data_validation", f"{national_tranche_4_adjudications_path.name}.records[{index}]{issue.path[1:]}", issue.message))
        for evidence in record.get("evidence", []):
            if evidence.get("source_id") not in national_tranche_4_source_ids:
                issues.append(Issue("referential_integrity", f"{national_tranche_4_adjudications_path.name}.records[{index}]", "unknown evidence source"))

    national_tranche_4_path = DATA_DIR / "silver" / "infrastructure" / "im3-2026.02.09-lifecycle-national-tranche-4.json"
    national_tranche_4 = load_json(national_tranche_4_path)
    national_tranche_4_collections = national_tranche_4.get("collections", {})
    expected_national_tranche_4_collection_counts = {
        "source": 16,
        "claim": 21,
        "claim_resolution": 8,
        "review_decision": 8,
        "event": 0,
        "observation": 3,
        "facility": 5,
    }
    if {
        name: len(national_tranche_4_collections.get(name, []))
        for name in expected_national_tranche_4_collection_counts
    } != expected_national_tranche_4_collection_counts:
        issues.append(Issue("public_data_validation", national_tranche_4_path.name, "fourth national lifecycle tranche collection counts changed"))
    if national_tranche_4.get("record_count") != sum(expected_national_tranche_4_collection_counts.values()):
        issues.append(Issue("public_data_validation", national_tranche_4_path.name, "fourth national lifecycle tranche record count is inconsistent"))
    for collection in expected_national_tranche_4_collection_counts:
        for index, record in enumerate(national_tranche_4_collections.get(collection, [])):
            for issue in validator.validate_record(record, schema_paths[collection]):
                issues.append(Issue("public_data_validation", f"{national_tranche_4_path.name}.{collection}[{index}]{issue.path[1:]}", issue.message))
    national_tranche_4_review_ids = {
        record.get("review_decision_id")
        for record in national_tranche_4_collections.get("review_decision", [])
    }
    if any(
        record.get("review_decision_id") not in national_tranche_4_review_ids
        for record in national_tranche_4_collections.get("claim_resolution", [])
    ):
        issues.append(Issue("referential_integrity", national_tranche_4_path.name, "claim resolution references an unknown review decision"))

    national_tranche_4_results_path = PUBLIC_DATA_DIR / "lifecycle" / "national-tranche-4-results.json"
    national_tranche_4_results = load_json(national_tranche_4_results_path)
    result_4_priority_ids = {record.get("national_priority_id") for record in national_tranche_4_results}
    result_4_resolution_counts = Counter(record.get("resolution_status") for record in national_tranche_4_results)
    result_4_review_counts = Counter(record.get("review_status") for record in national_tranche_4_results)
    if (
        len(national_tranche_4_results) != 8
        or result_4_priority_ids != expected_reviewed_4_priority_ids
        or sorted(record.get("initial_tranche_rank") for record in national_tranche_4_results) != list(range(25, 33))
        or result_4_resolution_counts != Counter({"resolved": 5, "unresolved": 3})
        or result_4_review_counts != Counter({"verified": 5, "in_research": 3})
        or any(
            record.get("resolved_current_status") != "operational"
            for record in national_tranche_4_results
            if record.get("resolution_status") == "resolved"
        )
    ):
        issues.append(Issue("public_data_validation", national_tranche_4_results_path.name, "fourth national tranche result states or ranks are inconsistent"))
    for index, record in enumerate(national_tranche_4_results):
        for issue in validator.validate_record(record, schema_paths["public_national_lifecycle_verification_record"]):
            issues.append(Issue("public_data_validation", f"{national_tranche_4_results_path.name}[{index}]{issue.path[1:]}", issue.message))
        if not set(record.get("evidence_source_ids", [])).issubset(national_tranche_4_source_ids):
            issues.append(Issue("referential_integrity", f"{national_tranche_4_results_path.name}[{index}]", "result references an unknown evidence source"))

    national_remaining_4_path = PUBLIC_DATA_DIR / "lifecycle" / "national-tranche-4-remaining-queue.json"
    national_remaining_4 = load_json(national_remaining_4_path)
    prior_remaining_3_priority_ids = {record.get("national_priority_id") for record in national_remaining_3}
    remaining_4_priority_ids = {record.get("national_priority_id") for record in national_remaining_4}
    if (
        len(national_remaining_4) != 16
        or len(remaining_4_priority_ids) != 16
        or remaining_4_priority_ids & result_4_priority_ids
        or remaining_4_priority_ids | result_4_priority_ids != prior_remaining_3_priority_ids
    ):
        issues.append(Issue("public_data_validation", national_remaining_4_path.name, "remaining queue must be the sixteen unreviewed records after ranks twenty-five through thirty-two"))
    for index, record in enumerate(national_remaining_4):
        for issue in validator.validate_record(record, schema_paths["lifecycle_national_priority_record"]):
            issues.append(Issue("public_data_validation", f"{national_remaining_4_path.name}[{index}]{issue.path[1:]}", issue.message))

    national_tranche_4_coverage_path = PUBLIC_DATA_DIR / "counties" / "lifecycle-national-tranche-4-coverage.json"
    national_tranche_4_coverage = load_json(national_tranche_4_coverage_path)
    national_tranche_4_coverage_fips = [record.get("county_fips") for record in national_tranche_4_coverage]
    if (
        len(national_tranche_4_coverage) != 3144
        or set(national_tranche_4_coverage_fips) != feature_fips
        or len(national_tranche_4_coverage_fips) != len(set(national_tranche_4_coverage_fips))
    ):
        issues.append(Issue("public_data_validation", national_tranche_4_coverage_path.name, "fourth national tranche coverage must contain every Census county exactly once"))
    for index, record in enumerate(national_tranche_4_coverage):
        for issue in validator.validate_record(record, schema_paths["public_lifecycle_verification_coverage"]):
            issues.append(Issue("public_data_validation", f"{national_tranche_4_coverage_path.name}[{index}]{issue.path[1:]}", issue.message))
    if (
        sum(record.get("active_canonical_facility_count", 0) for record in national_tranche_4_coverage) != 1337
        or sum(record.get("queued_facility_count", 0) for record in national_tranche_4_coverage) != 16
        or sum(record.get("in_research_facility_count", 0) for record in national_tranche_4_coverage) != 17
        or sum(record.get("needs_review_facility_count", 0) for record in national_tranche_4_coverage) != 3
        or sum(record.get("verified_facility_count", 0) for record in national_tranche_4_coverage) != 36
        or sum(record.get("unknown_status_facility_count", 0) for record in national_tranche_4_coverage) != 1301
    ):
        issues.append(Issue("public_data_validation", national_tranche_4_coverage_path.name, "fourth national tranche coverage totals are inconsistent"))

    national_tranche_4_metadata_path = PUBLIC_DATA_DIR / "lifecycle" / "national-tranche-4-metadata.json"
    national_tranche_4_metadata = load_json(national_tranche_4_metadata_path)
    for issue in validator.validate_record(national_tranche_4_metadata, schema_paths["public_national_lifecycle_tranche_summary"]):
        issues.append(Issue("public_data_validation", f"{national_tranche_4_metadata_path.name}{issue.path[1:]}", issue.message))
    expected_national_tranche_4_counts = {
        "active_canonical_facility_count": 1337,
        "initial_tranche_facility_count": 48,
        "reviewed_facility_count": 8,
        "tranche_verified_facility_count": 5,
        "cumulative_verified_facility_count": 36,
        "in_research_facility_count": 17,
        "needs_review_facility_count": 3,
        "remaining_queue_facility_count": 16,
        "unknown_status_facility_count": 1301,
        "source_count": 16,
        "claim_count": 21,
        "event_count": 0,
        "observation_count": 3,
    }
    if national_tranche_4_metadata.get("counts") != expected_national_tranche_4_counts:
        issues.append(Issue("public_data_validation", national_tranche_4_metadata_path.name, "fourth national tranche summary counts are inconsistent"))

    national_tranche_4_manifest_path = DATA_DIR / "silver" / "infrastructure" / "im3-2026.02.09-lifecycle-national-tranche-4.manifest.json"
    national_tranche_4_manifest = load_json(national_tranche_4_manifest_path)
    for issue in validator.validate_record(national_tranche_4_manifest, schema_paths["dataset_manifest"]):
        issues.append(Issue("public_data_validation", f"{national_tranche_4_manifest_path.name}{issue.path[1:]}", issue.message))
    total_national_tranche_4_manifest_records = 0
    for index, part in enumerate(national_tranche_4_manifest.get("parts", [])):
        part_path = (ROOT / part.get("path", "")).resolve()
        if not part_path.is_relative_to(ROOT) or not part_path.is_file():
            issues.append(Issue("public_data_validation", f"{national_tranche_4_manifest_path.name}.parts[{index}]", "part path is missing or outside the repository"))
            continue
        payload = part_path.read_bytes()
        total_national_tranche_4_manifest_records += part.get("record_count", 0)
        if part.get("byte_size") != len(payload) or part.get("sha256") != hashlib.sha256(payload).hexdigest():
            issues.append(Issue("public_data_validation", f"{national_tranche_4_manifest_path.name}.parts[{index}]", "byte size or SHA-256 does not match the artifact"))
    if national_tranche_4_manifest.get("record_count") != total_national_tranche_4_manifest_records:
        issues.append(Issue("public_data_validation", national_tranche_4_manifest_path.name, "manifest record count does not equal its parts"))

    national_tranche_5_sources_path = CONFIG_DIR / "national-lifecycle-tranche-5-evidence-sources.json"
    national_tranche_5_sources_document = load_json(national_tranche_5_sources_path)
    national_tranche_5_sources = national_tranche_5_sources_document.get("records", [])
    national_tranche_5_source_ids = {record.get("source_id") for record in national_tranche_5_sources}
    if national_tranche_5_sources_document.get("record_count") != 14 or len(national_tranche_5_sources) != 14:
        issues.append(Issue("public_data_validation", national_tranche_5_sources_path.name, "expected fourteen governed evidence sources"))
    for index, record in enumerate(national_tranche_5_sources):
        for issue in validator.validate_record(record, schema_paths["source"]):
            issues.append(Issue("public_data_validation", f"{national_tranche_5_sources_path.name}.records[{index}]{issue.path[1:]}", issue.message))

    national_tranche_5_adjudications_path = CONFIG_DIR / "national-lifecycle-tranche-5-adjudications.json"
    national_tranche_5_adjudications_document = load_json(national_tranche_5_adjudications_path)
    national_tranche_5_adjudications = national_tranche_5_adjudications_document.get("records", [])
    expected_reviewed_5_priority_ids = {
        record.get("national_priority_id")
        for record in national_remaining_4
        if record.get("initial_tranche_rank") in range(33, 41)
    }
    adjudicated_5_priority_ids = {record.get("national_priority_id") for record in national_tranche_5_adjudications}
    if (
        national_tranche_5_adjudications_document.get("record_count") != 8
        or len(national_tranche_5_adjudications) != 8
        or adjudicated_5_priority_ids != expected_reviewed_5_priority_ids
    ):
        issues.append(Issue("public_data_validation", national_tranche_5_adjudications_path.name, "adjudications must cover national initial-tranche ranks thirty-three through forty exactly once"))
    for index, record in enumerate(national_tranche_5_adjudications):
        for issue in validator.validate_record(record, schema_paths["national_lifecycle_evidence_adjudication"]):
            issues.append(Issue("public_data_validation", f"{national_tranche_5_adjudications_path.name}.records[{index}]{issue.path[1:]}", issue.message))
        for evidence in record.get("evidence", []):
            if evidence.get("source_id") not in national_tranche_5_source_ids:
                issues.append(Issue("referential_integrity", f"{national_tranche_5_adjudications_path.name}.records[{index}]", "unknown evidence source"))

    national_tranche_5_path = DATA_DIR / "silver" / "infrastructure" / "im3-2026.02.09-lifecycle-national-tranche-5.json"
    national_tranche_5 = load_json(national_tranche_5_path)
    national_tranche_5_collections = national_tranche_5.get("collections", {})
    expected_national_tranche_5_collection_counts = {
        "source": 14,
        "claim": 22,
        "claim_resolution": 8,
        "review_decision": 8,
        "event": 0,
        "observation": 5,
        "facility": 5,
    }
    if {
        name: len(national_tranche_5_collections.get(name, []))
        for name in expected_national_tranche_5_collection_counts
    } != expected_national_tranche_5_collection_counts:
        issues.append(Issue("public_data_validation", national_tranche_5_path.name, "fifth national lifecycle tranche collection counts changed"))
    if national_tranche_5.get("record_count") != sum(expected_national_tranche_5_collection_counts.values()):
        issues.append(Issue("public_data_validation", national_tranche_5_path.name, "fifth national lifecycle tranche record count is inconsistent"))
    for collection in expected_national_tranche_5_collection_counts:
        for index, record in enumerate(national_tranche_5_collections.get(collection, [])):
            for issue in validator.validate_record(record, schema_paths[collection]):
                issues.append(Issue("public_data_validation", f"{national_tranche_5_path.name}.{collection}[{index}]{issue.path[1:]}", issue.message))
    national_tranche_5_review_ids = {
        record.get("review_decision_id")
        for record in national_tranche_5_collections.get("review_decision", [])
    }
    if any(
        record.get("review_decision_id") not in national_tranche_5_review_ids
        for record in national_tranche_5_collections.get("claim_resolution", [])
    ):
        issues.append(Issue("referential_integrity", national_tranche_5_path.name, "claim resolution references an unknown review decision"))

    national_tranche_5_results_path = PUBLIC_DATA_DIR / "lifecycle" / "national-tranche-5-results.json"
    national_tranche_5_results = load_json(national_tranche_5_results_path)
    result_5_priority_ids = {record.get("national_priority_id") for record in national_tranche_5_results}
    result_5_resolution_counts = Counter(record.get("resolution_status") for record in national_tranche_5_results)
    result_5_review_counts = Counter(record.get("review_status") for record in national_tranche_5_results)
    if (
        len(national_tranche_5_results) != 8
        or result_5_priority_ids != expected_reviewed_5_priority_ids
        or sorted(record.get("initial_tranche_rank") for record in national_tranche_5_results) != list(range(33, 41))
        or result_5_resolution_counts != Counter({"resolved": 5, "unresolved": 2, "disputed": 1})
        or result_5_review_counts != Counter({"verified": 5, "in_research": 2, "needs_review": 1})
        or any(
            record.get("resolved_current_status") != "operational"
            for record in national_tranche_5_results
            if record.get("resolution_status") == "resolved"
        )
    ):
        issues.append(Issue("public_data_validation", national_tranche_5_results_path.name, "fifth national tranche result states or ranks are inconsistent"))
    for index, record in enumerate(national_tranche_5_results):
        for issue in validator.validate_record(record, schema_paths["public_national_lifecycle_verification_record"]):
            issues.append(Issue("public_data_validation", f"{national_tranche_5_results_path.name}[{index}]{issue.path[1:]}", issue.message))
        if not set(record.get("evidence_source_ids", [])).issubset(national_tranche_5_source_ids):
            issues.append(Issue("referential_integrity", f"{national_tranche_5_results_path.name}[{index}]", "result references an unknown evidence source"))

    national_remaining_5_path = PUBLIC_DATA_DIR / "lifecycle" / "national-tranche-5-remaining-queue.json"
    national_remaining_5 = load_json(national_remaining_5_path)
    prior_remaining_4_priority_ids = {record.get("national_priority_id") for record in national_remaining_4}
    remaining_5_priority_ids = {record.get("national_priority_id") for record in national_remaining_5}
    if (
        len(national_remaining_5) != 8
        or len(remaining_5_priority_ids) != 8
        or remaining_5_priority_ids & result_5_priority_ids
        or remaining_5_priority_ids | result_5_priority_ids != prior_remaining_4_priority_ids
    ):
        issues.append(Issue("public_data_validation", national_remaining_5_path.name, "remaining queue must be the eight unreviewed records after ranks thirty-three through forty"))
    for index, record in enumerate(national_remaining_5):
        for issue in validator.validate_record(record, schema_paths["lifecycle_national_priority_record"]):
            issues.append(Issue("public_data_validation", f"{national_remaining_5_path.name}[{index}]{issue.path[1:]}", issue.message))

    national_tranche_5_coverage_path = PUBLIC_DATA_DIR / "counties" / "lifecycle-national-tranche-5-coverage.json"
    national_tranche_5_coverage = load_json(national_tranche_5_coverage_path)
    national_tranche_5_coverage_fips = [record.get("county_fips") for record in national_tranche_5_coverage]
    if (
        len(national_tranche_5_coverage) != 3144
        or set(national_tranche_5_coverage_fips) != feature_fips
        or len(national_tranche_5_coverage_fips) != len(set(national_tranche_5_coverage_fips))
    ):
        issues.append(Issue("public_data_validation", national_tranche_5_coverage_path.name, "fifth national tranche coverage must contain every Census county exactly once"))
    for index, record in enumerate(national_tranche_5_coverage):
        for issue in validator.validate_record(record, schema_paths["public_lifecycle_verification_coverage"]):
            issues.append(Issue("public_data_validation", f"{national_tranche_5_coverage_path.name}[{index}]{issue.path[1:]}", issue.message))
    if (
        sum(record.get("active_canonical_facility_count", 0) for record in national_tranche_5_coverage) != 1337
        or sum(record.get("queued_facility_count", 0) for record in national_tranche_5_coverage) != 8
        or sum(record.get("in_research_facility_count", 0) for record in national_tranche_5_coverage) != 19
        or sum(record.get("needs_review_facility_count", 0) for record in national_tranche_5_coverage) != 4
        or sum(record.get("verified_facility_count", 0) for record in national_tranche_5_coverage) != 41
        or sum(record.get("unknown_status_facility_count", 0) for record in national_tranche_5_coverage) != 1296
    ):
        issues.append(Issue("public_data_validation", national_tranche_5_coverage_path.name, "fifth national tranche coverage totals are inconsistent"))

    national_tranche_5_metadata_path = PUBLIC_DATA_DIR / "lifecycle" / "national-tranche-5-metadata.json"
    national_tranche_5_metadata = load_json(national_tranche_5_metadata_path)
    for issue in validator.validate_record(national_tranche_5_metadata, schema_paths["public_national_lifecycle_tranche_summary"]):
        issues.append(Issue("public_data_validation", f"{national_tranche_5_metadata_path.name}{issue.path[1:]}", issue.message))
    expected_national_tranche_5_counts = {
        "active_canonical_facility_count": 1337,
        "initial_tranche_facility_count": 48,
        "reviewed_facility_count": 8,
        "tranche_verified_facility_count": 5,
        "cumulative_verified_facility_count": 41,
        "in_research_facility_count": 19,
        "needs_review_facility_count": 4,
        "remaining_queue_facility_count": 8,
        "unknown_status_facility_count": 1296,
        "source_count": 14,
        "claim_count": 22,
        "event_count": 0,
        "observation_count": 5,
    }
    if national_tranche_5_metadata.get("counts") != expected_national_tranche_5_counts:
        issues.append(Issue("public_data_validation", national_tranche_5_metadata_path.name, "fifth national tranche summary counts are inconsistent"))

    national_tranche_5_manifest_path = DATA_DIR / "silver" / "infrastructure" / "im3-2026.02.09-lifecycle-national-tranche-5.manifest.json"
    national_tranche_5_manifest = load_json(national_tranche_5_manifest_path)
    for issue in validator.validate_record(national_tranche_5_manifest, schema_paths["dataset_manifest"]):
        issues.append(Issue("public_data_validation", f"{national_tranche_5_manifest_path.name}{issue.path[1:]}", issue.message))
    total_national_tranche_5_manifest_records = 0
    for index, part in enumerate(national_tranche_5_manifest.get("parts", [])):
        part_path = (ROOT / part.get("path", "")).resolve()
        if not part_path.is_relative_to(ROOT) or not part_path.is_file():
            issues.append(Issue("public_data_validation", f"{national_tranche_5_manifest_path.name}.parts[{index}]", "part path is missing or outside the repository"))
            continue
        payload = part_path.read_bytes()
        total_national_tranche_5_manifest_records += part.get("record_count", 0)
        if part.get("byte_size") != len(payload) or part.get("sha256") != hashlib.sha256(payload).hexdigest():
            issues.append(Issue("public_data_validation", f"{national_tranche_5_manifest_path.name}.parts[{index}]", "byte size or SHA-256 does not match the artifact"))
    if national_tranche_5_manifest.get("record_count") != total_national_tranche_5_manifest_records:
        issues.append(Issue("public_data_validation", national_tranche_5_manifest_path.name, "manifest record count does not equal its parts"))

    national_tranche_6_sources_path = CONFIG_DIR / "national-lifecycle-tranche-6-evidence-sources.json"
    national_tranche_6_sources_document = load_json(national_tranche_6_sources_path)
    national_tranche_6_sources = national_tranche_6_sources_document.get("records", [])
    national_tranche_6_source_ids = {record.get("source_id") for record in national_tranche_6_sources}
    if national_tranche_6_sources_document.get("record_count") != 22 or len(national_tranche_6_sources) != 22:
        issues.append(Issue("public_data_validation", national_tranche_6_sources_path.name, "expected twenty-two governed evidence sources"))
    for index, record in enumerate(national_tranche_6_sources):
        for issue in validator.validate_record(record, schema_paths["source"]):
            issues.append(Issue("public_data_validation", f"{national_tranche_6_sources_path.name}.records[{index}]{issue.path[1:]}", issue.message))

    national_tranche_6_adjudications_path = CONFIG_DIR / "national-lifecycle-tranche-6-adjudications.json"
    national_tranche_6_adjudications_document = load_json(national_tranche_6_adjudications_path)
    national_tranche_6_adjudications = national_tranche_6_adjudications_document.get("records", [])
    expected_reviewed_6_priority_ids = {
        record.get("national_priority_id")
        for record in national_remaining_5
        if record.get("initial_tranche_rank") in range(41, 49)
    }
    adjudicated_6_priority_ids = {record.get("national_priority_id") for record in national_tranche_6_adjudications}
    if (
        national_tranche_6_adjudications_document.get("record_count") != 8
        or len(national_tranche_6_adjudications) != 8
        or adjudicated_6_priority_ids != expected_reviewed_6_priority_ids
    ):
        issues.append(Issue("public_data_validation", national_tranche_6_adjudications_path.name, "adjudications must cover national initial-tranche ranks forty-one through forty-eight exactly once"))
    for index, record in enumerate(national_tranche_6_adjudications):
        for issue in validator.validate_record(record, schema_paths["national_lifecycle_evidence_adjudication"]):
            issues.append(Issue("public_data_validation", f"{national_tranche_6_adjudications_path.name}.records[{index}]{issue.path[1:]}", issue.message))
        for evidence in record.get("evidence", []):
            if evidence.get("source_id") not in national_tranche_6_source_ids:
                issues.append(Issue("referential_integrity", f"{national_tranche_6_adjudications_path.name}.records[{index}]", "unknown evidence source"))

    national_tranche_6_path = DATA_DIR / "silver" / "infrastructure" / "im3-2026.02.09-lifecycle-national-tranche-6.json"
    national_tranche_6 = load_json(national_tranche_6_path)
    national_tranche_6_collections = national_tranche_6.get("collections", {})
    expected_national_tranche_6_collection_counts = {
        "source": 22,
        "claim": 26,
        "claim_resolution": 8,
        "review_decision": 8,
        "event": 3,
        "observation": 4,
        "facility": 6,
    }
    if {
        name: len(national_tranche_6_collections.get(name, []))
        for name in expected_national_tranche_6_collection_counts
    } != expected_national_tranche_6_collection_counts:
        issues.append(Issue("public_data_validation", national_tranche_6_path.name, "sixth national lifecycle tranche collection counts changed"))
    if national_tranche_6.get("record_count") != sum(expected_national_tranche_6_collection_counts.values()):
        issues.append(Issue("public_data_validation", national_tranche_6_path.name, "sixth national lifecycle tranche record count is inconsistent"))
    for collection in expected_national_tranche_6_collection_counts:
        for index, record in enumerate(national_tranche_6_collections.get(collection, [])):
            for issue in validator.validate_record(record, schema_paths[collection]):
                issues.append(Issue("public_data_validation", f"{national_tranche_6_path.name}.{collection}[{index}]{issue.path[1:]}", issue.message))
    national_tranche_6_review_ids = {
        record.get("review_decision_id")
        for record in national_tranche_6_collections.get("review_decision", [])
    }
    if any(
        record.get("review_decision_id") not in national_tranche_6_review_ids
        for record in national_tranche_6_collections.get("claim_resolution", [])
    ):
        issues.append(Issue("referential_integrity", national_tranche_6_path.name, "claim resolution references an unknown review decision"))

    national_tranche_6_results_path = PUBLIC_DATA_DIR / "lifecycle" / "national-tranche-6-results.json"
    national_tranche_6_results = load_json(national_tranche_6_results_path)
    result_6_priority_ids = {record.get("national_priority_id") for record in national_tranche_6_results}
    result_6_resolution_counts = Counter(record.get("resolution_status") for record in national_tranche_6_results)
    result_6_review_counts = Counter(record.get("review_status") for record in national_tranche_6_results)
    result_6_status_counts = Counter(
        record.get("resolved_current_status")
        for record in national_tranche_6_results
        if record.get("resolution_status") == "resolved"
    )
    if (
        len(national_tranche_6_results) != 8
        or result_6_priority_ids != expected_reviewed_6_priority_ids
        or sorted(record.get("initial_tranche_rank") for record in national_tranche_6_results) != list(range(41, 49))
        or result_6_resolution_counts != Counter({"resolved": 6, "unresolved": 2})
        or result_6_review_counts != Counter({"verified": 6, "in_research": 2})
        or result_6_status_counts != Counter({"operational": 5, "closed": 1})
    ):
        issues.append(Issue("public_data_validation", national_tranche_6_results_path.name, "sixth national tranche result states or ranks are inconsistent"))
    for index, record in enumerate(national_tranche_6_results):
        for issue in validator.validate_record(record, schema_paths["public_national_lifecycle_verification_record"]):
            issues.append(Issue("public_data_validation", f"{national_tranche_6_results_path.name}[{index}]{issue.path[1:]}", issue.message))
        if not set(record.get("evidence_source_ids", [])).issubset(national_tranche_6_source_ids):
            issues.append(Issue("referential_integrity", f"{national_tranche_6_results_path.name}[{index}]", "result references an unknown evidence source"))

    national_remaining_6_path = PUBLIC_DATA_DIR / "lifecycle" / "national-tranche-6-remaining-queue.json"
    national_remaining_6 = load_json(national_remaining_6_path)
    prior_remaining_5_priority_ids = {record.get("national_priority_id") for record in national_remaining_5}
    remaining_6_priority_ids = {record.get("national_priority_id") for record in national_remaining_6}
    if (
        national_remaining_6
        or remaining_6_priority_ids
        or result_6_priority_ids != prior_remaining_5_priority_ids
    ):
        issues.append(Issue("public_data_validation", national_remaining_6_path.name, "remaining queue must be empty after ranks forty-one through forty-eight"))

    national_tranche_6_coverage_path = PUBLIC_DATA_DIR / "counties" / "lifecycle-national-tranche-6-coverage.json"
    national_tranche_6_coverage = load_json(national_tranche_6_coverage_path)
    national_tranche_6_coverage_fips = [record.get("county_fips") for record in national_tranche_6_coverage]
    if (
        len(national_tranche_6_coverage) != 3144
        or set(national_tranche_6_coverage_fips) != feature_fips
        or len(national_tranche_6_coverage_fips) != len(set(national_tranche_6_coverage_fips))
    ):
        issues.append(Issue("public_data_validation", national_tranche_6_coverage_path.name, "sixth national tranche coverage must contain every Census county exactly once"))
    for index, record in enumerate(national_tranche_6_coverage):
        for issue in validator.validate_record(record, schema_paths["public_lifecycle_verification_coverage"]):
            issues.append(Issue("public_data_validation", f"{national_tranche_6_coverage_path.name}[{index}]{issue.path[1:]}", issue.message))
    if (
        sum(record.get("active_canonical_facility_count", 0) for record in national_tranche_6_coverage) != 1337
        or sum(record.get("queued_facility_count", 0) for record in national_tranche_6_coverage) != 0
        or sum(record.get("in_research_facility_count", 0) for record in national_tranche_6_coverage) != 21
        or sum(record.get("needs_review_facility_count", 0) for record in national_tranche_6_coverage) != 4
        or sum(record.get("verified_facility_count", 0) for record in national_tranche_6_coverage) != 47
        or sum(record.get("unknown_status_facility_count", 0) for record in national_tranche_6_coverage) != 1290
    ):
        issues.append(Issue("public_data_validation", national_tranche_6_coverage_path.name, "sixth national tranche coverage totals are inconsistent"))

    national_tranche_6_metadata_path = PUBLIC_DATA_DIR / "lifecycle" / "national-tranche-6-metadata.json"
    national_tranche_6_metadata = load_json(national_tranche_6_metadata_path)
    for issue in validator.validate_record(national_tranche_6_metadata, schema_paths["public_national_lifecycle_tranche_summary"]):
        issues.append(Issue("public_data_validation", f"{national_tranche_6_metadata_path.name}{issue.path[1:]}", issue.message))
    expected_national_tranche_6_counts = {
        "active_canonical_facility_count": 1337,
        "initial_tranche_facility_count": 48,
        "reviewed_facility_count": 8,
        "tranche_verified_facility_count": 6,
        "cumulative_verified_facility_count": 47,
        "in_research_facility_count": 21,
        "needs_review_facility_count": 4,
        "remaining_queue_facility_count": 0,
        "unknown_status_facility_count": 1290,
        "source_count": 22,
        "claim_count": 26,
        "event_count": 3,
        "observation_count": 4,
    }
    if national_tranche_6_metadata.get("counts") != expected_national_tranche_6_counts:
        issues.append(Issue("public_data_validation", national_tranche_6_metadata_path.name, "sixth national tranche summary counts are inconsistent"))

    national_tranche_6_manifest_path = DATA_DIR / "silver" / "infrastructure" / "im3-2026.02.09-lifecycle-national-tranche-6.manifest.json"
    national_tranche_6_manifest = load_json(national_tranche_6_manifest_path)
    for issue in validator.validate_record(national_tranche_6_manifest, schema_paths["dataset_manifest"]):
        issues.append(Issue("public_data_validation", f"{national_tranche_6_manifest_path.name}{issue.path[1:]}", issue.message))
    total_national_tranche_6_manifest_records = 0
    for index, part in enumerate(national_tranche_6_manifest.get("parts", [])):
        part_path = (ROOT / part.get("path", "")).resolve()
        if not part_path.is_relative_to(ROOT) or not part_path.is_file():
            issues.append(Issue("public_data_validation", f"{national_tranche_6_manifest_path.name}.parts[{index}]", "part path is missing or outside the repository"))
            continue
        payload = part_path.read_bytes()
        total_national_tranche_6_manifest_records += part.get("record_count", 0)
        if part.get("byte_size") != len(payload) or part.get("sha256") != hashlib.sha256(payload).hexdigest():
            issues.append(Issue("public_data_validation", f"{national_tranche_6_manifest_path.name}.parts[{index}]", "byte size or SHA-256 does not match the artifact"))
    if national_tranche_6_manifest.get("record_count") != total_national_tranche_6_manifest_records:
        issues.append(Issue("public_data_validation", national_tranche_6_manifest_path.name, "manifest record count does not equal its parts"))
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

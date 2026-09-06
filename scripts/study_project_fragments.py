"""Merge project-scoped study inputs into the governed release payloads.

The legacy release inputs remain authoritative base files.  Parallel workers add one
fragment per project, and the orchestrator rebuilds the aggregate products from the
base plus every fragment in deterministic project-id order.
"""
from __future__ import annotations

import copy
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
EVIDENCE_BASE = ROOT / "config/v1/study-economic-evidence.json"
SYNTHESIS_BASE = ROOT / "config/v1/study-modeled-synthesis.json"
EVIDENCE_FRAGMENTS = ROOT / "config/v1/study-economic-evidence.projects"
SYNTHESIS_FRAGMENTS = ROOT / "config/v1/study-modeled-synthesis.projects"

EVIDENCE_KEYS = {
    "schema_version", "project_id", "reviewed_on", "scope_note",
    "sources", "records", "project_updates",
}
SYNTHESIS_KEYS = {
    "schema_version", "project_id", "reviewed_on", "scope_note",
    "sources", "estimates",
}


def _read(path: Path):
    return json.loads(path.read_text(encoding="utf-8"))


def _fragment_paths(directory: Path):
    return sorted(directory.glob("prj_study_*.json")) if directory.exists() else []


def _validate_fragment(fragment, path: Path, required_keys, row_keys):
    keys = set(fragment)
    missing = required_keys - keys
    extra = keys - required_keys
    if missing or extra:
        raise ValueError(f"Invalid project fragment keys in {path}: missing={sorted(missing)}, extra={sorted(extra)}")
    if fragment["schema_version"] != "1.0.0":
        raise ValueError(f"Unsupported project fragment schema in {path}")
    project_id = fragment["project_id"]
    if path.stem != project_id:
        raise ValueError(f"Project fragment filename must equal project_id: {path}")
    if not fragment["reviewed_on"] or not fragment["scope_note"]:
        raise ValueError(f"Project fragment requires reviewed_on and scope_note: {path}")
    for key in row_keys:
        if not isinstance(fragment[key], list):
            raise ValueError(f"Project fragment {key} must be an array: {path}")
    for key in row_keys - {"sources"}:
        for row in fragment[key]:
            if row.get("project_id") != project_id:
                raise ValueError(f"Project fragment contains cross-project {key}: {path}")
    return project_id


def load_evidence(base_path: Path = EVIDENCE_BASE, fragments_dir: Path = EVIDENCE_FRAGMENTS):
    payload = copy.deepcopy(_read(base_path))
    notes = []
    seen_projects = set()
    for path in _fragment_paths(fragments_dir):
        fragment = _read(path)
        project_id = _validate_fragment(
            fragment, path, EVIDENCE_KEYS, {"sources", "records", "project_updates"}
        )
        if project_id in seen_projects:
            raise ValueError(f"Duplicate evidence project fragment: {project_id}")
        seen_projects.add(project_id)
        payload["sources"].extend(fragment["sources"])
        payload["records"].extend(fragment["records"])
        payload.setdefault("project_updates", []).extend(fragment["project_updates"])
        notes.append(f"{project_id}: {fragment['scope_note']}")
        payload["reviewed_on"] = max(payload["reviewed_on"], fragment["reviewed_on"])
    if notes:
        payload["scope_note"] += " Project fragments: " + " ".join(notes)
    return payload


def load_synthesis(base_path: Path = SYNTHESIS_BASE, fragments_dir: Path = SYNTHESIS_FRAGMENTS):
    payload = copy.deepcopy(_read(base_path))
    notes = []
    seen_projects = set()
    for path in _fragment_paths(fragments_dir):
        fragment = _read(path)
        project_id = _validate_fragment(
            fragment, path, SYNTHESIS_KEYS, {"sources", "estimates"}
        )
        if project_id in seen_projects:
            raise ValueError(f"Duplicate synthesis project fragment: {project_id}")
        seen_projects.add(project_id)
        payload["sources"].extend(fragment["sources"])
        payload["estimates"].extend(fragment["estimates"])
        notes.append(f"{project_id}: {fragment['scope_note']}")
        payload["reviewed_on"] = max(payload["reviewed_on"], fragment["reviewed_on"])
    if notes:
        payload["scope_note"] += " Project fragments: " + " ".join(notes)
    return payload


def fragment_input_paths():
    return [*_fragment_paths(EVIDENCE_FRAGMENTS), *_fragment_paths(SYNTHESIS_FRAGMENTS)]

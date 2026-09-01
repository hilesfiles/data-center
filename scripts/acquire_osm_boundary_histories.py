#!/usr/bin/env python3
"""Acquire OSM way histories used by the final IM3 boundary review.

Only JSON artifacts are retained. The payload preserves the API elements and
adds the observatory source-entity role needed to reproduce the adjudication.
"""

from __future__ import annotations

import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen


ROOT = Path(__file__).resolve().parents[1]
OUTPUT_PATH = ROOT / "data/raw/openstreetmap/im3-final-boundary-way-history.json"
MANIFEST_PATH = ROOT / "data/raw/openstreetmap/im3-final-boundary-way-history.acquisition.json"
PARSER_VERSION = "1.0.0"
SOURCE_ID = "src_osm_boundary_way_history_20260831"
WAYS = (
    (428021816, "fac_im3_building_00428021816", "one_wilshire_building"),
    (495115494, "cam_im3_campus_00495115494", "one_wilshire_inner_polygon"),
    (151179323, "fac_im3_building_00151179323", "lumen_building"),
    (1052182309, "cam_im3_campus_01052182309", "4010_data_center_boundary"),
)


def write_json(path: Path, value: Any, *, compact: bool = False) -> bytes:
    text = (
        json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
        if compact
        else json.dumps(value, ensure_ascii=False, indent=2)
    )
    payload = (text + "\n").encode("utf-8")
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(payload)
    return payload


def fetch_history(way_id: int) -> tuple[str, dict[str, Any], int]:
    url = f"https://api.openstreetmap.org/api/0.6/way/{way_id}/history.json"
    request = Request(
        url,
        headers={"User-Agent": "DCCIO-boundary-review/1.0 (+https://github.com/)"},
    )
    try:
        with urlopen(request, timeout=120) as response:
            return url, json.loads(response.read()), response.status
    except (HTTPError, URLError, TimeoutError, json.JSONDecodeError) as exc:
        raise RuntimeError(f"OSM way {way_id} history acquisition failed: {exc}") from exc


def main() -> int:
    retrieved_at = datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")
    records = []
    statuses = []
    for way_id, source_entity_id, role in WAYS:
        history_url, response, status = fetch_history(way_id)
        statuses.append(status)
        elements = sorted(response.get("elements", []), key=lambda item: item.get("version", 0))
        if not elements or any(item.get("id") != way_id for item in elements):
            raise RuntimeError(f"OSM way {way_id} returned an incomplete history")
        records.append(
            {
                "way_id": way_id,
                "source_entity_id": source_entity_id,
                "review_role": role,
                "history_url": history_url,
                "version_count": len(elements),
                "elements": elements,
            }
        )

    document = {
        "schema_version": "1.0.0",
        "artifact_type": "openstreetmap_way_history_collection",
        "artifact_version": "2026.08.31",
        "generated_at": retrieved_at,
        "record_count": len(records),
        "records": records,
    }
    payload = write_json(OUTPUT_PATH, document, compact=True)
    manifest = {
        "schema_version": "1.0.0",
        "manifest_id": "acq_osm_im3_final_boundary_history_20260831",
        "source_id": SOURCE_ID,
        "source_url": "https://www.openstreetmap.org/",
        "request_url": records[0]["history_url"],
        "retrieved_at": retrieved_at,
        "http_status": min(statuses),
        "sha256": hashlib.sha256(payload).hexdigest(),
        "local_path": OUTPUT_PATH.relative_to(ROOT).as_posix(),
        "license": "Open Database License (ODbL); © OpenStreetMap contributors",
        "parser_version": PARSER_VERSION,
        "attempt": 1,
        "created_at": retrieved_at,
        "updated_at": retrieved_at,
        "record_status": "active",
    }
    write_json(MANIFEST_PATH, manifest)
    print(json.dumps({"retrieved_at": retrieved_at, "way_count": len(records), "versions": {str(item["way_id"]): item["version_count"] for item in records}}, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

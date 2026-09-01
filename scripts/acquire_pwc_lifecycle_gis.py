#!/usr/bin/env python3
"""Acquire the Prince William County GIS records surrounding Amazon IAD14."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
from urllib.parse import urlencode
from urllib.request import Request, urlopen

from acquire_im3_facilities import write_json


ROOT = Path(__file__).resolve().parents[1]
ENDPOINT = "https://gisweb.pwcva.gov/arcgis/rest/services/Planning/Build_Out_Analysis/MapServer/9/query"
PARAMETERS = {
    "f": "json",
    "geometry": "-77.5482168,38.7899318",
    "geometryType": "esriGeometryPoint",
    "inSR": "4326",
    "spatialRel": "esriSpatialRelIntersects",
    "distance": "1000",
    "units": "esriSRUnit_Meter",
    "outFields": "*",
    "returnGeometry": "false",
}
RETRIEVED_AT = "2026-08-31T23:45:00Z"


def main() -> int:
    url = f"{ENDPOINT}?{urlencode(PARAMETERS)}"
    request = Request(url, headers={"User-Agent": "DCCIO/1.0 lifecycle evidence acquisition"})
    with urlopen(request, timeout=60) as response:
        raw = response.read()
    payload = json.loads(raw)
    if "error" in payload or not payload.get("features"):
        raise RuntimeError(f"Prince William County GIS query failed: {payload}")

    output_path = ROOT / "data/raw/prince-william-county/lifecycle-tranche-1-iad14.json"
    output = write_json(output_path, payload)
    manifest = {
        "schema_version": "1.0.0",
        "manifest_id": "acq_pwc_iad14_lifecycle_20260831",
        "source_id": "src_pwc_data_center_gis_20260831",
        "source_url": ENDPOINT,
        "request_url": url,
        "retrieved_at": RETRIEVED_AT,
        "http_status": 200,
        "sha256": hashlib.sha256(output).hexdigest(),
        "local_path": "data/raw/prince-william-county/lifecycle-tranche-1-iad14.json",
        "license": "Prince William County public GIS record; terms not independently determined",
        "parser_version": "pwc-lifecycle-gis-v1",
        "attempt": 1,
        "created_at": RETRIEVED_AT,
        "updated_at": RETRIEVED_AT,
        "record_status": "active",
    }
    write_json(
        ROOT / "data/raw/prince-william-county/lifecycle-tranche-1-iad14.acquisition.json",
        manifest,
    )
    print(json.dumps({"feature_count": len(payload["features"]), "output": str(output_path)}, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

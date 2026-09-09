"""Acquire a pinned DEPLOY facility-tier registry snapshot.

DEPLOY publishes its reviewed data-center facility collection as an unauthenticated
JSON API.  The snapshot is wrapped with retrieval and licensing metadata so later
comparison-county builds do not depend on a moving network response.
"""

from __future__ import annotations

import json
from datetime import date
from pathlib import Path
from urllib.request import Request, urlopen


ROOT = Path(__file__).resolve().parents[1]
API_URL = "https://registry.deploy.report/v1/datacenters/facilities"
DOCUMENTATION_URL = "https://registry.deploy.report/open-data-center-registry"
OUTPUT_PATH = ROOT / "data" / "bronze" / "external" / "deploy-data-center-facilities-2026-09-09.json"
RETRIEVED_ON = date(2026, 9, 9)


def fetch(url: str) -> dict:
    request = Request(url, headers={"User-Agent": "Mozilla/5.0 DCCIO research acquisition"})
    with urlopen(request, timeout=180) as response:
        return json.load(response)


def acquire() -> dict:
    payload = fetch(API_URL)
    facilities = payload.get("facilities")
    if not isinstance(facilities, list) or payload.get("count") != len(facilities):
        raise ValueError("DEPLOY response count does not match the facility collection")
    return {
        "schema_version": "1.0.0",
        "name": "DEPLOY open data-center facility registry",
        "documentation": DOCUMENTATION_URL,
        "api_url": API_URL,
        "license": "CC BY 4.0",
        "retrieved": RETRIEVED_ON.isoformat(),
        "count": len(facilities),
        "note": payload.get("note"),
        "facilities": sorted(facilities, key=lambda item: item["id"]),
    }


def main() -> int:
    result = acquire()
    OUTPUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    OUTPUT_PATH.write_text(json.dumps(result, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps({"output": str(OUTPUT_PATH), "records": result["count"]}, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

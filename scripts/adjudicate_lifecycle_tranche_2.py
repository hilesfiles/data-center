#!/usr/bin/env python3
"""Build the second governed lifecycle tranche and cumulative public pilot state."""

from __future__ import annotations

import json
from pathlib import Path

from acquire_im3_facilities import ATTRIBUTION, write_json
from adjudicate_lifecycle_tranche_1 import build, digest


ROOT = Path(__file__).resolve().parents[1]
DATASET_ID = "im3_lifecycle_tranche_2_20260831"
ARTIFACT_VERSION = "2026.08.31"


def main() -> int:
    document, queue, coverage, public = build(
        queue_path="site/public/data/v1/lifecycle/tranche-1-queue.json",
        coverage_path="site/public/data/v1/counties/lifecycle-tranche-1-coverage.json",
        sources_path="config/v1/lifecycle-tranche-2-evidence-sources.json",
        adjudications_path="config/v1/lifecycle-tranche-2-adjudications.json",
        previous_results_path="site/public/data/v1/lifecycle/tranche-1-results.json",
        namespace="lifecycle_tranche_2",
        notices=[
            "All twenty-four pilot facilities have now received a governed evidence review.",
            "Ten facility statuses are resolved as operational; eleven remain in research because evidence does not identify the building; three remain disputed because official records conflict.",
            "The research queue is complete, but unresolved and disputed records remain unknown and do not count as operating facilities.",
            "Site-wide capacity, floor area, and operator-market presence are not assigned to individual buildings without an exact facility match.",
        ],
    )
    document["artifact_type"] = "lifecycle_verification_tranche_2"
    metadata = public["metadata"]
    metadata["artifact_type"] = "public_lifecycle_verification_pilot_complete_summary"
    metadata["input_dataset_id"] = "im3_lifecycle_tranche_1_20260831"
    results = public["results"]
    report = {**metadata, "artifact_type": "lifecycle_verification_tranche_2_processing_report"}
    outputs = [
        ("data/silver/infrastructure/im3-2026.02.09-lifecycle-tranche-2.json", document, True, document["record_count"], "silver", "lifecycle_tranche"),
        ("data/silver/infrastructure/im3-2026.02.09-lifecycle-tranche-2.processing-report.json", report, False, 1, "silver", "processing_report"),
        ("site/public/data/v1/lifecycle/tranche-2-queue.json", queue, True, len(queue), "public", "lifecycle_queue"),
        ("site/public/data/v1/lifecycle/tranche-2-results.json", results, True, len(results), "public", "lifecycle_results"),
        ("site/public/data/v1/counties/lifecycle-tranche-2-coverage.json", coverage, True, len(coverage), "public", "lifecycle_coverage"),
        ("site/public/data/v1/lifecycle/tranche-2-metadata.json", metadata, False, 1, "public", "lifecycle_metadata"),
    ]
    parts = []
    for relative_path, value, compact, record_count, zone, projection in outputs:
        payload = write_json(ROOT / relative_path, value, compact=compact)
        parts.append(
            {
                "path": relative_path,
                "sha256": digest(payload),
                "byte_size": len(payload),
                "record_count": record_count,
                "partition_values": {"zone": zone, "projection": projection},
            }
        )
    manifest = {
        "schema_version": "1.0.0",
        "dataset_id": DATASET_ID,
        "artifact_type": "lifecycle_verification_tranche_2",
        "artifact_version": ARTIFACT_VERSION,
        "generated_at": metadata["generated_at"],
        "data_vintage": "2026-08-31",
        "record_schema": "https://dccio.org/schemas/v1/public-lifecycle-verification-record.schema.json",
        "format": "json",
        "parts": parts,
        "record_count": sum(part["record_count"] for part in parts),
        "input_dataset_ids": ["im3_lifecycle_tranche_1_20260831"],
        "license_metadata": {
            "license": "Mixed source metadata; IM3-derived records remain ODbL",
            "redistribution_status": "mixed",
            "attribution": ATTRIBUTION,
        },
    }
    write_json(ROOT / "data/silver/infrastructure/im3-2026.02.09-lifecycle-tranche-2.manifest.json", manifest)
    print(json.dumps(metadata, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

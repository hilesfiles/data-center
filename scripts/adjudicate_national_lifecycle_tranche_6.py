#!/usr/bin/env python3
"""Build the sixth governed national lifecycle-evidence tranche."""

from __future__ import annotations

import adjudicate_national_lifecycle_tranche_2 as builder


builder.DATASET_ID = "im3_lifecycle_national_tranche_6_20260831"
builder.TRANCHE_ID = "trn_lifecycle_national_6_20260831"
builder.NAMESPACE = "national_lifecycle_tranche_6"
builder.PRIOR_QUEUE_PATH = "site/public/data/v1/lifecycle/national-tranche-5-remaining-queue.json"
builder.BASELINE_COVERAGE_PATH = "site/public/data/v1/counties/lifecycle-national-tranche-5-coverage.json"
builder.SOURCE_CONFIG_PATH = "config/v1/national-lifecycle-tranche-6-evidence-sources.json"
builder.ADJUDICATION_CONFIG_PATH = "config/v1/national-lifecycle-tranche-6-adjudications.json"
builder.EXPECTED_RANKS = set(range(41, 49))
builder.EXPECTED_RANK_LABEL = "forty-one through forty-eight"
builder.INPUT_DATASET_ID = "im3_lifecycle_national_tranche_5_20260831"
builder.OUTPUT_TRANCHE_NUMBER = "6"
builder.EXTRACTOR_VERSION = "national-lifecycle-tranche-6-v1"
builder.METADATA_NOTICES = [
    "National initial-tranche ranks forty-one through forty-eight are reviewed: five resolve operational, one resolves closed, and two remain unresolved.",
    "Closed describes the former Flexential operation at 744 Roble Road, not the continued existence or future reuse of the building.",
    "The Comcast and Verizon source labels lack policy-compliant evidence that maps current data-center operation to the selected footprints.",
    "The balanced 48-facility initial national tranche is complete; no facility remains queued.",
]


if __name__ == "__main__":
    raise SystemExit(builder.main())

#!/usr/bin/env python3
"""Build the fourth governed national lifecycle-evidence tranche."""

from __future__ import annotations

import adjudicate_national_lifecycle_tranche_2 as builder


builder.DATASET_ID = "im3_lifecycle_national_tranche_4_20260831"
builder.TRANCHE_ID = "trn_lifecycle_national_4_20260831"
builder.NAMESPACE = "national_lifecycle_tranche_4"
builder.PRIOR_QUEUE_PATH = "site/public/data/v1/lifecycle/national-tranche-3-remaining-queue.json"
builder.BASELINE_COVERAGE_PATH = "site/public/data/v1/counties/lifecycle-national-tranche-3-coverage.json"
builder.SOURCE_CONFIG_PATH = "config/v1/national-lifecycle-tranche-4-evidence-sources.json"
builder.ADJUDICATION_CONFIG_PATH = "config/v1/national-lifecycle-tranche-4-adjudications.json"
builder.EXPECTED_RANKS = set(range(25, 33))
builder.EXPECTED_RANK_LABEL = "twenty-five through thirty-two"
builder.INPUT_DATASET_ID = "im3_lifecycle_national_tranche_3_20260831"
builder.OUTPUT_TRANCHE_NUMBER = "4"
builder.EXTRACTOR_VERSION = "national-lifecycle-tranche-4-v1"
builder.METADATA_NOTICES = [
    "National initial-tranche ranks twenty-five through thirty-two are reviewed: five resolve operational and three remain unresolved.",
    "Lumen Norristown and CyrusOne CIN3 lack a current policy-compliant exact-building operator or official lifecycle record.",
    "QTS DAL10 remains unresolved because current evidence identifies the six-building Irving campus but not the mapped building.",
    "Sixteen facilities remain queued in the balanced initial national tranche.",
]


if __name__ == "__main__":
    raise SystemExit(builder.main())

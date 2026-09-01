#!/usr/bin/env python3
"""Build the fifth governed national lifecycle-evidence tranche."""

from __future__ import annotations

import adjudicate_national_lifecycle_tranche_2 as builder


builder.DATASET_ID = "im3_lifecycle_national_tranche_5_20260831"
builder.TRANCHE_ID = "trn_lifecycle_national_5_20260831"
builder.NAMESPACE = "national_lifecycle_tranche_5"
builder.PRIOR_QUEUE_PATH = "site/public/data/v1/lifecycle/national-tranche-4-remaining-queue.json"
builder.BASELINE_COVERAGE_PATH = "site/public/data/v1/counties/lifecycle-national-tranche-4-coverage.json"
builder.SOURCE_CONFIG_PATH = "config/v1/national-lifecycle-tranche-5-evidence-sources.json"
builder.ADJUDICATION_CONFIG_PATH = "config/v1/national-lifecycle-tranche-5-adjudications.json"
builder.EXPECTED_RANKS = set(range(33, 41))
builder.EXPECTED_RANK_LABEL = "thirty-three through forty"
builder.INPUT_DATASET_ID = "im3_lifecycle_national_tranche_4_20260831"
builder.OUTPUT_TRANCHE_NUMBER = "5"
builder.EXTRACTOR_VERSION = "national-lifecycle-tranche-5-v1"
builder.METADATA_NOTICES = [
    "National initial-tranche ranks thirty-three through forty are reviewed: five resolve operational, two remain unresolved, and one is disputed.",
    "Google Papillion and the Union Pacific Jack Koraleski center lack policy-compliant exact-building evidence.",
    "The mapped Microsoft Data Center 1 point conflicts with Prince William County's exact-coordinate Corscale GCDC1 record.",
    "Eight facilities remain queued in the balanced initial national tranche.",
]


if __name__ == "__main__":
    raise SystemExit(builder.main())

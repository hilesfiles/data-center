#!/usr/bin/env python3
"""Build the third governed national lifecycle-evidence tranche."""

from __future__ import annotations

import adjudicate_national_lifecycle_tranche_2 as builder


builder.DATASET_ID = "im3_lifecycle_national_tranche_3_20260831"
builder.TRANCHE_ID = "trn_lifecycle_national_3_20260831"
builder.NAMESPACE = "national_lifecycle_tranche_3"
builder.PRIOR_QUEUE_PATH = "site/public/data/v1/lifecycle/national-tranche-2-remaining-queue.json"
builder.BASELINE_COVERAGE_PATH = "site/public/data/v1/counties/lifecycle-national-tranche-2-coverage.json"
builder.SOURCE_CONFIG_PATH = "config/v1/national-lifecycle-tranche-3-evidence-sources.json"
builder.ADJUDICATION_CONFIG_PATH = "config/v1/national-lifecycle-tranche-3-adjudications.json"
builder.EXPECTED_RANKS = set(range(17, 25))
builder.EXPECTED_RANK_LABEL = "seventeen through twenty-four"
builder.INPUT_DATASET_ID = "im3_lifecycle_national_tranche_2_20260831"
builder.OUTPUT_TRANCHE_NUMBER = "3"
builder.EXTRACTOR_VERSION = "national-lifecycle-tranche-3-v1"
builder.METADATA_NOTICES = [
    "National initial-tranche ranks seventeen through twenty-four are reviewed: seven resolve operational and one remains unresolved.",
    "SAP's current Colorado Springs market record does not independently map the COS02 code to the mapped building.",
    "Oxford Networks and DataSite Atlanta are retained as historical seed labels; FirstLight and CoreSite publish the current facility records.",
    "Twenty-four facilities remain queued in the balanced initial national tranche.",
]


if __name__ == "__main__":
    raise SystemExit(builder.main())

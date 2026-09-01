#!/usr/bin/env python3
"""Acquire the BLS 2025 annual QCEW county baseline as governed JSON.

The official annual-by-area ZIP and its CSV members are temporary transport
inputs. The adapter pins the final 2025 archive published with the August 2026
QCEW update, extracts total-covered and private-construction county rows, joins
them to the Census 2025 county reference, and writes durable JSON only.
"""

from __future__ import annotations

import csv
import hashlib
import io
import json
import re
import tempfile
import zipfile
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

from acquire_census_counties import write_json


ROOT = Path(__file__).resolve().parents[1]
PARSER_VERSION = "bls-qcew-county-baseline-v1"
RELEASE_DATE = "2026-08-28"
DATA_YEAR = 2025
ARTIFACT_VERSION = "2025.1"
SOURCE_ID = "src_bls_qcew_annual_by_area_2025"
ARCHIVE_URL = "https://data.bls.gov/cew/data/files/2025/csv/2025_annual_by_area.zip"
EXPECTED_SHA256 = "b2f6ed3b854af15bea207c1ef5ab8f1c22ee5b7abf79687505292beb44585921"
EXPECTED_BYTES = 114_997_862

ROW_SPECS = {
    "total_covered": {
        "own_code": "0",
        "industry_code": "10",
        "agglvl_code": "70",
        "description": "Total covered employment, all industries",
    },
    "private_construction": {
        "own_code": "5",
        "industry_code": "23",
        "agglvl_code": "74",
        "description": "Private construction",
    },
}

METRICS = {
    "annual_avg_covered_employment": {
        "metric_code": "economic.employment.total",
        "row": "total_covered",
        "field": "annual_avg_emplvl",
        "value_type": "number",
        "unit": None,
    },
    "annual_avg_establishments": {
        "metric_code": "economic.establishments.total",
        "row": "total_covered",
        "field": "annual_avg_estabs_count",
        "value_type": "number",
        "unit": None,
    },
    "total_annual_wages_nominal_usd": {
        "metric_code": "economic.wages.total.nominal",
        "row": "total_covered",
        "field": "total_annual_wages",
        "value_type": "quantity",
        "unit": "USD",
    },
    "annual_avg_weekly_wage_nominal_usd": {
        "metric_code": "economic.wages.average_weekly.nominal",
        "row": "total_covered",
        "field": "annual_avg_wkly_wage",
        "value_type": "quantity",
        "unit": "USD_per_week",
    },
    "private_construction_annual_avg_employment": {
        "metric_code": "economic.employment.construction.private",
        "row": "private_construction",
        "field": "annual_avg_emplvl",
        "value_type": "number",
        "unit": None,
    },
}


def stable_id(prefix: str, *parts: str) -> str:
    value = hashlib.sha256("\x1f".join(parts).encode("utf-8")).hexdigest()[:20]
    return f"{prefix}_{value}"


def digest(payload: bytes) -> str:
    return hashlib.sha256(payload).hexdigest()


def load_counties() -> dict[str, dict[str, Any]]:
    path = ROOT / "site" / "public" / "data" / "v1" / "maps" / "counties.geojson"
    document = json.loads(path.read_text(encoding="utf-8"))
    counties = {
        feature["properties"]["county_fips"]: feature["properties"]
        for feature in document.get("features", [])
    }
    if len(counties) != 3144:
        raise RuntimeError(f"Expected 3,144 Census counties; found {len(counties)}")
    return counties


def download_archive(temporary_directory: Path) -> tuple[Path, dict[str, Any]]:
    request = Request(
        ARCHIVE_URL,
        headers={"User-Agent": "DCCIO-QCEW-adapter/1.0 (+https://github.com/hilesfiles/data-center)"},
    )
    target = temporary_directory / "2025_annual_by_area.zip"
    hasher = hashlib.sha256()
    byte_size = 0
    try:
        with urlopen(request, timeout=180) as response, target.open("wb") as output:
            while chunk := response.read(1024 * 1024):
                output.write(chunk)
                hasher.update(chunk)
                byte_size += len(chunk)
            metadata = {
                "http_status": response.status,
                "etag": response.headers.get("ETag"),
                "last_modified": response.headers.get("Last-Modified"),
                "sha256": hasher.hexdigest(),
                "byte_size": byte_size,
            }
    except (HTTPError, URLError, TimeoutError) as exc:
        raise RuntimeError(f"BLS QCEW download failed: {exc}") from exc

    if metadata["sha256"] != EXPECTED_SHA256 or byte_size != EXPECTED_BYTES:
        raise RuntimeError(
            "BLS QCEW archive no longer matches the pinned final 2025 release; "
            "review the upstream revision before ingesting it"
        )
    return target, metadata


def parse_integer(raw_value: str, *, fips: str, field: str) -> int | None:
    value = raw_value.strip().replace(",", "")
    if value == "":
        return None
    try:
        return int(value)
    except ValueError as exc:
        raise RuntimeError(f"Invalid QCEW value {raw_value!r} for county {fips} field {field}") from exc


def summarize_row(row: dict[str, str], fips: str) -> dict[str, Any]:
    disclosure_code = (row.get("disclosure_code") or "").strip()
    suppressed = disclosure_code == "N"
    metrics: dict[str, dict[str, Any]] = {}
    for field in {
        "annual_avg_estabs_count",
        "annual_avg_emplvl",
        "total_annual_wages",
        "annual_avg_wkly_wage",
        "avg_annual_pay",
    }:
        raw_value = (row.get(field) or "").strip()
        metrics[field] = {
            "raw_value": raw_value,
            "value": None if suppressed else parse_integer(raw_value, fips=fips, field=field),
            "value_status": "suppressed" if suppressed else "observed",
        }
    return {
        "area_fips": (row.get("area_fips") or "").strip(),
        "area_title": (row.get("area_title") or "").strip(),
        "own_code": (row.get("own_code") or "").strip(),
        "own_title": (row.get("own_title") or "").strip(),
        "industry_code": (row.get("industry_code") or "").strip(),
        "industry_title": (row.get("industry_title") or "").strip(),
        "agglvl_code": (row.get("agglvl_code") or "").strip(),
        "size_code": (row.get("size_code") or "").strip(),
        "disclosure_code": disclosure_code,
        "metrics": metrics,
    }


def parse_archive(
    archive_path: Path,
    county_fips: set[str],
) -> tuple[dict[str, dict[str, Any]], dict[str, Any]]:
    values: dict[str, dict[str, Any]] = {fips: {} for fips in county_fips}
    member_pattern = re.compile(r"^2025\.annual\.by_area/2025\.annual (\d{5}) .+\.csv$")
    matched_members: dict[str, str] = {}
    ignored_geographies: set[str] = set()

    with zipfile.ZipFile(archive_path) as archive:
        for name in archive.namelist():
            match = member_pattern.match(name)
            if not match:
                continue
            fips = match.group(1)
            if fips not in county_fips:
                ignored_geographies.add(fips)
                continue
            if fips in matched_members:
                raise RuntimeError(f"Duplicate QCEW area member for county {fips}")
            matched_members[fips] = name

        for fips, member_name in sorted(matched_members.items()):
            with archive.open(member_name) as binary_stream:
                reader = csv.DictReader(io.TextIOWrapper(binary_stream, encoding="utf-8-sig", newline=""))
                found: dict[str, dict[str, Any]] = {}
                for row in reader:
                    if (row.get("year") or "").strip() != str(DATA_YEAR) or (row.get("qtr") or "").strip() != "A":
                        continue
                    for row_name, spec in ROW_SPECS.items():
                        if (
                            (row.get("own_code") or "").strip() == spec["own_code"]
                            and (row.get("industry_code") or "").strip() == spec["industry_code"]
                            and (row.get("agglvl_code") or "").strip() == spec["agglvl_code"]
                            and (row.get("size_code") or "").strip() == "0"
                        ):
                            if row_name in found:
                                raise RuntimeError(f"Duplicate QCEW {row_name} row for county {fips}")
                            found[row_name] = summarize_row(row, fips)
                values[fips] = found

    total_present = sum("total_covered" in record for record in values.values())
    construction_present = sum("private_construction" in record for record in values.values())
    construction_suppressed = sum(
        record.get("private_construction", {}).get("disclosure_code") == "N"
        for record in values.values()
    )
    if total_present < 3000:
        raise RuntimeError(f"QCEW total-covered county coverage is unexpectedly low: {total_present}")
    return values, {
        "archive_member_count": len(matched_members),
        "matched_county_count": len(matched_members),
        "unmatched_county_count": len(county_fips - set(matched_members)),
        "unmatched_county_sample": sorted(county_fips - set(matched_members))[:20],
        "total_covered_row_count": total_present,
        "private_construction_row_count": construction_present,
        "private_construction_suppressed_count": construction_suppressed,
        "ignored_geography_count": len(ignored_geographies),
        "ignored_geography_sample": sorted(ignored_geographies)[:20],
    }


def source_record(generated_at: str) -> dict[str, Any]:
    return {
        "schema_version": "1.0.0",
        "source_id": SOURCE_ID,
        "source_type": "federal_dataset",
        "publisher": "U.S. Bureau of Labor Statistics",
        "agency": "U.S. Bureau of Labor Statistics",
        "jurisdiction": "United States",
        "title": "Quarterly Census of Employment and Wages: 2025 annual averages by area",
        "url": ARCHIVE_URL,
        "publication_date": {"date": RELEASE_DATE, "precision": "day"},
        "language": "en",
        "license": "U.S. government data",
        "copyright_policy": "redistributable",
        "source_quality_prior": 1.0,
        "created_at": generated_at,
        "updated_at": generated_at,
        "record_status": "active",
    }


def build() -> dict[str, Any]:
    generated_at = datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")
    counties = load_counties()

    with tempfile.TemporaryDirectory(prefix="dccio-qcew-") as temporary:
        archive_path, download = download_archive(Path(temporary))
        parsed, parse_report = parse_archive(archive_path, set(counties))

    acquisition = {
        "schema_version": "1.0.0",
        "manifest_id": "acq_bls_qcew_annual_by_area_2025",
        "source_id": SOURCE_ID,
        "source_url": ARCHIVE_URL,
        "request_url": ARCHIVE_URL,
        "retrieved_at": generated_at,
        "http_status": download["http_status"],
        "sha256": download["sha256"],
        "license": "U.S. government data",
        "parser_version": PARSER_VERSION,
        "attempt": 1,
        "created_at": generated_at,
        "updated_at": generated_at,
        "record_status": "active",
    }
    if download.get("etag"):
        acquisition["etag"] = download["etag"]
    if download.get("last_modified"):
        acquisition["last_modified"] = download["last_modified"]
    write_json(
        ROOT / "data" / "raw" / "bls-qcew" / "2025-annual-by-area.acquisition.json",
        acquisition,
    )

    bronze_records: list[dict[str, Any]] = []
    observations: list[dict[str, Any]] = []
    public_records: list[dict[str, Any]] = []
    missing_value_count = 0
    suppressed_value_count = 0

    for fips, county in sorted(counties.items()):
        source_rows = parsed[fips]
        bronze_records.append(
            {
                "schema_version": "1.0.0",
                "county_fips": fips,
                "county_name": county["county_name"],
                "state_abbr": county["state_abbr"],
                "year": DATA_YEAR,
                "source_rows": source_rows,
                "created_at": generated_at,
                "updated_at": generated_at,
                "record_status": "active",
            }
        )

        normalized: dict[str, int | None] = {}
        for public_field, metric in METRICS.items():
            source_row = source_rows.get(metric["row"])
            metric_value = None
            value_status = "not_available"
            missingness_reason = "not_available"
            if source_row:
                field_value = source_row["metrics"][metric["field"]]
                metric_value = field_value["value"]
                if field_value["value_status"] == "suppressed":
                    value_status = "suppressed"
                    missingness_reason = "suppressed"
                    suppressed_value_count += 1
                elif metric_value is not None:
                    value_status = "observed"
                    missingness_reason = ""
            normalized[public_field] = metric_value
            observation = {
                "schema_version": "1.0.0",
                "observation_id": stable_id("obs", "bls-qcew", fips, str(DATA_YEAR), metric["metric_code"]),
                "metric_code": metric["metric_code"],
                "subject": {"subject_type": "county", "subject_id": fips},
                "period": {"year": DATA_YEAR, "precision": "year"},
                "value_status": value_status,
                "source_ids": [SOURCE_ID],
                "release_vintage": RELEASE_DATE,
                "revision_number": 0,
                "created_at": generated_at,
                "updated_at": generated_at,
                "record_status": "active",
            }
            if metric_value is None:
                observation["missingness_reason"] = missingness_reason
                missing_value_count += 1
            elif metric["value_type"] == "number":
                observation["value"] = {"type": "number", "value": metric_value}
            else:
                observation["value"] = {
                    "type": "quantity",
                    "value": metric_value,
                    "unit": metric["unit"],
                }
            observations.append(observation)

        populated = sum(value is not None for value in normalized.values())
        public_records.append(
            {
                "schema_version": "1.0.0",
                "county_fips": fips,
                "county_name": county["county_name"],
                "state_abbr": county["state_abbr"],
                "year": DATA_YEAR,
                **normalized,
                "coverage_status": (
                    "complete"
                    if populated == len(METRICS)
                    else "unavailable"
                    if populated == 0
                    else "partial"
                ),
                "source_ids": [SOURCE_ID],
                "release_vintage": RELEASE_DATE,
                "generated_at": generated_at,
            }
        )

    bronze_document = {
        "schema_version": "1.0.0",
        "artifact_type": "bls_qcew_county_source_rows",
        "artifact_version": ARTIFACT_VERSION,
        "generated_at": generated_at,
        "data_vintage": str(DATA_YEAR),
        "record_count": len(bronze_records),
        "records": bronze_records,
    }
    bronze_path = ROOT / "data" / "bronze" / "economic" / "bls-qcew-county-2025-source-rows.json"
    bronze_payload = write_json(bronze_path, bronze_document, compact=True)

    sources = [source_record(generated_at)]
    silver_document = {
        "schema_version": "1.0.0",
        "artifact_type": "bls_qcew_county_baseline",
        "artifact_version": ARTIFACT_VERSION,
        "generated_at": generated_at,
        "data_vintage": str(DATA_YEAR),
        "record_count": len(sources) + len(observations),
        "collections": {"source": sources, "observation": observations},
    }
    silver_path = ROOT / "data" / "silver" / "economic" / "bls-qcew-county-2025.json"
    silver_payload = write_json(silver_path, silver_document, compact=True)

    public_path = ROOT / "site" / "public" / "data" / "v1" / "counties" / "employment-wages-baseline-2025.json"
    public_payload = write_json(public_path, public_records, compact=True)

    coverage_counts = {
        status: sum(record["coverage_status"] == status for record in public_records)
        for status in ("complete", "partial", "unavailable")
    }
    report = {
        "schema_version": "1.0.0",
        "artifact_type": "bls_qcew_county_baseline_processing_report",
        "artifact_version": ARTIFACT_VERSION,
        "generated_at": generated_at,
        "data_vintage": str(DATA_YEAR),
        "county_count": len(public_records),
        "source_count": len(sources),
        "observation_count": len(observations),
        "metric_count": len(METRICS),
        "missing_value_count": missing_value_count,
        "suppressed_value_count": suppressed_value_count,
        "coverage_counts": coverage_counts,
        "archive_parse_report": parse_report,
        "notices": [
            "Employment is the annual average of monthly QCEW covered employment levels.",
            "Establishments are the annual average of quarterly QCEW establishment counts.",
            "Total annual wages and average weekly wages are current-dollar measures and are explicitly labeled nominal.",
            "Construction employment is private-sector NAICS 23 employment because QCEW does not publish an all-ownership county-industry aggregate.",
            "Disclosure-coded cells are retained as suppressed and are never displayed as zero.",
            "The BLS ZIP and CSV files are temporary transport inputs; durable outputs are JSON only.",
        ],
    }
    report_path = ROOT / "data" / "silver" / "economic" / "bls-qcew-county-2025.processing-report.json"
    report_payload = write_json(report_path, report)

    parts = []
    for path, payload, count, zone, projection in [
        (bronze_path, bronze_payload, len(bronze_records), "bronze", "source_rows"),
        (silver_path, silver_payload, len(sources) + len(observations), "silver", "observations"),
        (public_path, public_payload, len(public_records), "public", "county_baseline"),
        (report_path, report_payload, 1, "silver", "processing_report"),
    ]:
        parts.append(
            {
                "path": path.relative_to(ROOT).as_posix(),
                "sha256": digest(payload),
                "byte_size": len(payload),
                "record_count": count,
                "partition_values": {"zone": zone, "projection": projection},
            }
        )

    dataset_manifest = {
        "schema_version": "1.0.0",
        "dataset_id": "bls_qcew_county_baseline_2025",
        "artifact_type": "county_employment_wages_baseline",
        "artifact_version": ARTIFACT_VERSION,
        "generated_at": generated_at,
        "data_vintage": str(DATA_YEAR),
        "record_schema": "https://dccio.org/schemas/v1/public-county-employment-wages-baseline.schema.json",
        "format": "json",
        "parts": parts,
        "record_count": sum(part["record_count"] for part in parts),
        "input_dataset_ids": ["geo_counties_2025_5m"],
        "license_metadata": {
            "license": "U.S. government data",
            "redistribution_status": "allowed",
            "attribution": "Source: U.S. Bureau of Labor Statistics, Quarterly Census of Employment and Wages",
        },
    }
    write_json(
        ROOT / "data" / "silver" / "economic" / "bls-qcew-county-2025.manifest.json",
        dataset_manifest,
    )
    return report


def main() -> int:
    print(json.dumps(build(), indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

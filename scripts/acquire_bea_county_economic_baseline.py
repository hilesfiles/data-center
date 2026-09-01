#!/usr/bin/env python3
"""Acquire the BEA 2024 county economic baseline as governed JSON.

The BEA ZIP and CSV files are temporary transport inputs. The adapter pins the
February 5, 2026 release, extracts the latest county values from CAGDP1 and
CAINC1, joins them to the published Census 2025 county reference, and writes
only JSON artifacts for durable storage and GitHub Pages.
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
PARSER_VERSION = "bea-county-economic-baseline-v1"
RELEASE_DATE = "2026-02-05"
DATA_YEAR = 2024
ARTIFACT_VERSION = "2024.1"

TABLES = {
    "CAGDP1": {
        "url": "https://apps.bea.gov/regional/zip/CAGDP1.zip",
        "expected_sha256": "95b49283df20772ded04ea53e1142955b8ade5e7f93047c0a3dfaf403b166fe1",
        "expected_bytes": 1_928_241,
        "source_id": "src_bea_cagdp1_2024",
        "line_codes": {"1": "real_gdp_thousands_chained_2017_usd"},
    },
    "CAINC1": {
        "url": "https://apps.bea.gov/regional/zip/CAINC1.zip",
        "expected_sha256": "e1465c8b0e7e75f541241fe2fa64364b784dd6d2223901f9d576c4c5d49480b5",
        "expected_bytes": 3_467_441,
        "source_id": "src_bea_cainc1_2024",
        "line_codes": {
            "1": "personal_income_thousands_current_usd",
            "2": "population_persons",
            "3": "per_capita_personal_income_current_usd",
        },
    },
}

METRICS = {
    "real_gdp_thousands_chained_2017_usd": {
        "metric_code": "economic.gdp.real",
        "value_type": "quantity",
        "unit": "USD",
        "multiplier": 1000,
        "source_id": "src_bea_cagdp1_2024",
    },
    "personal_income_thousands_current_usd": {
        "metric_code": "economic.personal_income.nominal",
        "value_type": "quantity",
        "unit": "USD",
        "multiplier": 1000,
        "source_id": "src_bea_cainc1_2024",
    },
    "population_persons": {
        "metric_code": "demographic.population",
        "value_type": "number",
        "unit": None,
        "multiplier": 1,
        "source_id": "src_bea_cainc1_2024",
    },
    "per_capita_personal_income_current_usd": {
        "metric_code": "economic.personal_income.per_capita.nominal",
        "value_type": "quantity",
        "unit": "USD_per_person",
        "multiplier": 1,
        "source_id": "src_bea_cainc1_2024",
    },
}


def stable_id(prefix: str, *parts: str) -> str:
    digest = hashlib.sha256("\x1f".join(parts).encode("utf-8")).hexdigest()[:20]
    return f"{prefix}_{digest}"


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


def download_table(table_name: str, temporary_directory: Path) -> tuple[Path, dict[str, Any]]:
    spec = TABLES[table_name]
    request = Request(
        spec["url"],
        headers={"User-Agent": "DCCIO-BEA-adapter/1.0 (+https://github.com/hilesfiles/data-center)"},
    )
    target = temporary_directory / f"{table_name}.zip"
    hasher = hashlib.sha256()
    byte_size = 0
    try:
        with urlopen(request, timeout=120) as response, target.open("wb") as output:
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
        raise RuntimeError(f"BEA {table_name} download failed: {exc}") from exc

    if metadata["sha256"] != spec["expected_sha256"] or byte_size != spec["expected_bytes"]:
        raise RuntimeError(
            f"BEA {table_name} no longer matches the pinned February 5, 2026 release; "
            "review the upstream revision before ingesting it"
        )
    return target, metadata


def parse_integer(raw_value: str, *, table_name: str, fips: str, line_code: str) -> int | None:
    value = raw_value.strip().replace(",", "")
    if value in {"", "(NA)", "(D)", "(L)"}:
        return None
    try:
        return int(value)
    except ValueError as exc:
        raise RuntimeError(
            f"Invalid BEA value {raw_value!r} in {table_name} county {fips} line {line_code}"
        ) from exc


def parse_table(
    table_name: str,
    archive_path: Path,
    county_fips: set[str],
) -> tuple[dict[str, dict[str, Any]], dict[str, Any]]:
    spec = TABLES[table_name]
    line_codes = spec["line_codes"]
    values: dict[str, dict[str, Any]] = {fips: {} for fips in county_fips}
    ignored_geographies: set[str] = set()
    member_name = ""

    with zipfile.ZipFile(archive_path) as archive:
        candidates = [
            name
            for name in archive.namelist()
            if name.startswith(f"{table_name}__ALL_AREAS_") and name.endswith(".csv")
        ]
        if len(candidates) != 1:
            raise RuntimeError(f"Expected one all-areas CSV in {table_name}; found {candidates}")
        member_name = candidates[0]
        with archive.open(member_name) as binary_stream:
            reader = csv.DictReader(io.TextIOWrapper(binary_stream, encoding="cp1252", newline=""))
            if str(DATA_YEAR) not in (reader.fieldnames or []):
                raise RuntimeError(f"BEA {table_name} does not contain data year {DATA_YEAR}")
            for row in reader:
                fips = (row.get("GeoFIPS") or "").strip().strip('"')
                line_code = (row.get("LineCode") or "").strip()
                if line_code not in line_codes or re.fullmatch(r"\d{5}", fips) is None:
                    continue
                if fips not in county_fips:
                    ignored_geographies.add(fips)
                    continue
                field = line_codes[line_code]
                if field in values[fips]:
                    raise RuntimeError(f"Duplicate BEA {table_name} county {fips} line {line_code}")
                raw_value = row.get(str(DATA_YEAR), "")
                values[fips][field] = {
                    "raw_value": raw_value.strip(),
                    "value": parse_integer(raw_value, table_name=table_name, fips=fips, line_code=line_code),
                    "geo_name": (row.get("GeoName") or "").strip(),
                    "description": (row.get("Description") or "").strip(),
                    "unit": (row.get("Unit") or "").strip(),
                    "line_code": int(line_code),
                }

    expected_fields = set(line_codes.values())
    incomplete = {
        fips: sorted(expected_fields - set(record))
        for fips, record in values.items()
        if set(record) != expected_fields
    }
    complete_count = len(values) - len(incomplete)
    if complete_count < 3000:
        sample = dict(list(sorted(incomplete.items()))[:10])
        raise RuntimeError(
            f"BEA {table_name} county coverage is unexpectedly low ({complete_count}): {sample}"
        )
    return values, {
        "member_name": member_name,
        "matched_county_count": complete_count,
        "unmatched_county_count": len(incomplete),
        "unmatched_county_sample": sorted(incomplete)[:20],
        "ignored_geography_count": len(ignored_geographies),
        "ignored_geography_sample": sorted(ignored_geographies)[:20],
    }


def source_records(generated_at: str) -> list[dict[str, Any]]:
    return [
        {
            "schema_version": "1.0.0",
            "source_id": "src_bea_cagdp1_2024",
            "source_type": "federal_dataset",
            "publisher": "U.S. Bureau of Economic Analysis",
            "agency": "U.S. Bureau of Economic Analysis",
            "jurisdiction": "United States",
            "title": "CAGDP1 County GDP Summary",
            "url": TABLES["CAGDP1"]["url"],
            "publication_date": {"date": RELEASE_DATE, "precision": "day"},
            "language": "en",
            "license": "U.S. government data",
            "copyright_policy": "redistributable",
            "source_quality_prior": 1.0,
            "created_at": generated_at,
            "updated_at": generated_at,
            "record_status": "active",
        },
        {
            "schema_version": "1.0.0",
            "source_id": "src_bea_cainc1_2024",
            "source_type": "federal_dataset",
            "publisher": "U.S. Bureau of Economic Analysis",
            "agency": "U.S. Bureau of Economic Analysis",
            "jurisdiction": "United States",
            "title": "CAINC1 County Personal Income Summary",
            "url": TABLES["CAINC1"]["url"],
            "publication_date": {"date": RELEASE_DATE, "precision": "day"},
            "language": "en",
            "license": "U.S. government data",
            "copyright_policy": "redistributable",
            "source_quality_prior": 1.0,
            "created_at": generated_at,
            "updated_at": generated_at,
            "record_status": "active",
        },
    ]


def build() -> dict[str, Any]:
    generated_at = datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")
    counties = load_counties()
    downloads: dict[str, dict[str, Any]] = {}
    parsed: dict[str, dict[str, dict[str, Any]]] = {}
    parse_reports: dict[str, dict[str, Any]] = {}

    with tempfile.TemporaryDirectory(prefix="dccio-bea-") as temporary:
        temporary_directory = Path(temporary)
        for table_name in TABLES:
            archive_path, downloads[table_name] = download_table(table_name, temporary_directory)
            parsed[table_name], parse_reports[table_name] = parse_table(
                table_name, archive_path, set(counties)
            )

    acquisitions = []
    for table_name, spec in TABLES.items():
        download = downloads[table_name]
        manifest = {
            "schema_version": "1.0.0",
            "manifest_id": f"acq_bea_{table_name.lower()}_2024",
            "source_id": spec["source_id"],
            "source_url": spec["url"],
            "request_url": spec["url"],
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
            manifest["etag"] = download["etag"]
        if download.get("last_modified"):
            manifest["last_modified"] = download["last_modified"]
        acquisitions.append(manifest)
        write_json(
            ROOT / "data" / "raw" / "bea-regional" / f"2024-{table_name.lower()}.acquisition.json",
            manifest,
        )

    bronze_records: list[dict[str, Any]] = []
    observations: list[dict[str, Any]] = []
    public_records: list[dict[str, Any]] = []
    missing_value_count = 0

    for fips, county in sorted(counties.items()):
        source_fields = {
            **parsed["CAGDP1"][fips],
            **parsed["CAINC1"][fips],
        }
        bronze = {
            "schema_version": "1.0.0",
            "county_fips": fips,
            "county_name": county["county_name"],
            "state_abbr": county["state_abbr"],
            "year": DATA_YEAR,
            "source_values": source_fields,
            "created_at": generated_at,
            "updated_at": generated_at,
            "record_status": "active",
        }
        bronze_records.append(bronze)

        normalized: dict[str, int | None] = {}
        for source_field, metric in METRICS.items():
            source_value = source_fields.get(source_field, {}).get("value")
            normalized_value = None if source_value is None else source_value * metric["multiplier"]
            normalized[metric["metric_code"]] = normalized_value
            observation = {
                "schema_version": "1.0.0",
                "observation_id": stable_id("obs", "bea", fips, str(DATA_YEAR), metric["metric_code"]),
                "metric_code": metric["metric_code"],
                "subject": {"subject_type": "county", "subject_id": fips},
                "period": {"year": DATA_YEAR, "precision": "year"},
                "value_status": "observed" if normalized_value is not None else "not_available",
                "source_ids": [metric["source_id"]],
                "release_vintage": RELEASE_DATE,
                "revision_number": 0,
                "created_at": generated_at,
                "updated_at": generated_at,
                "record_status": "active",
            }
            if normalized_value is None:
                observation["missingness_reason"] = "not_available"
                missing_value_count += 1
            elif metric["value_type"] == "number":
                observation["value"] = {"type": "number", "value": normalized_value}
            else:
                observation["value"] = {
                    "type": "quantity",
                    "value": normalized_value,
                    "unit": metric["unit"],
                }
            observations.append(observation)

        values = [value for value in normalized.values() if value is not None]
        public_records.append(
            {
                "schema_version": "1.0.0",
                "county_fips": fips,
                "county_name": county["county_name"],
                "state_abbr": county["state_abbr"],
                "year": DATA_YEAR,
                "real_gdp_usd": normalized["economic.gdp.real"],
                "personal_income_nominal_usd": normalized["economic.personal_income.nominal"],
                "population": normalized["demographic.population"],
                "per_capita_personal_income_nominal_usd": normalized[
                    "economic.personal_income.per_capita.nominal"
                ],
                "coverage_status": (
                    "complete"
                    if len(values) == len(METRICS)
                    else "unavailable"
                    if not values
                    else "partial"
                ),
                "source_ids": ["src_bea_cagdp1_2024", "src_bea_cainc1_2024"],
                "release_vintage": RELEASE_DATE,
                "generated_at": generated_at,
            }
        )

    bronze_document = {
        "schema_version": "1.0.0",
        "artifact_type": "bea_county_economic_source_rows",
        "artifact_version": ARTIFACT_VERSION,
        "generated_at": generated_at,
        "data_vintage": str(DATA_YEAR),
        "record_count": len(bronze_records),
        "records": bronze_records,
    }
    bronze_path = ROOT / "data" / "bronze" / "economic" / "bea-county-2024-source-rows.json"
    bronze_payload = write_json(bronze_path, bronze_document, compact=True)

    sources = source_records(generated_at)
    silver_document = {
        "schema_version": "1.0.0",
        "artifact_type": "bea_county_economic_baseline",
        "artifact_version": ARTIFACT_VERSION,
        "generated_at": generated_at,
        "data_vintage": str(DATA_YEAR),
        "record_count": len(sources) + len(observations),
        "collections": {"source": sources, "observation": observations},
    }
    silver_path = ROOT / "data" / "silver" / "economic" / "bea-county-2024.json"
    silver_payload = write_json(silver_path, silver_document, compact=True)

    public_path = ROOT / "site" / "public" / "data" / "v1" / "counties" / "economic-baseline-2024.json"
    public_payload = write_json(public_path, public_records, compact=True)

    report = {
        "schema_version": "1.0.0",
        "artifact_type": "bea_county_economic_baseline_processing_report",
        "artifact_version": ARTIFACT_VERSION,
        "generated_at": generated_at,
        "data_vintage": str(DATA_YEAR),
        "county_count": len(public_records),
        "source_count": len(sources),
        "observation_count": len(observations),
        "metric_count": len(METRICS),
        "missing_value_count": missing_value_count,
        "complete_county_count": sum(record["coverage_status"] == "complete" for record in public_records),
        "table_parse_reports": parse_reports,
        "notices": [
            "Real GDP is normalized from thousands of chained 2017 dollars to chained 2017 dollars.",
            "Personal income and per-capita personal income are current-dollar measures and are explicitly labeled nominal.",
            "The BEA ZIP and CSV files are temporary transport inputs; durable outputs are JSON only.",
        ],
    }
    report_path = ROOT / "data" / "silver" / "economic" / "bea-county-2024.processing-report.json"
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
        "dataset_id": "bea_county_economic_baseline_2024",
        "artifact_type": "county_economic_baseline",
        "artifact_version": ARTIFACT_VERSION,
        "generated_at": generated_at,
        "data_vintage": str(DATA_YEAR),
        "record_schema": "https://dccio.org/schemas/v1/public-county-economic-baseline.schema.json",
        "format": "json",
        "parts": parts,
        "record_count": sum(part["record_count"] for part in parts),
        "input_dataset_ids": ["geo_counties_2025_5m"],
        "license_metadata": {
            "license": "U.S. government data",
            "redistribution_status": "allowed",
            "attribution": "Source: U.S. Bureau of Economic Analysis",
        },
    }
    write_json(
        ROOT / "data" / "silver" / "economic" / "bea-county-2024.manifest.json",
        dataset_manifest,
    )
    return report


def main() -> int:
    print(json.dumps(build(), indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

#!/usr/bin/env python3
"""Build the first governed BEA-BLS county-year panel for 2021-2024.

The panel is deliberately a four-year research scaffold, not a model-ready
sample. Official BEA ZIPs and BLS CSV slices are temporary transport inputs;
all durable artifacts are JSON. Current Census county identities are retained,
and historical source geographies are never allocated or back-cast.
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
PARSER_VERSION = "county-economic-history-panel-v1"
PANEL_NAME = "county-economic-core-2021-2024"
BUILD_VERSION = "2021-2024.1"
YEARS = tuple(range(2021, 2025))

BEA_TABLES = {
    "CAGDP1": {
        "url": "https://apps.bea.gov/regional/zip/CAGDP1.zip",
        "expected_sha256": "95b49283df20772ded04ea53e1142955b8ade5e7f93047c0a3dfaf403b166fe1",
        "expected_bytes": 1_928_241,
        "source_id": "src_bea_cagdp1_2024",
        "line_code": "1",
        "metric_code": "economic.gdp.real",
        "multiplier": 1000,
        "unit": "USD",
    },
    "CAINC1": {
        "url": "https://apps.bea.gov/regional/zip/CAINC1.zip",
        "expected_sha256": "e1465c8b0e7e75f541241fe2fa64364b784dd6d2223901f9d576c4c5d49480b5",
        "expected_bytes": 3_467_441,
        "source_id": "src_bea_cainc1_2024",
        "line_code": "2",
        "metric_code": "demographic.population",
        "multiplier": 1,
        "unit": None,
    },
}

BLS_SLICES = {
    2021: {
        "url": "https://data.bls.gov/cew/data/api/2021/a/industry/10.csv",
        "expected_sha256": "331d81786235e57217ef1498efc64d5e3abf39f1cbca1cf841ea10533920db51",
        "expected_bytes": 3_512_154,
        "release_date": "2022-08-31",
    },
    2022: {
        "url": "https://data.bls.gov/cew/data/api/2022/a/industry/10.csv",
        "expected_sha256": "9a95487df1dd1ded3f2dc712b5d19747e2aacfc30102869cd3a0b985501e739a",
        "expected_bytes": 3_543_500,
        "release_date": "2023-08-31",
    },
    2023: {
        "url": "https://data.bls.gov/cew/data/api/2023/a/industry/10.csv",
        "expected_sha256": "0115a20a201b821d29f731340976aad8fc8dac16cb6a0c13df0f7f52afe108b1",
        "expected_bytes": 3_561_704,
        "release_date": "2024-08-28",
    },
    2024: {
        "url": "https://data.bls.gov/cew/data/api/2024/a/industry/10.csv",
        "expected_sha256": "e73da8f6b2b415180b1910351327faa51183589021357535fd880f8761e12a12",
        "expected_bytes": 3_562_701,
        "release_date": "2025-09-02",
    },
}

METRICS = {
    "real_gdp_usd": {
        "metric_code": "economic.gdp.real",
        "source_family": "bea",
        "value_type": "quantity",
        "unit": "USD",
        "role": "covariate",
    },
    "population": {
        "metric_code": "demographic.population",
        "source_family": "bea",
        "value_type": "number",
        "unit": None,
        "role": "covariate",
    },
    "annual_avg_covered_employment": {
        "metric_code": "economic.employment.total",
        "source_family": "bls",
        "value_type": "number",
        "unit": None,
        "role": "outcome",
    },
    "annual_avg_weekly_wage_nominal_usd": {
        "metric_code": "economic.wages.average_weekly.nominal",
        "source_family": "bls",
        "value_type": "quantity",
        "unit": "USD_per_week",
        "role": "context",
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


def download(
    url: str,
    target: Path,
    expected_sha256: str,
    expected_bytes: int,
) -> dict[str, Any]:
    request = Request(
        url,
        headers={"User-Agent": "DCCIO-panel-adapter/1.0 (+https://github.com/hilesfiles/data-center)"},
    )
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
        raise RuntimeError(f"Download failed for {url}: {exc}") from exc
    if metadata["sha256"] != expected_sha256 or byte_size != expected_bytes:
        raise RuntimeError(f"Pinned source changed at {url}; review the upstream revision before ingesting")
    return metadata


def parse_integer(raw_value: str) -> int | None:
    value = raw_value.strip().replace(",", "")
    if value in {"", "(NA)", "(D)", "(L)"}:
        return None
    return int(value)


def parse_bea(
    table_name: str,
    archive_path: Path,
    county_fips: set[str],
) -> tuple[dict[int, dict[str, dict[str, Any]]], dict[str, Any]]:
    spec = BEA_TABLES[table_name]
    values = {year: {fips: {} for fips in county_fips} for year in YEARS}
    ignored_geographies: set[str] = set()
    with zipfile.ZipFile(archive_path) as archive:
        candidates = [
            name for name in archive.namelist()
            if name.startswith(f"{table_name}__ALL_AREAS_") and name.endswith(".csv")
        ]
        if len(candidates) != 1:
            raise RuntimeError(f"Expected one all-areas CSV in {table_name}; found {candidates}")
        member_name = candidates[0]
        with archive.open(member_name) as binary_stream:
            reader = csv.DictReader(io.TextIOWrapper(binary_stream, encoding="cp1252", newline=""))
            if any(str(year) not in (reader.fieldnames or []) for year in YEARS):
                raise RuntimeError(f"BEA {table_name} does not contain every panel year")
            for row in reader:
                fips = (row.get("GeoFIPS") or "").strip().strip('"')
                if (row.get("LineCode") or "").strip() != spec["line_code"] or re.fullmatch(r"\d{5}", fips) is None:
                    continue
                if fips not in county_fips:
                    ignored_geographies.add(fips)
                    continue
                for year in YEARS:
                    raw_value = (row.get(str(year)) or "").strip()
                    parsed = parse_integer(raw_value)
                    values[year][fips] = {
                        "raw_value": raw_value,
                        "value": None if parsed is None else parsed * spec["multiplier"],
                        "value_status": "observed" if parsed is not None else "not_available",
                    }
    matched_by_year = {
        str(year): sum(bool(record) for record in values[year].values())
        for year in YEARS
    }
    return values, {
        "member_name": member_name,
        "matched_county_count_by_year": matched_by_year,
        "ignored_geography_count": len(ignored_geographies),
        "ignored_geography_sample": sorted(ignored_geographies)[:20],
    }


def parse_bls_slice(
    year: int,
    csv_path: Path,
    county_fips: set[str],
) -> tuple[dict[str, dict[str, Any]], dict[str, Any]]:
    values: dict[str, dict[str, Any]] = {fips: {} for fips in county_fips}
    ignored_geographies: set[str] = set()
    with csv_path.open("r", encoding="utf-8-sig", newline="") as stream:
        reader = csv.DictReader(stream)
        for row in reader:
            fips = (row.get("area_fips") or "").strip()
            if (
                (row.get("year") or "").strip() != str(year)
                or (row.get("qtr") or "").strip().upper() != "A"
                or (row.get("own_code") or "").strip() != "0"
                or (row.get("industry_code") or "").strip() != "10"
                or (row.get("agglvl_code") or "").strip() != "70"
                or (row.get("size_code") or "").strip() != "0"
                or re.fullmatch(r"\d{5}", fips) is None
            ):
                continue
            if fips not in county_fips:
                ignored_geographies.add(fips)
                continue
            if values[fips]:
                raise RuntimeError(f"Duplicate BLS total-covered row for {fips} in {year}")
            disclosure_code = (row.get("disclosure_code") or "").strip()
            suppressed = disclosure_code == "N"
            employment_raw = (row.get("annual_avg_emplvl") or "").strip()
            weekly_wage_raw = (row.get("annual_avg_wkly_wage") or "").strip()
            values[fips] = {
                "disclosure_code": disclosure_code,
                "annual_avg_covered_employment": {
                    "raw_value": employment_raw,
                    "value": None if suppressed else parse_integer(employment_raw),
                    "value_status": "suppressed" if suppressed else "observed",
                },
                "annual_avg_weekly_wage_nominal_usd": {
                    "raw_value": weekly_wage_raw,
                    "value": None if suppressed else parse_integer(weekly_wage_raw),
                    "value_status": "suppressed" if suppressed else "observed",
                },
            }
    matched = sum(bool(record) for record in values.values())
    if matched < 3000:
        raise RuntimeError(f"BLS QCEW {year} current-county coverage is unexpectedly low: {matched}")
    return values, {
        "matched_county_count": matched,
        "unmatched_county_count": len(county_fips) - matched,
        "unmatched_county_sample": sorted(fips for fips, record in values.items() if not record)[:20],
        "ignored_geography_count": len(ignored_geographies),
        "ignored_geography_sample": sorted(ignored_geographies)[:20],
    }


def source_records(generated_at: str) -> list[dict[str, Any]]:
    records = [
        {
            "schema_version": "1.0.0",
            "source_id": "src_bea_cagdp1_2024",
            "source_type": "federal_dataset",
            "publisher": "U.S. Bureau of Economic Analysis",
            "agency": "U.S. Bureau of Economic Analysis",
            "jurisdiction": "United States",
            "title": "CAGDP1 County GDP Summary, 2001-2024",
            "url": BEA_TABLES["CAGDP1"]["url"],
            "publication_date": {"date": "2026-02-05", "precision": "day"},
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
            "title": "CAINC1 County Personal Income Summary, 1969-2024",
            "url": BEA_TABLES["CAINC1"]["url"],
            "publication_date": {"date": "2026-02-05", "precision": "day"},
            "language": "en",
            "license": "U.S. government data",
            "copyright_policy": "redistributable",
            "source_quality_prior": 1.0,
            "created_at": generated_at,
            "updated_at": generated_at,
            "record_status": "active",
        },
    ]
    for year, spec in BLS_SLICES.items():
        records.append(
            {
                "schema_version": "1.0.0",
                "source_id": f"src_bls_qcew_total_{year}",
                "source_type": "federal_dataset",
                "publisher": "U.S. Bureau of Labor Statistics",
                "agency": "U.S. Bureau of Labor Statistics",
                "jurisdiction": "United States",
                "title": f"QCEW {year} annual averages: total covered employment, all industries",
                "url": spec["url"],
                "publication_date": {"date": spec["release_date"], "precision": "day"},
                "language": "en",
                "license": "U.S. government data",
                "copyright_policy": "redistributable",
                "source_quality_prior": 1.0,
                "created_at": generated_at,
                "updated_at": generated_at,
                "record_status": "active",
            }
        )
    return records


def build() -> dict[str, Any]:
    generated_at = datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")
    counties = load_counties()
    county_fips = set(counties)
    downloads: dict[str, dict[str, Any]] = {}
    bea_values: dict[str, dict[int, dict[str, dict[str, Any]]]] = {}
    bea_reports: dict[str, dict[str, Any]] = {}
    bls_values: dict[int, dict[str, dict[str, Any]]] = {}
    bls_reports: dict[str, dict[str, Any]] = {}

    with tempfile.TemporaryDirectory(prefix="dccio-panel-") as temporary:
        temporary_directory = Path(temporary)
        for table_name, spec in BEA_TABLES.items():
            target = temporary_directory / f"{table_name}.zip"
            downloads[table_name] = download(
                spec["url"], target, spec["expected_sha256"], spec["expected_bytes"]
            )
            bea_values[table_name], bea_reports[table_name] = parse_bea(
                table_name, target, county_fips
            )
        for year, spec in BLS_SLICES.items():
            target = temporary_directory / f"qcew-{year}-10.csv"
            downloads[f"BLS-{year}"] = download(
                spec["url"], target, spec["expected_sha256"], spec["expected_bytes"]
            )
            bls_values[year], bls_reports[str(year)] = parse_bls_slice(
                year, target, county_fips
            )

    for year, spec in BLS_SLICES.items():
        downloaded = downloads[f"BLS-{year}"]
        acquisition = {
            "schema_version": "1.0.0",
            "manifest_id": f"acq_bls_qcew_total_{year}",
            "source_id": f"src_bls_qcew_total_{year}",
            "source_url": spec["url"],
            "request_url": spec["url"],
            "retrieved_at": generated_at,
            "http_status": downloaded["http_status"],
            "sha256": downloaded["sha256"],
            "license": "U.S. government data",
            "parser_version": PARSER_VERSION,
            "attempt": 1,
            "created_at": generated_at,
            "updated_at": generated_at,
            "record_status": "active",
        }
        if downloaded.get("etag"):
            acquisition["etag"] = downloaded["etag"]
        if downloaded.get("last_modified"):
            acquisition["last_modified"] = downloaded["last_modified"]
        write_json(
            ROOT / "data" / "raw" / "bls-qcew" / "history" / f"{year}-total-all-industries.acquisition.json",
            acquisition,
        )

    bronze_records: list[dict[str, Any]] = []
    observations: list[dict[str, Any]] = []
    panel_rows: list[dict[str, Any]] = []
    public_by_county: dict[str, dict[str, Any]] = {
        fips: {
            "schema_version": "1.0.0",
            "county_fips": fips,
            "county_name": county["county_name"],
            "state_abbr": county["state_abbr"],
            "start_year": YEARS[0],
            "end_year": YEARS[-1],
            "years": [],
            "complete_year_count": 0,
            "coverage_status": "unavailable",
            "generated_at": generated_at,
        }
        for fips, county in counties.items()
    }
    value_status_counts: dict[str, int] = {}

    for year in YEARS:
        for fips, county in sorted(counties.items()):
            raw_values = {
                "real_gdp_usd": bea_values["CAGDP1"][year][fips],
                "population": bea_values["CAINC1"][year][fips],
                "annual_avg_covered_employment": bls_values[year][fips].get("annual_avg_covered_employment", {}),
                "annual_avg_weekly_wage_nominal_usd": bls_values[year][fips].get("annual_avg_weekly_wage_nominal_usd", {}),
            }
            bronze_records.append(
                {
                    "schema_version": "1.0.0",
                    "county_fips": fips,
                    "county_name": county["county_name"],
                    "state_abbr": county["state_abbr"],
                    "year": year,
                    "source_values": raw_values,
                    "created_at": generated_at,
                    "updated_at": generated_at,
                    "record_status": "active",
                }
            )

            observation_refs = []
            public_year = {"year": year}
            available_count = 0
            for public_field, metric in METRICS.items():
                raw = raw_values[public_field]
                value = raw.get("value")
                value_status = raw.get("value_status", "not_available")
                if not raw:
                    value_status = "not_available"
                value_status_counts[value_status] = value_status_counts.get(value_status, 0) + 1
                source_id = (
                    "src_bea_cagdp1_2024"
                    if public_field == "real_gdp_usd"
                    else "src_bea_cainc1_2024"
                    if public_field == "population"
                    else f"src_bls_qcew_total_{year}"
                )
                observation_id = stable_id(
                    "obs", "county-economic-history", fips, str(year), metric["metric_code"]
                )
                observation = {
                    "schema_version": "1.0.0",
                    "observation_id": observation_id,
                    "metric_code": metric["metric_code"],
                    "subject": {"subject_type": "county", "subject_id": fips},
                    "period": {"year": year, "precision": "year"},
                    "value_status": value_status,
                    "source_ids": [source_id],
                    "release_vintage": "2026-02-05" if metric["source_family"] == "bea" else BLS_SLICES[year]["release_date"],
                    "revision_number": 0,
                    "created_at": generated_at,
                    "updated_at": generated_at,
                    "record_status": "active",
                }
                if value is None:
                    observation["missingness_reason"] = "suppressed" if value_status == "suppressed" else "not_available"
                elif metric["value_type"] == "number":
                    observation["value"] = {"type": "number", "value": value}
                    available_count += 1
                else:
                    observation["value"] = {"type": "quantity", "value": value, "unit": metric["unit"]}
                    available_count += 1
                observations.append(observation)
                observation_refs.append(
                    {
                        "metric_code": metric["metric_code"],
                        "observation_id": observation_id,
                        "role": metric["role"],
                    }
                )
                public_year[public_field] = value

            coverage = available_count / len(METRICS)
            coverage_status = "complete" if available_count == len(METRICS) else "unavailable" if available_count == 0 else "partial"
            panel_rows.append(
                {
                    "schema_version": "1.0.0",
                    "panel_row_id": stable_id("pnl", PANEL_NAME, fips, str(year)),
                    "panel_name": PANEL_NAME,
                    "geography": {"geography_type": "county", "geography_id": fips},
                    "period": {"year": year, "precision": "year"},
                    "observation_refs": observation_refs,
                    "completeness": {
                        "required_metric_count": len(METRICS),
                        "available_metric_count": available_count,
                        "coverage": coverage,
                    },
                    "build_version": BUILD_VERSION,
                    "created_at": generated_at,
                    "updated_at": generated_at,
                    "record_status": "provisional",
                }
            )
            public_year["coverage_status"] = coverage_status
            public_by_county[fips]["years"].append(public_year)
            public_by_county[fips]["complete_year_count"] += int(coverage_status == "complete")

    public_records = []
    for fips in sorted(public_by_county):
        record = public_by_county[fips]
        populated_years = sum(year["coverage_status"] != "unavailable" for year in record["years"])
        record["coverage_status"] = (
            "complete"
            if record["complete_year_count"] == len(YEARS)
            else "unavailable"
            if populated_years == 0
            else "partial"
        )
        public_records.append(record)

    bronze_document = {
        "schema_version": "1.0.0",
        "artifact_type": "county_economic_history_source_rows",
        "artifact_version": BUILD_VERSION,
        "generated_at": generated_at,
        "data_vintage": f"{YEARS[0]}-{YEARS[-1]}",
        "record_count": len(bronze_records),
        "records": bronze_records,
    }
    bronze_path = ROOT / "data" / "bronze" / "economic" / "county-history-2021-2024-source-rows.json"
    bronze_payload = write_json(bronze_path, bronze_document, compact=True)

    sources = source_records(generated_at)
    silver_document = {
        "schema_version": "1.0.0",
        "artifact_type": "county_economic_history_panel",
        "artifact_version": BUILD_VERSION,
        "generated_at": generated_at,
        "data_vintage": f"{YEARS[0]}-{YEARS[-1]}",
        "record_count": len(sources) + len(observations) + len(panel_rows),
        "collections": {
            "source": sources,
            "observation": observations,
            "panel_row": panel_rows,
        },
    }
    silver_path = ROOT / "data" / "silver" / "panels" / "county-economic-core-2021-2024.json"
    silver_payload = write_json(silver_path, silver_document, compact=True)

    public_path = ROOT / "site" / "public" / "data" / "v1" / "panels" / "county-economic-history-2021-2024.json"
    public_payload = write_json(public_path, public_records, compact=True)

    public_coverage_counts = {
        status: sum(record["coverage_status"] == status for record in public_records)
        for status in ("complete", "partial", "unavailable")
    }
    report = {
        "schema_version": "1.0.0",
        "artifact_type": "county_economic_history_panel_processing_report",
        "artifact_version": BUILD_VERSION,
        "generated_at": generated_at,
        "data_vintage": f"{YEARS[0]}-{YEARS[-1]}",
        "county_count": len(counties),
        "year_count": len(YEARS),
        "panel_row_count": len(panel_rows),
        "source_count": len(sources),
        "observation_count": len(observations),
        "metric_count": len(METRICS),
        "value_status_counts": value_status_counts,
        "public_coverage_counts": public_coverage_counts,
        "bea_parse_reports": bea_reports,
        "bls_parse_reports": bls_reports,
        "model_readiness": {
            "status": "insufficient_history",
            "available_years": len(YEARS),
            "required_minimum_pre_periods": 7,
            "required_minimum_post_periods": 3,
            "treatment_dates_available": False,
        },
        "notices": [
            "This four-year panel is a research scaffold and is not eligible for econometric estimation.",
            "BEA historical values use the February 2026 release and therefore share its current revision vintage.",
            "BLS direct data slices are pinned independently by year.",
            "Current Census county identities are retained; legacy source geographies are never allocated or back-cast.",
            "Missing and disclosure-protected values are never treated as zero.",
            "All upstream ZIP and CSV files are temporary transport inputs; durable outputs are JSON only.",
        ],
    }
    report_path = ROOT / "data" / "silver" / "panels" / "county-economic-core-2021-2024.processing-report.json"
    report_payload = write_json(report_path, report)

    parts = []
    for path, payload, count, zone, projection in [
        (bronze_path, bronze_payload, len(bronze_records), "bronze", "source_rows"),
        (silver_path, silver_payload, silver_document["record_count"], "silver", "observations_and_panel_rows"),
        (public_path, public_payload, len(public_records), "public", "county_history_summary"),
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
    manifest = {
        "schema_version": "1.0.0",
        "dataset_id": "county_economic_core_panel_2021_2024",
        "artifact_type": "county_year_panel",
        "artifact_version": BUILD_VERSION,
        "generated_at": generated_at,
        "data_vintage": f"{YEARS[0]}-{YEARS[-1]}",
        "record_schema": "https://dccio.org/schemas/v1/panel-row.schema.json",
        "format": "json",
        "parts": parts,
        "record_count": sum(part["record_count"] for part in parts),
        "input_dataset_ids": [
            "geo_counties_2025_5m",
            "bea_county_economic_baseline_2024",
            "bls_qcew_county_baseline_2025",
        ],
        "license_metadata": {
            "license": "U.S. government data",
            "redistribution_status": "allowed",
            "attribution": "Sources: U.S. Bureau of Economic Analysis and U.S. Bureau of Labor Statistics",
        },
    }
    write_json(
        ROOT / "data" / "silver" / "panels" / "county-economic-core-2021-2024.manifest.json",
        manifest,
    )
    return report


def main() -> int:
    print(json.dumps(build(), indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

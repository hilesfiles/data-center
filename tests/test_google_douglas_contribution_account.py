import json
import unittest
from pathlib import Path

from scripts.build_private_sector_study import CONFIG, MODELING_POLICY, PUBLIC, build_products, read
from scripts.study_economic_evidence import load_evidence, validate_evidence
from scripts.study_modeled_synthesis import load_synthesis, modeled_products


PROJECT = "prj_study_im3_campus_00578435601"
ROOT = Path(__file__).resolve().parents[1]
EVIDENCE_FRAGMENT = ROOT / "config/v1/study-economic-evidence.projects" / f"{PROJECT}.json"
MODEL_FRAGMENT = ROOT / "config/v1/study-modeled-synthesis.projects" / f"{PROJECT}.json"


class GoogleDouglasContributionAccountTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.fragment = json.loads(EVIDENCE_FRAGMENT.read_text(encoding="utf-8"))
        cls.model_fragment = json.loads(MODEL_FRAGMENT.read_text(encoding="utf-8"))
        cls.candidates = read(CONFIG)
        cls.evidence = load_evidence()
        cls.synthesis = load_synthesis()
        cls.policy = read(MODELING_POLICY)
        validate_evidence(cls.evidence, cls.candidates["candidates"])
        cls.grouped, _ = modeled_products(
            cls.synthesis, cls.candidates["candidates"], cls.evidence, cls.policy
        )
        inventory = {row["entity_id"]: row for row in read(PUBLIC / "facilities/index.json")}
        panels = {
            row["county_fips"]: row
            for path in (PUBLIC / "panels/county-economic-history/by-state").glob("*.json")
            for row in read(path)
        }
        _, details, _ = build_products(
            cls.candidates,
            inventory,
            panels,
            "2026-09-07T00:00:00+00:00",
            cls.evidence,
            cls.synthesis,
            cls.policy,
        )
        cls.detail = next(row for row in details if row["project_id"] == PROJECT)

    def test_fragment_counts_and_project_identity(self):
        self.assertEqual(len(self.fragment["sources"]), 26)
        self.assertEqual(len(self.fragment["records"]), 22)
        self.assertEqual(len(self.fragment["project_updates"]), 11)
        self.assertEqual(
            sum(row["basis"] == "reported_actual" for row in self.fragment["records"]), 20
        )
        self.assertEqual(
            sum(row["basis"] == "source_projection" for row in self.fragment["records"]), 2
        )
        self.assertEqual(self.detail["county_fips"], "13097")
        self.assertEqual(self.detail["economic_record_count"], 26)
        self.assertEqual(self.detail["reported_actual_count"], 24)
        self.assertEqual(self.detail["projection_count"], 2)
        self.assertEqual(self.detail["modeled_synthesis_count"], 3)

        descriptions = [
            row["project_description"]
            for row in self.fragment["project_updates"]
            if "project_description" in row
        ]
        self.assertEqual(len(descriptions), 1)
        self.assertIn("300 Riverside Parkway", descriptions[0])
        self.assertIn("Development Authority of Douglas County", descriptions[0])

    def test_assessor_tax_investment_workforce_and_community_observations(self):
        records = {row["claim_id"]: row for row in self.detail["economic_records"]}
        self.assertEqual(records["clm_study_google_douglas_taxable_assessed_2019"]["value"], 124_479_075)
        self.assertEqual(records["clm_study_google_douglas_taxable_assessed_2020"]["value"], 112_997_111)
        self.assertEqual(records["clm_study_google_douglas_taxable_assessed_2021"]["value"], 93_469_679)
        self.assertEqual(records["clm_study_google_douglas_p88150_assessed_2025"]["value"], 15_560_354)
        exempt = records["clm_study_google_douglas_p79020_exempt_assessed_2025"]
        self.assertEqual(exempt["value"], 308_368_064)
        self.assertIn("fully exempt", exempt["notes"])

        floor = sorted(
            row["value"]
            for row in records.values()
            if row["metric_code"] == "study.operating_property_floor_area"
        )
        self.assertEqual(floor, [11_700, 224_078, 482_220])
        self.assertEqual(
            records["clm_study_google_douglas_interior_remodel_permit_2025"]["value"],
            249_864.77,
        )
        self.assertEqual(
            records["clm_study_google_douglas_cumulative_investment_2018"]["value"],
            1_200_000_000,
        )
        self.assertEqual(
            records["clm_study_google_douglas_operating_employees_2015"]["value"], 350
        )
        self.assertEqual(
            records["clm_study_google_douglas_operating_jobs_projection_2015"]["basis"],
            "source_projection",
        )
        self.assertEqual(
            records["clm_study_google_douglas_contracted_solar_capacity_2024"]["value"], 78.8
        )
        self.assertEqual(
            records["clm_study_google_douglas_mercer_workforce_grant_2022"]["value"], 42_000
        )

    def test_audit_log_covers_required_families_and_negative_results(self):
        text = " ".join(
            row["title"] + " " + row["notes"] for row in self.fragment["project_updates"]
        ).lower()
        for phrase in [
            "assessor",
            "tax-bill",
            "permit",
            "contractor",
            "bond",
            "abatement",
            "water",
            "electricity",
            "workforce",
            "payroll",
            "supplier",
            "community",
            "public-cost",
            "county outcome",
            "captcha",
            "no invoice",
            "no meter",
            "no same-scope marginal service cost",
        ]:
            self.assertIn(phrase, text)

        source_ids = {row["source_id"] for row in self.fragment["sources"]}
        self.assertTrue(
            {
                "src_study_douglas_qpublic_real_08741820001_2026",
                "src_study_douglas_qpublic_pp_p88150_2026",
                "src_study_douglas_qpublic_pp_p79020_2026",
                "src_study_douglas_tax_payment_portal_2026",
                "src_study_douglas_permits_2025_11",
                "src_study_google_douglas_npdes_2019",
                "src_study_google_douglas_air_application_27010",
                "src_study_dadc_agendas_2023_google",
                "src_study_dca_debt_issuances_2008_douglas",
            }.issubset(source_ids)
        )

        metrics = {row["metric_code"] for row in self.detail["economic_records"]}
        self.assertNotIn("study.property_taxes_paid", metrics)
        self.assertNotIn("study.property_taxes_billed", metrics)
        self.assertNotIn("study.incentive_payments", metrics)

    def test_only_bounded_unallocated_water_models_survive(self):
        rows = self.grouped[PROJECT]
        self.assertEqual(len(self.model_fragment["sources"]), 2)
        self.assertEqual(len(self.model_fragment["estimates"]), 3)
        self.assertEqual(len(rows), 3)
        self.assertEqual(
            {(row["period"]["year"], row["value"]) for row in rows},
            {(2022, 305_200_000), (2023, 345_600_000), (2024, 366_900_000)},
        )
        self.assertTrue(
            all(row["metric_code"] == "study.modeled_annual_water_consumption" for row in rows)
        )
        self.assertTrue(all(row["category"] == "resources" for row in rows))
        self.assertTrue(all(row["presentation"] == "modeled_not_observed_or_audited" for row in rows))
        self.assertTrue(all(row["scope"]["inventory_allocation"] == "unallocated" for row in rows))
        self.assertTrue(all(row["interval"]["kind"] == "reported_band" for row in rows))
        self.assertTrue(all(row["derivation"]["method"] == "engineering_estimate" for row in rows))
        self.assertFalse(any(row["category"] in {"construction", "suppliers", "operations", "fiscal", "public_costs", "county_outcome"} for row in rows))


if __name__ == "__main__":
    unittest.main()

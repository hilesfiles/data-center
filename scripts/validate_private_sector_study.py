"""Check published study membership, provenance, schema and projection consistency."""
from pathlib import Path

if __package__:
    from .build_private_sector_study import CONFIG, OUT, PUBLIC, ROOT, SILVER, build_products, digest, manifest_size, read
    from .study_economic_evidence import EVIDENCE, economic_products
    from .study_modeled_synthesis import MODELING_POLICY, SYNTHESIS, modeled_products
else:
    from build_private_sector_study import CONFIG, OUT, PUBLIC, ROOT, SILVER, build_products, digest, manifest_size, read
    from study_economic_evidence import EVIDENCE, economic_products
    from study_modeled_synthesis import MODELING_POLICY, SYNTHESIS, modeled_products


def validate_study(validator):
    errors = []
    try:
        index = read(OUT / "index.json")
        config = read(CONFIG)
        evidence = read(EVIDENCE)
        synthesis = read(SYNTHESIS)
        modeling_policy = read(MODELING_POLICY)
        inventory = {r["entity_id"]: r for r in read(PUBLIC / "facilities/index.json")}
        panels = {r["county_fips"]: r for p in (PUBLIC / "panels/county-economic-history/by-state").glob("*.json") for r in read(p)}
        expected_index, expected_details, expected_entities = build_products(config, inventory, panels, index["generated_at"], evidence, synthesis, modeling_policy)
        _, expected_claims, expected_sources = economic_products(evidence, config["candidates"], index["generated_at"])
        modeled_products(synthesis, config["candidates"], evidence, modeling_policy)
        errors.extend(str(e) for e in validator.validate_record(synthesis, ROOT / "schemas/v1/study-modeled-synthesis.schema.json"))
        errors.extend(str(e) for e in validator.validate_record(modeling_policy, ROOT / "schemas/v1/study-modeling-policy.schema.json"))
        if read(SILVER / "modeled-syntheses.json") != synthesis:
            errors.append("modeled-syntheses.json differs from reviewed modeled synthesis")
        for name, expected, schema in [("economic-claims.json", expected_claims, "claim"), ("economic-sources.json", expected_sources, "source")]:
            published_rows = read(SILVER / name)
            if published_rows != expected:
                errors.append(f"{name} differs from reviewed economic evidence")
            for record in published_rows:
                errors.extend(str(e) for e in validator.validate_record(record, ROOT / f"schemas/v1/{schema}.schema.json"))
        if index != expected_index:
            errors.append("Study index differs from reviewed inputs, panel coverage or generated counts")
        errors.extend(str(e) for e in validator.validate_record(index, ROOT / "schemas/v1/public-study-index.schema.json"))
        entities = read(SILVER / "projects.json")
        if entities != expected_entities:
            errors.append("Provisional project entities differ from study inputs")
        for entity in entities:
            errors.extend(str(e) for e in validator.validate_record(entity, ROOT / "schemas/v1/project.schema.json"))
        for expected in expected_details:
            detail = read(OUT / expected["detail_path"])
            if detail != expected:
                errors.append(f"{expected['project_id']}: detail differs from source wording, readiness or evidence")
            errors.extend(str(e) for e in validator.validate_record(detail, ROOT / "schemas/v1/public-study-project.schema.json"))
        published = {p.name for p in (OUT / "projects").glob("*.json")}
        if published != {Path(r["detail_path"]).name for r in index["projects"]}:
            errors.append("Orphan or missing public project profile")
        manifest = read(OUT / "manifest.json")
        expected_parts = {"site/public/data/v1/study/index.json", "data/silver/study/projects.json", "data/silver/study/economic-claims.json", "data/silver/study/economic-sources.json", "data/silver/study/modeled-syntheses.json", *[f"site/public/data/v1/study/{r['detail_path']}" for r in index["projects"]]}
        if {p["path"] for p in manifest["parts"]} != expected_parts:
            errors.append("Study manifest does not cover the publication")
        if manifest["release_id"] != index["release_id"] or manifest["generated_at"] != index["generated_at"]:
            errors.append("Mixed study release vintages")
        required_inputs = {"config/v1/study-economic-evidence.json", "scripts/study_economic_evidence.py", "config/v1/study-modeled-synthesis.json", "config/v1/study-modeling-policy.json", "scripts/study_modeled_synthesis.py", "config/v1/private-sector-study-candidates.json", "scripts/build_private_sector_study.py"}
        if not required_inputs.issubset({p["path"] for p in manifest["inputs"]}):
            errors.append("Study manifest omits economic evidence inputs")
        for part in manifest["inputs"] + manifest["parts"]:
            path = (ROOT / part["path"]).resolve()
            if not path.is_relative_to(ROOT) or not path.is_file() or digest(path) != part["sha256"]:
                errors.append(f"Study input/output hash mismatch: {part['path']}")
            elif "byte_size" in part and manifest_size(path) != part["byte_size"]:
                errors.append(f"Study byte-size mismatch: {part['path']}")
    except (KeyError, ValueError, OSError, TypeError) as exc:
        errors.append(f"Study publication invalid: {exc}")
    return errors

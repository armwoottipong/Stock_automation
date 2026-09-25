import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def test_background_benchmark_manifest_covers_required_categories():
    manifest = json.loads((ROOT / "benchmarks" / "background" / "cases.json").read_text(encoding="utf-8"))
    assert manifest["policy"] == "clean_cutout_remove_original_shadow_and_floor_reflection"
    cases = manifest["cases"]
    assert {case["category"] for case in cases} == {
        "portrait_hair", "product_solid", "glass", "translucent", "furniture", "thin_structure", "complex_shadow",
    }
    assert len({case["id"] for case in cases}) == len(cases)
    assert all(case["input"] and case["source"] and case["license"] for case in cases)


def test_isolate_fixture_plan_records_stock_exclusions_and_actual_background():
    base = ROOT / "benchmarks" / "background"
    plan = json.loads((base / "isolated_generation.json").read_text(encoding="utf-8"))
    manifest = json.loads((base / "isolated_cases.json").read_text(encoding="utf-8"))
    expected = {
        "fur_object", "product_solid", "glass", "translucent", "furniture",
        "thin_structure", "complex_shadow",
    }
    assert {case["category"] for case in plan["cases"]} == expected
    assert {case["id"] for case in manifest["cases"]} == {case["id"] for case in plan["cases"]}
    assert all(case["background"] == "white" for case in plan["cases"])
    assert all(case["requested_background"] == "white" for case in manifest["cases"])
    assert all("pure white" in case["prompt"] for case in plan["cases"])
    negative = plan["negative_prompt"]
    assert all(term in negative for term in ("text", "logo", "trademark", "watermark", "label"))
    assert all(len(case["corner_mean_rgb"]) == 3 for case in manifest["cases"])
    assert all(
        case["near_white_corner"]
        == (min(case["corner_mean_rgb"]) >= 245 and max(case["corner_stddev_rgb"]) <= 5)
        for case in manifest["cases"]
    )

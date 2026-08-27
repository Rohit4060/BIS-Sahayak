"""
Automated test for deterministic metadata extraction (Milestone 9).

Verifies that services/metadata_extractor.py correctly extracts
standard_number, title, and version from the two existing BIS PDFs,
and that source_url is never fabricated when not genuinely present
in the document text.

Usage (from project root, venv active):
    python backend/scripts/test_metadata_extraction.py

Exits with code 0 if all checks pass, 1 if any check fails.
"""
import sys
from pathlib import Path

sys.path.append(str(Path(__file__).resolve().parent.parent))

from services.pdf_utils import extract_pages
from services.metadata_extractor import extract_metadata

# (file, expected_standard_number, expected_title_substring, expected_version)
TEST_CASES = [
    (
        "data/raw/IS_302_Part1_Household_Appliances_Safety.pdf",
        "IS 302",
        "HOUSEHOLD AND SIMILAR ELECTRICAL APPLIANCES",
        "Seventh Revision",
    ),
    (
        "data/raw/17423_2021.pdf",
        "IS 17423",
        "Bio-Protective Coveralls",
        "First Revision",
    ),
]

failures = []
passed = 0

for file_path, expected_std, expected_title_part, expected_version in TEST_CASES:
    path = Path(file_path)
    print(f"\n=== {path.name} ===")

    if not path.exists():
        failures.append(f"{path.name}: FILE NOT FOUND at {path}")
        print("  FAIL: file not found")
        continue

    pages = extract_pages(path)
    result = extract_metadata(path, pages)

    checks = [
        ("standard_number present", result["standard_number"] is not None),
        ("standard_number contains expected value",
            result["standard_number"] and expected_std in result["standard_number"]),
        ("title present", result["title"] is not None),
        ("title contains expected substring",
            result["title"] and expected_title_part.lower() in result["title"].lower()),
        ("version present", result["version"] is not None),
        ("version contains expected value",
            result["version"] and expected_version in result["version"]),
        ("source_url is None or a real bis.gov.in URL (never fabricated)",
            result["source_url"] is None or "bis.gov.in" in result["source_url"]),
    ]

    for check_name, ok in checks:
        status = "PASS" if ok else "FAIL"
        print(f"  [{status}] {check_name}")
        if ok:
            passed += 1
        else:
            failures.append(f"{path.name}: {check_name}")

    print(f"  -> standard_number : {result['standard_number']}")
    print(f"  -> title           : {result['title']}")
    print(f"  -> version         : {result['version']}")
    print(f"  -> source_url      : {result['source_url']}")

print(f"\n{'='*50}")
print(f"RESULT: {passed} checks passed, {len(failures)} failed")

if failures:
    print("\nFAILURES:")
    for f in failures:
        print(f"  - {f}")
    sys.exit(1)
else:
    print("ALL CHECKS PASSED.")
    sys.exit(0)
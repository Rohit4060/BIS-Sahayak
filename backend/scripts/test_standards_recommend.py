"""
Automated test for Milestone 10 — /api/standards/recommend.

Live-execution test against the real DB + Gemini, same style as
test_metadata_extraction.py. Run with:
    python backend\\scripts\\test_standards_recommend.py

Checks:
  - valid product description returns a structured response, no crash
  - a broad query retrieves evidence grouped across multiple candidate
    standards (tests grouping logic directly, before Gemini narrows it down)
  - every standard_number returned is one that is ACTUALLY in the ingested
    documents table (hallucination check, done against the live DB, not
    just trusting Gemini's output)
  - every recommendation has a non-empty citations list
  - an unrelated product description returns the honest insufficient-evidence
    message and an empty recommendations list
"""
import sys
import os

sys.path.append(os.path.join(os.path.dirname(__file__), ".."))

from dotenv import load_dotenv
load_dotenv(os.path.join(os.path.dirname(__file__), "..", ".env"))

from database import SessionLocal
from models import Document
from services.search_service import search_chunks
from services.standards_recommender import (
    recommend_standards,
    _group_chunks_by_standard,
    INSUFFICIENT_EVIDENCE_MSG,
)

failures = []


def check(label, condition, detail=""):
    status = "PASS" if condition else "FAIL"
    print(f"  [{status}] {label}" + (f" -- {detail}" if detail and not condition else ""))
    if not condition:
        failures.append(f"{label} -- {detail}")


def main():
    db = SessionLocal()
    try:
        # Ground truth: which standard_numbers actually exist in the DB right now.
        known_standards = {
            row.standard_number
            for row in db.query(Document).all()
            if row.standard_number
        }
        print(f"Known ingested standards: {known_standards}\n")

        # --- Test 1: valid product description, relevant to IS 302 ---
        print("=== Test 1: valid product description (electric pressure cooker) ===")
        result = recommend_standards(db, "I manufacture electric pressure cookers")
        check("response has product_description", "product_description" in result)
        check("response has recommendations list", isinstance(result.get("recommendations"), list))
        check(
            "a known-answerable query returns at least one recommendation",
            len(result.get("recommendations", [])) > 0,
            f"got empty recommendations; message={result.get('message')!r}",
        )

        for rec in result["recommendations"]:
            check(
                f"no hallucinated standard_number ({rec['standard_number']})",
                rec["standard_number"] in known_standards,
                f"got {rec['standard_number']!r}, known = {known_standards}",
            )
            check(
                f"recommendation for {rec['standard_number']} has non-empty citations",
                len(rec["citations"]) > 0,
            )
            check(
                f"recommendation for {rec['standard_number']} has non-empty evidence",
                len(rec["evidence"]) > 0,
            )
            check(
                f"relevance is a valid value ({rec['relevance']})",
                rec["relevance"] in ("high", "medium", "low"),
            )
            check(
                f"requirement_status distinguishes potentially-applicable vs mandatory",
                "mandatory" in rec["requirement_status"].lower(),
            )
        print()

        # --- Test 2: grouping picks up multiple candidate standards from a broad query ---
        print("=== Test 2: broad query retrieves multiple candidate groups ===")
        broad_chunks = search_chunks(
            db,
            "marking, certification, and quality requirements for BIS certified products",
            top_k=20,
        )
        groups = _group_chunks_by_standard(broad_chunks)
        check(
            "retrieval + grouping surfaces more than one candidate standard",
            len(groups) > 1,
            f"got groups: {list(groups.keys())}",
        )
        print(f"  -> candidate groups found: {list(groups.keys())}\n")

        # --- Test 3: insufficient evidence returns the honest message ---
        print("=== Test 3: unrelated product description (insufficient evidence) ===")
        try:
            result3 = recommend_standards(db, "I manufacture titanium spacecraft heat shields")
            check("recommendations list is empty", result3["recommendations"] == [])
            check(
                "insufficient-evidence message is returned",
                result3.get("message") == INSUFFICIENT_EVIDENCE_MSG,
                f"got: {result3.get('message')!r}",
            )
        except Exception as e:
            check(
                "Test 3 completed without a transient API error",
                False,
                f"Gemini call failed (likely transient, not a code bug): {e}",
            )
        print()

    finally:
        db.close()

    print("=" * 50)
    if failures:
        print(f"RESULT: {len(failures)} check(s) FAILED")
        print("FAILURES:")
        for f in failures:
            print(f"  - {f}")
        sys.exit(1)
    else:
        print("ALL CHECKS PASSED.")
        sys.exit(0)


if __name__ == "__main__":
    main()
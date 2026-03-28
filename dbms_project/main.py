"""
main.py — DBMS Project Entry Point
====================================
Orchestrates the full normalisation pipeline:
  1. Parse schema and FDs from config.py
  2. Print input summary
  3. Demonstrate attribute closure
  4. Find candidate keys
  5. Check and decompose into 2NF
  6. Check and decompose into 3NF
  7. Check and decompose into BCNF
  8. Print final summary

Run with:
    python main.py

Flask integration note:
  Import individual modules and call their functions directly from route handlers.
  config.py values can be replaced by request JSON payload parsing.
"""

import sys

# ── Project modules ──────────────────────────────────────────────────────────
from config import SCHEMA_STR, FD_STRINGS
from parser import parse_schema, parse_fds, format_fd
from closure import closure_verbose_demo
from candidate_keys import (
    find_candidate_keys,
    get_prime_attributes,
    get_non_prime_attributes,
    summarise_keys,
)
from normalization import (
    check_1nf,
    is_in_2nf,
    decompose_2nf,
    is_in_3nf,
    decompose_3nf,
    is_in_bcnf,
    decompose_bcnf,
)
from utils import print_section, format_relation, attrs_to_str, relation_to_json


# ── Helpers ──────────────────────────────────────────────────────────────────

def print_relations(relations: list[dict]) -> None:
    """Pretty-print a list of relation dicts."""
    for rel in relations:
        print(format_relation(rel))
        print()


def print_summary_row(label: str, relations: list[dict]) -> None:
    """Print a single row of the final summary table."""
    names = ", ".join(r["name"] for r in relations)
    sizes = ", ".join(str(len(r["attributes"])) + " attrs" for r in relations)
    print(f"  {label:<22}: {names}  ({sizes})")


# ── Main pipeline ─────────────────────────────────────────────────────────────

def run_pipeline() -> None:
    """Execute the complete DBMS normalization pipeline."""

    # ── 1. Parse inputs ───────────────────────────────────────────────────────
    print_section("INPUT PARSING")
    try:
        relation_name, schema = parse_schema(SCHEMA_STR)
        fds = parse_fds(FD_STRINGS, schema)
    except ValueError as exc:
        print(f"\n  ERROR during parsing:\n  {exc}")
        sys.exit(1)

    # ── 2. Print input summary ────────────────────────────────────────────────
    print_section("INPUT SUMMARY")
    print(f"  Relation   : {relation_name}")
    print(f"  Attributes : {attrs_to_str(schema)}")
    print(f"  # Attributes: {len(schema)}")
    print(f"\n  Functional Dependencies ({len(fds)} total):")
    for lhs, rhs in fds:
        print(f"    {format_fd(lhs, rhs)}")

    # ── 3. Attribute closure demo ─────────────────────────────────────────────
    print_section("ATTRIBUTE CLOSURE")

    # Demo closure for {BookingID} and {PaymentID}
    demo_sets = [{"BookingID"}, {"PaymentID"}, {"CustomerID"}, {"BikeID"}]
    print()
    for demo in demo_sets:
        closure_verbose_demo([demo], fds, schema)

    # ── 4. Candidate keys ─────────────────────────────────────────────────────
    print_section("CANDIDATE KEY FINDING")
    print()
    try:
        candidate_keys = find_candidate_keys(schema, fds, verbose=True)
    except RuntimeError as exc:
        print(f"\n  {exc}")
        sys.exit(1)

    print()
    summarise_keys(schema, candidate_keys)
    prime = get_prime_attributes(candidate_keys)
    non_prime = get_non_prime_attributes(schema, candidate_keys)

    # ── 5. 1NF ───────────────────────────────────────────────────────────────
    print_section("1NF CHECK")
    print()
    check_1nf(schema, verbose=True)

    # ── 6. 2NF ───────────────────────────────────────────────────────────────
    print_section("2NF CHECK & DECOMPOSITION")
    print()
    already_2nf = is_in_2nf(schema, fds, candidate_keys, verbose=True)
    print()

    print("  Decomposed Relations in 2NF:")
    print()
    relations_2nf = decompose_2nf(
        schema, fds, candidate_keys, relation_name=relation_name, verbose=True
    )

    # ── 7. 3NF ───────────────────────────────────────────────────────────────
    print_section("3NF CHECK & DECOMPOSITION")
    print()
    already_3nf = is_in_3nf(schema, fds, candidate_keys, verbose=True)
    print()

    print("  Decomposed Relations in 3NF (synthesis algorithm):")
    print()
    relations_3nf = decompose_3nf(
        schema, fds, candidate_keys, relation_name=relation_name, verbose=True
    )

    # ── 8. BCNF ──────────────────────────────────────────────────────────────
    print_section("BCNF CHECK & DECOMPOSITION")
    print()
    already_bcnf = is_in_bcnf(schema, fds, candidate_keys, verbose=True)
    print()

    print("  Decomposed Relations in BCNF (lossless-join algorithm):")
    print()
    relations_bcnf = decompose_bcnf(
        schema, fds, candidate_keys, relation_name=relation_name, verbose=True
    )

    # ── 9. Final summary ──────────────────────────────────────────────────────
    print_section("FINAL SUMMARY")
    print()
    print(
        f"  Original Relation : {relation_name} "
        f"({len(schema)} attributes, {len(candidate_keys)} candidate key(s))"
    )
    print(f"  Candidate Keys    : {', '.join(attrs_to_str(ck) for ck in candidate_keys)}")
    print(f"  Prime Attributes  : {attrs_to_str(prime)}")
    print(f"  Non-Prime Attrs   : {attrs_to_str(non_prime)}")
    print()
    print_summary_row("2NF Decomposition", relations_2nf)
    print_summary_row("3NF Decomposition", relations_3nf)
    print_summary_row("BCNF Decomposition", relations_bcnf)
    print()

    # JSON-serializable output (Flask-ready)
    print("  JSON-serializable output (ready for Flask API):")
    import json
    for stage, rels in [
        ("2NF", relations_2nf),
        ("3NF", relations_3nf),
        ("BCNF", relations_bcnf),
    ]:
        serialized = [relation_to_json(r) for r in rels]
        print(f"\n  [{stage}]")
        print(
            "  "
            + json.dumps(serialized, indent=4)
            .replace("\n", "\n  ")
        )

    print()
    print("=" * 60)
    print(" Pipeline complete.".center(60))
    print("=" * 60)


# ── Entry point ────────────────────────────────────────────────────────────

if __name__ == "__main__":
    run_pipeline()

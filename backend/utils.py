"""
utils.py — Shared Helper Functions and Formatters
==================================================
Provides utility functions used across all modules:
  - Power-set enumeration
  - Superkey checking
  - FD projection onto sub-schemas
  - Human-readable formatting
  - JSON serialization helpers

Flask-ready: All functions accept/return plain Python objects.
"""

from itertools import combinations
from typing import TYPE_CHECKING


# ---------------------------------------------------------------------------
# Set & combinatorics helpers
# ---------------------------------------------------------------------------

def power_set(s: set) -> list[frozenset]:
    """
    Return all non-empty subsets of `s`, sorted by cardinality (smallest first).

    Args:
        s: The base set.

    Returns:
        A list of frozensets, ordered from size-1 up to size-len(s).
    """
    elements = list(s)
    result: list[frozenset] = []
    for size in range(1, len(elements) + 1):
        for combo in combinations(elements, size):
            result.append(frozenset(combo))
    return result


def is_superkey(attrs: set, schema: set, fds: list[tuple[frozenset, frozenset]]) -> bool:
    """
    Check if `attrs` is a superkey of the relation described by `schema` and `fds`.

    A set of attributes is a superkey if its closure equals the entire schema.

    Args:
        attrs:  The attribute set to test.
        schema: The full relation schema.
        fds:    List of (lhs, rhs) FD tuples.

    Returns:
        True if attrs+ == schema, False otherwise.
    """
    # Import here to avoid circular dependency
    from closure import compute_closure
    closure = compute_closure(attrs, fds, schema, verbose=False)
    return closure >= schema


def project_fds(
    fds: list[tuple[frozenset, frozenset]],
    sub_schema: set,
) -> list[tuple[frozenset, frozenset]]:
    """
    Project a set of FDs onto a sub-relation schema.

    Step 1: Keep only FDs where all attributes in LHS ∪ RHS ⊆ sub_schema.
    Step 2: For every subset X of sub_schema, compute closure(X) restricted to
            sub_schema; if X → anything new is found, add implied FDs.

    Args:
        fds:        List of (lhs, rhs) FD tuples for the original relation.
        sub_schema: The attribute set of the sub-relation.

    Returns:
        A list of (lhs, rhs) FD tuples that hold within the sub-relation.
        Trivial FDs (lhs == rhs) are excluded.
    """
    from closure import compute_closure

    projected: list[tuple[frozenset, frozenset]] = []

    for subset in power_set(sub_schema):
        # Compute the closure of this subset in the *original* FD set
        full_closure = compute_closure(set(subset), fds, sub_schema, verbose=False)
        # Restrict to attributes in the sub-schema
        restricted = frozenset(full_closure & sub_schema)
        implied_rhs = restricted - subset
        if implied_rhs:
            fd = (frozenset(subset), implied_rhs)
            # Avoid duplicates
            if fd not in projected:
                projected.append(fd)

    return projected


# ---------------------------------------------------------------------------
# Formatting helpers
# ---------------------------------------------------------------------------

def format_relation(relation: dict) -> str:
    """
    Return a multi-line human-readable string for a relation dict.

    Args:
        relation: Dict with keys 'name', 'attributes', 'primary_key', 'fds'.

    Returns:
        Formatted string describing the relation.

    Example output:
        Relation R1:
          Attributes : {BookingID, CustomerID, ...}
          Primary Key: {BookingID}
          FDs        : BookingID → CustomerID, BikeID, StartDate, EndDate
    """
    from parser import format_fd

    name = relation["name"]
    attrs = "{" + ", ".join(sorted(relation["attributes"])) + "}"
    pk = "{" + ", ".join(sorted(relation["primary_key"])) + "}"
    fd_lines = "\n              ".join(
        format_fd(lhs, rhs) for lhs, rhs in relation.get("fds", [])
    ) or "(none)"

    return (
        f"  Relation {name}:\n"
        f"    Attributes : {attrs}\n"
        f"    Primary Key: {pk}\n"
        f"    FDs        : {fd_lines}"
    )


def print_section(title: str) -> None:
    """
    Print a visually prominent section divider to stdout.

    Args:
        title: The section title to display.
    """
    width = 60
    border = "=" * width
    padded = f" {title} "
    print(f"\n{border}")
    print(padded.center(width))
    print(f"{border}")


def attrs_to_str(attrs: set | frozenset) -> str:
    """
    Render an attribute set as a sorted, braced string.

    Args:
        attrs: Any iterable of attribute name strings.

    Returns:
        e.g. "{A, B, C}"
    """
    return "{" + ", ".join(sorted(attrs)) + "}"


# ---------------------------------------------------------------------------
# JSON serialization helper
# ---------------------------------------------------------------------------

def relation_to_json(relation: dict) -> dict:
    """
    Convert a relation dict (containing sets/frozensets) to a fully
    JSON-serializable dict.

    Args:
        relation: Dict with keys 'name', 'attributes', 'primary_key', 'fds'.

    Returns:
        A dict where all set values are replaced by sorted lists, suitable
        for json.dumps() or returning from a Flask route.
    """
    return {
        "name": relation["name"],
        "attributes": sorted(list(relation["attributes"])),
        "primary_key": sorted(list(relation["primary_key"])),
        "fds": [
            {
                "lhs": sorted(list(lhs)),
                "rhs": sorted(list(rhs)),
            }
            for lhs, rhs in relation.get("fds", [])
        ],
    }

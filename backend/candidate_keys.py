"""
candidate_keys.py — Candidate Key Discovery
============================================
Finds ALL candidate keys of a relation using an optimised approach:
  1. Identify "essential" attributes (not on any RHS of any FD) — these must
     appear in every candidate key, so we start from them.
  2. Enumerate power-set extensions of the essential set over the remaining
     attributes, sorted smallest-first, with superkey pruning.

This reduces the 2^12 = 4095 worst-case subset checks to a much smaller
targeted search for schemas with multiple FDs.

Flask-ready: All functions accept/return plain Python objects.
"""

from closure import compute_closure
from utils import power_set, is_superkey, attrs_to_str
from parser import format_fd


def find_candidate_keys(
    schema: set,
    fds: list[tuple[frozenset, frozenset]],
    verbose: bool = True,
) -> list[frozenset]:
    """
    Find all candidate keys of the relation.

    Optimised algorithm:
      1. Compute "essential" attributes: those that never appear on any RHS of
         any FD.  These attributes cannot be derived from anything else, so they
         MUST appear in every candidate key (a.k.a. the "non-derived" core).
      2. Check whether the essential set alone is already a key.  If so, it may
         be the only candidate key.
      3. Enumerate power-set extensions of the essential set (adding attributes
         from the remaining schema one at a time), smallest-first.
      4. Prune: skip any superset of an already-found candidate key.

    Falls back to the full power-set search if the essential-set heuristic
    does not narrow things down (e.g. when every attribute appears on some RHS).

    Args:
        schema:  The full attribute set of the relation.
        fds:     List of (lhs: frozenset, rhs: frozenset) FD tuples.
        verbose: If True, print progress.

    Returns:
        A list of frozensets, each being a minimal candidate key.

    Raises:
        ValueError:  If schema is empty.
        RuntimeError: If no candidate key is found.
    """
    # Flask-ready: call this function directly from a route handler
    # Input/output are JSON-serializable (convert frozensets to sorted lists before returning)

    if not schema:
        raise ValueError("Schema is empty — cannot find candidate keys.")

    # ── Step 1: identify "essential" (never-derived) attributes ─────────────
    all_rhs_attrs: set[str] = set()
    for _, rhs in fds:
        all_rhs_attrs |= set(rhs)

    essential: frozenset[str] = frozenset(schema - all_rhs_attrs)
    remaining: set[str] = schema - set(essential)

    if verbose:
        print(f"  Essential attributes (never appear on any RHS, must be in every key):")
        print(f"    {attrs_to_str(essential) if essential else '(none — every attribute is derivable)'}")
        print(f"  Remaining attributes to extend with: {attrs_to_str(remaining) if remaining else '(none)'}")
        print()

    candidate_keys: list[frozenset] = []

    # Generate all subsets of `remaining`, including the empty set
    from itertools import combinations as _comb
    extension_subsets: list[frozenset] = [frozenset()]
    for size in range(1, len(remaining) + 1):
        for combo in _comb(sorted(remaining), size):   # sorted for determinism
            extension_subsets.append(frozenset(combo))

    # Sort by size (essential is already fixed; sort extensions by size)
    extension_subsets.sort(key=len)

    for ext in extension_subsets:
        candidate = essential | ext

        # Pruning: skip if already a superset of a known candidate key
        if any(ck < candidate for ck in candidate_keys):
            continue

        closure = compute_closure(set(candidate), fds, schema, verbose=False)
        is_key = closure >= schema

        if verbose:
            subset_str = attrs_to_str(candidate)
            closure_str = attrs_to_str(closure)
            if is_key:
                print(f"    Checking {subset_str}:")
                print(f"      closure = {closure_str}")
                print(f"      CANDIDATE KEY")
                print()
            else:
                if len(candidate) <= 3:   # limit noise for large schemas
                    print(f"    Checking {subset_str}:")
                    print(f"      closure = {closure_str}")
                    print(f"      Not a key")
                    print()

        if is_key:
            candidate_keys.append(frozenset(candidate))

    if not candidate_keys:
        raise RuntimeError(
            "ERROR: No candidate key found. Check your FDs and schema.\n"
            "       Every relation must have at least one candidate key."
        )

    return candidate_keys


def get_prime_attributes(candidate_keys: list[frozenset]) -> set:
    """
    Return the set of all prime attributes (those in at least one candidate key).

    Args:
        candidate_keys: List of frozenset candidate keys.

    Returns:
        A set of prime attribute names.
    """
    prime: set[str] = set()
    for ck in candidate_keys:
        prime |= ck
    return prime


def get_non_prime_attributes(schema: set, candidate_keys: list[frozenset]) -> set:
    """
    Return the set of non-prime attributes (not in any candidate key).

    Args:
        schema:         Full relation attribute set.
        candidate_keys: List of frozenset candidate keys.

    Returns:
        A set of non-prime attribute names.
    """
    return schema - get_prime_attributes(candidate_keys)


def summarise_keys(
    schema: set,
    candidate_keys: list[frozenset],
) -> None:
    """
    Print a concise summary of candidate keys, prime, and non-prime attributes.

    Args:
        schema:         Full relation attribute set.
        candidate_keys: List of frozenset candidate keys.
    """
    prime = get_prime_attributes(candidate_keys)
    non_prime = get_non_prime_attributes(schema, candidate_keys)
    keys_str = ", ".join(attrs_to_str(ck) for ck in candidate_keys)

    print(f"  Candidate Keys Found : {keys_str}")
    print(f"  Prime Attributes     : {attrs_to_str(prime)}")
    print(f"  Non-Prime Attributes : {attrs_to_str(non_prime)}")

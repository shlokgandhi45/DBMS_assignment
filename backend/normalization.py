"""
normalization.py — Relational Normalization (1NF, 2NF, 3NF, BCNF)
==================================================================
Provides:
  • check_1nf         — 1NF check (atomicity assumption)
  • is_in_2nf         — 2NF violation detection
  • decompose_2nf     — 2NF decomposition (remove partial dependencies)
  • is_in_3nf         — 3NF violation detection
  • find_minimal_cover— Canonical / minimal cover computation
  • decompose_3nf     — 3NF synthesis algorithm
  • is_in_bcnf        — BCNF violation detection
  • decompose_bcnf    — BCNF decomposition algorithm (lossless; may lose FDs)

Flask-ready: All functions accept/return plain Python objects.
"""

from closure import compute_closure
from candidate_keys import (
    find_candidate_keys,
    get_prime_attributes,
    get_non_prime_attributes,
)
from utils import (
    power_set,
    is_superkey,
    project_fds,
    format_relation,
    attrs_to_str,
)
from parser import format_fd


# ============================================================
# 1NF
# ============================================================

def check_1nf(schema: set, verbose: bool = True) -> bool:
    """
    Check whether the relation satisfies 1NF.

    For this project we assume all attributes are atomic (stored as scalars,
    no repeating groups or set-valued attributes).  1NF is therefore satisfied
    by definition whenever the schema is non-empty.

    Args:
        schema:  Full relation attribute set.
        verbose: If True, print a confirmation message.

    Returns:
        True (always, given the atomicity assumption).
    """
    # Flask-ready: call this function directly from a route handler
    if not schema:
        raise ValueError("Schema is empty — cannot check 1NF.")

    if verbose:
        print(
            "  ✓ Relation is in 1NF.\n"
            "    Assumption: All attributes are atomic (single-valued, indivisible).\n"
            "    No repeating groups or multi-valued attributes are present."
        )
    return True


# ============================================================
# 2NF helpers
# ============================================================

def _find_partial_dependencies(
    schema: set,
    fds: list[tuple[frozenset, frozenset]],
    candidate_keys: list[frozenset],
) -> list[tuple[frozenset, frozenset]]:
    """
    Identify all partial dependencies in the relation.

    A partial dependency occurs when a non-prime attribute Y is functionally
    determined by a *proper subset* of *some* candidate key.

    Args:
        schema:         Full relation attribute set.
        fds:            List of (lhs, rhs) FD tuples.
        candidate_keys: List of frozenset candidate keys.

    Returns:
        A list of (lhs, rhs) FD tuples that are partial dependencies.
        RHS contains only non-prime attributes.
    """
    prime = get_prime_attributes(candidate_keys)
    non_prime = get_non_prime_attributes(schema, candidate_keys)
    partial_deps: list[tuple[frozenset, frozenset]] = []

    # Find all non-trivial closures of proper subsets of candidate keys
    for ck in candidate_keys:
        for subset in power_set(set(ck)):
            if subset == ck:
                continue  # not a *proper* subset
            if not subset:
                continue
            # Compute closure of this proper subset
            closure = compute_closure(set(subset), fds, schema, verbose=False)
            # Non-prime attributes determined by this proper subset
            determined_non_prime = frozenset(closure & non_prime)
            if determined_non_prime:
                partial_dep = (frozenset(subset), determined_non_prime)
                # Avoid duplicates
                if partial_dep not in partial_deps:
                    partial_deps.append(partial_dep)

    return partial_deps


# ============================================================
# 2NF
# ============================================================

def is_in_2nf(
    schema: set,
    fds: list[tuple[frozenset, frozenset]],
    candidate_keys: list[frozenset],
    verbose: bool = True,
) -> bool:
    """
    Check whether the relation is in 2NF.

    2NF requires:
      - The relation is in 1NF (assumed).
      - There are NO partial dependencies (no non-prime attribute is determined
        by a proper subset of any candidate key).

    If every candidate key is a single attribute, 2NF is automatically satisfied.

    Args:
        schema:         Full relation attribute set.
        fds:            List of (lhs, rhs) FD tuples.
        candidate_keys: List of frozenset candidate keys.
        verbose:        If True, print detailed violation report.

    Returns:
        True if the relation is in 2NF, False otherwise.
    """
    # Flask-ready: call this function directly from a route handler
    # 2NF is trivially satisfied when all candidate keys are single-attribute
    all_atomic_keys = all(len(ck) == 1 for ck in candidate_keys)
    if all_atomic_keys:
        if verbose:
            print(
                "  ✓ All candidate keys are single-attribute.\n"
                "    Partial dependencies are impossible → Relation is in 2NF."
            )
        return True

    partial_deps = _find_partial_dependencies(schema, fds, candidate_keys)
    if not partial_deps:
        if verbose:
            print("  ✓ No partial dependencies found. Relation is in 2NF.")
        return True

    if verbose:
        print("  ✗ Partial dependencies found (2NF violations):")
        for lhs, rhs in partial_deps:
            print(f"    {format_fd(lhs, rhs)}")
    return False


def decompose_2nf(
    schema: set,
    fds: list[tuple[frozenset, frozenset]],
    candidate_keys: list[frozenset],
    relation_name: str = "R",
    verbose: bool = True,
) -> list[dict]:
    """
    Decompose a relation into 2NF by eliminating partial dependencies.

    Algorithm:
      1. Find all partial dependencies.
      2. Group them by their LHS.
      3. For each group create a new relation:
           Attributes = LHS ∪ {determined non-prime attributes}
           Primary key = LHS
      4. The main relation retains:
           - All prime attributes (candidate key attributes)
           - Non-prime attributes that depend FULLY on every candidate key
             (not involved in any partial dependency)

    Args:
        schema:          Full relation attribute set.
        fds:             List of (lhs, rhs) FD tuples.
        candidate_keys:  List of frozenset candidate keys.
        relation_name:   Base name for generated relations (e.g. "R").
        verbose:         If True, print decomposition steps.

    Returns:
        A list of relation dicts, each with keys:
          'name', 'attributes', 'primary_key', 'fds'.
    """
    # Flask-ready: call this function directly from a route handler
    all_atomic_keys = all(len(ck) == 1 for ck in candidate_keys)
    if all_atomic_keys:
        # Already in 2NF; return original relation
        result = _build_relation_dict(relation_name, schema, candidate_keys[0], fds)
        if verbose:
            print(f"  All candidate keys are single-attribute.")
            print(f"  Relation {relation_name} is already in 2NF. No decomposition needed.")
            print()
            print(format_relation(result))
        return [result]

    partial_deps = _find_partial_dependencies(schema, fds, candidate_keys)
    if not partial_deps:
        result = _build_relation_dict(relation_name, schema, candidate_keys[0], fds)
        if verbose:
            print(f"  No partial dependencies. Relation {relation_name} stays intact.")
            print(format_relation(result))
        return [result]

    prime = get_prime_attributes(candidate_keys)

    # Group partial deps by LHS
    lhs_groups: dict[frozenset, frozenset] = {}
    for lhs, rhs in partial_deps:
        lhs_groups[lhs] = lhs_groups.get(lhs, frozenset()) | rhs

    # Collect attributes covered by partial deps
    partial_dep_attrs: set[str] = set()
    for rhs in lhs_groups.values():
        partial_dep_attrs |= set(rhs)

    relations: list[dict] = []
    counter = 1

    # --- Sub-relations for each partial-dep group ---------------------------
    for lhs, rhs in lhs_groups.items():
        sub_attrs = set(lhs) | set(rhs)
        sub_fds = project_fds(fds, sub_attrs)
        rel = {
            "name": f"{relation_name}{counter}",
            "attributes": sub_attrs,
            "primary_key": set(lhs),
            "fds": sub_fds,
        }
        relations.append(rel)
        counter += 1

    # --- Main relation: prime attrs + fully-dependent non-prime attrs -------
    main_attrs = prime | (schema - prime - partial_dep_attrs)
    main_fds = project_fds(fds, main_attrs)
    # Primary key of main relation: pick the first candidate key whose attrs ⊆ main_attrs
    main_pk = next(
        (set(ck) for ck in candidate_keys if ck <= main_attrs),
        prime,  # fallback
    )
    main_rel = {
        "name": f"{relation_name}{counter}",
        "attributes": main_attrs,
        "primary_key": main_pk,
        "fds": main_fds,
    }
    relations.append(main_rel)

    # Remove trivially single-attribute relations (already in all NFs)
    relations = [r for r in relations if len(r["attributes"]) > 1]

    if verbose:
        print(f"  Decomposed into {len(relations)} relation(s) in 2NF:\n")
        for rel in relations:
            print(format_relation(rel))
            print()

    return relations


# ============================================================
# 3NF helpers
# ============================================================

def _find_transitive_dependencies(
    schema: set,
    fds: list[tuple[frozenset, frozenset]],
    candidate_keys: list[frozenset],
) -> list[tuple[frozenset, frozenset]]:
    """
    Find all transitive dependencies in the relation.

    A transitive dependency X → Y exists when:
      - X is NOT a superkey of the full relation
      - Y contains at least one non-prime attribute
      - Y ⊄ X (non-trivial)

    Args:
        schema:         Full relation attribute set.
        fds:            List of (lhs, rhs) FD tuples.
        candidate_keys: List of frozenset candidate keys.

    Returns:
        List of (lhs, rhs) FD tuples that are transitive dependencies.
    """
    prime = get_prime_attributes(candidate_keys)
    non_prime = get_non_prime_attributes(schema, candidate_keys)

    transitive: list[tuple[frozenset, frozenset]] = []
    for lhs, rhs in fds:
        # Skip trivial FDs
        effective_rhs = rhs - lhs
        if not effective_rhs:
            continue
        # Non-prime part of RHS
        non_prime_rhs = effective_rhs & non_prime
        if not non_prime_rhs:
            continue
        # LHS must NOT be a superkey
        if is_superkey(set(lhs), schema, fds):
            continue
        dep = (lhs, frozenset(non_prime_rhs))
        if dep not in transitive:
            transitive.append(dep)

    return transitive


# ============================================================
# 3NF
# ============================================================

def is_in_3nf(
    schema: set,
    fds: list[tuple[frozenset, frozenset]],
    candidate_keys: list[frozenset],
    verbose: bool = True,
) -> bool:
    """
    Check whether the relation is in 3NF.

    3NF requires that for every non-trivial FD X → Y:
      - X is a superkey, OR
      - Every attribute in Y is a prime attribute.

    Equivalently: no non-prime attribute depends (directly or transitively)
    on a non-superkey set.

    Args:
        schema:         Full relation attribute set.
        fds:            List of (lhs, rhs) FD tuples.
        candidate_keys: List of frozenset candidate keys.
        verbose:        If True, print detailed violation report.

    Returns:
        True if in 3NF, False otherwise.
    """
    # Flask-ready: call this function directly from a route handler
    prime = get_prime_attributes(candidate_keys)
    violations: list[tuple[frozenset, frozenset]] = []

    for lhs, rhs in fds:
        effective_rhs = rhs - lhs
        if not effective_rhs:
            continue
        # Check 3NF condition
        if not is_superkey(set(lhs), schema, fds):
            non_prime_rhs = effective_rhs - prime
            if non_prime_rhs:
                violations.append((lhs, frozenset(non_prime_rhs)))

    if not violations:
        if verbose:
            print("  ✓ No 3NF violations found. Relation is in 3NF.")
        return True

    if verbose:
        print("  ✗ 3NF violations (non-superkey LHS determining non-prime attributes):")
        for lhs, rhs in violations:
            lhs_type = "non-prime" if not lhs <= prime else "prime subset"
            print(f"    {format_fd(lhs, rhs)}")
            print(f"      (LHS {attrs_to_str(lhs)} is not a superkey; "
                  f"RHS {attrs_to_str(rhs)} contains non-prime attributes)")
    return False


def find_minimal_cover(
    fds: list[tuple[frozenset, frozenset]],
    schema: set,
) -> list[tuple[frozenset, frozenset]]:
    """
    Compute the minimal (canonical) cover of a set of FDs.

    Steps:
      1. Decompose RHS so each FD has exactly one attribute on the RHS.
      2. Remove extraneous attributes from each LHS.
      3. Remove redundant FDs (those derivable from the remaining set).

    Args:
        fds:    List of (lhs, rhs) FD tuples.
        schema: Full relation schema (used for closure computations).

    Returns:
        A list of (lhs, rhs) FD tuples forming the minimal cover.
    """
    # Step 1: Split RHS — one attribute per FD
    single: list[tuple[frozenset, frozenset]] = []
    for lhs, rhs in fds:
        for attr in rhs:
            candidate = (lhs, frozenset({attr}))
            if candidate not in single:
                single.append(candidate)

    # Step 2: Remove extraneous attributes from LHS
    minimised: list[tuple[frozenset, frozenset]] = list(single)
    changed = True
    while changed:
        changed = False
        new_minimised: list[tuple[frozenset, frozenset]] = []
        for i, (lhs, rhs) in enumerate(minimised):
            if len(lhs) == 1:
                new_minimised.append((lhs, rhs))
                continue
            # Try removing each attribute from LHS
            reduced = False
            for attr in list(lhs):
                reduced_lhs = lhs - frozenset({attr})
                # Check if rhs is still derivable without `attr` in lhs
                remaining_fds = [fd for j, fd in enumerate(minimised) if j != i]
                remaining_fds.append((reduced_lhs, rhs))
                closure = compute_closure(set(reduced_lhs), remaining_fds, schema, verbose=False)
                if rhs <= closure:
                    # `attr` is extraneous in lhs
                    new_minimised.append((reduced_lhs, rhs))
                    reduced = True
                    changed = True
                    break
            if not reduced:
                new_minimised.append((lhs, rhs))
        minimised = new_minimised

    # Step 3: Remove redundant FDs
    non_redundant: list[tuple[frozenset, frozenset]] = []
    for i, (lhs, rhs) in enumerate(minimised):
        # Check if removing this FD still lets us derive lhs → rhs
        remaining = [fd for j, fd in enumerate(minimised) if j != i]
        closure = compute_closure(set(lhs), remaining, schema, verbose=False)
        if rhs <= closure:
            pass  # FD is redundant — drop it
        else:
            non_redundant.append((lhs, rhs))

    # Merge FDs with identical LHS back together
    merged: dict[frozenset, frozenset] = {}
    for lhs, rhs in non_redundant:
        merged[lhs] = merged.get(lhs, frozenset()) | rhs

    return [(lhs, rhs) for lhs, rhs in merged.items()]


def decompose_3nf(
    schema: set,
    fds: list[tuple[frozenset, frozenset]],
    candidate_keys: list[frozenset],
    relation_name: str = "R",
    verbose: bool = True,
) -> list[dict]:
    """
    Decompose a relation into 3NF using the **synthesis algorithm**.

    Algorithm:
      1. Compute minimal cover of the FD set.
      2. For each FD (X → Y) in the minimal cover, create relation (X ∪ Y) with PK = X.
      3. If no resulting relation contains any candidate key of the original schema,
         add a relation that holds one candidate key.
      4. Remove redundant relations (whose attributes are a subset of another).

    The result is guaranteed to be lossless-join and dependency preserving.

    Args:
        schema:         Full relation attribute set.
        fds:            List of (lhs, rhs) FD tuples.
        candidate_keys: List of frozenset candidate keys.
        relation_name:  Base name for generated relations.
        verbose:        If True, print all steps.

    Returns:
        A list of relation dicts with keys 'name', 'attributes', 'primary_key', 'fds'.
    """
    # Flask-ready: call this function directly from a route handler
    if verbose:
        print("  Step 1: Computing minimal cover …")

    min_cover = find_minimal_cover(fds, schema)

    if verbose:
        print("    Minimal cover FDs:")
        for lhs, rhs in min_cover:
            print(f"      {format_fd(lhs, rhs)}")
        print()
        print("  Step 2: Creating relations from minimal cover …")

    relations: list[dict] = []
    counter = 1

    for lhs, rhs in min_cover:
        sub_attrs = set(lhs) | set(rhs)
        if len(sub_attrs) <= 1:
            continue  # Skip trivial single-attribute relations
        sub_fds = project_fds(fds, sub_attrs)
        rel = {
            "name": f"{relation_name}{counter}",
            "attributes": sub_attrs,
            "primary_key": set(lhs),
            "fds": sub_fds,
        }
        relations.append(rel)
        if verbose:
            print(format_relation(rel))
            print()
        counter += 1

    # Step 3: Ensure at least one relation contains a candidate key
    has_candidate_key = any(
        any(ck <= frozenset(r["attributes"]) for ck in candidate_keys)
        for r in relations
    )
    if not has_candidate_key:
        ck = candidate_keys[0]
        ck_fds = project_fds(fds, set(ck))
        ck_rel = {
            "name": f"{relation_name}{counter}",
            "attributes": set(ck),
            "primary_key": set(ck),
            "fds": ck_fds,
        }
        relations.append(ck_rel)
        if verbose:
            print(f"  Step 3: No relation contained a candidate key — adding:")
            print(format_relation(ck_rel))
            print()
        counter += 1

    # Step 4: Remove redundant relations
    attrs_list = [frozenset(r["attributes"]) for r in relations]
    non_redundant = []
    for i, rel in enumerate(relations):
        rel_attrs = frozenset(rel["attributes"])
        dominated = any(
            rel_attrs < attrs_list[j]
            for j in range(len(relations))
            if j != i
        )
        if not dominated:
            non_redundant.append(rel)

    if verbose and len(non_redundant) < len(relations):
        dropped = len(relations) - len(non_redundant)
        print(f"  Step 4: Removed {dropped} redundant relation(s).\n")

    return non_redundant


# ============================================================
# BCNF
# ============================================================

def is_in_bcnf(
    schema: set,
    fds: list[tuple[frozenset, frozenset]],
    candidate_keys: list[frozenset],
    verbose: bool = True,
) -> bool:
    """
    Check whether the relation is in BCNF.

    BCNF requires that for every non-trivial FD X → Y, X is a superkey.
    (This is stricter than 3NF, which allows Y to be prime.)

    Args:
        schema:         Full relation attribute set.
        fds:            List of (lhs, rhs) FD tuples.
        candidate_keys: Candidate keys (for display purposes).
        verbose:        If True, print violation details.

    Returns:
        True if in BCNF, False otherwise.
    """
    # Flask-ready: call this function directly from a route handler
    violations: list[tuple[frozenset, frozenset]] = []

    for lhs, rhs in fds:
        effective_rhs = rhs - lhs
        if not effective_rhs:
            continue
        if not is_superkey(set(lhs), schema, fds):
            violations.append((lhs, effective_rhs))

    if not violations:
        if verbose:
            print("  ✓ No BCNF violations found. Relation is in BCNF.")
        return True

    if verbose:
        print("  ✗ BCNF violations (LHS is not a superkey):")
        for lhs, rhs in violations:
            print(f"    {format_fd(lhs, rhs)}")
            print(f"      (LHS {attrs_to_str(lhs)} is not a superkey of the relation)")
    return False


def decompose_bcnf(
    schema: set,
    fds: list[tuple[frozenset, frozenset]],
    candidate_keys: list[frozenset],
    relation_name: str = "R",
    verbose: bool = True,
) -> list[dict]:
    """
    Decompose a relation into BCNF using the lossless-join decomposition algorithm.

    Algorithm (recursive):
      1. If the relation is already in BCNF, return it as-is.
      2. Find a violating FD X → Y (X is not a superkey).
      3. Decompose into:
           R1 = X ∪ Y            (PK = X)
           R2 = X ∪ (schema − Y) (the "remainder", PK TBD via projection)
      4. Project FDs onto each sub-relation.
      5. Recursively apply to R1 and R2.
      6. After recursion, detect any FDs lost in the decomposition and warn.

    Note: BCNF decomposition is always lossless-join but may NOT preserve
          all functional dependencies.

    Args:
        schema:         Full relation attribute set.
        fds:            List of (lhs, rhs) FD tuples.
        candidate_keys: Candidate keys of the original (full) relation.
        relation_name:  Base name for sub-relations.
        verbose:        If True, print each decomposition step.

    Returns:
        A list of relation dicts in BCNF.
    """
    # Flask-ready: call this function directly from a route handler

    # Use a counter passed by reference via a mutable container
    counter_ref = [1]
    original_fds = list(fds)
    original_schema = set(schema)
    lost_fds: list[tuple[frozenset, frozenset]] = []

    def _decompose(sub_schema: set, sub_fds: list, depth: int) -> list[dict]:
        """Recursive inner helper."""
        if len(sub_schema) <= 1:
            return []  # trivially in BCNF

        # Find all candidate keys of the sub-relation
        try:
            sub_cks = find_candidate_keys(sub_schema, sub_fds, verbose=False)
        except RuntimeError:
            # If no key found (degenerate sub-relation), treat the whole set as key
            sub_cks = [frozenset(sub_schema)]

        # Check for BCNF violation
        violating_fd: tuple[frozenset, frozenset] | None = None
        for lhs, rhs in sub_fds:
            eff_rhs = rhs - lhs
            if not eff_rhs:
                continue
            if not is_superkey(set(lhs), sub_schema, sub_fds):
                violating_fd = (lhs, eff_rhs)
                break

        if violating_fd is None:
            # Sub-relation is in BCNF
            rel = {
                "name": f"{relation_name}{counter_ref[0]}",
                "attributes": sub_schema,
                "primary_key": set(sub_cks[0]) if sub_cks else sub_schema,
                "fds": sub_fds,
            }
            counter_ref[0] += 1
            if verbose:
                indent = "  " * depth
                print(f"{indent}{format_relation(rel)}")
                print()
            return [rel]

        lhs, rhs = violating_fd
        r1_attrs = set(lhs) | set(rhs)
        r2_attrs = set(lhs) | (sub_schema - set(rhs))

        if verbose:
            indent = "  " * depth
            print(
                f"{indent}BCNF violation: {format_fd(lhs, rhs)}\n"
                f"{indent}  Decomposing into:\n"
                f"{indent}    R_a = {attrs_to_str(r1_attrs)}\n"
                f"{indent}    R_b = {attrs_to_str(r2_attrs)}\n"
            )

        r1_fds = project_fds(sub_fds, r1_attrs)
        r2_fds = project_fds(sub_fds, r2_attrs)

        return _decompose(r1_attrs, r1_fds, depth + 1) + _decompose(r2_attrs, r2_fds, depth + 1)

    result_relations = _decompose(set(schema), list(fds), 0)

    # --- Check for lost FDs -------------------------------------------------
    all_result_attrs = [frozenset(r["attributes"]) for r in result_relations]
    for lhs, rhs in original_fds:
        # An FD X → Y is preserved iff there exists a result relation
        # whose attribute set contains X ∪ Y
        preserved = any((lhs | rhs) <= r_attrs for r_attrs in all_result_attrs)
        if not preserved:
            lost_fds.append((lhs, rhs))

    if lost_fds and verbose:
        print("  ⚠  WARNING: The following FDs are NOT preserved in the BCNF decomposition:")
        for lhs, rhs in lost_fds:
            print(f"       {format_fd(lhs, rhs)}")
        print()

    return result_relations


# ============================================================
# Internal helpers
# ============================================================

def _build_relation_dict(
    name: str,
    attrs: set,
    pk: frozenset | set,
    fds: list[tuple[frozenset, frozenset]],
) -> dict:
    """
    Build a relation dict from raw components.

    Args:
        name: Relation name.
        attrs: Attribute set.
        pk:   Primary key attribute set.
        fds:  FDs relevant to this relation.

    Returns:
        A dict with keys 'name', 'attributes', 'primary_key', 'fds'.
    """
    return {
        "name": name,
        "attributes": set(attrs),
        "primary_key": set(pk),
        "fds": project_fds(fds, set(attrs)),
    }


# ============================================================
# 1NF — DETAILED CHECK & DECOMPOSITION  (NEW ADDITION)
# Original check_1nf() above is UNTOUCHED.
# ============================================================
import re as _re


def check_1nf_detailed(schema: set) -> dict:
    """
    Detailed 1NF check: detects repeating groups (Phone1, Phone2)
    and common multi-valued attribute names (PhoneNumbers, Emails).

    Returns a dict suitable for the API (unlike check_1nf which returns bool).
    """
    if not schema:
        raise ValueError("Schema is empty — cannot check 1NF.")

    violations = []
    attr_list = sorted(schema)

    # 1. Detect repeating groups: Phone1, Phone2, Email1, Email2 …
    prefixes = {}
    for attr in attr_list:
        m = _re.match(r'^([A-Za-z_]+)(\d+)$', attr)
        if m:
            prefixes.setdefault(m.group(1), []).append(attr)
    for prefix, group in prefixes.items():
        if len(group) > 1:
            violations.append({
                "type": "repeating_group",
                "attributes": sorted(group),
                "message": "Repeating attribute group detected: " + ", ".join(sorted(group)),
            })

    # 2. Detect common multi-valued / plural attribute names
    already_flagged = {a for v in violations for a in v["attributes"]}
    MULTIVAL = {
        "phones", "phonenumbers", "emails", "emailaddresses",
        "addresses", "numbers", "ids", "tags", "skills", "hobbies",
    }
    for attr in attr_list:
        if attr in already_flagged:
            continue
        if attr.lower().replace("_", "").replace(" ", "") in MULTIVAL:
            violations.append({
                "type": "multi_valued",
                "attributes": [attr],
                "message": "Attribute '" + attr + "' appears multi-valued (non-atomic by convention).",
            })

    return {"is_1nf": len(violations) == 0, "violations": violations}


def decompose_1nf(
    schema: set,
    fds: list,
    candidate_keys: list,
    relation_name: str = "R",
) -> list:
    """
    Decompose into 1NF by extracting repeating / multi-valued attributes
    into child relations linked via the primary key.
    """
    result = check_1nf_detailed(schema)
    if result["is_1nf"]:
        return [{
            "name": relation_name,
            "attributes": set(schema),
            "primary_key": set(candidate_keys[0]) if candidate_keys else set(),
            "fds": fds,
        }]

    pk = set(candidate_keys[0]) if candidate_keys else set()
    problematic = {a for v in result["violations"] for a in v["attributes"]}
    remaining = schema - problematic

    relations = [{
        "name": relation_name + "_Base",
        "attributes": remaining | pk,
        "primary_key": pk,
        "fds": project_fds(fds, remaining | pk),
    }]

    for v in result["violations"]:
        v_attrs = set(v["attributes"])
        raw = sorted(v_attrs)[0]
        # strip trailing digits (repeating groups)
        clean = _re.sub(r'\d+$', '', raw)
        # strip trailing plural 's' (multi-valued)
        if v["type"] == "multi_valued" and len(clean) > 3 and clean.lower().endswith("s"):
            clean = clean[:-1]
        sub_attrs = pk | v_attrs
        relations.append({
            "name": relation_name + "_" + clean.capitalize(),
            "attributes": sub_attrs,
            "primary_key": pk | v_attrs,
            "fds": project_fds(fds, sub_attrs),
        })

    return relations

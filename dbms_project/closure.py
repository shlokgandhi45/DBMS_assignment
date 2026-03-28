"""
closure.py — Attribute Closure Computation
==========================================
Implements the standard fixed-point algorithm for computing
the attribute closure X+ under a set of functional dependencies.

Flask-ready: All functions accept/return plain Python objects.
"""

from parser import format_fd


def compute_closure(
    attributes: set,
    fds: list[tuple[frozenset, frozenset]],
    schema: set,
    verbose: bool = True,
) -> set:
    """
    Compute the attribute closure of a given set of attributes under the given FDs.

    Uses the standard chase / fixed-point algorithm:
      1. closure ← copy of attributes
      2. Repeat until no change:
           For each FD (X → Y):
               If X ⊆ closure  →  closure ← closure ∪ Y
      3. Return closure

    Args:
        attributes: The starting set of attributes whose closure to compute.
        fds:        List of (lhs: frozenset, rhs: frozenset) FD tuples.
        schema:     The full relation schema (used only for completeness checking).
        verbose:    If True, print each step of the algorithm.

    Returns:
        The full attribute closure as a set.

    Example:
        >>> compute_closure({"BookingID"}, fds, schema)
        {'BookingID', 'CustomerID', ...}  # all 12 attributes
    """
    # Flask-ready: call this function directly from a route handler
    # Input/output are JSON-serializable (convert set to sorted list before returning)

    closure: set[str] = set(attributes)
    step = 1

    if verbose:
        attrs_display = "{" + ", ".join(sorted(attributes)) + "}"
        print(f"  Computing closure of {attrs_display}:")
        print(f"    Step {step}: Start → {{{', '.join(sorted(closure))}}}")

    changed = True
    while changed:
        changed = False
        for lhs, rhs in fds:
            # Skip trivial FDs (entirely already in closure)
            new_attrs = rhs - closure
            if lhs <= closure and new_attrs:
                closure |= new_attrs
                step += 1
                changed = True
                if verbose:
                    fd_str = format_fd(lhs, rhs)
                    print(
                        f"    Step {step}: Applied [{fd_str}]"
                        f"\n             → {{{', '.join(sorted(closure))}}}"
                    )

    if verbose:
        determines_all = closure >= schema
        suffix = " ✓ Determines entire schema" if determines_all else ""
        print(f"    Final closure = {{{', '.join(sorted(closure))}}}{suffix}")

    return closure


def closure_verbose_demo(
    demo_sets: list[set],
    fds: list[tuple[frozenset, frozenset]],
    schema: set,
) -> dict[str, set]:
    """
    Run compute_closure with verbose output for a list of demonstration attribute sets.

    Args:
        demo_sets: List of attribute sets to demo closure for.
        fds:       List of (lhs, rhs) FD tuples.
        schema:    Full relation schema.

    Returns:
        A dict mapping each demo set's string representation to its closure.
    """
    results: dict[str, set] = {}
    for attr_set in demo_sets:
        key_str = "{" + ", ".join(sorted(attr_set)) + "}"
        result = compute_closure(attr_set, fds, schema, verbose=True)
        results[key_str] = result
        print()
    return results

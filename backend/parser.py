"""
parser.py — Schema and Functional Dependency Parser
====================================================
Parses human-readable schema and FD strings into Python objects
that the rest of the DBMS pipeline can consume.

Flask-ready: All functions return plain Python objects (str, set, list, tuple).
"""

import re
from typing import Optional


def parse_schema(schema_str: str, fd_strings: Optional[list[str]] = None) -> tuple[str, set]:
    """
    Parse a relation schema string into a relation name and attribute set.

    Args:
        schema_str: Schema in format "R(A, B, C, D)" — relation name followed
                    by a parenthesised, comma-separated attribute list.
        fd_strings: Optional list of FD strings; if provided, validates that
                    all FD attributes appear in the parsed schema.

    Returns:
        A tuple (relation_name: str, attributes: set[str]).

    Raises:
        ValueError: If the format is invalid or if an FD attribute is absent
                    from the schema (only when fd_strings is provided).

    Example:
        >>> parse_schema("R(A, B, C)")
        ('R', {'A', 'B', 'C'})
    """
    # Flask-ready: call this function directly from a route handler
    # Input/output are JSON-serializable (convert sets to sorted lists before returning)

    schema_str = schema_str.strip()
    match = re.fullmatch(r"(\w+)\((.+)\)", schema_str)
    if not match:
        raise ValueError(
            f"Invalid schema format: '{schema_str}'. "
            "Expected format: 'RelationName(Attr1, Attr2, ...)'"
        )

    relation_name = match.group(1).strip()
    raw_attrs = match.group(2)

    if not raw_attrs.strip():
        raise ValueError("Schema must have at least one attribute.")

    attributes: set[str] = {attr.strip() for attr in raw_attrs.split(",")}
    if "" in attributes:
        raise ValueError("Schema contains an empty attribute name (check for stray commas).")

    return relation_name, attributes


def parse_fds(fd_list: list[str], schema: set) -> list[tuple[frozenset, frozenset]]:
    """
    Parse a list of FD strings into a list of (LHS, RHS) frozenset pairs.

    Args:
        fd_list:  List of FD strings in format "A, B -> C, D".
        schema:   The full attribute set of the relation. Used to validate
                  that every attribute mentioned in any FD belongs to the schema.

    Returns:
        A list of 2-tuples (lhs: frozenset[str], rhs: frozenset[str]).

    Raises:
        ValueError: If any FD string is malformed (missing "->", empty LHS/RHS),
                    or if an attribute is not present in the schema.

    Example:
        >>> parse_fds(["A -> B, C", "B -> D"], {"A","B","C","D"})
        [(frozenset({'A'}), frozenset({'B', 'C'})), (frozenset({'B'}), frozenset({'D'}))]
    """
    # Flask-ready: call this function directly from a route handler
    # Input/output are JSON-serializable (convert frozensets to sorted lists before returning)

    if not fd_list:
        raise ValueError("FD list is empty. Provide at least one functional dependency.")
    if not schema:
        raise ValueError("Schema is empty. Cannot validate FD attributes.")

    parsed: list[tuple[frozenset, frozenset]] = []

    for raw_fd in fd_list:
        raw_fd = raw_fd.strip()
        if "->" not in raw_fd:
            raise ValueError(
                f"Malformed FD '{raw_fd}': missing '->' separator."
            )

        parts = raw_fd.split("->", maxsplit=1)
        lhs_str, rhs_str = parts[0].strip(), parts[1].strip()

        if not lhs_str:
            raise ValueError(f"Malformed FD '{raw_fd}': LHS is empty.")
        if not rhs_str:
            raise ValueError(f"Malformed FD '{raw_fd}': RHS is empty.")

        lhs: frozenset[str] = frozenset(attr.strip() for attr in lhs_str.split(","))
        rhs: frozenset[str] = frozenset(attr.strip() for attr in rhs_str.split(","))

        if "" in lhs:
            raise ValueError(f"Malformed FD '{raw_fd}': LHS contains an empty attribute.")
        if "" in rhs:
            raise ValueError(f"Malformed FD '{raw_fd}': RHS contains an empty attribute.")

        # Validate each attribute against the schema
        for attr in lhs | rhs:
            if attr not in schema:
                raise ValueError(
                    f"Attribute '{attr}' in FD '{raw_fd}' not found in schema. "
                    f"Known attributes: {sorted(schema)}"
                )

        parsed.append((lhs, rhs))

    return parsed


def format_fd(lhs: frozenset, rhs: frozenset) -> str:
    """
    Format a single FD tuple as a human-readable string.

    Args:
        lhs: The left-hand side frozenset of attributes.
        rhs: The right-hand side frozenset of attributes.

    Returns:
        A string like "A, B → C, D".
    """
    lhs_str = ", ".join(sorted(lhs))
    rhs_str = ", ".join(sorted(rhs))
    return f"{lhs_str} → {rhs_str}"

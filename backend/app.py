"""
app.py — Flask REST API for the DBMS Normalization Tool
========================================================
Exposes three endpoints:
  POST /closure          — Compute attribute closure (with step trace)
  POST /candidate-keys   — Find all candidate keys
  POST /normalize        — Decompose into 2NF, 3NF, and/or BCNF

All routes return JSON. Uses flask-cors for cross-origin requests.
"""

import logging
import sys
import os

from flask import Flask, request, jsonify, render_template
from flask_cors import CORS

# ── Ensure the backend directory is on sys.path so sibling modules resolve ──
sys.path.insert(0, os.path.dirname(__file__))

from parser import parse_schema, parse_fds, format_fd
from closure import compute_closure
from candidate_keys import (
    find_candidate_keys,
    get_prime_attributes,
    get_non_prime_attributes,
)
from normalization import (
    check_1nf_detailed,
    decompose_1nf,
    is_in_2nf,
    is_in_3nf,
    is_in_bcnf,
    decompose_2nf,
    decompose_3nf,
    decompose_bcnf,
)
from utils import relation_to_json, is_superkey

# ── Logging setup ─────────────────────────────────────────────────────────────
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    datefmt="%H:%M:%S",
)
logger = logging.getLogger(__name__)

# ── Flask app ─────────────────────────────────────────────────────────────────
import os
frontend_dir = os.path.join(os.path.dirname(os.path.dirname(__file__)), "frontend")
app = Flask(__name__, 
            template_folder=frontend_dir,
            static_folder=os.path.join(frontend_dir, "static"))
CORS(app)  # Allow all origins (needed for file:// and localhost dev)


# ── Internal helpers (not exposed as routes) ──────────────────────────────────

def _compute_closure_with_steps(
    attributes: set,
    fds: list[tuple[frozenset, frozenset]],
    schema: set,
) -> tuple[set, list[str]]:
    """
    Compute attribute closure and return both the final closure and a human-readable
    step trace suitable for the API response.

    Args:
        attributes: Starting attribute set.
        fds:        List of (lhs, rhs) FD tuples.
        schema:     Full relation schema.

    Returns:
        (closure: set, steps: list[str])
    """
    closure: set[str] = set(attributes)
    steps: list[str] = [f"Start: {{{', '.join(sorted(closure))}}}"]

    changed = True
    while changed:
        changed = False
        for lhs, rhs in fds:
            new_attrs = rhs - closure
            if lhs <= closure and new_attrs:
                closure |= new_attrs
                added_str = ", ".join(sorted(new_attrs))
                lhs_str = ", ".join(sorted(lhs))
                rhs_str = ", ".join(sorted(rhs))
                steps.append(
                    f"Applied [{lhs_str} \u2192 {rhs_str}] \u2192 Added: {added_str}"
                )
                changed = True

    steps.append("No more FDs applicable. Closure complete.")
    return closure, steps


def _extract_2nf_violations(
    schema: set,
    fds: list[tuple[frozenset, frozenset]],
    candidate_keys: list[frozenset],
) -> list[str]:
    """
    Return human-readable 2NF violation strings.

    A violation exists when a non-prime attribute is determined by a proper
    subset of some candidate key.

    Args:
        schema:         Full relation schema.
        fds:            List of (lhs, rhs) FD tuples.
        candidate_keys: All candidate keys.

    Returns:
        List of violation description strings.
    """
    from utils import power_set

    prime = get_prime_attributes(candidate_keys)
    non_prime = get_non_prime_attributes(schema, candidate_keys)
    violations: list[str] = []
    seen: set[tuple] = set()

    for ck in candidate_keys:
        for subset in power_set(set(ck)):
            if subset >= ck or not subset:
                continue
            closure = compute_closure(set(subset), fds, schema, verbose=False)
            determined_np = frozenset(closure & non_prime)
            if determined_np:
                key = (frozenset(subset), determined_np)
                if key not in seen:
                    seen.add(key)
                    lhs_str = ", ".join(sorted(subset))
                    rhs_str = ", ".join(sorted(determined_np))
                    violations.append(
                        f"{lhs_str} \u2192 {rhs_str} "
                        f"(partial: {lhs_str} is a proper subset of candidate key "
                        f"{{{', '.join(sorted(ck))}}})"
                    )

    return violations


def _extract_3nf_violations(
    schema: set,
    fds: list[tuple[frozenset, frozenset]],
    candidate_keys: list[frozenset],
) -> list[str]:
    """
    Return human-readable 3NF violation strings.

    A violation is a non-trivial FD X \u2192 Y where X is not a superkey and Y
    contains non-prime attributes.

    Args:
        schema:         Full relation schema.
        fds:            List of (lhs, rhs) FD tuples.
        candidate_keys: All candidate keys.

    Returns:
        List of violation description strings.
    """
    prime = get_prime_attributes(candidate_keys)
    violations: list[str] = []

    for lhs, rhs in fds:
        eff_rhs = rhs - lhs
        if not eff_rhs:
            continue
        if not is_superkey(set(lhs), schema, fds):
            non_prime_rhs = eff_rhs - prime
            if non_prime_rhs:
                lhs_str = ", ".join(sorted(lhs))
                rhs_str = ", ".join(sorted(non_prime_rhs))
                violations.append(
                    f"{lhs_str} \u2192 {rhs_str} "
                    f"(transitive: {lhs_str} is non-prime / not a superkey)"
                )

    return violations


def _extract_bcnf_violations(
    schema: set,
    fds: list[tuple[frozenset, frozenset]],
) -> list[str]:
    """
    Return human-readable BCNF violation strings.

    A violation is any non-trivial FD X \u2192 Y where X is not a superkey.

    Args:
        schema: Full relation schema.
        fds:    List of (lhs, rhs) FD tuples.

    Returns:
        List of violation description strings.
    """
    violations: list[str] = []
    for lhs, rhs in fds:
        eff_rhs = rhs - lhs
        if not eff_rhs:
            continue
        if not is_superkey(set(lhs), schema, fds):
            lhs_str = ", ".join(sorted(lhs))
            rhs_str = ", ".join(sorted(eff_rhs))
            violations.append(
                f"{lhs_str} \u2192 {rhs_str} "
                f"(BCNF violation: {lhs_str} is not a superkey)"
            )
    return violations


def _detect_lost_fds(
    original_fds: list[tuple[frozenset, frozenset]],
    result_relations: list[dict],
) -> list[str]:
    """
    Detect FDs from the original relation that are not preserved in any
    resulting sub-relation after BCNF decomposition.

    Args:
        original_fds:     FD list of the original relation.
        result_relations: List of decomposed relation dicts.

    Returns:
        List of human-readable strings for each lost FD.
    """
    lost: list[str] = []
    all_attrs = [frozenset(r["attributes"]) for r in result_relations]
    for lhs, rhs in original_fds:
        preserved = any((lhs | rhs) <= r_attrs for r_attrs in all_attrs)
        if not preserved:
            lost.append(
                f"{', '.join(sorted(lhs))} \u2192 {', '.join(sorted(rhs))}"
            )
    return lost


# ── Route: /closure ───────────────────────────────────────────────────────────

@app.route("/closure", methods=["POST"])
def route_closure():
    """
    POST /closure
    Compute the attribute closure of a given set under the provided FDs.

    Flask-ready: accepts JSON body, returns JSON response.

    Request JSON:
        schema (str): Relation schema string, e.g. "R(A, B, C)".
        fds (list[str]): FD strings, e.g. ["A -> B", "B -> C"].
        attributes (list[str]): Starting attribute set.

    Returns:
        JSON with keys: success, input_attributes, closure, steps, determines_all.
        HTTP 400 on validation errors, HTTP 500 on unexpected errors.
    """
    try:
        body = request.get_json(force=True, silent=True) or {}

        schema_str: str = body.get("schema", "").strip()
        fd_strings: list = body.get("fds", [])
        attr_list: list = body.get("attributes", [])

        if not schema_str:
            return jsonify({"success": False, "error": "Field 'schema' is required."}), 400
        if not fd_strings:
            return jsonify({"success": False, "error": "Field 'fds' is required and must not be empty."}), 400
        if not attr_list:
            return jsonify({"success": False, "error": "Field 'attributes' is required and must not be empty."}), 400

        _, schema = parse_schema(schema_str)
        fds = parse_fds(fd_strings, schema)

        attributes: set[str] = {a.strip() for a in attr_list}
        for attr in attributes:
            if attr not in schema:
                return jsonify({
                    "success": False,
                    "error": f"Attribute '{attr}' not found in schema. "
                             f"Known attributes: {sorted(schema)}",
                }), 400

        closure, steps = _compute_closure_with_steps(attributes, fds, schema)
        determines_all = closure >= schema

        logger.info("POST /closure — closure of %s computed successfully", sorted(attributes))
        return jsonify({
            "success": True,
            "input_attributes": sorted(attributes),
            "closure": sorted(closure),
            "steps": steps,
            "determines_all": determines_all,
        })

    except ValueError as exc:
        logger.warning("POST /closure — validation error: %s", exc)
        return jsonify({"success": False, "error": str(exc)}), 400
    except Exception as exc:
        logger.error("POST /closure — unexpected error: %s", exc, exc_info=True)
        return jsonify({"success": False, "error": "Internal server error. Check backend logs."}), 500


# ── Route: /candidate-keys ────────────────────────────────────────────────────

@app.route("/candidate-keys", methods=["POST"])
def route_candidate_keys():
    """
    POST /candidate-keys
    Find all candidate keys of the given relation.

    Flask-ready: accepts JSON body, returns JSON response.

    Request JSON:
        schema (str): Relation schema string.
        fds (list[str]): FD strings.

    Returns:
        JSON with keys: success, candidate_keys, prime_attributes, non_prime_attributes.
        HTTP 400 on validation errors, HTTP 500 on unexpected errors.
    """
    try:
        body = request.get_json(force=True, silent=True) or {}

        schema_str: str = body.get("schema", "").strip()
        fd_strings: list = body.get("fds", [])

        if not schema_str:
            return jsonify({"success": False, "error": "Field 'schema' is required."}), 400
        if not fd_strings:
            return jsonify({"success": False, "error": "Field 'fds' is required and must not be empty."}), 400

        _, schema = parse_schema(schema_str)
        fds = parse_fds(fd_strings, schema)

        candidate_keys = find_candidate_keys(schema, fds, verbose=False)
        prime = get_prime_attributes(candidate_keys)
        non_prime = get_non_prime_attributes(schema, candidate_keys)

        logger.info(
            "POST /candidate-keys — found %d key(s): %s",
            len(candidate_keys),
            [sorted(ck) for ck in candidate_keys],
        )
        return jsonify({
            "success": True,
            "candidate_keys": [sorted(ck) for ck in candidate_keys],
            "prime_attributes": sorted(prime),
            "non_prime_attributes": sorted(non_prime),
        })

    except ValueError as exc:
        logger.warning("POST /candidate-keys — validation error: %s", exc)
        return jsonify({"success": False, "error": str(exc)}), 400
    except RuntimeError as exc:
        logger.warning("POST /candidate-keys — runtime error: %s", exc)
        return jsonify({"success": False, "error": str(exc)}), 400
    except Exception as exc:
        logger.error("POST /candidate-keys — unexpected error: %s", exc, exc_info=True)
        return jsonify({"success": False, "error": "Internal server error. Check backend logs."}), 500


# ── Route: /normalize ─────────────────────────────────────────────────────────

@app.route("/normalize", methods=["POST"])
def route_normalize():
    """
    POST /normalize
    Decompose the relation into 2NF, 3NF, and/or BCNF.

    Flask-ready: accepts JSON body, returns JSON response.

    Request JSON:
        schema (str):   Relation schema string.
        fds (list[str]):FD strings.
        target (str):   Optional. "2NF", "3NF", or "BCNF". Defaults to "ALL".

    Returns:
        JSON with key 'results' containing one entry per requested normal form.
        Each entry has: already_satisfied, violations, relations, (optional) warnings.
        HTTP 400 on validation errors, HTTP 500 on unexpected errors.
    """
    try:
        body = request.get_json(force=True, silent=True) or {}

        schema_str: str = body.get("schema", "").strip()
        fd_strings: list = body.get("fds", [])
        target: str = body.get("target", "ALL").upper()

        if not schema_str:
            return jsonify({"success": False, "error": "Field 'schema' is required."}), 400
        if not fd_strings:
            return jsonify({"success": False, "error": "Field 'fds' is required and must not be empty."}), 400
        if target not in ("1NF", "2NF", "3NF", "BCNF", "ALL"):
            return jsonify({
                "success": False,
                "error": f"Invalid target '{target}'. Must be one of: 1NF, 2NF, 3NF, BCNF, ALL.",
            }), 400

        relation_name, schema = parse_schema(schema_str)
        fds = parse_fds(fd_strings, schema)
        candidate_keys = find_candidate_keys(schema, fds, verbose=False)

        results: dict = {}

        # ── 1NF ──────────────────────────────────────────────────────────────
        if target in ("1NF", "ALL"):
            check_1nf_res = check_1nf_detailed(schema)
            already_1nf = check_1nf_res["is_1nf"]
            violations_1nf = [v["message"] for v in check_1nf_res["violations"]]

            if already_1nf:
                rels_1nf = [{
                    "name": relation_name,
                    "attributes": sorted(schema),
                    "primary_key": sorted(candidate_keys[0]) if candidate_keys else [],
                    "fds": [{"lhs": sorted(l), "rhs": sorted(r)} for l, r in fds],
                }]
            else:
                raw_1nf = decompose_1nf(schema, fds, candidate_keys, relation_name=relation_name)
                rels_1nf = [relation_to_json(r) for r in raw_1nf]

            results["1NF"] = {
                "already_satisfied": already_1nf,
                "violations": violations_1nf,
                "problematic_attributes": [a for v in check_1nf_res["violations"] for a in v["attributes"]],
                "relations": rels_1nf,
            }

        # ── 2NF ──────────────────────────────────────────────────────────────
        if target in ("2NF", "ALL"):
            already_2nf = is_in_2nf(schema, fds, candidate_keys, verbose=False)
            violations_2nf = [] if already_2nf else _extract_2nf_violations(schema, fds, candidate_keys)
            if already_2nf:
                # Return original relation when already satisfied
                rels_2nf = [{
                    "name": relation_name,
                    "attributes": sorted(schema),
                    "primary_key": sorted(candidate_keys[0]),
                    "fds": [{"lhs": sorted(l), "rhs": sorted(r)} for l, r in fds],
                }]
            else:
                raw_2nf = decompose_2nf(schema, fds, candidate_keys, relation_name=relation_name, verbose=False)
                rels_2nf = [relation_to_json(r) for r in raw_2nf]

            results["2NF"] = {
                "already_satisfied": already_2nf,
                "violations": violations_2nf,
                "relations": rels_2nf,
            }

        # ── 3NF ──────────────────────────────────────────────────────────────
        if target in ("3NF", "ALL"):
            already_3nf = is_in_3nf(schema, fds, candidate_keys, verbose=False)
            violations_3nf = [] if already_3nf else _extract_3nf_violations(schema, fds, candidate_keys)
            if already_3nf:
                rels_3nf = [{
                    "name": relation_name,
                    "attributes": sorted(schema),
                    "primary_key": sorted(candidate_keys[0]),
                    "fds": [{"lhs": sorted(l), "rhs": sorted(r)} for l, r in fds],
                }]
            else:
                raw_3nf = decompose_3nf(schema, fds, candidate_keys, relation_name=relation_name, verbose=False)
                rels_3nf = [relation_to_json(r) for r in raw_3nf]

            results["3NF"] = {
                "already_satisfied": already_3nf,
                "violations": violations_3nf,
                "relations": rels_3nf,
            }

        # ── BCNF ─────────────────────────────────────────────────────────────
        if target in ("BCNF", "ALL"):
            already_bcnf = is_in_bcnf(schema, fds, candidate_keys, verbose=False)
            violations_bcnf = [] if already_bcnf else _extract_bcnf_violations(schema, fds)
            if already_bcnf:
                rels_bcnf = [{
                    "name": relation_name,
                    "attributes": sorted(schema),
                    "primary_key": sorted(candidate_keys[0]),
                    "fds": [{"lhs": sorted(l), "rhs": sorted(r)} for l, r in fds],
                }]
                lost_fds: list[str] = []
            else:
                raw_bcnf = decompose_bcnf(schema, fds, candidate_keys, relation_name=relation_name, verbose=False)
                rels_bcnf = [relation_to_json(r) for r in raw_bcnf]
                lost_fds = _detect_lost_fds(fds, raw_bcnf)

            bcnf_entry: dict = {
                "already_satisfied": already_bcnf,
                "violations": violations_bcnf,
                "relations": rels_bcnf,
            }
            if lost_fds:
                bcnf_entry["fd_preservation_warning"] = (
                    "The following FDs are NOT preserved in the BCNF decomposition: "
                    + "; ".join(f"[{fd}]" for fd in lost_fds)
                )
            results["BCNF"] = bcnf_entry

        logger.info("POST /normalize — target=%s completed successfully", target)
        return jsonify({
            "success": True,
            "target": target,
            "results": results,
        })

    except ValueError as exc:
        logger.warning("POST /normalize — validation error: %s", exc)
        return jsonify({"success": False, "error": str(exc)}), 400
    except RuntimeError as exc:
        logger.warning("POST /normalize — runtime error: %s", exc)
        return jsonify({"success": False, "error": str(exc)}), 400
    except Exception as exc:
        logger.error("POST /normalize — unexpected error: %s", exc, exc_info=True)
        return jsonify({"success": False, "error": "Internal server error. Check backend logs."}), 500


# ── Health check ──────────────────────────────────────────────────────────────

@app.route("/", methods=["GET"])
def root():
    """GET / — Serves the frontend UI."""
    return render_template("index.html")


@app.route("/health", methods=["GET"])
def health():
    """GET /health — Simple liveness probe for the backend."""
    return jsonify({"status": "ok", "message": "DBMS Normalization API is running."})


@app.route("/test", methods=["GET"])
def test():
    """GET /test — Quick sanity check route."""
    return jsonify({"message": "Backend working"})


# ── Entry point ───────────────────────────────────────────────────────────────

if __name__ == "__main__":
    import socket

    def is_port_in_use(port):
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            return s.connect_ex(('localhost', port)) == 0

    port = 5000
    if is_port_in_use(port):
        logger.warning("Port %d is busy, switching to 5001", port)
        port = 5001
    
    logger.info("="*55)
    logger.info(" DBMS Normalization API + UI")
    logger.info(f" Local:   http://127.0.0.1:{port}")
    logger.info(f" Network: http://0.0.0.0:{port}")
    logger.info("="*55)
    app.run(debug=True, use_reloader=False, host="0.0.0.0", port=port)

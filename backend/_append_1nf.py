"""Appends check_1nf_detailed and decompose_1nf to backend/normalization.py"""
import os

NEW_CODE = r'''

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
'''

target = os.path.join(os.path.dirname(__file__), "normalization.py")
with open(target, "a", encoding="utf-8") as f:
    f.write(NEW_CODE)

print("Done — 1NF functions appended to", target)

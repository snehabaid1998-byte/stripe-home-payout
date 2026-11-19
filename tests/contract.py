"""Minimal JSON Schema checker for the payout state contract (standard library only).

Supports what the contract uses: type, enum, const, pattern, minLength, minimum,
exclusiveMinimum, exclusiveMaximum, required, additionalProperties, $ref to $defs,
and allOf with if/then/else.
"""
import json
import re
from pathlib import Path

SCHEMA_PATH = Path(__file__).resolve().parent.parent / "specs" / "001-payout-status" / "contracts" / "payout-state.schema.json"
SCHEMA = json.loads(SCHEMA_PATH.read_text(encoding="utf-8"))

TYPES = {
    "string": lambda v: isinstance(v, str),
    "integer": lambda v: isinstance(v, int) and not isinstance(v, bool),
    "null": lambda v: v is None,
    "object": lambda v: isinstance(v, dict),
}


def _resolve(node):
    if "$ref" in node:
        ref = node["$ref"].split("/")[-1]
        merged = dict(SCHEMA["$defs"][ref])
        merged.update({k: v for k, v in node.items() if k != "$ref"})
        return merged
    return node


def _errors(value, node, path="$"):
    node = _resolve(node)
    errs = []
    if "type" in node:
        types = node["type"] if isinstance(node["type"], list) else [node["type"]]
        if not any(TYPES[t](value) for t in types):
            return [f"{path}: {value!r} is not {types}"]
    if "enum" in node and value not in node["enum"]:
        errs.append(f"{path}: {value!r} not in enum")
    if "const" in node and value != node["const"]:
        errs.append(f"{path}: {value!r} != {node['const']!r}")
    if isinstance(value, str):
        if "pattern" in node and not re.search(node["pattern"], value):
            errs.append(f"{path}: {value!r} does not match {node['pattern']}")
        if "minLength" in node and len(value) < node["minLength"]:
            errs.append(f"{path}: too short")
    if isinstance(value, int) and not isinstance(value, bool):
        if "minimum" in node and value < node["minimum"]:
            errs.append(f"{path}: {value} < {node['minimum']}")
        if "exclusiveMinimum" in node and value <= node["exclusiveMinimum"]:
            errs.append(f"{path}: {value} <= {node['exclusiveMinimum']}")
        if "exclusiveMaximum" in node and value >= node["exclusiveMaximum"]:
            errs.append(f"{path}: {value} >= {node['exclusiveMaximum']}")
    if isinstance(value, dict):
        for key in node.get("required", []):
            if key not in value:
                errs.append(f"{path}: missing {key}")
        props = node.get("properties", {})
        if node.get("additionalProperties") is False:
            errs += [f"{path}: extra field {k}" for k in value if k not in props]
        for key, sub in props.items():
            if key in value:
                errs += _errors(value[key], sub, f"{path}.{key}")
    for rule in node.get("allOf", []):
        if "if" in rule:
            branch = rule.get("then") if not _errors(value, rule["if"], path) else rule.get("else")
            if branch:
                errs += _errors(value, branch, path)
        else:
            errs += _errors(value, rule, path)
    return errs


def contract_errors(response):
    return _errors(response, SCHEMA)

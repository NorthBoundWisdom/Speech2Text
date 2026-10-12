from __future__ import annotations

import json
from functools import lru_cache
from importlib.resources import files
from typing import Any, cast

JsonObject = dict[str, Any]

_CONTRACT_RESOURCE = "data/service_contract.json"
_ARRAY_TYPES = {"argv", "path_array", "string_array"}


@lru_cache
def load_service_contract() -> JsonObject:
    payload = files("atot").joinpath(_CONTRACT_RESOURCE).read_text(encoding="utf-8")
    return cast(JsonObject, json.loads(payload))


def service_method_specs(contract: JsonObject | None = None) -> dict[str, JsonObject]:
    payload = contract or load_service_contract()
    methods = payload.get("methods", [])
    if not isinstance(methods, list):
        raise ValueError("Service contract methods must be a list.")
    specs: dict[str, JsonObject] = {}
    for item in methods:
        if not isinstance(item, dict) or not isinstance(item.get("name"), str):
            raise ValueError("Every service contract method needs a string name.")
        name = cast(str, item["name"])
        if name in specs:
            raise ValueError(f"Duplicate service contract method: {name}")
        specs[name] = cast(JsonObject, item)
    return specs


def validate_service_request(
    method: str,
    params: dict[str, Any],
    *,
    allow_extra: bool = True,
    contract: JsonObject | None = None,
) -> None:
    specs = service_method_specs(contract)
    spec = specs.get(method)
    if spec is None:
        raise ValueError(f"Unknown service method: {method}")

    param_specs = _param_specs(spec)
    missing = [
        name
        for name, param in param_specs.items()
        if bool(param.get("required", False)) and name not in params
    ]
    if missing:
        raise ValueError(
            f"Missing required service params for {method}: {', '.join(sorted(missing))}"
        )

    if not allow_extra:
        unknown = sorted(set(params) - set(param_specs))
        if unknown:
            raise ValueError(f"Unknown service params for {method}: {', '.join(unknown)}")

    type_errors = [
        f"{name} must be {_type_label(str(param_specs[name].get('type', 'any')))}"
        for name, value in params.items()
        if name in param_specs
        and not _matches_type(value, str(param_specs[name].get("type", "any")))
    ]
    if type_errors:
        raise ValueError(f"Invalid service params for {method}: {'; '.join(type_errors)}")

    item_errors = [
        f"{name} needs at least {int(param_specs[name]['min_items'])} item(s)"
        for name, value in params.items()
        if name in param_specs
        and str(param_specs[name].get("type", "")) in _ARRAY_TYPES
        and "min_items" in param_specs[name]
        and isinstance(value, list)
        and len(value) < int(param_specs[name]["min_items"])
    ]
    if item_errors:
        raise ValueError(f"Invalid service params for {method}: {'; '.join(item_errors)}")


def _param_specs(method_spec: JsonObject) -> dict[str, JsonObject]:
    params = method_spec.get("params", [])
    if not isinstance(params, list):
        raise ValueError(
            f"Service contract method {method_spec.get('name')} params must be a list."
        )
    specs: dict[str, JsonObject] = {}
    for item in params:
        if not isinstance(item, dict) or not isinstance(item.get("name"), str):
            raise ValueError(f"Invalid service contract param in method {method_spec.get('name')}.")
        name = cast(str, item["name"])
        if name in specs:
            raise ValueError(
                f"Duplicate service contract param {name} in method {method_spec.get('name')}."
            )
        specs[name] = cast(JsonObject, item)
    return specs


def _matches_type(value: Any, type_name: str) -> bool:
    if value is None:
        return True
    if type_name in {"path", "string"}:
        return isinstance(value, str)
    if type_name == "boolean":
        return isinstance(value, bool)
    if type_name == "integer":
        return isinstance(value, int) and not isinstance(value, bool)
    if type_name == "number":
        return isinstance(value, (int, float)) and not isinstance(value, bool)
    if type_name in _ARRAY_TYPES:
        return isinstance(value, list) and all(isinstance(item, str) for item in value)
    if type_name == "any":
        return True
    raise ValueError(f"Unknown service contract param type: {type_name}")


def _type_label(type_name: str) -> str:
    if type_name in {"path", "string"}:
        return "a string"
    if type_name == "boolean":
        return "a boolean"
    if type_name == "integer":
        return "an integer"
    if type_name == "number":
        return "a number"
    if type_name in _ARRAY_TYPES:
        return "a list of strings"
    return "a JSON value"

from __future__ import annotations

import pytest

from atot import cli
from atot.service_contract import (
    load_service_contract,
    service_method_specs,
    validate_service_request,
)
from atot.service_protocol import handle_service_request
from atot.workflow_service import WorkflowService


def test_service_contract_declares_valid_method_params() -> None:
    contract = load_service_contract()
    specs = service_method_specs(contract)

    assert specs
    for method, spec in specs.items():
        assert spec["handler"]
        params = {
            item["name"]: _example_value(item["type"])
            for item in spec["params"]
            if item.get("required")
        }
        validate_service_request(method, params, allow_extra=False, contract=contract)


def test_service_contract_cli_paths_are_real_commands(capsys: pytest.CaptureFixture[str]) -> None:
    for spec in service_method_specs().values():
        path = spec.get("cli")
        if not path:
            continue

        rc = cli.main([*path, "--help"])

        assert rc == 0, path
        assert capsys.readouterr().out


def test_service_contract_rejects_missing_required_params() -> None:
    with pytest.raises(ValueError, match="Missing required service params for transcribe: input"):
        validate_service_request("transcribe", {})


def test_service_contract_rejects_wrong_param_types() -> None:
    with pytest.raises(ValueError, match="inputs must be a list of strings"):
        validate_service_request("srt", {"inputs": "episode.mp4"})


def test_service_contract_rejects_unknown_params_in_strict_mode() -> None:
    with pytest.raises(ValueError, match="Unknown service params for qa: extra"):
        validate_service_request("qa", {"output": "work/show", "extra": True}, allow_extra=False)


def test_service_contract_rejects_empty_required_arrays() -> None:
    with pytest.raises(ValueError, match="inputs needs at least 1 item"):
        validate_service_request("srt", {"inputs": []})


def test_stdio_service_uses_shared_contract_before_dispatch() -> None:
    response = handle_service_request(
        {"id": "1", "method": "transcribe", "params": {}}, service=WorkflowService()
    )

    assert response["ok"] is False
    assert response["error"]["type"] == "ValueError"
    assert "Missing required service params for transcribe: input" in response["error"]["message"]


def _example_value(type_name: str) -> object:
    if type_name in {"path", "string"}:
        return "value"
    if type_name == "boolean":
        return True
    if type_name == "integer":
        return 1
    if type_name == "number":
        return 1.0
    if type_name in {"argv", "path_array", "string_array"}:
        return ["value"]
    if type_name == "any":
        return "value"
    raise AssertionError(f"Unhandled service contract type: {type_name}")

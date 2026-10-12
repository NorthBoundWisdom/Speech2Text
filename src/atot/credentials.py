from __future__ import annotations

import os
from pathlib import Path
import sys
import tempfile
from typing import Any, Protocol, cast

import tomlkit

SERVICE = "org.audio2text.cloud"
STORE = "system"


class CredentialBackend(Protocol):
    def get_password(self, service: str, username: str) -> str | None: ...
    def set_password(self, service: str, username: str, password: str) -> None: ...
    def delete_password(self, service: str, username: str) -> None: ...


def credential_backend() -> CredentialBackend:
    # Select native encrypted storage directly: never accept a plaintext plugin backend.
    if sys.platform == "darwin":
        from keyring.backends.macOS import Keyring
        return cast(CredentialBackend, Keyring())  # type: ignore[no-untyped-call]
    if sys.platform == "win32":
        from keyring.backends.Windows import WinVaultKeyring
        return cast(CredentialBackend, WinVaultKeyring())  # type: ignore[no-untyped-call]
    raise RuntimeError("Cloud credential storage requires macOS Keychain or Windows Credential Manager.")


def account(path: Path) -> str:
    return str(path.expanduser().resolve())


def read_api_key(path: Path) -> str:
    try:
        value = credential_backend().get_password(SERVICE, account(path))
    except Exception as exc:
        raise RuntimeError("Cannot read the system cloud credential store. Unlock it and retry.") from exc
    if value is None:
        raise RuntimeError("The configured cloud credential is missing from the system store.")
    return value


def store_api_key(path: Path, value: str) -> None:
    try:
        backend = credential_backend()
        if value:
            backend.set_password(SERVICE, account(path), value)
        elif backend.get_password(SERVICE, account(path)) is not None:
            backend.delete_password(SERVICE, account(path))
    except Exception as exc:
        raise RuntimeError("Cannot save the cloud credential in system storage. Configuration was not rewritten.") from exc


def write_private_config(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    if path.is_symlink():
        raise ValueError("Config file must not be a symlink.")
    fd, name = tempfile.mkstemp(prefix=".config-", dir=path.parent)
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as handle:
            handle.write(text)
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(name, path)
    finally:
        Path(name).unlink(missing_ok=True)


def resolve_api_key(path: Path, cloud: dict[str, Any]) -> str:
    legacy = cloud.get("api_key", "")
    if isinstance(legacy, str) and legacy.strip():
        # First persist securely, then erase the plaintext atomically. Keep it on failure.
        document = tomlkit.parse(path.read_text(encoding="utf-8"))
        store_api_key(path, legacy.strip())
        document["cloud"]["api_key"] = ""
        document["cloud"]["api_key_store"] = STORE
        write_private_config(path, tomlkit.dumps(document))
        cloud["api_key"] = ""
        cloud["api_key_store"] = STORE
        return legacy.strip()
    store = cloud.get("api_key_store", "")
    if store and store != STORE:
        raise ValueError("Unknown cloud.api_key_store. Only system storage is supported.")
    return read_api_key(path) if store == STORE else ""

from configs import ios_workflow
import pytest


def test_app_build_settings_read_active_source_roots_lock(tmp_path, monkeypatch):
    active_lock = tmp_path / "source_roots.lock.jsonc"
    active_lock.write_text(
        """
        {
          // Active source-root values drive package versions.
          "AppConfigs": {
            "MARKETING_VERSION": "2.3.4",
            "ARCHIVE_ID": "56",
          }
        }
        """,
        encoding="utf-8",
    )
    monkeypatch.setattr(ios_workflow, "SOURCE_ROOTS_ACTIVE_LOCK", active_lock)

    assert ios_workflow._app_build_settings() == {
        "MARKETING_VERSION": "2.3.4",
        "ARCHIVE_ID": "56",
    }


def test_package_dmg_path_includes_version():
    assert ios_workflow._package_dmg_path("1.2.3", "45").name == "Audio2Text_v1.2.3_45.dmg"


def test_package_uses_audio2textcli_name():
    assert ios_workflow.CLI_NAME == "Audio2TextCli"


def test_package_defaults_to_development_distribution():
    args = ios_workflow.build_parser().parse_args(["package"])

    assert args.distribution == "development"


def test_build_accepts_ios_platform_and_selects_ios_scheme():
    args = ios_workflow.build_parser().parse_args(["build", "--platform", "ios"])

    assert args.platform == "ios"
    assert ios_workflow._selected_scheme(args.platform, args.scheme) == ios_workflow.IOS_SCHEME_NAME


def test_ios_package_is_rejected(monkeypatch):
    monkeypatch.setattr(ios_workflow, "_ensure_local_app_config", lambda: None)

    assert ios_workflow.main(["package", "--platform", "ios"]) == 1


def test_development_identity_returns_sha1(monkeypatch):
    monkeypatch.setattr(
        ios_workflow,
        "_list_codesigning_identities",
        lambda: [
            ("A" * 40, "Apple Development: Ethan Kang (9SU2C8FL8D)"),
            ("B" * 40, "Apple Development: Ethan Kang (9SU2C8FL8D)"),
        ],
    )

    assert ios_workflow._select_development_identity() == "A" * 40


def test_developer_id_identity_returns_sha1(monkeypatch):
    monkeypatch.setattr(
        ios_workflow,
        "_list_codesigning_identities",
        lambda: [
            ("A" * 40, "Apple Development: Ethan Kang (9SU2C8FL8D)"),
            ("B" * 40, "Developer ID Application: Ethan Kang (9SU2C8FL8D)"),
        ],
    )

    assert ios_workflow._select_developer_id_identity() == "B" * 40


def test_website_codesign_does_not_use_sandbox_entitlements(tmp_path, monkeypatch):
    app = tmp_path / "Audio2Text.app"
    executable = app / "Contents" / "MacOS" / ios_workflow.PRODUCT_NAME
    executable.parent.mkdir(parents=True)
    executable.write_text("", encoding="utf-8")
    commands = []
    monkeypatch.setattr(ios_workflow, "_run", lambda cmd, **_: commands.append(cmd))

    ios_workflow._codesign_for_website(app, "A" * 40)

    flattened = [item for command in commands for item in command]
    assert "--entitlements" not in flattened
    assert "runtime" in flattened


def test_developer_id_codesign_uses_secure_timestamp(tmp_path, monkeypatch):
    app = tmp_path / "Audio2Text.app"
    executable = app / "Contents" / "MacOS" / ios_workflow.PRODUCT_NAME
    executable.parent.mkdir(parents=True)
    executable.write_text("", encoding="utf-8")
    commands = []
    monkeypatch.setattr(ios_workflow, "_select_developer_id_identity", lambda: "A" * 40)
    monkeypatch.setattr(ios_workflow, "_run", lambda cmd, **_: commands.append(cmd))

    ios_workflow._codesign_for_developer_id(app)

    flattened = [item for command in commands for item in command]
    assert "--timestamp" in flattened
    assert "--timestamp=none" not in flattened


def test_notarize_dmg_submits_staples_and_verifies(tmp_path, monkeypatch):
    package = tmp_path / "Audio2Text.dmg"
    package.write_bytes(b"dmg")
    commands = []
    monkeypatch.setattr(
        ios_workflow.shutil,
        "which",
        lambda name: f"/usr/bin/{name}" if name in {"xcrun", "spctl"} else None,
    )
    monkeypatch.setattr(ios_workflow, "_run", lambda cmd, **_: commands.append(cmd))

    ios_workflow._notarize_dmg(package, keychain_profile="Audio2Text Release")

    assert commands[0] == [
        "/usr/bin/xcrun",
        "notarytool",
        "submit",
        str(package),
        "--keychain-profile",
        "Audio2Text Release",
        "--wait",
    ]
    assert commands[1:3] == [
        ["/usr/bin/xcrun", "stapler", "staple", str(package)],
        ["/usr/bin/xcrun", "stapler", "validate", str(package)],
    ]
    assert commands[3][0:4] == ["/usr/bin/spctl", "--assess", "--type", "open"]


def test_notary_profile_is_required(monkeypatch):
    monkeypatch.delenv(ios_workflow.NOTARY_PROFILE_ENV, raising=False)

    with pytest.raises(RuntimeError, match="Keychain profile"):
        ios_workflow._notary_profile(None)


def test_notary_profile_prefers_explicit_value_over_environment(monkeypatch):
    monkeypatch.setenv(ios_workflow.NOTARY_PROFILE_ENV, "Environment Profile")

    assert ios_workflow._notary_profile("Explicit Profile") == "Explicit Profile"


def test_developer_id_package_preflights_and_notarizes(monkeypatch, tmp_path):
    app = tmp_path / "Audio2Text.app"
    package = tmp_path / "Audio2Text.dmg"
    calls = []
    monkeypatch.setattr(
        ios_workflow,
        "_notary_profile",
        lambda value: calls.append(("profile", value)) or "Resolved Profile",
    )
    monkeypatch.setattr(ios_workflow, "_ensure_local_app_config", lambda: calls.append(("setup",)))
    monkeypatch.setattr(
        ios_workflow,
        "_package_app",
        lambda configuration, distribution: calls.append(
            ("app", configuration, distribution)
        )
        or app,
    )
    monkeypatch.setattr(
        ios_workflow, "_dmg_app_bundle", lambda value: calls.append(("dmg", value)) or package
    )
    monkeypatch.setattr(
        ios_workflow,
        "_notarize_dmg",
        lambda value, keychain_profile: calls.append(("notarize", value, keychain_profile)),
    )

    assert (
        ios_workflow.main(
            [
                "package",
                "--distribution",
                "developer-id",
                "--notary-profile",
                "Explicit Profile",
            ]
        )
        == 0
    )
    assert calls == [
        ("profile", "Explicit Profile"),
        ("setup",),
        ("app", "release", "developer-id"),
        ("dmg", app),
        ("notarize", package, "Resolved Profile"),
    ]


def test_quit_running_app_uses_bundle_quit_then_waits(monkeypatch):
    executable_path = (
        ios_workflow.REPO_ROOT / "build/app/Audio2Text.app/Contents/MacOS/Audio2TextApp"
    )
    calls = []
    monkeypatch.setattr(
        ios_workflow.subprocess, "run", lambda cmd, **kwargs: calls.append((cmd, kwargs))
    )
    pid_results = iter([["123"], []])
    monkeypatch.setattr(
        ios_workflow,
        "_running_pids_for_executable_name",
        lambda _: next(pid_results),
    )
    sleeps = []
    monkeypatch.setattr(ios_workflow.time, "sleep", lambda value: sleeps.append(value))

    ios_workflow._quit_running_app("com.audio2text.local", executable_path)

    assert calls[0][0][0] == "osascript"
    assert "com.audio2text.local" in calls[0][0][-1]
    assert sleeps == [0.2]


def test_quit_running_app_force_kills_when_process_remains(monkeypatch):
    executable_path = (
        ios_workflow.REPO_ROOT / "build/app/Audio2Text.app/Contents/MacOS/Audio2TextApp"
    )
    calls = []
    monkeypatch.setattr(
        ios_workflow.subprocess, "run", lambda cmd, **kwargs: calls.append((cmd, kwargs))
    )
    monkeypatch.setattr(ios_workflow, "_running_pids_for_executable_name", lambda _: ["123"])
    monotonic_values = iter([0, 5])
    monkeypatch.setattr(ios_workflow.time, "monotonic", lambda: next(monotonic_values))
    monkeypatch.setattr(ios_workflow.time, "sleep", lambda _: None)

    ios_workflow._quit_running_app(None, executable_path)

    assert calls == [
        (
            ["pkill", "-x", "Audio2TextApp"],
            {"cwd": ios_workflow.REPO_ROOT, "text": True, "check": False},
        )
    ]


def test_run_command_does_not_force_new_app_instance():
    script = (ios_workflow.REPO_ROOT / "configs" / "ios_workflow.py").read_text(encoding="utf-8")
    run_branch = script[
        script.index('elif args.command == "run"') : script.index('elif args.command == "test"')
    ]

    assert (
        "_quit_running_app(_app_bundle_identifier(app), _app_bundle_executable_path(app))"
        in run_branch
    )
    assert '["open", str(app)]' in run_branch
    assert '["open", "-n", str(app)]' not in run_branch

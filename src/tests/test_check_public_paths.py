import subprocess
from pathlib import Path

from scripts.check_public_paths import find_private_path_hits, find_repository_private_path_hits


def git(root: Path, *args: str) -> None:
    subprocess.run(
        ["git", *args], cwd=root, check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE
    )


def test_private_path_check_flags_public_files(tmp_path: Path):
    public_file = tmp_path / "README.md"
    public_file.write_text("path: /" + "Users/example/Documents/Audio2Text\n", encoding="utf-8")

    hits = find_private_path_hits([public_file], root=tmp_path)

    assert len(hits) == 1
    assert hits[0].label == "private absolute path"


def test_private_path_check_scans_historical_experiment_docs(tmp_path: Path):
    historical = tmp_path / "doc" / "experiments" / "note.md"
    historical.parent.mkdir(parents=True)
    historical.write_text(
        "/" + "Users/privateuser/Downloads/sample.wav\n",
        encoding="utf-8",
    )

    hits = find_private_path_hits([historical], root=tmp_path)

    assert len(hits) == 1


def test_private_path_check_flags_api_key_like_values_in_historical_experiment_docs(tmp_path: Path):
    historical = tmp_path / "doc" / "experiments" / "note.md"
    historical.parent.mkdir(parents=True)
    historical.write_text('api_key = "sk-' + ("A" * 32) + '"\n', encoding="utf-8")

    hits = find_private_path_hits([historical], root=tmp_path)

    assert len(hits) == 1
    assert hits[0].label == "API-key-like secret"


def test_private_path_check_flags_api_key_like_values(tmp_path: Path):
    public_file = tmp_path / "config.md"
    public_file.write_text('api_key = "sk-' + ("A" * 32) + '"\n', encoding="utf-8")

    hits = find_private_path_hits([public_file], root=tmp_path)

    assert len(hits) == 1
    assert hits[0].label == "API-key-like secret"


def test_private_path_check_allows_short_placeholder_keys(tmp_path: Path):
    public_file = tmp_path / "README.md"
    public_file.write_text('api_key = "sk-..."\napi_key = "sk-secret"\n', encoding="utf-8")

    hits = find_private_path_hits([public_file], root=tmp_path)

    assert hits == []


def test_private_path_check_flags_local_secret_config_file(tmp_path: Path):
    local_config = tmp_path / "app" / "cloud.local.json"
    local_config.parent.mkdir(parents=True)
    local_config.write_text("{}\n", encoding="utf-8")

    hits = find_private_path_hits([local_config], root=tmp_path)

    assert len(hits) == 1
    assert hits[0].label == "local secret config file"


def test_private_path_check_reads_staged_blob_not_just_worktree(tmp_path: Path):
    git(tmp_path, "init")
    public_file = tmp_path / "README.md"
    public_file.write_text('api_key = "sk-' + ("A" * 32) + '"\n', encoding="utf-8")
    git(tmp_path, "add", "README.md")
    public_file.write_text('api_key = "sk-..."\n', encoding="utf-8")

    hits = find_repository_private_path_hits(root=tmp_path)

    assert len(hits) == 1
    assert hits[0].path == public_file
    assert hits[0].label == "API-key-like secret"


def test_check_detects_unstaged_tracked_secrets_and_masks_output(tmp_path, capsys):
    from scripts.check_public_paths import main
    git(tmp_path, 'init')
    public = tmp_path / 'README.md'
    public.write_text('clean\n')
    git(tmp_path, 'add', 'README.md')
    secret = 'ghp_' + 'A' * 36
    public.write_text(secret + '\n')
    assert find_repository_private_path_hits(root=tmp_path, scope='staged') == []
    hits = find_repository_private_path_hits(root=tmp_path, scope='worktree')
    assert len(hits) == 1 and secret not in hits[0].text
    assert main(['--root', str(tmp_path), '--scope', 'worktree']) == 1
    assert secret not in capsys.readouterr().err


def test_check_recurses_into_current_and_staged_submodule(tmp_path):
    remote = tmp_path / 'vendor'
    remote.mkdir()
    git(remote, 'init')
    (remote / 'README.md').write_text('clean\n')
    git(remote, 'add', '.')
    git(remote, '-c', 'user.name=Test', '-c', 'user.email=test@example.com', 'commit', '-m', 'fixture')
    host = tmp_path / 'host'
    host.mkdir()
    git(host, 'init')
    git(host, '-c', 'protocol.file.allow=always', 'submodule', 'add', str(remote), 'vendor')
    file = host / 'vendor' / 'README.md'
    file.write_text('path: /' + 'home/privateuser/source\n')
    assert len(find_repository_private_path_hits(root=host, scope='worktree')) == 1
    assert find_repository_private_path_hits(root=host, scope='staged') == []
    git(host / 'vendor', 'add', '.')
    git(host / 'vendor', '-c', 'user.name=Test', '-c', 'user.email=test@example.com', 'commit', '-m', 'fixture change')
    git(host, 'add', 'vendor')
    assert len(find_repository_private_path_hits(root=host, scope='staged')) == 1


def test_check_windows_paths_and_private_keys(tmp_path):
    file = tmp_path / 'README.md'
    file.write_text('C:' + '\\Users\\privateuser\\project\n-----BEGIN ' + 'RSA PRIVATE KEY-----\n')
    hits = find_private_path_hits([file], root=tmp_path)
    assert {hit.label for hit in hits} == {'private absolute path', 'private key'}


def test_check_detects_opaque_json_credentials(tmp_path):
    public = tmp_path / 'settings.json'
    public.write_text('{"api_key": "' + 'opaque' * 6 + '"}\n')
    hits = find_private_path_hits([public], root=tmp_path)
    assert len(hits) == 1 and hits[0].label == 'credential assignment'


def test_check_detects_bare_user_home_paths(tmp_path):
    public = tmp_path / 'README.md'
    public.write_text('/' + 'Users/privateuser\n/' + 'home/privateuser\nC:' + '\\Users\\privateuser\n')
    assert len(find_private_path_hits([public], root=tmp_path)) == 3

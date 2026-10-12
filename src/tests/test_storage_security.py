
import pytest

from atot.library_store import LibraryStore
from atot.task_store import TaskStore
from atot.utils import write_json_atomic


@pytest.mark.parametrize('identifier', ['../victim', '..', '.', '/tmp/victim', r'C:\victim', 'a/b', r'a\b', 'a\x00b', 'a' * 129])
def test_library_operations_reject_paths(tmp_path, identifier):
    store = LibraryStore(tmp_path / 'library', data_root=tmp_path / 'data')
    victim = tmp_path / 'victim'
    victim.mkdir()
    (victim / 'keep').write_text('untouched')
    operations = [
        lambda: store.delete_episode(identifier), lambda: store.load_episode(identifier),
        lambda: store.upsert_episode({'episode_id': identifier, 'title': 'episode'}),
        lambda: store.write_episode_documents(identifier, summary='s', transcript='t'),
        lambda: store.write_episode_summary(identifier, summary='s', generator='test'),
        lambda: store.local_material_dir(identifier), lambda: store.local_work_dir(identifier),
        lambda: store.delete_local_episode_files(identifier),
        lambda: store.delete_subscription(identifier),
        lambda: store.upsert_subscription({'id': identifier, 'title': 'subscription'}),
    ]
    for operation in operations:
        with pytest.raises(ValueError):
            operation()
    assert (victim / 'keep').read_text() == 'untouched'


def test_delete_preflights_local_symlinks_before_removing_library(tmp_path):
    store = LibraryStore(tmp_path / 'library', data_root=tmp_path / 'data')
    store.upsert_episode({'episode_id': 'valid', 'title': 'episode'})
    victim = tmp_path / 'victim'
    victim.mkdir()
    (victim / 'keep').write_text('untouched')
    material_root = tmp_path / 'data' / 'materials'
    material_root.mkdir(parents=True)
    (material_root / 'valid').symlink_to(victim, target_is_directory=True)
    with pytest.raises(ValueError, match='root|Symlink'):
        store.delete_episode('valid')
    assert (store.episodes_root / 'valid' / 'episode.json').is_file()
    assert (victim / 'keep').read_text() == 'untouched'


@pytest.mark.parametrize('target', ['episode.json', 'documents', 'documents/transcript.md', 'documents/summary.md'])
def test_library_rejects_symlink_metadata_and_documents(tmp_path, target):
    store = LibraryStore(tmp_path / 'library', data_root=tmp_path / 'data')
    store.upsert_episode({'episode_id': 'valid', 'title': 'episode'})
    victim = tmp_path / 'victim'
    victim.mkdir()
    (victim / 'text').write_text('untouched')
    link = store.episode_dir('valid') / target
    link.parent.mkdir(parents=True, exist_ok=True)
    if link.exists():
        link.unlink()
    link.symlink_to(victim if target == 'documents' else victim / 'text')
    with pytest.raises(ValueError):
        store.load_episode('valid')
    assert (victim / 'text').read_text() == 'untouched'


def test_metadata_identity_cannot_redirect_deletion(tmp_path):
    store = LibraryStore(tmp_path / 'library')
    store.ensure()
    write_json_atomic(store.episodes_root / 'valid' / 'episode.json', {
        'episode_id': '../victim', 'title': 'episode', 'subscription_id': 'sub'})
    write_json_atomic(store.subscriptions_root / 'sub.json', {'id': 'sub'})
    with pytest.raises(ValueError):
        store.delete_subscription('sub')
    assert (store.subscriptions_root / 'sub.json').exists()


@pytest.mark.parametrize('identifier', ['../victim', '/tmp/victim', r'a\b', 'a/b'])
def test_task_store_rejects_traversal(tmp_path, identifier):
    store = TaskStore(tmp_path)
    for operation in (store.record, store.events, store.status):
        with pytest.raises(ValueError):
            operation(identifier)


def test_task_store_rejects_symlink_event_files(tmp_path):
    store = TaskStore(tmp_path / 'tasks')
    task = store.create_task('qa', 'test')
    victim = tmp_path / 'victim'
    victim.write_text('untouched')
    task.events_path.unlink()
    task.events_path.symlink_to(victim)
    with pytest.raises(ValueError):
        store.append(task, 'task.finished', success=True)
    assert victim.read_text() == 'untouched'

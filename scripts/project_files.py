"""Replace application files in place while leaving local storage untouched."""
import os
from pathlib import Path
import shutil
import uuid


LOCAL_DIRECTORIES = {
    '.git', '.venv', 'venv', 'node_modules', '__pycache__', '.pytest_cache',
    '.ruff_cache', '.mypy_cache', 'data', 'media', 'staticfiles', 'backups',
    'test-results', 'logs', '.direnv',
}
NESTED_CACHES = {'.git', '.venv', 'venv', 'node_modules', '__pycache__', '.pytest_cache', '.ruff_cache', '.mypy_cache'}


def source_files(root, protected=()):
    root = Path(root).resolve()
    protected = tuple(Path(path).resolve() for path in protected)
    files = []

    def local(path):
        relative = path.relative_to(root)
        return (relative.parts[0] in LOCAL_DIRECTORIES
                or any(part in NESTED_CACHES for part in relative.parts)
                or any(path == item or path.is_relative_to(item) for item in protected)
                or path.name == '.env'
                or path.name == 'Gravewright Runner.lnk'
                or (path.name.startswith('.env.') and path.name != '.env.example')
                or path.name.endswith(('.sqlite3', '.sqlite3-wal', '.sqlite3-shm', '.log', '.pyc')))

    for folder, directories, names in os.walk(root, followlinks=False):
        for name in directories[:]:
            path = Path(folder) / name
            if local(path):
                directories.remove(name)
            elif path.is_symlink() or path.is_junction():
                raise ValueError('Application directories must not be links or junctions')
        for name in names:
            path = Path(folder) / name
            if local(path):
                continue
            if path.is_symlink():
                raise ValueError('Application files must not be symlinks')
            files.append(path.relative_to(root).as_posix())
    return sorted(files)


def checked_path(root, name):
    root = Path(root).resolve()
    path = root / name
    if path.is_symlink() or path.is_junction() or not path.resolve().is_relative_to(root) or path.resolve() == root:
        raise ValueError('Project file escapes its installation')
    return path


def copy_files(source, target, names):
    for name in names:
        origin = checked_path(source, name)
        destination = checked_path(target, name)
        if destination.is_dir():
            destination.rmdir()  # Never remove nonempty/local directories.
        destination.parent.mkdir(parents=True, exist_ok=True)
        temporary = destination.with_name('.update-' + uuid.uuid4().hex)
        try:
            shutil.copy2(origin, temporary)
            temporary.replace(destination)
        finally:
            temporary.unlink(missing_ok=True)


def replace_files(source, target, names, previous):
    """The journal records both lists before any changes, including new files."""
    for name in sorted(set(previous) - set(names), reverse=True):
        destination = checked_path(target, name)
        destination.unlink(missing_ok=True)
        parent = destination.parent
        while parent != Path(target).resolve():
            try:
                parent.rmdir()
            except OSError:
                break
            parent = parent.parent
    copy_files(source, target, names)
    for folder in {checked_path(target, name).parent / '__pycache__'
                   for name in set(names) | set(previous) if name.endswith('.py')}:
        remove_work_tree(folder, target)


def remove_work_tree(path, parent):
    path, parent = Path(path).resolve(), Path(parent).resolve()
    if path == parent or not path.is_relative_to(parent):
        raise ValueError('Refusing to remove a directory outside updater storage')
    if path.exists():
        shutil.rmtree(path)

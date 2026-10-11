"""Content versions keep module imports and page templates in the same release."""

from functools import lru_cache
from hashlib import sha256
from pathlib import PurePosixPath

from django.contrib.staticfiles.finders import get_finders
from django.templatetags.static import static as static_url


@lru_cache(maxsize=1)
def versions():
    # Cache once per server process; application updates restart that process.
    # Finder order matches collectstatic when multiple apps provide one path.
    result = {}
    for finder in get_finders():
        for path, storage in finder.list([]):
            key = path.replace('\\', '/')
            if PurePosixPath(key).suffix not in {'.js', '.mjs', '.css'} or key in result:
                continue
            with storage.open(path, 'rb') as source:
                result[key] = sha256(source.read()).hexdigest()[:16]
    return result


def static(path):
    url = static_url(path)
    version = versions().get(path)
    return url + ('&' if '?' in url else '?') + 'v=' + version if version else url


def module_import_map():
    # Entry scripts use versioned URLs too, so a module loaded by a script tag
    # and by another module shares one instance, including relative imports.
    return {'imports': {
        static_url(path): static(path)
        for path in versions() if PurePosixPath(path).suffix in {'.js', '.mjs'}
    }}

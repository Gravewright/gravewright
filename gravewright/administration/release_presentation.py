"""Present installed release notes without requiring a network request."""

from pathlib import Path
import re
import tomllib

from .release_metadata import normalize_version, update_version_is_valid, version_label


MAX_RELEASE_NOTES_BYTES = 128 * 1024
_PROJECT_ROOT = Path(__file__).resolve().parents[2]
_REPOSITORY = re.compile(r"[A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+")


def bounded_notes(value):
    """Keep complete ordinary notes while bounding UTF-8 response/cache size."""
    return str(value or "").encode("utf-8")[:MAX_RELEASE_NOTES_BYTES].decode("utf-8", errors="ignore")


def _bundled_text(relative, limit):
    try:
        root = _PROJECT_ROOT.resolve()
        path = root / relative
        resolved = path.resolve()
        if not resolved.is_relative_to(root):
            return ""
        for component in (path, *path.parents):
            if component == root:
                break
            if component.is_symlink() or component.is_junction():
                return ""
        with resolved.open("rb") as stream:
            raw = stream.read(limit + 1)
        # A bounded read may end in the middle of a multibyte character.
        return raw[:limit].decode("utf-8", errors="ignore").replace("\r\n", "\n").replace("\r", "\n")
    except (OSError, UnicodeError, ValueError, RuntimeError):
        return ""


def _fallback_name(version):
    name = f"Gravewright {version_label(version)}"
    try:
        project = tomllib.loads(_bundled_text("pyproject.toml", 64 * 1024)).get("project", {})
        if normalize_version(str(project.get("version", ""))) == version:
            classifiers = project.get("classifiers", [])
            for classifier, stage in (("Development Status :: 3 - Alpha", "Alpha"),
                                      ("Development Status :: 4 - Beta", "Beta")):
                if classifier in classifiers and version_label(version) == version:
                    return f"{name} — {stage}"
    except (ValueError, TypeError):
        pass
    return name


def installed_release(version, repository, releases=()):
    """Decorate status only; bundled notes never become update-cache state.

    Existing 4,000-character cache bodies can be incomplete. Prefer the complete
    bundled document in that case, while retaining the published release name.
    """
    valid_version = update_version_is_valid(version)
    version = normalize_version(version)
    bundled = _bundled_text(f"docs/releases/{version}.md", MAX_RELEASE_NOTES_BYTES) if valid_version else ""
    title = re.search(r"^#\s+(.+?)\s*#*\s*$", bundled, re.MULTILINE)
    local_name = title.group(1).strip()[:240] if title else ""
    published = next((item for item in releases if isinstance(item, dict)
                      and isinstance(item.get("version"), str)
                      and normalize_version(item["version"]) == version), {}) if isinstance(releases, (list, tuple)) else {}
    published_name = str(published.get("name") or "").strip()[:240]
    published_notes = bounded_notes(published.get("notes"))
    use_bundled = bool(bundled) and (not published_notes or len(published_notes) <= 4000)
    notes = bundled if use_bundled else published_notes
    source = "bundled" if use_bundled else "published" if published_notes or published_name else "metadata"
    return {
        "version": version,
        "name": published_name or local_name or _fallback_name(version),
        "notes": notes,
        "url": f"https://github.com/{repository}/releases/tag/v{version}"
        if valid_version and _REPOSITORY.fullmatch(repository)
        and all(part not in {".", ".."} for part in repository.split("/")) else "",
        "source": source,
    }

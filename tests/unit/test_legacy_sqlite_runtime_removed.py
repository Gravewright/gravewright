from __future__ import annotations

from pathlib import Path

import app.persistence as persistence
import app.persistence.database as db_module


def test_legacy_runtime_facade_removed():
    removed_names = ["get" + "_connection", "Compat" + "Connection"]
    assert all(not hasattr(db_module, name) for name in removed_names)


def test_legacy_schema_package_removed():
    assert not Path(persistence.__path__[0], "schema").exists()

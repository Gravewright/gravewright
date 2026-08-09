"""Um banco que aplicou a 0033 pela metade tem de sarar sozinho.

A 0033 saiu numa primeira versão que acrescentava ``angle``/``rotation`` e
derrubava ``opacity``/``animated_core``, mas não trocava o CHECK de
``animation``. Quem migrou naquele momento ficou com a tabela nova e a lista de
emissões velha, e gravar uma vela falhava com ``IntegrityError``.

Corrigir o arquivo da 0033 não alcança esse banco: Alembic não reaplica revisão
carimbada. Reparo de migração aplicada mora em revisão nova — e é isso que este
teste cobra, reproduzindo o estado exato antes de rodar o upgrade.
"""
from __future__ import annotations

from pathlib import Path

import pytest
from sqlalchemy import create_engine, inspect, text
from sqlalchemy.exc import IntegrityError

import app.persistence.database as db_module
from app.persistence import engine as engine_module
from app.persistence.tables import metadata

from tests.unit.test_schema_alembic_parity import _schema_fingerprint
from tests.unit.test_schema_legacy_upgrade import _alembic_config


_OLD_CHECK = "animation IN ('none','torch','pulse')"


def _half_applied_database(path: Path) -> None:
    """Esquema completo de hoje, com ``scene_lights`` rebaixado ao estado ruim."""
    engine = create_engine(f"sqlite:///{path.as_posix()}")
    metadata.create_all(engine)
    with engine.begin() as conn:
        conn.execute(text("DROP TABLE scene_lights"))
        conn.execute(text(f"""
            CREATE TABLE scene_lights (
                id VARCHAR(64) NOT NULL,
                campaign_id VARCHAR(64) NOT NULL,
                scene_id VARCHAR(64) NOT NULL,
                x FLOAT NOT NULL,
                y FLOAT NOT NULL,
                bright_radius FLOAT DEFAULT 2.0 NOT NULL,
                dim_radius FLOAT DEFAULT 4.0 NOT NULL,
                color VARCHAR(191) DEFAULT '#ffd8a8' NOT NULL,
                intensity FLOAT DEFAULT 1.0 NOT NULL,
                animation VARCHAR(191) DEFAULT 'none' NOT NULL,
                enabled INTEGER DEFAULT 1 NOT NULL,
                created_by_user_id VARCHAR(64) NOT NULL,
                created_at INTEGER NOT NULL,
                updated_at INTEGER NOT NULL,
                angle FLOAT DEFAULT 360.0 NOT NULL,
                rotation FLOAT DEFAULT 0.0 NOT NULL,
                PRIMARY KEY (id),
                CONSTRAINT fk_scene_lights_campaign_id_campaigns
                    FOREIGN KEY(campaign_id) REFERENCES campaigns (id) ON DELETE CASCADE,
                CONSTRAINT fk_scene_lights_scene_id_scenes
                    FOREIGN KEY(scene_id) REFERENCES scenes (id) ON DELETE CASCADE,
                CONSTRAINT fk_scene_lights_created_by_user_id_users
                    FOREIGN KEY(created_by_user_id) REFERENCES users (id) ON DELETE CASCADE,
                CONSTRAINT ck_scene_lights_animation CHECK ({_OLD_CHECK})
            )
        """))
        conn.execute(text(
            "CREATE INDEX idx_scene_lights_scene ON scene_lights (scene_id, created_at)"
        ))
        # Um foco já gravado: o reparo recria a tabela, e perder a luz da mesa
        # seria pior do que o problema que ele conserta.
        conn.execute(text(
            "INSERT INTO scene_lights (id, campaign_id, scene_id, x, y,"
            " created_by_user_id, created_at, updated_at, animation, dim_radius)"
            " VALUES ('light-1','c1','s1',10,20,'u1',1,1,'torch',9.5)"
        ))
    engine.dispose()


def _insert(engine, light_id: str, animation: str) -> None:
    with engine.begin() as conn:
        conn.execute(text(
            "INSERT INTO scene_lights (id, campaign_id, scene_id, x, y,"
            " created_by_user_id, created_at, updated_at, animation)"
            f" VALUES ('{light_id}','c1','s1',10,20,'u1',1,1,'{animation}')"
        ))


def test_the_half_applied_shape_really_is_broken(tmp_path):
    """Sem esta guarda o teste abaixo poderia passar por não reproduzir nada."""
    db = tmp_path / "half.sqlite3"
    _half_applied_database(db)
    engine = create_engine(f"sqlite:///{db.as_posix()}")
    try:
        with pytest.raises(IntegrityError):
            _insert(engine, "light-2", "candle")
    finally:
        engine.dispose()


def test_the_repair_revision_reconciles_it(tmp_path, monkeypatch):
    from alembic import command

    db = tmp_path / "half.sqlite3"
    _half_applied_database(db)

    monkeypatch.setattr(db_module, "DATABASE_PATH", db)
    monkeypatch.setattr(db_module, "_initialized", False)
    engine_module.reset_engine()

    cfg = _alembic_config()
    command.stamp(cfg, "0033_light_emission_shape")
    command.upgrade(cfg, "head")
    engine_module.reset_engine()

    repaired = create_engine(f"sqlite:///{db.as_posix()}")
    reference = create_engine(f"sqlite:///{(tmp_path / 'reference.sqlite3').as_posix()}")
    metadata.create_all(reference)
    try:
        # As emissões de hoje passam a ser aceitas — o sintoma que a mesa via.
        for index, animation in enumerate(
            ("none", "torch", "pulse")
        ):
            _insert(repaired, f"new-{index}", animation)

        # E a tabela ficou igual ao metadata de hoje, não só "aceitando insert".
        assert _schema_fingerprint(repaired)["scene_lights"] == \
            _schema_fingerprint(reference)["scene_lights"]

        # O foco que já existia sobreviveu à recriação, com os valores dele.
        row = repaired.connect().execute(
            text("SELECT animation, dim_radius, angle FROM scene_lights WHERE id = 'light-1'")
        ).one()
        assert row.animation == "torch" and row.dim_radius == 9.5 and row.angle == 360.0

        assert "opacity" not in {c["name"] for c in inspect(repaired).get_columns("scene_lights")}
    finally:
        repaired.dispose()
        reference.dispose()


def test_swapping_an_emission_survives_a_row_that_still_uses_the_old_one(tmp_path, monkeypatch):
    """A troca farol → fumaça não pode ser barrada pelo próprio CHECK.

    Com um foco `beacon` gravado — que é o caso de qualquer mesa que já usou o
    tipo — as duas ordens ingênuas falham: converter antes é recusado pelo CHECK
    em vigor, que não conhece `smoke`; recriar antes é recusado pelas linhas
    `beacon` durante a cópia. Só passa alargando o CHECK no meio do caminho.
    """
    from alembic import command

    db = tmp_path / "with-beacon.sqlite3"
    engine = create_engine(f"sqlite:///{db.as_posix()}")
    metadata.create_all(engine)
    with engine.begin() as conn:
        # A tabela de hoje não aceita `beacon`; o cenário precisa da anterior.
        conn.execute(text("DROP TABLE scene_lights"))
        conn.execute(text("""
            CREATE TABLE scene_lights (
                id VARCHAR(64) NOT NULL, campaign_id VARCHAR(64) NOT NULL,
                scene_id VARCHAR(64) NOT NULL, x FLOAT NOT NULL, y FLOAT NOT NULL,
                bright_radius FLOAT DEFAULT 2.0 NOT NULL,
                dim_radius FLOAT DEFAULT 4.0 NOT NULL,
                color VARCHAR(191) DEFAULT '#ffd8a8' NOT NULL,
                intensity FLOAT DEFAULT 1.0 NOT NULL,
                animation VARCHAR(191) DEFAULT 'none' NOT NULL,
                enabled INTEGER DEFAULT 1 NOT NULL,
                created_by_user_id VARCHAR(64) NOT NULL,
                created_at INTEGER NOT NULL, updated_at INTEGER NOT NULL,
                angle FLOAT DEFAULT 360.0 NOT NULL,
                rotation FLOAT DEFAULT 0.0 NOT NULL,
                PRIMARY KEY (id),
                CONSTRAINT ck_scene_lights_animation CHECK (
                    animation IN ('none','candle','torch','fire','pulse','arcane','beacon')
                )
            )
        """))
        conn.execute(text(
            "INSERT INTO scene_lights (id, campaign_id, scene_id, x, y,"
            " created_by_user_id, created_at, updated_at, animation, dim_radius, angle)"
            " VALUES ('farol','c1','s1',10,20,'u1',1,1,'beacon',12.0,40.0)"
        ))
    engine.dispose()

    monkeypatch.setattr(db_module, "DATABASE_PATH", db)
    monkeypatch.setattr(db_module, "_initialized", False)
    engine_module.reset_engine()

    cfg = _alembic_config()
    command.stamp(cfg, "0034_light_emission_check_repair")
    command.upgrade(cfg, "head")
    engine_module.reset_engine()

    upgraded = create_engine(f"sqlite:///{db.as_posix()}")
    try:
        # O foco virou fumaça em vez de sumir: apagá-lo deixaria um buraco escuro
        # numa cena já montada, e alcance e posição continuam valendo.
        # O farol virou fumaça na 0035 e, na 0036, emissor de partícula: o foco
        # sai da tabela de luz porque ele nunca iluminou de verdade.
        assert not upgraded.connect().execute(
            text("SELECT 1 FROM scene_lights WHERE id = 'farol'")
        ).first()
        row = upgraded.connect().execute(
            text("SELECT kind, scale FROM scene_particles WHERE scene_id = 's1'")
        ).one()
        assert row.kind == "smoke"
        # O alcance do foco virou a escala da coluna de fumaça.
        assert row.scale == 12.0

        # E o CHECK terminou estreito: farol não é mais aceito.
        with pytest.raises(IntegrityError):
            _insert(upgraded, "novo", "candle")
        _insert(upgraded, "ok", "torch")
    finally:
        upgraded.dispose()

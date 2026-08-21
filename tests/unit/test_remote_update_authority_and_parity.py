from __future__ import annotations

from argparse import Namespace
from dataclasses import dataclass

from app.actions.inside.core_updates import check_core_update
from app.actions.sdk.marketplace import MarketplaceInstallForm, marketplace_install
from app.cli import packages as package_cli
from app.engine.sdk.marketplace_installer import MarketplaceInstallResult, MarketplaceInstaller


class Request:
    headers = {"accept": "application/json"}


def test_non_owner_cannot_check_core_or_start_marketplace_update() -> None:
    user = {"id": "user", "system_role": "user"}
    core = check_core_update.fn(current_user=user)
    package = marketplace_install.fn(request=Request(), current_user=user,
                                     data=MarketplaceInstallForm(package_id="demo"))
    assert core.status_code == 403
    assert package.status_code == 403


def test_cli_remote_single_and_all_use_marketplace_installer(monkeypatch) -> None:
    calls = []
    monkeypatch.setattr(MarketplaceInstaller, "install", lambda _self, *, package_id, user_id:
                        calls.append(package_id) or MarketplaceInstallResult(True, package_id))
    @dataclass
    class Installed:
        def list_all(self): return [{"id": "one"}, {"id": "two"}]
    class Service:
        installed = Installed()
    monkeypatch.setattr(package_cli, "_install_service", lambda: Service())
    assert package_cli.cmd_update(Namespace(id="one", remote=True, json=True)) == 0
    assert package_cli.cmd_update(Namespace(id="all", remote=True, json=True)) == 0
    assert calls == ["one", "one", "two"]

from __future__ import annotations

import pytest

from app.cli import build_parser


@pytest.mark.parametrize(
    "argv",
    [
        ["doctor"],
        ["doctor", "--json"],
        ["doctor", "--ai"],
        ["doctor", "--strict", "--verbose"],
        ["run", "--open"],
        ["run", "--host", "127.0.0.1", "--port", "8001", "--no-install"],
        ["backup", "-o", "backup.zip", "--verify"],
        ["backup", "--include-assets"],
        ["backup", "--include-assets", "--include-packages", "--no-verify"],
        ["restore", "backup.zip", "--dry-run"],
        ["restore", "backup.zip", "--yes", "--replace-assets"],
        ["lock"],
        ["lock", "-o", "grave.lock.json"],
        ["lock", "--json"],
        ["package", "list"],
        ["package", "list", "--json"],
        ["package", "validate", "data/packages/rulesets/sample-ruleset"],
        ["package", "doctor", "sample-ruleset", "--json"],
        ["package", "install", "sample-ruleset", "--yes", "--enable"],
        ["package", "install", "sample-addon", "--yes", "--enable", "--activate", "campaign-id"],
        ["package", "disable", "sample-addon", "--force"],
        ["package", "remove", "sample-addon", "--force"],
        ["package", "update", "all", "--json"],
        ["campaign", "package", "list", "campaign-id", "--json"],
        ["campaign", "package", "activate", "campaign-id", "sample-addon"],
        ["campaign", "package", "deactivate", "campaign-id", "sample-addon"],
        ["ruleset", "list"],
        ["ruleset", "new", "my-rpg", "--name", "My RPG", "--sheets", "--rolls", "--combat", "--dry-run"],
        ["addon", "new", "my-addon", "--name", "My Addon", "--js", "--settings", "--dry-run"],
        ["theme", "new", "my-theme", "--name", "My Theme", "--dry-run"],
        ["content", "new", "my-content", "--name", "My Content", "--dry-run"],
        ["assets", "new", "my-assets", "--name", "My Assets", "--images", "--dry-run"],
        ["library", "new", "my-library", "--name", "My Library", "--dry-run"],
    ],
)
def test_cli_parser_accepts_command(argv: list[str]) -> None:
    parser = build_parser()
    args = parser.parse_args(argv)
    assert callable(args.func)

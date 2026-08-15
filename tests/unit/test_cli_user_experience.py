from __future__ import annotations

import pytest

from app.cli import build_parser, main


def test_no_arguments_shows_quick_start_instead_of_usage_error(capsys):
    assert main([]) == 0
    output = capsys.readouterr()
    assert "Quick start:" in output.out
    assert "grave doctor" in output.out
    assert output.err == ""


def test_main_help_contains_workflows(capsys):
    with pytest.raises(SystemExit) as stopped:
        build_parser().parse_args(["--help"])
    assert stopped.value.code == 0
    output = capsys.readouterr().out
    assert "Common workflows:" in output
    assert "grave package validate" in output


def test_typo_suggests_the_nearest_command(capsys):
    with pytest.raises(SystemExit) as stopped:
        build_parser().parse_args(["pakage"])
    assert stopped.value.code == 2
    error = capsys.readouterr().err
    assert "Did you mean: grave package --help" in error
    assert "Try 'grave --help'" in error


def test_keyboard_interrupt_has_clean_exit(monkeypatch, capsys):
    parser = build_parser()
    args = parser.parse_args(["doctor"])
    monkeypatch.setattr(args, "func", lambda _args: (_ for _ in ()).throw(KeyboardInterrupt()))
    monkeypatch.setattr(parser, "parse_args", lambda _argv: args)
    monkeypatch.setattr("app.cli.build_parser", lambda: parser)
    assert main(["doctor"]) == 130
    assert "Cancelled." in capsys.readouterr().err

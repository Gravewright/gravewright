from app.actions.game import _protected_handlers
from app.actions.game.manage_journals import delete_journal_folder
from app.actions.game.manage_journals import rename_journal_folder
from app.actions.game.manage_journals import set_journal_folder_color


def test_all_journal_folder_mutations_are_registered():
    assert rename_journal_folder in _protected_handlers
    assert set_journal_folder_color in _protected_handlers
    assert delete_journal_folder in _protected_handlers

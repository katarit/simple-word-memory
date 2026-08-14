from __future__ import annotations

import pytest
from PySide6.QtWidgets import QApplication

from app import theme
from app.widget_window import WidgetWindow


@pytest.fixture(scope="module")
def qapp():
    app = QApplication.instance() or QApplication([])
    yield app


def test_context_menu_places_next_before_management_and_quit(qapp):
    widget = WidgetWindow(theme.tokens(False))
    widget.show_word("ephemeral")
    widget.set_can_advance(True)

    menu = widget._create_context_menu()
    actions = menu.actions()

    assert [action.text() for action in actions] == [
        "次の単語",
        "",
        "管理パネルを開く",
        "",
        "終了",
    ]
    assert actions[0].isEnabled() is True
    widget.close()


def test_next_action_is_disabled_when_no_other_word_exists(qapp):
    widget = WidgetWindow(theme.tokens(False))
    widget.show_word("ephemeral")
    widget.set_can_advance(False)

    menu = widget._create_context_menu()

    assert menu.actions()[0].isEnabled() is False
    widget.close()


def test_each_word_display_gets_a_new_manual_next_token(qapp):
    widget = WidgetWindow(theme.tokens(False))

    widget.show_word("first")
    first = widget.display_token
    widget.show_word("second")

    assert widget.display_token == first + 1
    widget.close()


def test_editing_visible_word_does_not_create_a_new_display_opportunity(qapp):
    widget = WidgetWindow(theme.tokens(False))
    widget.show_word("before")
    token = widget.display_token

    widget.update_word_text("after")

    assert widget.display_token == token
    widget.close()

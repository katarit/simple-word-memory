from __future__ import annotations

from datetime import datetime, timezone

import pytest
from PySide6.QtWidgets import QApplication, QSizePolicy

from app import i18n, theme
from app.db import Word
from app.panel_window import TAB_ADD, TAB_LEARNED, PanelWindow


JA = i18n.strings("ja")


@pytest.fixture(scope="module")
def qapp():
    app = QApplication.instance() or QApplication([])
    yield app


@pytest.mark.parametrize("dark", [False, True])
def test_content_editors_are_not_fixed_to_88_pixels(qapp, dark):
    panel = PanelWindow(theme.tokens(dark), JA)
    panel.apply_theme(theme.tokens(dark), dark)
    panel.show()
    qapp.processEvents()

    for editor in (panel._add_note, panel._edit_note):
        assert editor.maximumHeight() > 88
        assert editor.minimumHeight() < editor.maximumHeight()
        layout = editor.parentWidget().layout()
        editor_index = layout.indexOf(editor)
        assert layout.stretch(editor_index) == 1
        for index in range(editor_index + 1, layout.count()):
            spacer = layout.itemAt(index).spacerItem()
            assert spacer is None or (
                spacer.sizePolicy().verticalPolicy()
                is not QSizePolicy.Policy.Expanding
            )

    panel.close()


def test_quick_entry_opens_add_tab_and_focuses_word_field(qapp):
    panel = PanelWindow(theme.tokens(False), JA)
    panel.show()
    panel.show_tab(TAB_LEARNED)

    panel.show_add_for_quick_entry()
    qapp.processEvents()

    assert panel._stack.currentIndex() == TAB_ADD
    assert panel.focusWidget() is panel._add_text
    panel.close()


@pytest.mark.parametrize("confirmed", [True, False])
def test_delete_emits_only_after_confirmation(qapp, monkeypatch, confirmed):
    panel = PanelWindow(theme.tokens(False), JA)
    word = Word(
        id=5,
        text="mistake",
        note="",
        added_at=datetime.now(timezone.utc),
        learned=False,
        learned_at=None,
        last_filler_at=None,
    )
    panel.show_edit(word)
    asked = []
    deleted = []
    monkeypatch.setattr(panel, "_confirm_delete", lambda text: asked.append(text) or confirmed)
    panel.word_deleted.connect(deleted.append)

    panel._submit_delete()

    assert asked == ["mistake"]
    assert deleted == ([5] if confirmed else [])
    panel.close()


def _word(word_id: int, text: str) -> Word:
    return Word(
        id=word_id,
        text=text,
        note="",
        added_at=datetime.now(timezone.utc),
        learned=False,
        learned_at=None,
        last_filler_at=None,
    )


def _current_rows(panel: PanelWindow) -> list[int]:
    return [word_id for word_id, row in panel._rows.items() if row.objectName() == "rowCurrent"]


def test_word_on_screen_is_marked_in_list_and_survives_redraw(qapp):
    panel = PanelWindow(theme.tokens(False), JA)
    words = [_word(2, "adopt"), _word(1, "adapt")]
    panel.set_words(words, [])

    panel.set_current_word(2)
    assert _current_rows(panel) == [2]
    assert panel._rows[2]._current_badge.isVisibleTo(panel._rows[2])
    assert not panel._rows[1]._current_badge.isVisibleTo(panel._rows[1])

    panel.set_current_word(1)
    assert _current_rows(panel) == [1]

    # 学習済みの切り替え等でリストを描き直しても印は残る
    panel.set_words(words, [])
    assert _current_rows(panel) == [1]

    panel.set_current_word(None)
    assert _current_rows(panel) == []
    panel.close()

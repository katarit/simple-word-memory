from __future__ import annotations

import pytest
from PySide6.QtGui import QInputMethodEvent
from PySide6.QtWidgets import QApplication

from app import theme
from app.panel_window import PanelWindow


@pytest.fixture(scope="module")
def qapp():
    app = QApplication.instance() or QApplication([])
    yield app


def test_placeholder_hides_while_composing_and_returns_after_cancel(qapp):
    """変換中の未確定文字列にプレースホルダーが重ならないこと。

    QPlainTextEdit は preedit を空文書として扱うため、素のままでは
    プレースホルダーが描かれ続けて入力文字と重なる。
    """
    panel = PanelWindow(theme.tokens(False))
    panel.show()
    qapp.processEvents()

    note = panel._add_note
    assert note.placeholderText() != ""

    qapp.sendEvent(note, QInputMethodEvent("にほんご", []))
    assert note.placeholderText() == ""

    # 変換を取り消して空へ戻したらプレースホルダーが復帰する
    qapp.sendEvent(note, QInputMethodEvent("", []))
    assert note.placeholderText() != ""

    panel.close()

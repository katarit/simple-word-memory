from __future__ import annotations

import pytest
from PySide6.QtCore import QPoint, QRect, QSize
from PySide6.QtWidgets import QApplication

from app import theme
from app.meaning_window import MeaningWindow, popup_position


@pytest.fixture(scope="module")
def qapp():
    app = QApplication.instance() or QApplication([])
    yield app


def test_popup_is_placed_below_widget_when_space_is_available():
    available = QRect(0, 0, 800, 600)
    anchor = QRect(500, 100, 240, 72)

    assert popup_position(anchor, QSize(240, 120), available) == QPoint(500, 180)


def test_popup_flips_above_widget_near_screen_bottom():
    available = QRect(0, 0, 800, 600)
    anchor = QRect(500, 520, 240, 72)

    assert popup_position(anchor, QSize(240, 120), available) == QPoint(500, 392)


def test_empty_note_is_shown_as_unregistered_content(qapp):
    window = MeaningWindow(theme.tokens(False))

    window.show_note("", QRect(100, 100, 240, 72))

    assert window._editor.toPlainText() == "内容未登録"
    assert window._editor.focusPolicy().value == 0
    window.close()

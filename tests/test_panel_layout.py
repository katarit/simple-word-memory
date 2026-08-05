from __future__ import annotations

import pytest
from PySide6.QtWidgets import QApplication, QSizePolicy

from app import theme
from app.panel_window import PanelWindow


@pytest.fixture(scope="module")
def qapp():
    app = QApplication.instance() or QApplication([])
    yield app


@pytest.mark.parametrize("dark", [False, True])
def test_content_editors_are_not_fixed_to_88_pixels(qapp, dark):
    panel = PanelWindow(theme.tokens(dark))
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

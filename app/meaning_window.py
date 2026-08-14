"""現在表示中の単語の内容を、一時的な別ウィンドウで表示する。"""

from __future__ import annotations

from PySide6.QtCore import QEvent, QPoint, QRect, QSize, Qt
from PySide6.QtGui import QFontMetrics
from PySide6.QtWidgets import QApplication, QPlainTextEdit, QVBoxLayout, QWidget

from app import theme


def popup_position(anchor: QRect, popup_size: QSize, available: QRect) -> QPoint:
    """画面内に収めつつ、原則としてアンカーの下、無理なら上へ置く。"""
    x = min(max(anchor.left(), available.left()), available.right() - popup_size.width() + 1)
    below = anchor.bottom() + 1 + theme.MEANING_GAP
    if below + popup_size.height() - 1 <= available.bottom():
        y = below
    else:
        y = anchor.top() - theme.MEANING_GAP - popup_size.height()
    y = min(max(y, available.top()), available.bottom() - popup_size.height() + 1)
    return QPoint(x, y)


class MeaningWindow(QWidget):
    def __init__(self, tokens: dict[str, str], parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setWindowFlags(
            Qt.FramelessWindowHint
            | Qt.WindowStaysOnTopHint
            | Qt.Tool
            | Qt.WindowDoesNotAcceptFocus
        )
        self.setAttribute(Qt.WA_ShowWithoutActivating)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        self._editor = QPlainTextEdit()
        self._editor.setObjectName("meaningText")
        self._editor.setReadOnly(True)
        self._editor.setFocusPolicy(Qt.NoFocus)
        self._editor.viewport().installEventFilter(self)
        layout.addWidget(self._editor)

        self.setFixedWidth(theme.MEANING_WIDTH)
        self.apply_theme(tokens)

    def apply_theme(self, tokens: dict[str, str]) -> None:
        self.setStyleSheet(theme.meaning_qss(tokens))

    def show_note(self, note: str, anchor: QRect) -> None:
        content = note.strip() or "内容未登録"
        self._editor.setPlainText(content)
        metrics = QFontMetrics(self._editor.font())
        bounds = metrics.boundingRect(
            QRect(0, 0, theme.MEANING_WIDTH - 40, 10_000),
            Qt.TextWordWrap,
            content,
        )
        height = min(
            max(bounds.height() + 32, theme.MEANING_MIN_HEIGHT),
            theme.MEANING_MAX_HEIGHT,
        )
        self.setFixedHeight(height)

        app = QApplication.instance()
        screen = app.screenAt(anchor.center()) if app is not None else None
        if screen is None and app is not None:
            screen = app.primaryScreen()
        available = screen.availableGeometry() if screen is not None else anchor
        self.move(popup_position(anchor, self.size(), available))
        self.show()

    def eventFilter(self, watched, event) -> bool:  # noqa: N802
        if (
            watched is self._editor.viewport()
            and event.type() == QEvent.MouseButtonPress
            and event.button() == Qt.LeftButton
        ):
            self.hide()
            return True
        return super().eventFilter(watched, event)

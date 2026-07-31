"""常時最前面の単語表示ウィジェット。

凍結モック tasks/designs/confirmed/widget.html の 1:1 移植。
表示するのは単語だけで、内容（意味・メモ）は出さない。
"""

from __future__ import annotations

from PySide6.QtCore import QPoint, Qt, Signal
from PySide6.QtWidgets import QFrame, QHBoxLayout, QLabel, QMenu, QVBoxLayout, QWidget

from app import theme

DRAG_THRESHOLD_PX = 4
"""これを超えて動いたらドラッグ扱いにし、クリックとみなさない。"""


class WidgetWindow(QWidget):
    clicked = Signal()
    moved = Signal(int, int)
    quit_requested = Signal()

    def __init__(self, tokens: dict[str, str], parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._press_pos: QPoint | None = None
        self._dragging = False

        self.setWindowTitle("単語リマインダー")
        self.setWindowFlags(
            Qt.FramelessWindowHint | Qt.WindowStaysOnTopHint | Qt.Tool
        )
        self.setAttribute(Qt.WA_TranslucentBackground)
        self.setFixedSize(theme.WIDGET_WIDTH, theme.WIDGET_HEIGHT)
        self.setStyleSheet(theme.widget_qss(tokens))

        outer = QVBoxLayout(self)
        outer.setContentsMargins(0, 0, 0, 0)

        card = QFrame()
        card.setObjectName("widgetCard")
        outer.addWidget(card)

        inner = QHBoxLayout(card)
        inner.setContentsMargins(theme.WIDGET_PADDING_X, 0, theme.WIDGET_PADDING_X, 0)

        self._label = QLabel()
        self._label.setObjectName("widgetWord")
        self._label.setAlignment(Qt.AlignCenter)
        inner.addWidget(self._label)

        self.show_placeholder()

    def apply_theme(self, tokens: dict[str, str]) -> None:
        self.setStyleSheet(theme.widget_qss(tokens))

    def show_word(self, text: str) -> None:
        self._label.setObjectName("widgetWord")
        self._label.setText(self._elide(text))
        self._refresh_style()

    def show_placeholder(self, text: str = "登録単語なし") -> None:
        self._label.setObjectName("widgetEmpty")
        self._label.setText(text)
        self._refresh_style()

    def _elide(self, text: str) -> str:
        metrics = self._label.fontMetrics()
        available = theme.WIDGET_WIDTH - theme.WIDGET_PADDING_X * 2
        return metrics.elidedText(text, Qt.ElideRight, available)

    def _refresh_style(self) -> None:
        self._label.style().unpolish(self._label)
        self._label.style().polish(self._label)

    def contextMenuEvent(self, event) -> None:  # noqa: N802 - Qt の命名に合わせる
        """右クリックメニュー。枠なしウィンドウには閉じるボタンがないため、
        ここが唯一の終了導線になる。"""
        menu = QMenu(self)
        open_action = menu.addAction("管理パネルを開く")
        menu.addSeparator()
        quit_action = menu.addAction("終了")
        chosen = menu.exec(event.globalPos())
        if chosen == open_action:
            self.clicked.emit()
        elif chosen == quit_action:
            self.quit_requested.emit()

    # --- ドラッグ移動とクリック判定 -----------------------------------------
    def mousePressEvent(self, event) -> None:
        if event.button() == Qt.LeftButton:
            self._press_pos = event.globalPosition().toPoint() - self.frameGeometry().topLeft()
            self._drag_origin = event.globalPosition().toPoint()
            self._dragging = False
            event.accept()

    def mouseMoveEvent(self, event) -> None:
        if self._press_pos is None or not (event.buttons() & Qt.LeftButton):
            return
        current = event.globalPosition().toPoint()
        if (current - self._drag_origin).manhattanLength() > DRAG_THRESHOLD_PX:
            self._dragging = True
        if self._dragging:
            self.move(current - self._press_pos)
        event.accept()

    def mouseReleaseEvent(self, event) -> None:
        if event.button() != Qt.LeftButton or self._press_pos is None:
            return
        self._press_pos = None
        if self._dragging:
            self.moved.emit(self.x(), self.y())
        else:
            self.clicked.emit()
        self._dragging = False
        event.accept()

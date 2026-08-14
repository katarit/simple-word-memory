"""常時最前面の単語表示ウィジェット。

表示するのは単語だけで、内容（意味・メモ）は出さない。
枠なしウィンドウのため、終了は右クリックメニューから行う。
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
    drag_started = Signal()
    panel_requested = Signal()
    next_requested = Signal(int)
    quit_requested = Signal()

    def __init__(self, tokens: dict[str, str], parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._press_pos: QPoint | None = None
        self._dragging = False
        self._display_token = 0
        self._has_word = False
        self._can_advance = False

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
        self._display_token += 1
        self._has_word = True
        self.update_word_text(text)

    def update_word_text(self, text: str) -> None:
        """表示中の語を編集結果へ差し替える。表示機会は増やさない。"""
        self._label.setObjectName("widgetWord")
        self._label.setText(self._elide(text))
        self._refresh_style()

    def show_placeholder(self, text: str = "登録単語なし") -> None:
        self._display_token += 1
        self._has_word = False
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

    @property
    def display_token(self) -> int:
        return self._display_token

    def set_can_advance(self, can_advance: bool) -> None:
        self._can_advance = can_advance

    def _create_context_menu(self) -> QMenu:
        menu = QMenu(self)
        next_action = menu.addAction("次の単語")
        next_action.setEnabled(self._has_word and self._can_advance)
        next_action.triggered.connect(
            lambda: self.next_requested.emit(self._display_token)
        )
        menu.addSeparator()
        open_action = menu.addAction("管理パネルを開く")
        open_action.triggered.connect(self.panel_requested.emit)
        menu.addSeparator()
        quit_action = menu.addAction("終了")
        quit_action.triggered.connect(self.quit_requested.emit)
        return menu

    def contextMenuEvent(self, event) -> None:  # noqa: N802 - Qt の命名に合わせる
        """右クリックメニュー。枠なしウィンドウには閉じるボタンがないため、
        ここが唯一の終了導線になる。"""
        self._create_context_menu().exec(event.globalPos())

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
            if not self._dragging:
                self.drag_started.emit()
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

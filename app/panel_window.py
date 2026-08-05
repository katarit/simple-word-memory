"""管理パネル（登録／未学習／学習済み ＋ 編集ビュー）。

リスト行は 1 行目に単語（左）と登録日（右）、2 行目に内容プレビュー。
チェックボックスは学習済みの切り替えだけを担う。
"""

from __future__ import annotations

from datetime import datetime

from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import (
    QButtonGroup,
    QCheckBox,
    QFrame,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QPlainTextEdit,
    QPushButton,
    QScrollArea,
    QSizePolicy,
    QStackedWidget,
    QVBoxLayout,
    QWidget,
)

from app import __version__, theme
from app.db import Word

TAB_ADD = 0
TAB_UNLEARNED = 1
TAB_LEARNED = 2
VIEW_EDIT = 3


def _repolish(widget: QWidget) -> None:
    """objectName を変えたあとに QSS を再適用する。"""
    widget.style().unpolish(widget)
    widget.style().polish(widget)


def format_date(value: datetime | None) -> str:
    if value is None:
        return ""
    return value.astimezone().strftime("%Y/%m/%d")


class ElidedLabel(QLabel):
    """幅に収まらない場合に末尾を省略する QLabel。

    モックの text-overflow: ellipsis に対応する。QLabel は既定では
    クリップするだけで省略記号を出さないため。
    """

    def __init__(self, text: str, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._full_text = text
        self.setSizePolicy(QSizePolicy.Ignored, QSizePolicy.Preferred)
        self._apply_elide()

    def setText(self, text: str) -> None:  # noqa: N802 - Qt の命名に合わせる
        self._full_text = text
        self._apply_elide()

    def resizeEvent(self, event) -> None:  # noqa: N802 - Qt の命名に合わせる
        super().resizeEvent(event)
        self._apply_elide()

    def _apply_elide(self) -> None:
        super().setText(self.fontMetrics().elidedText(self._full_text, Qt.ElideRight, max(self.width(), 0)))


class WordRow(QFrame):
    """1 単語ぶんのリスト行。"""

    toggled = Signal(int, bool)
    opened = Signal(int)

    def __init__(self, word: Word, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setObjectName("row")
        self.setAttribute(Qt.WA_StyledBackground, True)
        self.setFixedHeight(theme.ROW_HEIGHT)
        self._word_id = word.id

        layout = QHBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(12)

        self._check = QCheckBox()
        self._check.setChecked(word.learned)
        self._check.setCursor(Qt.PointingHandCursor)
        self._check.toggled.connect(lambda checked: self.toggled.emit(self._word_id, checked))
        layout.addWidget(self._check, 0, Qt.AlignVCenter)

        text_col = QWidget()
        text_col.setCursor(Qt.PointingHandCursor)
        text_col.mousePressEvent = self._on_text_clicked  # noqa: SLF001 - 行クリックで編集を開く
        col_layout = QVBoxLayout(text_col)
        col_layout.setContentsMargins(0, 0, 0, 0)
        col_layout.setSpacing(2)

        top_line = QHBoxLayout()
        top_line.setContentsMargins(0, 0, 0, 0)
        top_line.setSpacing(8)

        word_label = ElidedLabel(word.text)
        word_label.setObjectName("rowWordLearned" if word.learned else "rowWord")
        top_line.addWidget(word_label, 1)

        date_label = QLabel(format_date(word.added_at))
        date_label.setObjectName("rowDate")
        top_line.addWidget(date_label, 0, Qt.AlignRight | Qt.AlignBaseline)

        col_layout.addLayout(top_line)

        note_label = ElidedLabel(word.note.replace("\n", " ") if word.note else "（内容未登録）")
        note_label.setObjectName("rowNote")
        col_layout.addWidget(note_label)

        layout.addWidget(text_col, 1)

    def _on_text_clicked(self, event) -> None:
        if event.button() == Qt.LeftButton:
            self.opened.emit(self._word_id)


class PanelWindow(QWidget):
    """管理パネル本体。データ操作はシグナルで controller に委譲する。"""

    word_added = Signal(str, str)
    word_updated = Signal(int, str, str)
    learned_toggled = Signal(int, bool)
    word_opened = Signal(int)
    theme_toggled = Signal()

    def __init__(self, tokens: dict[str, str], parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._editing_id: int | None = None
        self._return_tab = TAB_UNLEARNED
        self._suppress_toggle = False

        # バージョンは OS のタイトルバーに出す（アプリ内ヘッダーには置かない）。
        self.setWindowTitle(f"単語リマインダー  ver. {__version__}")
        self.setFixedSize(theme.PANEL_WIDTH, theme.PANEL_HEIGHT)
        self.setObjectName("panelRoot")
        self.setStyleSheet(theme.panel_qss(tokens))

        root = QVBoxLayout(self)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(0)
        root.addWidget(self._build_header())
        root.addWidget(self._build_tabs())
        root.addWidget(self._build_content(), 1)

    # --- 組み立て -----------------------------------------------------------
    def _build_header(self) -> QWidget:
        header = QFrame()
        header.setObjectName("panelHeader")
        header.setFixedHeight(theme.PANEL_HEADER_HEIGHT)
        layout = QHBoxLayout(header)
        layout.setContentsMargins(theme.PANEL_CONTENT_PADDING, 0, theme.PANEL_CONTENT_PADDING, 0)
        title = QLabel("単語リマインダー")
        title.setObjectName("panelTitle")
        layout.addWidget(title)
        layout.addStretch(1)

        self._theme_button = QPushButton("Dark")
        self._theme_button.setObjectName("themeToggle")
        self._theme_button.setCursor(Qt.PointingHandCursor)
        self._theme_button.setFixedHeight(theme.THEME_BUTTON_HEIGHT)
        self._theme_button.clicked.connect(self.theme_toggled)
        layout.addWidget(self._theme_button)
        return header

    def _build_tabs(self) -> QWidget:
        bar = QFrame()
        bar.setObjectName("tabBar")
        bar.setFixedHeight(theme.PANEL_TAB_HEIGHT)
        layout = QHBoxLayout(bar)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        self._tab_group = QButtonGroup(self)
        self._tab_group.setExclusive(True)
        self._tabs: list[QPushButton] = []
        self._tab_labels: list[QLabel] = []
        self._tab_badges: list[QLabel | None] = []

        for index, (text, has_badge) in enumerate(
            (("登録", False), ("未学習", True), ("学習済み", True))
        ):
            button = QPushButton()
            button.setObjectName("tab")
            button.setCheckable(True)
            button.setCursor(Qt.PointingHandCursor)
            # QPushButton の縦方向は既定で Fixed のため、タブバーの高さいっぱいに
            # 広げないと選択中の下線がバー下端に来ない。
            button.setSizePolicy(QSizePolicy.Preferred, QSizePolicy.Expanding)
            button.clicked.connect(lambda _checked, i=index: self.show_tab(i))

            # モックのタブは「ラベル＋件数ピル」の2要素。QPushButton のテキストでは
            # ピルを表現できないため、ボタン内にレイアウトを組む。
            inner = QHBoxLayout(button)
            inner.setContentsMargins(0, 0, 0, 0)
            inner.setSpacing(6)
            inner.addStretch(1)

            label = QLabel(text)
            label.setAttribute(Qt.WA_TransparentForMouseEvents, True)
            inner.addWidget(label)
            self._tab_labels.append(label)

            badge: QLabel | None = None
            if has_badge:
                badge = QLabel("0")
                badge.setAttribute(Qt.WA_TransparentForMouseEvents, True)
                badge.setAlignment(Qt.AlignCenter)
                inner.addWidget(badge)
            self._tab_badges.append(badge)

            inner.addStretch(1)

            self._tab_group.addButton(button, index)
            self._tabs.append(button)
            layout.addWidget(button, 1)
        return bar

    def _style_tabs(self, active_index: int | None) -> None:
        """子ラベルの色は QSS の :checked で追従できないため、明示的に切り替える。"""
        for index, (label, badge) in enumerate(zip(self._tab_labels, self._tab_badges)):
            active = index == active_index
            label.setObjectName("tabLabelActive" if active else "tabLabel")
            _repolish(label)
            if badge is not None:
                badge.setObjectName("badgeActive" if active else "badge")
                _repolish(badge)

    def _build_content(self) -> QWidget:
        self._stack = QStackedWidget()
        self._stack.addWidget(self._build_add_view())
        self._stack.addWidget(self._build_list_view("unlearned"))
        self._stack.addWidget(self._build_list_view("learned"))
        self._stack.addWidget(self._build_edit_view())
        return self._stack

    def _padded(self) -> tuple[QWidget, QVBoxLayout]:
        page = QWidget()
        page.setObjectName("page")
        layout = QVBoxLayout(page)
        pad = theme.PANEL_CONTENT_PADDING
        layout.setContentsMargins(pad, pad, pad, pad)
        layout.setSpacing(0)
        return page, layout

    def _field_label(self, text: str) -> QLabel:
        label = QLabel(text)
        label.setObjectName("fieldLabel")
        return label

    def _build_add_view(self) -> QWidget:
        page, layout = self._padded()

        layout.addWidget(self._field_label("単語"))
        layout.addSpacing(8)
        self._add_text = QLineEdit()
        self._add_text.setPlaceholderText("単語を入力")
        self._add_text.setFixedHeight(40)
        self._add_text.returnPressed.connect(self._submit_add)
        layout.addWidget(self._add_text)

        layout.addSpacing(20)
        layout.addWidget(self._field_label("内容（任意）"))
        layout.addSpacing(8)
        self._add_note = QPlainTextEdit()
        self._add_note.setPlaceholderText("意味・例文・メモなど自由に記入")
        layout.addWidget(self._add_note, 1)

        layout.addSpacing(8)
        self._add_hint = QLabel("")
        self._add_hint.setObjectName("hint")
        self._add_hint.setWordWrap(True)
        layout.addWidget(self._add_hint)

        button_row = QHBoxLayout()
        button_row.addStretch(1)
        add_button = QPushButton("追加")
        add_button.setObjectName("primary")
        add_button.setFixedHeight(40)
        add_button.setCursor(Qt.PointingHandCursor)
        add_button.clicked.connect(self._submit_add)
        button_row.addWidget(add_button)
        layout.addLayout(button_row)
        return page

    def _build_list_view(self, kind: str) -> QWidget:
        page = QWidget()
        page.setObjectName("page")
        outer = QVBoxLayout(page)
        outer.setContentsMargins(0, 0, 0, 0)

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)

        container = QWidget()
        container.setObjectName("page")
        layout = QVBoxLayout(container)
        pad = theme.PANEL_CONTENT_PADDING
        layout.setContentsMargins(pad, pad, pad, pad)
        layout.setSpacing(0)
        layout.addStretch(1)

        scroll.setWidget(container)
        outer.addWidget(scroll)

        setattr(self, f"_{kind}_layout", layout)
        return page

    def _build_edit_view(self) -> QWidget:
        page, layout = self._padded()

        back = QPushButton("← 戻る")
        back.setObjectName("back")
        back.setCursor(Qt.PointingHandCursor)
        back.clicked.connect(self._leave_edit)
        layout.addWidget(back, 0, Qt.AlignLeft)

        layout.addSpacing(16)
        self._edit_meta = QLabel("")
        self._edit_meta.setObjectName("metaLine")
        layout.addWidget(self._edit_meta)

        layout.addSpacing(16)
        layout.addWidget(self._field_label("単語"))
        layout.addSpacing(8)
        self._edit_text = QLineEdit()
        self._edit_text.setFixedHeight(40)
        layout.addWidget(self._edit_text)

        layout.addSpacing(20)
        layout.addWidget(self._field_label("内容（任意）"))
        layout.addSpacing(8)
        self._edit_note = QPlainTextEdit()
        layout.addWidget(self._edit_note, 1)

        layout.addSpacing(8)
        self._edit_hint = QLabel("")
        self._edit_hint.setObjectName("hint")
        self._edit_hint.setWordWrap(True)
        layout.addWidget(self._edit_hint)

        button_row = QHBoxLayout()
        button_row.addStretch(1)
        cancel = QPushButton("戻る")
        cancel.setObjectName("ghost")
        cancel.setFixedHeight(40)
        cancel.setCursor(Qt.PointingHandCursor)
        cancel.clicked.connect(self._leave_edit)
        button_row.addWidget(cancel)
        save = QPushButton("保存")
        save.setObjectName("primary")
        save.setFixedHeight(40)
        save.setCursor(Qt.PointingHandCursor)
        save.clicked.connect(self._submit_edit)
        button_row.addWidget(save)
        layout.addLayout(button_row)
        return page

    # --- 表示更新 -----------------------------------------------------------
    def apply_theme(self, tokens: dict[str, str], dark: bool) -> None:
        self.setStyleSheet(theme.panel_qss(tokens))
        # ボタンには「押すと何になるか」を出す。
        self._theme_button.setText("Light" if dark else "Dark")

    def show_tab(self, index: int) -> None:
        self._stack.setCurrentIndex(index)
        self._tabs[index].setChecked(True)
        self._style_tabs(index)

    def set_words(self, unlearned: list[Word], learned: list[Word]) -> None:
        """リストを描き直す。QWidget.render() と衝突するため render とは名付けない。"""
        self._fill_list(self._unlearned_layout, unlearned, "未学習の単語はありません")
        self._fill_list(self._learned_layout, learned, "学習済みの単語はありません")
        self._tab_badges[TAB_UNLEARNED].setText(str(len(unlearned)))
        self._tab_badges[TAB_LEARNED].setText(str(len(learned)))

    def _fill_list(self, layout: QVBoxLayout, words: list[Word], empty_message: str) -> None:
        self._suppress_toggle = True
        while layout.count():
            item = layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()

        if not words:
            empty = QLabel(empty_message)
            empty.setObjectName("emptyState")
            empty.setAlignment(Qt.AlignCenter)
            layout.addWidget(empty)
        else:
            for word in words:
                row = WordRow(word)
                row.toggled.connect(self._on_row_toggled)
                row.opened.connect(self.open_word)
                layout.addWidget(row)
        layout.addStretch(1)
        self._suppress_toggle = False

    def _on_row_toggled(self, word_id: int, checked: bool) -> None:
        if self._suppress_toggle:
            return
        self.learned_toggled.emit(word_id, checked)

    def open_word(self, word_id: int) -> None:
        """リストの単語をクリックしたとき。編集ビューを開く。"""
        self._return_tab = self._stack.currentIndex()
        if self._return_tab not in (TAB_UNLEARNED, TAB_LEARNED):
            self._return_tab = TAB_UNLEARNED
        self.word_opened.emit(word_id)

    def show_edit(self, word: Word) -> None:
        self._editing_id = word.id
        self._edit_meta.setText(f"登録日: {format_date(word.added_at)}")
        self._edit_text.setText(word.text)
        self._edit_note.setPlainText(word.note)
        self._edit_hint.setText("")
        self._edit_hint.setObjectName("hint")
        self._stack.setCurrentIndex(VIEW_EDIT)
        # 編集ビューはタブではないので、どのタブも選択されていない状態にする。
        # 排他グループのままでは最後の1つを外せないため一時的に解除する。
        self._tab_group.setExclusive(False)
        for button in self._tabs:
            button.setChecked(False)
        self._tab_group.setExclusive(True)
        self._style_tabs(None)

    def _leave_edit(self) -> None:
        self._editing_id = None
        self.show_tab(self._return_tab)

    # --- 入力処理 -----------------------------------------------------------
    def _submit_add(self) -> None:
        text = self._add_text.text().strip()
        if not text:
            self._set_hint(self._add_hint, "単語を入力してください", error=True)
            return
        self.word_added.emit(text, self._add_note.toPlainText())

    def _submit_edit(self) -> None:
        if self._editing_id is None:
            return
        text = self._edit_text.text().strip()
        if not text:
            self._set_hint(self._edit_hint, "単語を入力してください", error=True)
            return
        self.word_updated.emit(self._editing_id, text, self._edit_note.toPlainText())

    def clear_add_form(self, message: str) -> None:
        self._add_text.clear()
        self._add_note.clear()
        self._set_hint(self._add_hint, message, error=False)

    def show_add_error(self, message: str) -> None:
        self._set_hint(self._add_hint, message, error=True)

    def show_edit_error(self, message: str) -> None:
        self._set_hint(self._edit_hint, message, error=True)

    def leave_edit_after_save(self) -> None:
        self._leave_edit()

    def _set_hint(self, label: QLabel, message: str, error: bool) -> None:
        label.setObjectName("hintError" if error else "hint")
        label.setText(message)
        _repolish(label)

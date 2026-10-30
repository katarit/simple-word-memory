"""管理パネル（登録／未学習／学習済み ＋ 編集ビュー）。

リスト行は 1 行目に単語（左）と登録日（右）、2 行目に内容プレビュー。
チェックボックスは学習済みの切り替えだけを担う。削除は編集ビューから行う。
"""

from __future__ import annotations

from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import (
    QButtonGroup,
    QCheckBox,
    QFrame,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QMessageBox,
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
from app.i18n import Strings

TAB_ADD = 0
TAB_UNLEARNED = 1
TAB_LEARNED = 2
VIEW_EDIT = 3


def _repolish(widget: QWidget) -> None:
    """objectName を変えたあとに QSS を再適用する。"""
    widget.style().unpolish(widget)
    widget.style().polish(widget)


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


class NoteEdit(QPlainTextEdit):
    """変換中もプレースホルダーが重ならない複数行入力。

    QPlainTextEdit は日本語入力の未確定文字列（preedit）を「文書は空」と
    見なすため、変換を確定するまでプレースホルダーを描き続け、入力中の
    文字がその上に重なる。未確定のあいだだけプレースホルダーを外して
    避ける。QLineEdit は preedit を考慮するので同じ対処は要らない。
    """

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._placeholder = ""

    def setPlaceholderText(self, text: str) -> None:  # noqa: N802 - Qt の命名に合わせる
        self._placeholder = text
        super().setPlaceholderText(text)

    def inputMethodEvent(self, event) -> None:  # noqa: N802 - Qt の命名に合わせる
        super().inputMethodEvent(event)
        wanted = "" if event.preeditString() else self._placeholder
        if super().placeholderText() != wanted:
            super().setPlaceholderText(wanted)


class WordRow(QFrame):
    """1 単語ぶんのリスト行。"""

    toggled = Signal(int, bool)
    opened = Signal(int)

    def __init__(self, word: Word, strings: Strings, parent: QWidget | None = None) -> None:
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

        # ウィジェットに出ている語。似た語が並ぶと見分けにくく押し間違えるため、
        # 色だけでなく文字でも示す。
        self._current_badge = QLabel(strings("on_screen"))
        self._current_badge.setObjectName("currentBadge")
        self._current_badge.hide()
        top_line.addWidget(self._current_badge, 0, Qt.AlignVCenter)

        date_label = QLabel(strings.date(word.added_at))
        date_label.setObjectName("rowDate")
        top_line.addWidget(date_label, 0, Qt.AlignRight | Qt.AlignBaseline)

        col_layout.addLayout(top_line)

        note_label = ElidedLabel(word.note.replace("\n", " ") if word.note else strings("row_no_note"))
        note_label.setObjectName("rowNote")
        col_layout.addWidget(note_label)

        layout.addWidget(text_col, 1)

    def set_current(self, current: bool) -> None:
        self.setObjectName("rowCurrent" if current else "row")
        _repolish(self)
        self._current_badge.setVisible(current)

    def _on_text_clicked(self, event) -> None:
        if event.button() == Qt.LeftButton:
            self.opened.emit(self._word_id)


class PanelWindow(QWidget):
    """管理パネル本体。データ操作はシグナルで controller に委譲する。"""

    word_added = Signal(str, str)
    word_updated = Signal(int, str, str)
    word_deleted = Signal(int)
    learned_toggled = Signal(int, bool)
    word_opened = Signal(int)
    theme_toggled = Signal()

    def __init__(self, tokens: dict[str, str], strings: Strings, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._s = strings
        self._editing_id: int | None = None
        self._current_word_id: int | None = None
        self._rows: dict[int, WordRow] = {}
        self._return_tab = TAB_UNLEARNED
        self._suppress_toggle = False

        # バージョンは OS のタイトルバーに出す（アプリ内ヘッダーには置かない）。
        self.setWindowTitle(strings("window_title", version=__version__))
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
        title = QLabel(self._s("app_name"))
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

        for index, (key, has_badge) in enumerate(
            (("tab_add", False), ("tab_unlearned", True), ("tab_learned", True))
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

            label = QLabel(self._s(key))
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

        layout.addWidget(self._field_label(self._s("field_word")))
        layout.addSpacing(8)
        self._add_text = QLineEdit()
        self._add_text.setPlaceholderText(self._s("word_placeholder"))
        self._add_text.setFixedHeight(40)
        self._add_text.returnPressed.connect(self._submit_add)
        layout.addWidget(self._add_text)

        layout.addSpacing(20)
        layout.addWidget(self._field_label(self._s("field_note")))
        layout.addSpacing(8)
        self._add_note = NoteEdit()
        self._add_note.setPlaceholderText(self._s("note_placeholder"))
        layout.addWidget(self._add_note, 1)

        layout.addSpacing(8)
        self._add_hint = QLabel("")
        self._add_hint.setObjectName("hint")
        self._add_hint.setWordWrap(True)
        layout.addWidget(self._add_hint)

        button_row = QHBoxLayout()
        button_row.addStretch(1)
        add_button = QPushButton(self._s("add"))
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

        back = QPushButton(self._s("back_link"))
        back.setObjectName("back")
        back.setCursor(Qt.PointingHandCursor)
        back.clicked.connect(self._leave_edit)
        layout.addWidget(back, 0, Qt.AlignLeft)

        layout.addSpacing(16)
        self._edit_meta = QLabel("")
        self._edit_meta.setObjectName("metaLine")
        layout.addWidget(self._edit_meta)

        layout.addSpacing(16)
        layout.addWidget(self._field_label(self._s("field_word")))
        layout.addSpacing(8)
        self._edit_text = QLineEdit()
        self._edit_text.setFixedHeight(40)
        layout.addWidget(self._edit_text)

        layout.addSpacing(20)
        layout.addWidget(self._field_label(self._s("field_note")))
        layout.addSpacing(8)
        self._edit_note = NoteEdit()
        layout.addWidget(self._edit_note, 1)

        layout.addSpacing(8)
        self._edit_hint = QLabel("")
        self._edit_hint.setObjectName("hint")
        self._edit_hint.setWordWrap(True)
        layout.addWidget(self._edit_hint)

        button_row = QHBoxLayout()
        # 取り消せない操作なので、保存とは反対の端に離して置く。
        delete = QPushButton(self._s("delete"))
        delete.setObjectName("danger")
        delete.setFixedHeight(40)
        delete.setCursor(Qt.PointingHandCursor)
        delete.clicked.connect(self._submit_delete)
        button_row.addWidget(delete)
        button_row.addStretch(1)
        cancel = QPushButton(self._s("back"))
        cancel.setObjectName("ghost")
        cancel.setFixedHeight(40)
        cancel.setCursor(Qt.PointingHandCursor)
        cancel.clicked.connect(self._leave_edit)
        button_row.addWidget(cancel)
        save = QPushButton(self._s("save"))
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

    def show_add_for_quick_entry(self) -> None:
        """新規登録タブを開き、単語欄へ入力を移す。"""
        self.show_tab(TAB_ADD)
        self._add_text.setFocus(Qt.OtherFocusReason)

    def set_words(self, unlearned: list[Word], learned: list[Word]) -> None:
        """リストを描き直す。QWidget.render() と衝突するため render とは名付けない。"""
        self._rows = {}
        self._fill_list(self._unlearned_layout, unlearned, self._s("empty_unlearned"))
        self._fill_list(self._learned_layout, learned, self._s("empty_learned"))
        self._tab_badges[TAB_UNLEARNED].setText(str(len(unlearned)))
        self._tab_badges[TAB_LEARNED].setText(str(len(learned)))

    def set_current_word(self, word_id: int | None) -> None:
        """ウィジェットに出ている語をリストで示す。行は作り直さない。"""
        previous = self._rows.get(self._current_word_id)
        if previous is not None:
            previous.set_current(False)
        self._current_word_id = word_id
        current = self._rows.get(word_id)
        if current is not None:
            current.set_current(True)

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
                row = WordRow(word, self._s)
                row.set_current(word.id == self._current_word_id)
                self._rows[word.id] = row
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
        self._edit_meta.setText(self._s("added_on", date=self._s.date(word.added_at)))
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
            self._set_hint(self._add_hint, self._s("word_required"), error=True)
            return
        self.word_added.emit(text, self._add_note.toPlainText())

    def _submit_edit(self) -> None:
        if self._editing_id is None:
            return
        text = self._edit_text.text().strip()
        if not text:
            self._set_hint(self._edit_hint, self._s("word_required"), error=True)
            return
        self.word_updated.emit(self._editing_id, text, self._edit_note.toPlainText())

    def _submit_delete(self) -> None:
        if self._editing_id is None:
            return
        if self._confirm_delete(self._edit_text.text().strip()):
            self.word_deleted.emit(self._editing_id)

    def _confirm_delete(self, text: str) -> bool:
        box = QMessageBox(self)
        box.setIcon(QMessageBox.Warning)
        box.setWindowTitle(self._s("delete_title"))
        box.setText(self._s("delete_question", text=text))
        delete = box.addButton(self._s("delete"), QMessageBox.DestructiveRole)
        cancel = box.addButton(self._s("cancel"), QMessageBox.RejectRole)
        # 誤って Enter で消さないよう、既定は安全側に置く。
        box.setDefaultButton(cancel)
        box.setEscapeButton(cancel)
        box.exec()
        return box.clickedButton() is delete

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

    def leave_edit_after_delete(self) -> None:
        self._leave_edit()

    def _set_hint(self, label: QLabel, message: str, error: bool) -> None:
        label.setObjectName("hintError" if error else "hint")
        label.setText(message)
        _repolish(label)

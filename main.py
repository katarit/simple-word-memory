"""words-reminder のエントリポイント。

ウィジェットとパネルを組み立て、5 分ごとの出題ティックを回す。
出題ロジックそのものは app/scheduler.py（ADR-0002）にある。
"""

from __future__ import annotations

import sys
from pathlib import Path

from PySide6.QtCore import QTimer
from PySide6.QtWidgets import QApplication

from app import db, scheduler, theme
from app.panel_window import PanelWindow
from app.widget_window import WidgetWindow

DB_PATH = Path(__file__).resolve().parent / "data" / "words.db"

SETTING_POS_X = "widget_x"
SETTING_POS_Y = "widget_y"
SETTING_THEME = "theme"


class AppController:
    def __init__(self, app: QApplication, conn) -> None:
        self._app = app
        self._conn = conn
        self._current_word_id: int | None = None
        self._previous_word_id: int | None = None

        # 保存された選択があればそれを使い、初回だけ OS の設定に従う。
        saved_theme = db.get_setting(conn, SETTING_THEME)
        self._dark = saved_theme == "dark" if saved_theme else theme.is_dark(app)
        tokens = theme.tokens(self._dark)

        self._widget = WidgetWindow(tokens)
        self._panel = PanelWindow(tokens)
        self._panel.apply_theme(tokens, self._dark)

        self._widget.clicked.connect(self._open_panel)
        self._widget.moved.connect(self._save_position)
        self._widget.quit_requested.connect(self._quit)
        self._panel.word_added.connect(self._on_word_added)
        self._panel.word_updated.connect(self._on_word_updated)
        self._panel.learned_toggled.connect(self._on_learned_toggled)
        self._panel.word_opened.connect(self._on_word_opened)
        self._panel.theme_toggled.connect(self._toggle_theme)

        self._restore_position()

        self._timer = QTimer()
        self._timer.setInterval(scheduler.TICK_SECONDS * 1000)
        self._timer.timeout.connect(self.tick)

    def start(self) -> None:
        self._refresh_panel()
        self.tick()
        self._widget.show()
        self._timer.start()

    # --- 出題ティック -------------------------------------------------------
    def tick(self) -> None:
        now = db.utcnow()
        unlearned = db.list_words(self._conn, learned=False)
        selection = scheduler.select(unlearned, now, self._previous_word_id)

        if selection is None:
            self._current_word_id = None
            self._previous_word_id = None
            self._widget.show_placeholder()
            return

        word = selection.word
        if selection.credited:
            db.record_shown(self._conn, word.id, scheduler.next_strength(word, selection.retention), now)
        else:
            db.record_filler(self._conn, word.id, now)

        self._current_word_id = word.id
        self._previous_word_id = word.id
        self._widget.show_word(word.text)

    # --- パネル操作 ---------------------------------------------------------
    def _open_panel(self) -> None:
        self._refresh_panel()
        self._panel.show()
        self._panel.raise_()
        self._panel.activateWindow()

    def _refresh_panel(self) -> None:
        self._panel.set_words(
            db.list_words(self._conn, learned=False),
            db.list_words(self._conn, learned=True),
        )

    def _on_word_added(self, text: str, note: str) -> None:
        try:
            db.add_word(self._conn, text, note)
        except db.DuplicateWordError:
            self._panel.show_add_error(f"「{text}」は既に登録されています")
            return
        self._panel.clear_add_form(f"「{text}」を追加しました")
        self._refresh_panel()
        # 未表示の語は最優先になるため、すぐ画面へ反映する。
        self.tick()

    def _on_word_updated(self, word_id: int, text: str, note: str) -> None:
        try:
            db.update_word(self._conn, word_id, text, note)
        except db.DuplicateWordError:
            self._panel.show_edit_error(f"「{text}」は既に登録されています")
            return
        self._refresh_panel()
        self._panel.leave_edit_after_save()
        if word_id == self._current_word_id:
            self._widget.show_word(text)

    def _on_learned_toggled(self, word_id: int, learned: bool) -> None:
        db.set_learned(self._conn, word_id, learned)
        self._refresh_panel()
        if learned and word_id == self._current_word_id:
            self.tick()

    def _on_word_opened(self, word_id: int) -> None:
        word = db.get_word(self._conn, word_id)
        if word is None:
            return
        # ADR-0002: 表示中の単語の内容を確認した＝想起に失敗した、とみなす。
        if word_id == self._current_word_id:
            db.record_lapse(self._conn, word_id, scheduler.lapsed_strength(word))
        self._panel.show_edit(word)

    # --- テーマ切り替えと終了 -----------------------------------------------
    def _toggle_theme(self) -> None:
        self._dark = not self._dark
        tokens = theme.tokens(self._dark)
        self._widget.apply_theme(tokens)
        self._panel.apply_theme(tokens, self._dark)
        db.set_setting(self._conn, SETTING_THEME, "dark" if self._dark else "light")

    def _quit(self) -> None:
        self._timer.stop()
        self._panel.close()
        self._widget.close()
        self._app.quit()

    # --- ウィジェット位置の永続化 -------------------------------------------
    def _restore_position(self) -> None:
        x = db.get_setting(self._conn, SETTING_POS_X)
        y = db.get_setting(self._conn, SETTING_POS_Y)
        if x is not None and y is not None:
            self._widget.move(int(x), int(y))
            return
        screen = self._app.primaryScreen().availableGeometry()
        self._widget.move(
            screen.right() - theme.WIDGET_WIDTH - 24,
            screen.top() + 24,
        )

    def _save_position(self, x: int, y: int) -> None:
        db.set_setting(self._conn, SETTING_POS_X, str(x))
        db.set_setting(self._conn, SETTING_POS_Y, str(y))


def main() -> int:
    app = QApplication(sys.argv)
    app.setQuitOnLastWindowClosed(False)
    conn = db.connect(DB_PATH)
    controller = AppController(app, conn)
    controller.start()
    return app.exec()


if __name__ == "__main__":
    sys.exit(main())

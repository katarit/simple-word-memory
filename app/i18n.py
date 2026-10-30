"""画面に出る文言（日本語／英語）。

文言はすべてここに集約する。言語は起動時に OS の表示言語から一度だけ決め、
theme のトークンと同じく各ウィンドウへ引数で渡す（グローバル状態にしない）。
版番号やテーマボタンの Dark / Light など、訳さない文字列はここに入れない。
"""

from __future__ import annotations

from datetime import datetime

from PySide6.QtCore import QDate, QLocale

JA = {
    "app_name": "単語リマインダー",
    "window_title": "単語リマインダー  ver. {version}",
    "tab_add": "登録",
    "tab_unlearned": "未学習",
    "tab_learned": "学習済み",
    "field_word": "単語",
    "field_note": "内容（任意）",
    "word_placeholder": "単語を入力",
    "note_placeholder": "意味・例文・メモなど自由に記入",
    "add": "追加",
    "back_link": "← 戻る",
    "back": "戻る",
    "save": "保存",
    "delete": "削除",
    "cancel": "キャンセル",
    "empty_unlearned": "未学習の単語はありません",
    "empty_learned": "学習済みの単語はありません",
    "row_no_note": "（内容未登録）",
    "on_screen": "表示中",
    "added_on": "登録日: {date}",
    "word_required": "単語を入力してください",
    "word_added": "「{text}」を追加しました",
    "word_duplicate": "「{text}」は既に登録されています",
    "delete_title": "単語の削除",
    "delete_question": "「{text}」を削除しますか？\n削除すると元に戻せません。",
    "widget_empty": "登録単語なし",
    "meaning_empty": "内容未登録",
    "menu_next": "次の単語",
    "menu_manage": "管理パネルを開く",
    "menu_exit": "終了",
}

# 直訳でなく、英語の利用者が Windows で見て自然な語を選んでいる。
# - タブは Learning / Learned だと語尾しか違わず取り違えるため Studying にする
# - 終了は Windows の慣習どおり Exit（Quit は macOS の語）
# - 内容欄は Content では何を書くか伝わらないため Note
# - 単語が無い表示は、全部学習済みにしたときにも出るので "yet" を付けない
EN = {
    "app_name": "Word Reminder",
    "window_title": "Word Reminder  v{version}",
    "tab_add": "Add",
    "tab_unlearned": "Studying",
    "tab_learned": "Learned",
    "field_word": "Word",
    "field_note": "Note (optional)",
    "word_placeholder": "Enter a word",
    "note_placeholder": "Meaning, example sentences, anything that helps",
    "add": "Add",
    "back_link": "← Back",
    "back": "Back",
    "save": "Save",
    "delete": "Delete",
    "cancel": "Cancel",
    "empty_unlearned": "No words to study",
    "empty_learned": "No learned words yet",
    "row_no_note": "(No note)",
    "on_screen": "On screen",
    "added_on": "Added {date}",
    "word_required": "Enter a word.",
    "word_added": "Added “{text}”.",
    "word_duplicate": "“{text}” is already in your list.",
    "delete_title": "Delete word",
    "delete_question": "Delete “{text}”?\nThis can't be undone.",
    "widget_empty": "No words to show",
    "meaning_empty": "No note",
    "menu_next": "Next word",
    "menu_manage": "Manage words",
    "menu_exit": "Exit",
}

TABLES = {"ja": JA, "en": EN}


def detect_language(ui_languages: list[str]) -> str:
    """OS の表示言語の先頭が日本語なら "ja"、それ以外（空を含む）は "en"。

    QLocale.system() の言語は Windows では地域の書式に従うため使わない。
    翻訳を探す順は uiLanguages() が返す（Qt 6 公式 QLocale、2026-10-30 確認）。
    """
    if not ui_languages:
        return "en"
    primary = ui_languages[0].replace("_", "-").split("-")[0].lower()
    return "ja" if primary == "ja" else "en"


class Strings:
    """1 言語ぶんの文言。s("key", text=...) で引く。"""

    def __init__(self, language: str) -> None:
        self.language = language
        self._table = TABLES[language]

    def __call__(self, key: str, **fields: str) -> str:
        return self._table[key].format(**fields)

    def date(self, value: datetime | None) -> str:
        """登録日の表示。英語は月名にして、米英で月日を取り違えないようにする。"""
        if value is None:
            return ""
        local = value.astimezone()
        if self.language == "ja":
            return local.strftime("%Y/%m/%d")
        # strftime の %b は C ランタイムのロケールに依存するため Qt で固定する。
        return QLocale(QLocale.English, QLocale.UnitedStates).toString(
            QDate(local.year, local.month, local.day), "MMM d, yyyy"
        )


def strings(language: str) -> Strings:
    return Strings(language)

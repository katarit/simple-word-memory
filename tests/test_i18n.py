"""画面文言の日英切り替えの検証。"""

from __future__ import annotations

import ast
import re
from datetime import datetime, timezone
from pathlib import Path

import pytest
from PySide6.QtWidgets import QApplication

from app import i18n, theme
from app.panel_window import PanelWindow
from app.widget_window import WidgetWindow

ROOT = Path(__file__).resolve().parent.parent
JAPANESE = re.compile(r"[぀-ヿ㐀-鿿＀-￯]")

# 画面に出ない内部向けの文字列。訳す対象ではない（tech-rules 1-3）。
NOT_TRANSLATED = {
    ("app/db.py", "単語が空です"),
}


@pytest.fixture(scope="module")
def qapp():
    app = QApplication.instance() or QApplication([])
    yield app


def test_both_languages_have_the_same_keys():
    assert set(i18n.JA) == set(i18n.EN)


@pytest.mark.parametrize(
    ("ui_languages", "expected"),
    [
        (["ja-Jpan-JP", "ja-JP", "ja"], "ja"),
        (["ja_JP"], "ja"),
        (["en-Latn-US", "en-US", "en"], "en"),
        # 表示言語の先頭が日本語でなければ、2 番目以降に日本語があっても英語
        (["en-US", "ja-JP"], "en"),
        (["fr-FR"], "en"),
        ([], "en"),
    ],
)
def test_language_follows_first_ui_language_and_falls_back_to_english(ui_languages, expected):
    assert i18n.detect_language(ui_languages) == expected


def test_japanese_strings_are_unchanged_from_before_translation():
    """日英対応の前に画面へ出ていた日本語を固定する。"""
    ja = i18n.strings("ja")
    assert ja("window_title", version="1.2.3") == "単語リマインダー  ver. 1.2.3"
    assert [ja("tab_add"), ja("tab_unlearned"), ja("tab_learned")] == ["登録", "未学習", "学習済み"]
    assert ja("added_on", date="2026/10/30") == "登録日: 2026/10/30"
    assert ja("word_duplicate", text="x") == "「x」は既に登録されています"
    assert ja("word_added", text="x") == "「x」を追加しました"
    assert ja("widget_empty") == "登録単語なし"
    assert ja("row_no_note") == "（内容未登録）"


@pytest.mark.parametrize(
    ("language", "expected"),
    [("ja", "2026/01/05"), ("en", "Jan 5, 2026")],
)
def test_added_date_format(language, expected):
    # 正午 UTC なら、どのタイムゾーンでもローカル日付は 1/5 のまま
    value = datetime(2026, 1, 5, 12, 0, tzinfo=timezone.utc)
    assert i18n.strings(language).date(value) == expected


def test_user_text_with_braces_is_inserted_verbatim():
    assert i18n.strings("en")("word_added", text="{x}") == "Added “{x}”."


def _docstring_nodes(tree: ast.AST) -> set[int]:
    ids = set()
    for node in ast.walk(tree):
        if isinstance(node, (ast.Module, ast.ClassDef, ast.FunctionDef, ast.AsyncFunctionDef)):
            body = node.body
            if body and isinstance(body[0], ast.Expr) and isinstance(body[0].value, ast.Constant):
                ids.add(id(body[0].value))
        # モジュール定数の直後に置いた説明文字列（DRAG_THRESHOLD_PX 等）
        if isinstance(node, ast.Module):
            for stmt in node.body:
                if isinstance(stmt, ast.Expr) and isinstance(stmt.value, ast.Constant):
                    ids.add(id(stmt.value))
    return ids


def test_no_japanese_string_literals_outside_i18n():
    """画面文言が直書きへ戻る回帰を止める（tech-rules 1-9）。"""
    sources = [ROOT / "main.py", *sorted((ROOT / "app").glob("*.py"))]
    leaks = []
    for path in sources:
        rel = path.relative_to(ROOT).as_posix()
        if rel == "app/i18n.py":
            continue
        tree = ast.parse(path.read_text(encoding="utf-8"))
        docstrings = _docstring_nodes(tree)
        for node in ast.walk(tree):
            if (
                isinstance(node, ast.Constant)
                and isinstance(node.value, str)
                and id(node) not in docstrings
                and JAPANESE.search(node.value)
                and (rel, node.value) not in NOT_TRANSLATED
            ):
                leaks.append(f"{rel}:{node.lineno} {node.value!r}")
    assert leaks == []


def test_english_panel_shows_english_labels(qapp):
    panel = PanelWindow(theme.tokens(False), i18n.strings("en"))

    assert panel.windowTitle().startswith("Word Reminder  v")
    assert [label.text() for label in panel._tab_labels] == ["Add", "Studying", "Learned"]
    assert panel._add_text.placeholderText() == "Enter a word"
    panel.close()


def test_english_widget_menu_uses_windows_wording(qapp):
    widget = WidgetWindow(theme.tokens(False), i18n.strings("en"))
    widget.show_word("ephemeral")

    texts = [action.text() for action in widget._create_context_menu().actions()]

    assert texts == ["Next word", "", "Manage words", "", "Exit"]
    widget.close()

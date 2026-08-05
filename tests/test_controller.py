"""コントローラが表示を記憶評価へ変換しないことの回帰テスト。"""

from types import SimpleNamespace

from app import db
from main import AppController


def test_tick_records_formal_opportunity_with_new_scheduler_contract(tmp_path):
    """旧Selection APIを参照すると、起動直後の最初のtickで失敗する。"""
    conn = db.connect(tmp_path / "controller.db")
    word_id = db.add_word(conn, "ephemeral")
    shown = []

    controller = AppController.__new__(AppController)
    controller._conn = conn
    controller._current_word_id = None
    controller._previous_word_id = None
    controller._consecutive_new_opportunities = 0
    controller._widget = SimpleNamespace(
        show_word=shown.append,
        show_placeholder=lambda: None,
    )

    controller.tick()

    word = db.get_word(conn, word_id)
    assert word is not None
    assert word.opportunity_count == 1
    assert word.last_opportunity_at is not None
    assert controller._consecutive_new_opportunities == 1
    assert shown == ["ephemeral"]
    conn.close()


def test_tick_resets_new_streak_when_no_unlearned_words(tmp_path):
    conn = db.connect(tmp_path / "controller.db")
    placeholders = []

    controller = AppController.__new__(AppController)
    controller._conn = conn
    controller._current_word_id = 1
    controller._previous_word_id = 1
    controller._consecutive_new_opportunities = 2
    controller._widget = SimpleNamespace(
        show_word=lambda _text: None,
        show_placeholder=lambda: placeholders.append(True),
    )

    controller.tick()

    assert controller._consecutive_new_opportunities == 0
    assert placeholders == [True]
    conn.close()


def test_adding_word_waits_for_the_regular_tick(tmp_path):
    """登録操作そのものが正式機会を記録する回帰を検出する。"""
    conn = db.connect(tmp_path / "controller.db")
    panel = SimpleNamespace(
        clear_add_form=lambda _message: None,
        set_words=lambda _unlearned, _learned: None,
    )

    controller = AppController.__new__(AppController)
    controller._conn = conn
    controller._panel = panel
    controller._current_word_id = None
    controller._previous_word_id = None
    controller._consecutive_new_opportunities = 0
    controller._widget = SimpleNamespace(
        show_word=lambda _text: None,
        show_placeholder=lambda: None,
    )

    controller._on_word_added("ephemeral", "")

    word = db.list_words(conn, learned=False)[0]
    assert word.opportunity_count == 0
    assert word.last_opportunity_at is None
    conn.close()


def test_learning_current_word_clears_it_without_scheduling_another(tmp_path):
    """学習済み操作から次語の履歴を5分未満で進める回帰を検出する。"""
    conn = db.connect(tmp_path / "controller.db")
    current_id = db.add_word(conn, "current")
    other_id = db.add_word(conn, "other")
    placeholders = []

    controller = AppController.__new__(AppController)
    controller._conn = conn
    controller._current_word_id = current_id
    controller._previous_word_id = current_id
    controller._consecutive_new_opportunities = 0
    controller._panel = SimpleNamespace(
        set_words=lambda _unlearned, _learned: None,
    )
    controller._widget = SimpleNamespace(
        show_word=lambda _text: None,
        show_placeholder=lambda: placeholders.append(True),
    )

    controller._on_learned_toggled(current_id, True)

    other = db.get_word(conn, other_id)
    assert other is not None
    assert other.opportunity_count == 0
    assert other.last_opportunity_at is None
    assert controller._current_word_id is None
    assert controller._previous_word_id is None
    assert placeholders == [True]
    conn.close()


def test_tick_records_filler_without_advancing_formal_history(tmp_path):
    conn = db.connect(tmp_path / "controller.db")
    word_id = db.add_word(conn, "ephemeral")
    opportunity_at = db.utcnow()
    db.record_opportunity(conn, word_id, opportunity_at)

    controller = AppController.__new__(AppController)
    controller._conn = conn
    controller._current_word_id = None
    controller._previous_word_id = None
    controller._consecutive_new_opportunities = 1
    controller._widget = SimpleNamespace(
        show_word=lambda _text: None,
        show_placeholder=lambda: None,
    )

    controller.tick()

    word = db.get_word(conn, word_id)
    assert word is not None
    assert word.opportunity_count == 1
    assert word.last_opportunity_at == opportunity_at
    assert word.last_filler_at is not None
    assert controller._consecutive_new_opportunities == 1
    conn.close()


def test_opening_current_word_does_not_change_opportunity_history(tmp_path):
    """詳細表示を想起失敗とみなし、履歴を変更する回帰を検出する。"""
    conn = db.connect(tmp_path / "controller.db")
    word_id = db.add_word(conn, "ephemeral")
    before = db.get_word(conn, word_id)
    shown = []

    controller = AppController.__new__(AppController)
    controller._conn = conn
    controller._current_word_id = word_id
    controller._panel = SimpleNamespace(show_edit=shown.append)

    controller._on_word_opened(word_id)

    after = db.get_word(conn, word_id)
    assert before is not None
    assert after is not None
    assert after.opportunity_count == before.opportunity_count
    assert after.last_opportunity_at == before.last_opportunity_at
    assert [word.id for word in shown] == [word_id]
    conn.close()

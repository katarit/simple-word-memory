"""コントローラが表示を記憶評価へ変換しないことの回帰テスト。"""

from types import SimpleNamespace

from app import db, i18n
from main import AppController


def meaning_stub(**overrides):
    values = {
        "hide": lambda: None,
        "isVisible": lambda: False,
        "show_note": lambda _note, _anchor: None,
        "close": lambda: None,
        "apply_theme": lambda _tokens: None,
    }
    values.update(overrides)
    return SimpleNamespace(**values)


def widget_stub(**overrides):
    values = {
        "show_word": lambda _text: None,
        "update_word_text": lambda _text: None,
        "show_placeholder": lambda: None,
        "set_can_advance": lambda _enabled: None,
        "frameGeometry": lambda: None,
    }
    values.update(overrides)
    return SimpleNamespace(**values)


def panel_stub(**overrides):
    values = {
        "set_words": lambda _unlearned, _learned: None,
        "set_current_word": lambda _word_id: None,
    }
    values.update(overrides)
    return SimpleNamespace(**values)


def test_tick_records_formal_opportunity_with_new_scheduler_contract(tmp_path):
    """旧Selection APIを参照すると、起動直後の最初のtickで失敗する。"""
    conn = db.connect(tmp_path / "controller.db")
    word_id = db.add_word(conn, "ephemeral")
    shown = []
    marked = []

    controller = AppController.__new__(AppController)
    controller._conn = conn
    controller._current_word_id = None
    controller._previous_word_id = None
    controller._consecutive_new_opportunities = 0
    controller._panel = panel_stub(set_current_word=marked.append)
    controller._meaning = meaning_stub()
    controller._widget = widget_stub(show_word=shown.append)

    controller.tick()

    word = db.get_word(conn, word_id)
    assert word is not None
    assert word.opportunity_count == 1
    assert word.last_opportunity_at is not None
    assert controller._consecutive_new_opportunities == 1
    assert shown == ["ephemeral"]
    assert marked == [word_id]
    conn.close()


def test_tick_resets_new_streak_when_no_unlearned_words(tmp_path):
    conn = db.connect(tmp_path / "controller.db")
    placeholders = []
    marked = []

    controller = AppController.__new__(AppController)
    controller._conn = conn
    controller._current_word_id = 1
    controller._previous_word_id = 1
    controller._consecutive_new_opportunities = 2
    controller._panel = panel_stub(set_current_word=marked.append)
    controller._meaning = meaning_stub()
    controller._widget = widget_stub(
        show_placeholder=lambda: placeholders.append(True),
    )

    controller.tick()

    assert controller._consecutive_new_opportunities == 0
    assert placeholders == [True]
    assert marked == [None]
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
    controller._s = i18n.strings("ja")
    controller._panel = panel
    controller._current_word_id = None
    controller._previous_word_id = None
    controller._consecutive_new_opportunities = 0
    controller._meaning = meaning_stub()
    controller._widget = widget_stub()

    controller._on_word_added("ephemeral", "")

    word = db.list_words(conn, learned=False)[0]
    assert word.opportunity_count == 0
    assert word.last_opportunity_at is None
    conn.close()


def test_learning_current_word_shows_next_word_immediately(tmp_path):
    """表示中の語を学習済みにしたら、空白で 5 分待たせず次の語を出す（WR-9）。"""
    conn = db.connect(tmp_path / "controller.db")
    current_id = db.add_word(conn, "current")
    other_id = db.add_word(conn, "other")
    shown = []
    timer_starts = []

    controller = AppController.__new__(AppController)
    controller._conn = conn
    controller._current_word_id = current_id
    controller._previous_word_id = current_id
    controller._consecutive_new_opportunities = 0
    controller._panel = panel_stub(
        set_words=lambda _unlearned, _learned: None,
    )
    controller._meaning = meaning_stub()
    controller._widget = widget_stub(show_word=shown.append)
    controller._timer = SimpleNamespace(start=lambda: timer_starts.append(True))

    controller._on_learned_toggled(current_id, True)

    assert controller._current_word_id == other_id
    assert shown == ["other"]
    assert timer_starts == [True]
    conn.close()


def test_learning_last_word_shows_placeholder(tmp_path):
    conn = db.connect(tmp_path / "controller.db")
    only_id = db.add_word(conn, "only")
    placeholders = []

    controller = AppController.__new__(AppController)
    controller._conn = conn
    controller._current_word_id = only_id
    controller._previous_word_id = only_id
    controller._consecutive_new_opportunities = 0
    controller._panel = panel_stub(
        set_words=lambda _unlearned, _learned: None,
    )
    controller._meaning = meaning_stub()
    controller._widget = widget_stub(
        show_placeholder=lambda: placeholders.append(True),
    )
    controller._timer = SimpleNamespace(start=lambda: None)

    controller._on_learned_toggled(only_id, True)

    assert controller._current_word_id is None
    assert placeholders == [True]
    conn.close()


def test_deleting_current_word_removes_it_and_shows_next_word(tmp_path):
    conn = db.connect(tmp_path / "controller.db")
    current_id = db.add_word(conn, "mistake")
    other_id = db.add_word(conn, "other")
    shown = []
    left = []
    timer_starts = []

    controller = AppController.__new__(AppController)
    controller._conn = conn
    controller._current_word_id = current_id
    controller._previous_word_id = current_id
    controller._consecutive_new_opportunities = 0
    controller._panel = panel_stub(
        set_words=lambda _unlearned, _learned: None,
        leave_edit_after_delete=lambda: left.append(True),
    )
    controller._meaning = meaning_stub()
    controller._widget = widget_stub(show_word=shown.append)
    controller._timer = SimpleNamespace(start=lambda: timer_starts.append(True))

    controller._on_word_deleted(current_id)

    assert db.get_word(conn, current_id) is None
    assert controller._current_word_id == other_id
    assert shown == ["other"]
    assert timer_starts == [True]
    assert left == [True]
    conn.close()


def test_deleting_other_word_keeps_current_display(tmp_path):
    conn = db.connect(tmp_path / "controller.db")
    current_id = db.add_word(conn, "current")
    other_id = db.add_word(conn, "mistake")
    placeholders = []

    controller = AppController.__new__(AppController)
    controller._conn = conn
    controller._current_word_id = current_id
    controller._panel = panel_stub(
        set_words=lambda _unlearned, _learned: None,
        leave_edit_after_delete=lambda: None,
    )
    controller._meaning = meaning_stub()
    controller._widget = widget_stub(
        show_placeholder=lambda: placeholders.append(True),
    )

    controller._on_word_deleted(other_id)

    assert db.get_word(conn, other_id) is None
    assert controller._current_word_id == current_id
    assert placeholders == []
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
    controller._panel = panel_stub()
    controller._meaning = meaning_stub()
    controller._widget = widget_stub()

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


def test_manual_next_records_action_advances_word_and_restarts_timer(tmp_path):
    conn = db.connect(tmp_path / "controller.db")
    first_id = db.add_word(conn, "first")
    second_id = db.add_word(conn, "second")
    shown = []
    timer_starts = []

    controller = AppController.__new__(AppController)
    controller._conn = conn
    controller._current_word_id = first_id
    controller._previous_word_id = first_id
    controller._consecutive_new_opportunities = 0
    controller._last_manual_next_display_token = None
    controller._panel = panel_stub()
    controller._meaning = meaning_stub()
    controller._widget = widget_stub(show_word=shown.append)
    controller._timer = SimpleNamespace(start=lambda: timer_starts.append(True))

    controller._on_next_requested(7)

    first = db.get_word(conn, first_id)
    second = db.get_word(conn, second_id)
    assert first.manual_next_action_count == 1
    assert first.manual_next_bonus_pending is True
    assert second.opportunity_count == 1
    assert controller._current_word_id == second_id
    assert shown == ["second"]
    assert timer_starts == [True]
    conn.close()


def test_manual_next_ignores_duplicate_event_from_same_display(tmp_path):
    conn = db.connect(tmp_path / "controller.db")
    first_id = db.add_word(conn, "first")
    second_id = db.add_word(conn, "second")

    controller = AppController.__new__(AppController)
    controller._conn = conn
    controller._current_word_id = first_id
    controller._previous_word_id = first_id
    controller._consecutive_new_opportunities = 0
    controller._last_manual_next_display_token = None
    controller._panel = panel_stub()
    controller._meaning = meaning_stub()
    controller._widget = widget_stub()
    controller._timer = SimpleNamespace(start=lambda: None)

    controller._on_next_requested(7)
    controller._on_next_requested(7)

    words = db.list_words(conn)
    assert sum(word.manual_next_action_count for word in words) == 1
    conn.close()


def test_manual_next_does_nothing_when_only_one_unlearned_word_exists(tmp_path):
    conn = db.connect(tmp_path / "controller.db")
    word_id = db.add_word(conn, "only")

    controller = AppController.__new__(AppController)
    controller._conn = conn
    controller._current_word_id = word_id
    controller._last_manual_next_display_token = None
    controller._meaning = meaning_stub()
    controller._timer = SimpleNamespace(start=lambda: None)

    controller._on_next_requested(3)

    assert db.get_word(conn, word_id).manual_next_action_count == 0
    conn.close()


def test_left_click_shows_only_current_meaning(tmp_path):
    conn = db.connect(tmp_path / "controller.db")
    word_id = db.add_word(conn, "ephemeral", "儚い")
    shown_notes = []

    controller = AppController.__new__(AppController)
    controller._conn = conn
    controller._current_word_id = word_id
    # パネルに触れたら AttributeError で落ちる
    controller._panel = SimpleNamespace()
    controller._widget = widget_stub(frameGeometry=lambda: "anchor")
    controller._meaning = meaning_stub(
        show_note=lambda note, anchor: shown_notes.append((note, anchor))
    )

    controller._show_meaning()

    assert shown_notes == [("儚い", "anchor")]
    conn.close()


def test_left_click_again_closes_open_meaning(tmp_path):
    conn = db.connect(tmp_path / "controller.db")
    word_id = db.add_word(conn, "ephemeral", "儚い")
    hidden = []
    shown_notes = []

    controller = AppController.__new__(AppController)
    controller._conn = conn
    controller._current_word_id = word_id
    controller._widget = widget_stub(frameGeometry=lambda: "anchor")
    controller._meaning = meaning_stub(
        isVisible=lambda: True,
        hide=lambda: hidden.append(True),
        show_note=lambda note, anchor: shown_notes.append((note, anchor)),
    )

    controller._show_meaning()

    assert hidden == [True]
    assert shown_notes == []
    conn.close()


def test_open_panel_from_menu_starts_on_quick_entry(tmp_path):
    conn = db.connect(tmp_path / "controller.db")
    calls = []

    controller = AppController.__new__(AppController)
    controller._conn = conn
    controller._panel = panel_stub(
        isVisible=lambda: False,
        set_words=lambda _unlearned, _learned: calls.append("refresh"),
        show=lambda: calls.append("show"),
        show_add_for_quick_entry=lambda: calls.append("quick"),
        raise_=lambda: calls.append("raise"),
        activateWindow=lambda: calls.append("activate"),
    )
    controller._widget = widget_stub()

    controller._open_panel()

    assert calls == ["refresh", "show", "quick", "raise", "activate"]
    conn.close()


def test_open_panel_from_menu_preserves_visible_panel_view(tmp_path):
    conn = db.connect(tmp_path / "controller.db")
    quick_entries = []

    controller = AppController.__new__(AppController)
    controller._conn = conn
    controller._panel = panel_stub(
        isVisible=lambda: True,
        set_words=lambda _unlearned, _learned: None,
        show=lambda: None,
        show_add_for_quick_entry=lambda: quick_entries.append(True),
        raise_=lambda: None,
        activateWindow=lambda: None,
    )
    controller._widget = widget_stub()

    controller._open_panel()

    assert quick_entries == []
    conn.close()


def test_refresh_panel_updates_manual_next_availability(tmp_path):
    conn = db.connect(tmp_path / "controller.db")
    db.add_word(conn, "first")
    db.add_word(conn, "second")
    availability = []

    controller = AppController.__new__(AppController)
    controller._conn = conn
    controller._panel = panel_stub(
        set_words=lambda _unlearned, _learned: None,
    )
    controller._widget = widget_stub(
        set_can_advance=availability.append,
    )

    controller._refresh_panel()

    assert availability == [True]
    conn.close()

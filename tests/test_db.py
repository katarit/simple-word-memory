from datetime import datetime, timedelta, timezone

import pytest

from app import db


@pytest.fixture()
def conn(tmp_path):
    connection = db.connect(tmp_path / "test.db")
    yield connection
    connection.close()


def test_add_and_list(conn):
    db.add_word(conn, "ephemeral", "儚い、短命な")
    words = db.list_words(conn, learned=False)
    assert [w.text for w in words] == ["ephemeral"]
    assert words[0].note == "儚い、短命な"
    assert words[0].show_count == 0
    assert words[0].strength_days is None
    assert words[0].last_shown_at is None


def test_add_rejects_duplicate(conn):
    db.add_word(conn, "ephemeral")
    with pytest.raises(db.DuplicateWordError):
        db.add_word(conn, "ephemeral")


def test_add_rejects_blank(conn):
    with pytest.raises(ValueError):
        db.add_word(conn, "   ")


def test_update_word(conn):
    word_id = db.add_word(conn, "ephemeral", "旧メモ")
    db.update_word(conn, word_id, "ephemeral", "新メモ")
    assert db.get_word(conn, word_id).note == "新メモ"


def test_set_learned_keeps_scheduling_state(conn):
    """ADR-0002: チェックの切り替えで学習の経緯を破棄しない。"""
    word_id = db.add_word(conn, "ephemeral")
    now = db.utcnow()
    db.record_shown(conn, word_id, 1.6, now)
    db.record_lapse(conn, word_id, 0.8)

    db.set_learned(conn, word_id, True)
    db.set_learned(conn, word_id, False)

    word = db.get_word(conn, word_id)
    assert word.learned is False
    assert word.show_count == 1
    assert word.strength_days == 0.8
    assert word.lapse_count == 1
    assert word.last_shown_at is not None


def test_record_filler_does_not_touch_strength(conn):
    """ADR-0002: 埋め草は強度・表示回数・last_shown_at を更新しない。"""
    word_id = db.add_word(conn, "ephemeral")
    shown_at = datetime(2026, 7, 30, tzinfo=timezone.utc)
    db.record_shown(conn, word_id, 1.0, shown_at)

    db.record_filler(conn, word_id, shown_at + timedelta(minutes=5))

    word = db.get_word(conn, word_id)
    assert word.show_count == 1
    assert word.strength_days == 1.0
    assert word.last_shown_at == shown_at
    assert word.last_filler_at is not None


def test_learned_filter(conn):
    a = db.add_word(conn, "alpha")
    db.add_word(conn, "beta")
    db.set_learned(conn, a, True)
    assert [w.text for w in db.list_words(conn, learned=True)] == ["alpha"]
    assert [w.text for w in db.list_words(conn, learned=False)] == ["beta"]


def test_settings_roundtrip(conn):
    assert db.get_setting(conn, "widget_x") is None
    db.set_setting(conn, "widget_x", "100")
    db.set_setting(conn, "widget_x", "220")
    assert db.get_setting(conn, "widget_x") == "220"

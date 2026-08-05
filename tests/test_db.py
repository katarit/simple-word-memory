import sqlite3
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
    assert words[0].opportunity_count == 0
    assert words[0].last_opportunity_at is None
    assert words[0].last_filler_at is None


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


def test_set_learned_keeps_opportunity_history(conn):
    word_id = db.add_word(conn, "ephemeral")
    now = db.utcnow()
    db.record_opportunity(conn, word_id, now)

    db.set_learned(conn, word_id, True)
    db.set_learned(conn, word_id, False)

    word = db.get_word(conn, word_id)
    assert word.learned is False
    assert word.opportunity_count == 1
    assert word.last_opportunity_at == now


def test_record_opportunity_updates_only_opportunity_history(conn):
    word_id = db.add_word(conn, "ephemeral")
    shown_at = datetime(2026, 8, 4, 9, 0, tzinfo=timezone.utc)

    db.record_opportunity(conn, word_id, shown_at)

    word = db.get_word(conn, word_id)
    assert word.opportunity_count == 1
    assert word.last_opportunity_at == shown_at
    assert word.last_filler_at is None


def test_record_filler_does_not_advance_opportunity(conn):
    word_id = db.add_word(conn, "ephemeral")
    opportunity_at = datetime(2026, 8, 4, 9, 0, tzinfo=timezone.utc)
    filler_at = opportunity_at + timedelta(minutes=5)
    db.record_opportunity(conn, word_id, opportunity_at)

    db.record_filler(conn, word_id, filler_at)

    word = db.get_word(conn, word_id)
    assert word.opportunity_count == 1
    assert word.last_opportunity_at == opportunity_at
    assert word.last_filler_at == filler_at


def test_connect_migrates_legacy_scheduling_history(tmp_path):
    path = tmp_path / "legacy.db"
    legacy = sqlite3.connect(path)
    legacy.executescript(
        """
        CREATE TABLE words (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            text TEXT NOT NULL UNIQUE,
            note TEXT NOT NULL DEFAULT '',
            added_at TEXT NOT NULL,
            learned INTEGER NOT NULL DEFAULT 0,
            learned_at TEXT,
            show_count INTEGER NOT NULL DEFAULT 0,
            strength_days REAL,
            last_shown_at TEXT,
            last_filler_at TEXT,
            lapse_count INTEGER NOT NULL DEFAULT 0
        );
        CREATE TABLE settings (key TEXT PRIMARY KEY, value TEXT NOT NULL);
        """
    )
    shown_at = datetime(2026, 8, 3, 9, 0, tzinfo=timezone.utc)
    legacy.execute(
        """
        INSERT INTO words
            (text, note, added_at, show_count, strength_days, last_shown_at)
        VALUES (?, ?, ?, ?, ?, ?)
        """,
        ("ephemeral", "", db.to_iso(shown_at - timedelta(days=1)), 4, 6.4, db.to_iso(shown_at)),
    )
    legacy.commit()
    legacy.close()

    migrated = db.connect(path)
    word = db.list_words(migrated)[0]
    assert word.opportunity_count == 4
    assert word.last_opportunity_at == shown_at
    columns = {row["name"] for row in migrated.execute("PRAGMA table_info(words)")}
    assert {"show_count", "strength_days", "opportunity_count", "last_opportunity_at"} <= columns
    migrated.close()


def test_reconnect_does_not_overwrite_migrated_opportunity_history(tmp_path):
    path = tmp_path / "legacy.db"
    legacy = sqlite3.connect(path)
    legacy.executescript(
        """
        CREATE TABLE words (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            text TEXT NOT NULL UNIQUE,
            note TEXT NOT NULL DEFAULT '',
            added_at TEXT NOT NULL,
            learned INTEGER NOT NULL DEFAULT 0,
            learned_at TEXT,
            show_count INTEGER NOT NULL DEFAULT 0,
            strength_days REAL,
            last_shown_at TEXT,
            last_filler_at TEXT,
            lapse_count INTEGER NOT NULL DEFAULT 0
        );
        CREATE TABLE settings (key TEXT PRIMARY KEY, value TEXT NOT NULL);
        """
    )
    migrated_at = datetime(2026, 8, 3, 9, 0, tzinfo=timezone.utc)
    legacy.execute(
        """
        INSERT INTO words (text, added_at, show_count, last_shown_at)
        VALUES (?, ?, ?, ?)
        """,
        ("ephemeral", db.to_iso(migrated_at - timedelta(days=1)), 4, db.to_iso(migrated_at)),
    )
    legacy.commit()
    legacy.close()

    migrated = db.connect(path)
    word_id = db.list_words(migrated)[0].id
    updated_at = datetime(2026, 8, 4, 9, 0, tzinfo=timezone.utc)
    db.record_opportunity(migrated, word_id, updated_at)
    migrated.close()

    reconnected = db.connect(path)
    word = db.get_word(reconnected, word_id)
    assert word.opportunity_count == 5
    assert word.last_opportunity_at == updated_at
    reconnected.close()


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

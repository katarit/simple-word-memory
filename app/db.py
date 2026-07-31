"""SQLite 永続化層。

責務は保存と取り出しのみ。出題ロジックは scheduler.py が持つ。
"""

from __future__ import annotations

import sqlite3
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path

SCHEMA = """
CREATE TABLE IF NOT EXISTS words (
    id             INTEGER PRIMARY KEY AUTOINCREMENT,
    text           TEXT    NOT NULL UNIQUE,
    note           TEXT    NOT NULL DEFAULT '',
    added_at       TEXT    NOT NULL,
    learned        INTEGER NOT NULL DEFAULT 0,
    learned_at     TEXT,
    show_count     INTEGER NOT NULL DEFAULT 0,
    strength_days  REAL,
    last_shown_at  TEXT,
    last_filler_at TEXT,
    lapse_count    INTEGER NOT NULL DEFAULT 0
);

CREATE TABLE IF NOT EXISTS settings (
    key   TEXT PRIMARY KEY,
    value TEXT NOT NULL
);
"""


class DuplicateWordError(Exception):
    """同じ綴りの単語が既に登録されている。"""


@dataclass
class Word:
    id: int
    text: str
    note: str
    added_at: datetime
    learned: bool
    learned_at: datetime | None
    show_count: int
    strength_days: float | None
    last_shown_at: datetime | None
    last_filler_at: datetime | None
    lapse_count: int


def utcnow() -> datetime:
    return datetime.now(timezone.utc)


def to_iso(dt: datetime | None) -> str | None:
    return None if dt is None else dt.astimezone(timezone.utc).isoformat()


def from_iso(text: str | None) -> datetime | None:
    return None if text is None else datetime.fromisoformat(text)


def connect(db_path: str | Path) -> sqlite3.Connection:
    path = Path(db_path)
    path.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(path)
    conn.row_factory = sqlite3.Row
    conn.executescript(SCHEMA)
    conn.commit()
    return conn


def _row_to_word(row: sqlite3.Row) -> Word:
    return Word(
        id=row["id"],
        text=row["text"],
        note=row["note"],
        added_at=from_iso(row["added_at"]),
        learned=bool(row["learned"]),
        learned_at=from_iso(row["learned_at"]),
        show_count=row["show_count"],
        strength_days=row["strength_days"],
        last_shown_at=from_iso(row["last_shown_at"]),
        last_filler_at=from_iso(row["last_filler_at"]),
        lapse_count=row["lapse_count"],
    )


def add_word(conn: sqlite3.Connection, text: str, note: str = "", now: datetime | None = None) -> int:
    text = text.strip()
    if not text:
        raise ValueError("単語が空です")
    try:
        cur = conn.execute(
            "INSERT INTO words (text, note, added_at) VALUES (?, ?, ?)",
            (text, note.strip(), to_iso(now or utcnow())),
        )
    except sqlite3.IntegrityError as exc:
        raise DuplicateWordError(text) from exc
    conn.commit()
    return cur.lastrowid


def update_word(conn: sqlite3.Connection, word_id: int, text: str, note: str) -> None:
    text = text.strip()
    if not text:
        raise ValueError("単語が空です")
    try:
        conn.execute("UPDATE words SET text = ?, note = ? WHERE id = ?", (text, note.strip(), word_id))
    except sqlite3.IntegrityError as exc:
        raise DuplicateWordError(text) from exc
    conn.commit()


def delete_word(conn: sqlite3.Connection, word_id: int) -> None:
    conn.execute("DELETE FROM words WHERE id = ?", (word_id,))
    conn.commit()


def get_word(conn: sqlite3.Connection, word_id: int) -> Word | None:
    row = conn.execute("SELECT * FROM words WHERE id = ?", (word_id,)).fetchone()
    return _row_to_word(row) if row else None


def list_words(conn: sqlite3.Connection, learned: bool | None = None) -> list[Word]:
    """learned=None なら全件。並びは登録が新しい順。"""
    if learned is None:
        rows = conn.execute("SELECT * FROM words ORDER BY added_at DESC, id DESC").fetchall()
    else:
        rows = conn.execute(
            "SELECT * FROM words WHERE learned = ? ORDER BY added_at DESC, id DESC",
            (1 if learned else 0,),
        ).fetchall()
    return [_row_to_word(row) for row in rows]


def set_learned(conn: sqlite3.Connection, word_id: int, learned: bool, now: datetime | None = None) -> None:
    """学習済みフラグの切り替え。

    このフラグは表示するかどうかだけを決める。強度・表示回数・最終表示時刻・
    想起失敗回数は、チェックを外しても破棄しない（学び直しでも経緯を保つ）。
    """
    conn.execute(
        "UPDATE words SET learned = ?, learned_at = ? WHERE id = ?",
        (1 if learned else 0, to_iso(now or utcnow()) if learned else None, word_id),
    )
    conn.commit()


def record_shown(conn: sqlite3.Connection, word_id: int, strength_days: float, now: datetime) -> None:
    """クレジットありの表示を記録する（強度を更新する）。"""
    conn.execute(
        """UPDATE words
              SET show_count = show_count + 1,
                  strength_days = ?,
                  last_shown_at = ?
            WHERE id = ?""",
        (strength_days, to_iso(now), word_id),
    )
    conn.commit()


def record_filler(conn: sqlite3.Connection, word_id: int, now: datetime) -> None:
    """埋め草表示を記録する。

    埋め草は強度・表示回数・last_shown_at を更新しない（間隔をあけずに再表示
    しても記憶効果がないため、成果として数えない）。埋め草同士のローテーション
    のためだけに last_filler_at を進める。
    """
    conn.execute("UPDATE words SET last_filler_at = ? WHERE id = ?", (to_iso(now), word_id))
    conn.commit()


def record_lapse(conn: sqlite3.Connection, word_id: int, strength_days: float) -> None:
    """想起失敗（表示中の単語の内容をユーザーが確認した）を記録する。"""
    conn.execute(
        "UPDATE words SET strength_days = ?, lapse_count = lapse_count + 1 WHERE id = ?",
        (strength_days, word_id),
    )
    conn.commit()


def get_setting(conn: sqlite3.Connection, key: str, default: str | None = None) -> str | None:
    row = conn.execute("SELECT value FROM settings WHERE key = ?", (key,)).fetchone()
    return row["value"] if row else default


def set_setting(conn: sqlite3.Connection, key: str, value: str) -> None:
    conn.execute(
        "INSERT INTO settings (key, value) VALUES (?, ?) "
        "ON CONFLICT(key) DO UPDATE SET value = excluded.value",
        (key, value),
    )
    conn.commit()

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
    last_filler_at TEXT,
    opportunity_count INTEGER NOT NULL DEFAULT 0,
    last_opportunity_at TEXT
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
    last_filler_at: datetime | None
    opportunity_count: int = 0
    last_opportunity_at: datetime | None = None


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
    _migrate_words_schema(conn)
    conn.commit()
    return conn


def _column_names(conn: sqlite3.Connection, table: str) -> set[str]:
    return {row["name"] for row in conn.execute(f"PRAGMA table_info({table})")}


def _migrate_words_schema(conn: sqlite3.Connection) -> None:
    columns = _column_names(conn, "words")
    added_count = "opportunity_count" not in columns
    added_last = "last_opportunity_at" not in columns

    if added_count:
        conn.execute(
            "ALTER TABLE words ADD COLUMN opportunity_count INTEGER NOT NULL DEFAULT 0"
        )
    if added_last:
        conn.execute("ALTER TABLE words ADD COLUMN last_opportunity_at TEXT")

    if added_count and "show_count" in columns:
        conn.execute("UPDATE words SET opportunity_count = show_count")
    if added_last and "last_shown_at" in columns:
        conn.execute("UPDATE words SET last_opportunity_at = last_shown_at")


def _row_to_word(row: sqlite3.Row) -> Word:
    return Word(
        id=row["id"],
        text=row["text"],
        note=row["note"],
        added_at=from_iso(row["added_at"]),
        learned=bool(row["learned"]),
        learned_at=from_iso(row["learned_at"]),
        last_filler_at=from_iso(row["last_filler_at"]),
        opportunity_count=row["opportunity_count"],
        last_opportunity_at=from_iso(row["last_opportunity_at"]),
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

    このフラグは表示するかどうかだけを決める。想起機会の履歴は、
    チェックを外しても破棄しない（学び直しでも経緯を保つ）。
    """
    conn.execute(
        "UPDATE words SET learned = ?, learned_at = ? WHERE id = ?",
        (1 if learned else 0, to_iso(now or utcnow()) if learned else None, word_id),
    )
    conn.commit()


def record_opportunity(conn: sqlite3.Connection, word_id: int, now: datetime) -> None:
    conn.execute(
        """
        UPDATE words
           SET opportunity_count = opportunity_count + 1,
               last_opportunity_at = ?
         WHERE id = ?
        """,
        (to_iso(now), word_id),
    )
    conn.commit()


def record_filler(conn: sqlite3.Connection, word_id: int, now: datetime) -> None:
    """画面を埋めるためだけの表示を記録する。

    正式候補がないときもウィジェットを空にしないために出す表示であり、
    想起機会の履歴は進めない。同じ単語が居座らないようにするための
    last_filler_at だけを更新する。
    """
    conn.execute("UPDATE words SET last_filler_at = ? WHERE id = ?", (to_iso(now), word_id))
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

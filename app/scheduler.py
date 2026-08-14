"""想起機会の時刻判定と提供バランスを扱う純粋な選出ロジック。"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta
from enum import Enum

from app.db import Word


OPPORTUNITY_INTERVALS = (
    timedelta(0),
    timedelta(hours=2),
    timedelta(hours=4),
    timedelta(hours=8),
    timedelta(days=1),
    timedelta(days=3),
)
MAX_CONSECUTIVE_NEW = 2
TICK_SECONDS = 300


class SelectionKind(Enum):
    OPPORTUNITY = "opportunity"
    FILLER = "filler"


@dataclass
class Selection:
    word: Word
    kind: SelectionKind


def opportunity_interval(opportunity_count: int) -> timedelta:
    """正式な想起機会の回数に対応する最小間隔を返す。"""
    index = min(max(opportunity_count, 0), len(OPPORTUNITY_INTERVALS) - 1)
    return OPPORTUNITY_INTERVALS[index]


def next_eligible_at(word: Word) -> datetime:
    """次の正式な想起機会を提供できる最も早い時刻を返す。"""
    if word.opportunity_count == 0 or word.last_opportunity_at is None:
        return word.added_at
    bonus_steps = 1 if word.manual_next_bonus_pending else 0
    return word.last_opportunity_at + opportunity_interval(
        word.opportunity_count + bonus_steps
    )


def select(
    words: list[Word],
    now: datetime,
    previous_id: int | None = None,
    consecutive_new: int = 0,
) -> Selection | None:
    """次の表示を選ぶ。正式候補がなければフィラーを返す。"""
    if not words:
        return None

    new_words = [word for word in words if word.opportunity_count == 0]
    due_words = [
        word
        for word in words
        if word.opportunity_count > 0 and next_eligible_at(word) <= now
    ]

    if new_words and due_words and consecutive_new >= MAX_CONSECUTIVE_NEW:
        formal = due_words
    else:
        formal = new_words + due_words

    if previous_id is not None and len(words) > 1:
        formal_without_previous = [word for word in formal if word.id != previous_id]
        if formal and not formal_without_previous:
            return _select_filler(words, previous_id)
        formal = formal_without_previous

    if formal:
        word = min(formal, key=lambda item: (next_eligible_at(item), item.id))
        return Selection(word=word, kind=SelectionKind.OPPORTUNITY)

    return _select_filler(words, previous_id)


def _select_filler(words: list[Word], previous_id: int | None) -> Selection:
    pool = words
    if previous_id is not None and len(words) > 1:
        without_previous = [word for word in words if word.id != previous_id]
        if without_previous:
            pool = without_previous

    word = min(pool, key=lambda item: (_filler_key(item), item.id))
    return Selection(word=word, kind=SelectionKind.FILLER)


def _filler_key(word: Word) -> float:
    if word.last_filler_at is None:
        return float("-inf")
    return word.last_filler_at.timestamp()

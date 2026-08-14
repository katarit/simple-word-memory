"""想起機会スケジューラの検証。"""

from datetime import datetime, timedelta, timezone

import pytest

from app import scheduler
from app.db import Word

NOW = datetime(2026, 8, 4, 12, 0, tzinfo=timezone.utc)


def make_word(
    word_id: int,
    *,
    opportunity_count: int = 0,
    last_opportunity: datetime | None = None,
    last_filler: datetime | None = None,
    added_at: datetime | None = None,
    text: str | None = None,
    manual_next_bonus_pending: bool = False,
) -> Word:
    return Word(
        id=word_id,
        text=text or f"word{word_id}",
        note="",
        added_at=added_at or NOW - timedelta(days=30),
        learned=False,
        learned_at=None,
        last_filler_at=last_filler,
        opportunity_count=opportunity_count,
        last_opportunity_at=last_opportunity,
        manual_next_bonus_pending=manual_next_bonus_pending,
    )


@pytest.mark.parametrize(
    ("count", "expected"),
    [
        (0, timedelta(0)),
        (1, timedelta(hours=2)),
        (2, timedelta(hours=4)),
        (3, timedelta(hours=8)),
        (4, timedelta(days=1)),
        (5, timedelta(days=3)),
        (50, timedelta(days=3)),
    ],
)
def test_opportunity_interval_expands_then_stops(count, expected):
    assert scheduler.opportunity_interval(count) == expected


def test_never_presented_word_is_immediately_eligible():
    word = make_word(1, added_at=NOW)

    assert scheduler.next_eligible_at(word) == NOW


def test_presented_word_waits_for_its_minimum_interval():
    word = make_word(
        1,
        opportunity_count=2,
        last_opportunity=NOW - timedelta(hours=3),
    )

    assert scheduler.next_eligible_at(word) == NOW + timedelta(hours=1)
    selection = scheduler.select([word], NOW)
    assert selection is not None
    assert selection.kind is scheduler.SelectionKind.FILLER


def test_pending_manual_next_bonus_extends_only_the_next_interval_one_step():
    word = make_word(
        1,
        opportunity_count=2,
        last_opportunity=NOW,
        manual_next_bonus_pending=True,
    )

    assert scheduler.next_eligible_at(word) == NOW + timedelta(hours=8)


def test_pending_manual_next_bonus_stops_at_three_day_cap():
    word = make_word(
        1,
        opportunity_count=50,
        last_opportunity=NOW,
        manual_next_bonus_pending=True,
    )

    assert scheduler.next_eligible_at(word) == NOW + timedelta(days=3)


def test_empty_pool_returns_none():
    assert scheduler.select([], NOW) is None


def test_older_new_word_wins_by_its_added_time():
    older_new = make_word(1, added_at=NOW - timedelta(days=2))
    newer_new = make_word(2, added_at=NOW - timedelta(days=1))

    selection = scheduler.select([newer_new, older_new], NOW)

    assert selection is not None
    assert selection.word.id == older_new.id
    assert selection.kind is scheduler.SelectionKind.OPPORTUNITY


def test_third_consecutive_new_yields_to_due_past_word():
    new_a = make_word(10, added_at=NOW - timedelta(hours=2))
    new_b = make_word(11, added_at=NOW - timedelta(hours=1))
    overdue = make_word(
        1,
        opportunity_count=2,
        last_opportunity=NOW - timedelta(days=2),
    )

    selection = scheduler.select(
        [new_a, new_b, overdue],
        NOW,
        consecutive_new=2,
    )

    assert selection is not None
    assert selection.word.id == overdue.id
    assert selection.kind is scheduler.SelectionKind.OPPORTUNITY


def test_most_overdue_past_word_wins_within_due_pool():
    older_due = make_word(
        1,
        opportunity_count=2,
        last_opportunity=NOW - timedelta(days=3),
    )
    newer_due = make_word(
        2,
        opportunity_count=2,
        last_opportunity=NOW - timedelta(days=1),
    )

    selection = scheduler.select([newer_due, older_due], NOW)

    assert selection is not None
    assert selection.word.id == older_due.id


def test_new_and_due_words_share_one_eligibility_order_when_new_is_older():
    new_word = make_word(1, added_at=NOW - timedelta(days=3))
    due_word = make_word(
        2,
        opportunity_count=1,
        last_opportunity=NOW - timedelta(hours=3),
    )

    selection = scheduler.select([due_word, new_word], NOW)

    assert selection is not None
    assert selection.word.id == new_word.id


def test_new_and_due_words_share_one_eligibility_order_when_due_is_older():
    new_word = make_word(1, added_at=NOW - timedelta(hours=1))
    due_word = make_word(
        2,
        opportunity_count=1,
        last_opportunity=NOW - timedelta(hours=4),
    )

    selection = scheduler.select([new_word, due_word], NOW)

    assert selection is not None
    assert selection.word.id == due_word.id


def test_current_due_word_yields_to_other_word_as_filler():
    current_due = make_word(
        1,
        opportunity_count=1,
        last_opportunity=NOW - timedelta(days=1),
    )
    other = make_word(
        2,
        opportunity_count=4,
        last_opportunity=NOW - timedelta(hours=1),
    )

    selection = scheduler.select([current_due, other], NOW, previous_id=1)

    assert selection is not None
    assert selection.word.id == other.id
    assert selection.kind is scheduler.SelectionKind.FILLER


def test_filler_uses_oldest_filler_history_and_avoids_previous_word():
    previous = make_word(
        1,
        opportunity_count=1,
        last_opportunity=NOW - timedelta(hours=1),
        last_filler=NOW - timedelta(hours=3),
    )
    older_filler = make_word(
        2,
        opportunity_count=1,
        last_opportunity=NOW - timedelta(hours=1),
        last_filler=NOW - timedelta(hours=2),
    )
    newer_filler = make_word(
        3,
        opportunity_count=1,
        last_opportunity=NOW - timedelta(hours=1),
        last_filler=NOW - timedelta(minutes=5),
    )

    selection = scheduler.select(
        [previous, newer_filler, older_filler],
        NOW,
        previous_id=previous.id,
    )

    assert selection is not None
    assert selection.word.id == older_filler.id
    assert selection.kind is scheduler.SelectionKind.FILLER


def test_filler_prefers_word_without_filler_history():
    previous = make_word(
        1,
        opportunity_count=1,
        last_opportunity=NOW - timedelta(hours=1),
    )
    never_filler = make_word(
        2,
        opportunity_count=1,
        last_opportunity=NOW - timedelta(hours=1),
    )
    recorded_filler = make_word(
        3,
        opportunity_count=1,
        last_opportunity=NOW - timedelta(hours=1),
        last_filler=NOW - timedelta(days=1),
    )

    selection = scheduler.select(
        [previous, recorded_filler, never_filler],
        NOW,
        previous_id=previous.id,
    )

    assert selection is not None
    assert selection.word.id == never_filler.id
    assert selection.kind is scheduler.SelectionKind.FILLER


@pytest.mark.parametrize("word_count", [1, 10, 100, 300, 500])
def test_large_due_pool_always_returns_one_selection(word_count):
    words = [
        make_word(
            word_id,
            opportunity_count=5,
            last_opportunity=NOW - timedelta(days=10),
        )
        for word_id in range(1, word_count + 1)
    ]

    selection = scheduler.select(words, NOW)

    assert selection is not None
    assert selection.kind is scheduler.SelectionKind.OPPORTUNITY
    assert 1 <= selection.word.id <= word_count


def test_large_new_batch_does_not_monopolize_available_past_words():
    words = [
        make_word(word_id, added_at=NOW - timedelta(hours=2))
        for word_id in range(100, 200)
    ]
    words.extend(
        make_word(
            word_id,
            opportunity_count=1,
            last_opportunity=NOW - timedelta(hours=3),
        )
        for word_id in range(1, 11)
    )
    words.append(
        make_word(
            50,
            opportunity_count=4,
            last_opportunity=NOW,
        )
    )

    now = NOW
    previous_id = None
    consecutive_new = 0

    for _ in range(30):
        due_past = [
            word
            for word in words
            if word.opportunity_count > 0
            and scheduler.next_eligible_at(word) <= now
        ]
        selection = scheduler.select(
            words,
            now,
            previous_id=previous_id,
            consecutive_new=consecutive_new,
        )
        assert selection is not None

        was_new = selection.word.opportunity_count == 0
        if due_past and consecutive_new >= scheduler.MAX_CONSECUTIVE_NEW:
            assert selection.kind is scheduler.SelectionKind.OPPORTUNITY
            assert selection.word.id in {word.id for word in due_past}

        if selection.kind is scheduler.SelectionKind.OPPORTUNITY:
            selection.word.opportunity_count += 1
            selection.word.last_opportunity_at = now
            consecutive_new = consecutive_new + 1 if was_new else 0
        else:
            selection.word.last_filler_at = now

        previous_id = selection.word.id
        now += timedelta(seconds=scheduler.TICK_SECONDS)

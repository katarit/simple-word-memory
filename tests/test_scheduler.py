"""出題スケジューリングモデルの検証。"""

from datetime import datetime, timedelta, timezone

import pytest

from app import scheduler
from app.db import Word

NOW = datetime(2026, 7, 31, 12, 0, tzinfo=timezone.utc)


def make_word(word_id: int, *, strength=None, last_shown=None, last_filler=None, text=None) -> Word:
    return Word(
        id=word_id,
        text=text or f"word{word_id}",
        note="",
        added_at=NOW - timedelta(days=30),
        learned=False,
        learned_at=None,
        show_count=0 if strength is None else 1,
        strength_days=strength,
        last_shown_at=last_shown,
        last_filler_at=last_filler,
        lapse_count=0,
    )


# --- retention ---------------------------------------------------------------


def test_never_shown_word_has_zero_retention():
    """未表示の語は記憶が形成されていないため最優先。"""
    assert scheduler.retention(make_word(1), NOW) == 0.0


def test_retention_decays_with_elapsed_time():
    word = make_word(1, strength=1.0, last_shown=NOW - timedelta(days=1))
    assert scheduler.retention(word, NOW) == pytest.approx(0.3679, abs=1e-3)


def test_stronger_word_retains_more_at_same_elapsed_time():
    weak = make_word(1, strength=1.0, last_shown=NOW - timedelta(days=1))
    strong = make_word(2, strength=14.0, last_shown=NOW - timedelta(days=1))
    assert scheduler.retention(strong, NOW) > scheduler.retention(weak, NOW)


# --- select ------------------------------------------------------------------


def test_returns_none_when_no_words():
    assert scheduler.select([], NOW) is None


def test_new_word_is_selected_first_and_credited():
    fresh = make_word(1)
    due = make_word(2, strength=1.0, last_shown=NOW - timedelta(days=1))
    selection = scheduler.select([due, fresh], NOW)
    assert selection.word.id == fresh.id
    assert selection.credited is True


def test_most_forgotten_due_word_wins():
    mild = make_word(1, strength=1.0, last_shown=NOW - timedelta(hours=3))
    severe = make_word(2, strength=1.0, last_shown=NOW - timedelta(days=5))
    selection = scheduler.select([mild, severe], NOW)
    assert selection.word.id == severe.id


def test_recently_shown_words_are_not_credited():
    """絶対閾値のゲート: まだ覚えている語ばかりなら埋め草に落ちる。"""
    just_shown = [
        make_word(1, strength=1.0, last_shown=NOW - timedelta(minutes=5)),
        make_word(2, strength=1.0, last_shown=NOW - timedelta(minutes=10)),
    ]
    selection = scheduler.select(just_shown, NOW)
    assert selection.credited is False


def test_filler_rotates_by_last_filler_at():
    """埋め草は同じ語が居座らないよう last_filler_at の古い順に回る。"""
    recent_filler = make_word(
        1, strength=1.0, last_shown=NOW - timedelta(minutes=5), last_filler=NOW - timedelta(minutes=5)
    )
    old_filler = make_word(
        2, strength=1.0, last_shown=NOW - timedelta(minutes=5), last_filler=NOW - timedelta(hours=2)
    )
    selection = scheduler.select([recent_filler, old_filler], NOW)
    assert selection.word.id == old_filler.id
    assert selection.credited is False


def test_previous_word_is_avoided_when_alternatives_exist():
    a = make_word(1, strength=1.0, last_shown=NOW - timedelta(days=5))
    b = make_word(2, strength=1.0, last_shown=NOW - timedelta(days=4))
    selection = scheduler.select([a, b], NOW, previous_id=a.id)
    assert selection.word.id == b.id


def test_single_word_repeats_even_if_previous():
    only = make_word(1, strength=1.0, last_shown=NOW - timedelta(days=5))
    selection = scheduler.select([only], NOW, previous_id=only.id)
    assert selection.word.id == only.id


# --- strength update ---------------------------------------------------------


def test_first_show_sets_initial_strength():
    assert scheduler.next_strength(make_word(1), 0.0) == scheduler.S_FIRST_DAYS


def test_normal_review_grows_faster_than_relearn():
    word = make_word(1, strength=2.0, last_shown=NOW - timedelta(days=1))
    normal = scheduler.next_strength(word, current_retention=0.85)
    relearn = scheduler.next_strength(word, current_retention=0.05)
    assert normal == pytest.approx(2.0 * scheduler.GROW_NORMAL)
    assert relearn == pytest.approx(2.0 * scheduler.GROW_RELEARN)
    assert normal > relearn


def test_strength_is_capped():
    word = make_word(1, strength=13.0, last_shown=NOW - timedelta(days=1))
    assert scheduler.next_strength(word, 0.85) == scheduler.S_MAX_DAYS


def test_lapse_halves_strength_with_floor():
    word = make_word(1, strength=8.0, last_shown=NOW - timedelta(days=1))
    assert scheduler.lapsed_strength(word) == pytest.approx(4.0)
    weak = make_word(2, strength=0.2, last_shown=NOW - timedelta(days=1))
    assert scheduler.lapsed_strength(weak) == scheduler.LAPSE_MIN_DAYS


def test_new_word_shows_several_times_on_first_day():
    """登録当日は高頻度で出る、という設計意図の回帰テスト。"""
    word = make_word(1, text="fresh")
    now = NOW
    strength = None
    shows = []
    for _ in range(400):  # 5分刻みで約33時間ぶん回す
        current = Word(**{**word.__dict__, "strength_days": strength, "last_shown_at": shows[-1] if shows else None})
        selection = scheduler.select([current], now)
        if selection.credited:
            strength = scheduler.next_strength(current, selection.retention)
            shows.append(now)
        now += timedelta(seconds=scheduler.TICK_SECONDS)

    first_day = [t for t in shows if t < NOW + timedelta(days=1)]
    assert 3 <= len(first_day) <= 5

"""出題スケジューリング。

UI にも sqlite にも依存しない純粋なロジック。テストしやすさのため、
入力は Word のリストと現在時刻だけを受け取る。

モデルの要点:
- 推定保持率 R = exp(-t / S)。t は最終表示からの経過日数、S は記憶強度（日）。
- R <= TARGET_R の語だけが出題対象（絶対閾値のゲート）。プールの大小に
  よらず「まだ覚えている語を無駄に再表示しない」を成立させるための要。
- 対象がなければ、画面を空にしないために別の単語を出すが、これは復習として
  数えない（直前に見た単語をもう一度見ても記憶には効かないため）。
"""

from __future__ import annotations

import math
from dataclasses import dataclass
from datetime import datetime

from app.db import Word

# --- 定数 ---------------------------------------------------------------------
# 間隔効果・望ましい困難・指数的忘却といった一般的な原理にもとづく初期値であり、
# SM-2 や FSRS など特定のアルゴリズムから導出したものではない。実運用しながら
# 調整できるよう1か所に集約している（詳細は README を参照）。
TARGET_R = 0.90
"""この保持率を下回った語を出題対象とする。"""

S_FIRST_DAYS = 1.0
"""初回表示後に与える強度。次回は約 2.5 時間後になる。"""

S_MAX_DAYS = 14.0
"""受動的な露出だけで到達できる強度の上限。想起確認がない以上これ以上は主張しない。"""

GROW_NORMAL = 1.6
"""通常復習時の成長率。想起を確認できないため SM-2 系の約 2.5 より低く置く。"""

GROW_RELEARN = 1.2
"""ほぼ忘却状態からの復習時の成長率。"""

RELEARN_R = 0.30
"""GROW_NORMAL と GROW_RELEARN を切り替える保持率。"""

LAPSE_FACTOR = 0.5
LAPSE_MIN_DAYS = 0.5
"""想起失敗時の減衰率と、減衰後の下限。"""

TICK_SECONDS = 300
"""ウィジェットの切り替え間隔（5分）。"""

_SECONDS_PER_DAY = 86400.0


@dataclass
class Selection:
    """1ティック分の選出結果。"""

    word: Word
    credited: bool
    """True なら復習1回として数える表示（強度を更新する）。
    False なら画面を埋めるためだけの表示（記録を更新しない）。"""

    retention: float


def retention(word: Word, now: datetime) -> float:
    """推定保持率 R を返す。

    未表示の語は記憶がまだ形成されていないため 0（＝最優先）とする。
    """
    if word.last_shown_at is None or word.strength_days is None:
        return 0.0
    elapsed_days = (now - word.last_shown_at).total_seconds() / _SECONDS_PER_DAY
    if elapsed_days <= 0:
        return 1.0
    return math.exp(-elapsed_days / word.strength_days)


def select(words: list[Word], now: datetime, previous_id: int | None = None) -> Selection | None:
    """次に表示する単語を選ぶ。未学習の語だけを渡すこと。

    previous_id は直前のティックで表示した語。他に候補があれば連続表示を避ける。
    """
    if not words:
        return None

    scored = [(retention(w, now), w) for w in words]
    due = [item for item in scored if item[0] <= TARGET_R]

    pool = due if due else scored
    if previous_id is not None and len(pool) > 1:
        without_previous = [item for item in pool if item[1].id != previous_id]
        if without_previous:
            pool = without_previous

    if due:
        # 最も忘れている語を優先する。
        best = min(pool, key=lambda item: (item[0], item[1].id))
        return Selection(word=best[1], credited=True, retention=best[0])

    # 出題対象がない＝全語が最近表示済み。画面を空にしないための表示なので、
    # 最後にこの用途で出してから最も長い語を選ぶ（同じ語が居座らないように）。
    best = min(pool, key=lambda item: (_filler_key(item[1]), item[0], item[1].id))
    return Selection(word=best[1], credited=False, retention=best[0])


def _filler_key(word: Word) -> float:
    if word.last_filler_at is None:
        return float("-inf")
    return word.last_filler_at.timestamp()


def next_strength(word: Word, current_retention: float) -> float:
    """クレジットありの表示を行ったあとの強度を返す。

    表示されなかった期間の長さを根拠に強度を引き上げることはしない
    （PC を閉じていただけの可能性があり、保持の証拠にならないため）。
    """
    if word.strength_days is None:
        return S_FIRST_DAYS
    growth = GROW_NORMAL if current_retention >= RELEARN_R else GROW_RELEARN
    return min(word.strength_days * growth, S_MAX_DAYS)


def lapsed_strength(word: Word) -> float:
    """想起失敗時の強度を返す。"""
    current = word.strength_days if word.strength_days is not None else S_FIRST_DAYS
    return max(LAPSE_MIN_DAYS, current * LAPSE_FACTOR)

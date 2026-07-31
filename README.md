# simple-word-memory

A small always-on-top desktop widget for Windows that shows one word you are trying to learn, and rotates it every five minutes based on a forgetting-curve model.

Windows のデスクトップに常時表示される小さなウィジェットで、覚え中の単語を1語ずつ表示し、忘却曲線にもとづいて5分ごとに切り替えます。

---

## English

### Why this exists

Reviewing vocabulary requires you to decide to review. This tool removes that decision: a small widget sits on your desktop and keeps putting a word in front of you while you work on something else.

It deliberately shows the **word only** — no meaning, no part of speech. The goal is not to test recall, but to increase the number of times you meet the word. Meanings live in the management panel, available whenever you want to check them.

### Features

- An always-on-top widget (240×72) showing a single word, rotating every 5 minutes
- Click the widget to open the management panel: **Add / Not learned / Learned**
- Each word carries one free-form "content" field (meaning, example sentence, notes — whatever helps you). It is intentionally not split into part of speech, reading, and so on, so that you can write whatever actually helps you remember
- Click a word in a list to edit it. The date it was added is recorded automatically and shown read-only
- Checking a word marks it as learned and removes it from the rotation. **Unchecking never discards its learning history**
- Light and dark themes, switchable from the button in the panel header. The first launch follows the OS setting; after that your choice is remembered
- **Right-click the widget** to open the panel or quit. The widget has no title bar, so this is how you exit the application

### How words are chosen

Each word carries a continuous *memory strength*. From the time elapsed since it was last shown, the estimated retention is

```
R = exp(-elapsed_days / strength_days)
```

Only words whose `R` has fallen below **0.90** become candidates, and among those the most forgotten one is shown. Each time a word is shown with credit, its strength grows, so the interval widens: roughly 2.5 h → 4 h → 6.5 h → 10 h → 16 h → 26 h → 35 h.

- A newly added word has never been shown, so its retention is treated as 0 and it appears immediately. **The day you add a word is the day it appears most often.**
- When no word is due, a *filler* word is shown so the widget is never blank — but strength is **not** updated. Showing a word again minutes after you saw it produces no spacing benefit, so it earns no credit.
- If you open the panel and look at the content of the word currently on the widget, that is treated as "I could not recall it": strength is halved and the word returns sooner.
- Because this is passive exposure rather than verified recall, strength is capped at 14 days. The tool does not claim retention it cannot observe.

The constants are informed initial values based on well-established principles (the spacing effect, desirable difficulty, exponential forgetting). They are not derived from a specific published algorithm such as SM-2 or FSRS, and are collected in one place in `app/scheduler.py` so they can be tuned in real use.

### Requirements

Python 3.11 or later, on Windows.

### Setup

```
python -m venv .venv
.venv\Scripts\python -m pip install -r requirements.txt
```

### Running

Double-click `start-words-reminder.cmd`, or run:

```
.venv\Scripts\pythonw main.py
```

The launcher creates a `.venv` and installs dependencies on first run if one does not exist yet.

Drag the widget to move it; its position is restored on the next launch. Left-click opens the management panel; **right-click opens a menu with "open panel" and "quit"**. Data is stored locally in `data/words.db` (SQLite). Nothing is sent anywhere — the application makes no network requests.

### Tests

```
.venv\Scripts\python -m pytest
```

### Project layout

| Path | Role |
|---|---|
| `main.py` | Startup and wiring; drives the 5-minute rotation tick |
| `app/db.py` | SQLite persistence (words, settings) |
| `app/scheduler.py` | Selection logic and tuning constants; depends on neither UI nor DB |
| `app/widget_window.py` | The always-on-top word widget |
| `app/panel_window.py` | Management panel (add / lists / edit) |
| `app/theme.py` | Color and dimension tokens, and Qt stylesheets |
| `tests/` | Tests for persistence and selection logic (pytest) |

### Known limits and possible next steps

- This is an aid for increasing exposure, not a replacement for active recall practice
- The scheduling constants are initial values and are expected to be tuned through real use
- Words marked as learned are never shown again; periodic re-checking for long-term retention is a candidate for future work
- No standalone executable or Windows startup registration yet

---

## 日本語

### 何のためのツールか

単語の復習には「復習しよう」と決める手間があります。このツールはその決断を不要にします。小さなウィジェットがデスクトップに居座り、別の作業をしている間も単語を目の前に出し続けます。

表示するのは**単語だけ**です。意味も品詞も出しません。狙いは想起のテストではなく、単語に出会う回数を増やすことです。意味は管理パネルにあり、確認したいときにいつでも見られます。

### 機能

- 常に最前面の小さなウィジェット（240×72）に単語を1語だけ表示し、5分ごとに切り替える
- ウィジェットのクリックで管理パネルを開く（**登録／未学習／学習済み**）
- 単語には自由記述の「内容」を1つだけ持たせる（意味・例文・メモなど何でも）。品詞や読みに分割しないのは、覚えるために本当に役立つことを自由に書けるようにするため
- リストの単語をクリックすると編集できる。登録日は自動で記録され、読み取り専用で表示される
- チェックすると学習済みになり表示対象から外れる。**チェックを外しても学習の経緯は破棄されない**
- ライト／ダークはパネルのヘッダーのボタンで切り替えられる。初回起動時は OS の設定に従い、以降は選んだ状態を記憶する
- **ウィジェットを右クリック**すると、パネルを開く／終了のメニューが出る。ウィジェットにはタイトルバーがないため、これが終了の導線になる

### 出題の仕組み

単語ごとに連続値の**記憶の強さ**を持ちます。最終表示からの経過時間から、推定保持率を次の式で求めます。

```
R = exp(-経過日数 / 強さ(日))
```

`R` が **0.90** を下回った単語だけが出題対象になり、その中で最も忘れている単語を表示します。クレジットありで表示されるたびに強さが伸びるため、間隔は約 2.5時間 → 4時間 → 6.5時間 → 10時間 → 16時間 → 26時間 → 35時間 と広がります。

- 登録直後の単語は未表示のため保持率0として扱われ、すぐに出ます。**登録した当日がいちばん高頻度**です
- 出題対象がないときは画面を空にしないための**埋め草**を表示しますが、強さは更新しません。数分前に見た単語をもう一度見ても間隔効果は得られないため、成果として数えない設計です
- ウィジェットに出ている単語の内容をパネルで開いた場合、「思い出せなかった」とみなして強さを半減させ、早めに再出題します
- 想起を確認できない受動的な露出であるため、強さの上限は14日に制限しています。観測できない定着を主張しない設計です

定数は、間隔効果・望ましい困難・指数的忘却といった確立した原理にもとづく初期値です。SM-2 や FSRS などの特定のアルゴリズムから導出したものではありません。実運用で調整できるよう `app/scheduler.py` の1か所にまとめています。

### 動作要件

Windows 上の Python 3.11 以降。

### セットアップ

```
python -m venv .venv
.venv\Scripts\python -m pip install -r requirements.txt
```

### 起動

`start-words-reminder.cmd` をダブルクリックするか、次を実行します。

```
.venv\Scripts\pythonw main.py
```

`.venv` がまだない場合、起動スクリプトが作成して依存関係をインストールします。

ウィジェットはドラッグで移動でき、位置は次回起動時に復元されます。左クリックで管理パネルが開き、**右クリックで「管理パネルを開く／終了」のメニュー**が出ます。データはローカルの `data/words.db`（SQLite）に保存されます。外部への送信は一切なく、ネットワーク通信は行いません。

### テスト

```
.venv\Scripts\python -m pytest
```

### 構成

上の English セクションの表を参照してください。

### 既知の制約・今後の候補

- 能動的な想起練習の代替ではなく、接触回数を増やすための補助です
- 出題ロジックの定数は初期値であり、実運用しながらの調整を前提としています
- 学習済みにした単語は再表示されません。長期保持のための定期的な再確認は今後の検討候補です
- 単体実行ファイル化と Windows 自動起動への登録は未対応です

---

## License

MIT License. Copyright (c) 2026 katarit. See [LICENSE](LICENSE).

MIT ライセンスで公開しています。詳細は [LICENSE](LICENSE) を参照してください。

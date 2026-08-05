# simple-word-memory

A small always-on-top desktop widget for Windows that shows one word you are trying to learn and rotates it every five minutes to create spaced recall opportunities.

Windows のデスクトップに常時表示される小さなウィジェットで、覚え中の単語を1語ずつ表示し、間隔を空けた想起機会を作りながら5分ごとに切り替えます。

---

## English

### Why this exists

Add a word you want to remember, and that is the whole workload. From there a small widget on your desktop shows one word at a time, spacing formal recall opportunities while you get on with something else.

It shows the word only. Its job is to raise the number of times you meet a word; the meaning is in the management panel whenever you want it.

A word carries one free-form note. Because fields like part of speech or pronunciation belong to a particular language's grammar, keeping it to one subject and one note lets the same tool follow you across languages — and covers anything you want to keep resurfacing, not only words.

### Features

- An always-on-top widget (240×72) showing a single word, rotating every 5 minutes
- Click the widget to open the management panel: **Add / Not learned / Learned**
- Each word carries one free-form "content" field (meaning, example sentence, notes — whatever helps you). It is intentionally not split into part of speech, reading, and so on, so that you can write whatever actually helps you remember
- Click a word in a list to edit it. The date it was added is recorded automatically and shown read-only
- Checking a word marks it as learned and removes it from the rotation. **Unchecking never discards its learning history**
- Light and dark themes, switchable from the button in the panel header. The first launch follows the OS setting; after that your choice is remembered
- **Right-click the widget** to open the panel or quit. The widget has no title bar, so this is how you exit the application

### How words are chosen

The app does **not** estimate memory strength, retention, recall success, or failure. A word appearing on screen means only that the app provided an opportunity to recall it; it does not mean that a successful review occurred.

Formal recall opportunities use these minimum intervals:

**immediately → 2 hours → 4 hours → 8 hours → 1 day → 3 days (then stays at 3 days)**

- “Immediately” means eligible at the next regular five-minute selection. Adding or editing data never creates an extra scheduling tick.
- New and previously presented words share the same eligibility timeline. The word whose eligible time is oldest is normally chosen.
- If two new words have been presented consecutively and an eligible older word exists, the older word is inserted next. This is a bias guard, not a fixed new/old ratio.
- The widget still rotates about every five minutes. When no word is formally eligible, it rotates a filler word instead. A filler keeps the display useful but does **not** advance the formal opportunity history.
- If alternatives exist, the currently displayed word is not immediately counted as another formal opportunity.
- Opening the management panel, viewing details, or editing a word is scheduling-neutral. These actions are not treated as evidence that the word was remembered or forgotten.
- Words marked as learned are excluded from rotation. Unchecking them restores them with their previous opportunity history intact.

The shape of the schedule—spaced rather than massed presentation, initially expanding intervals, and no unlimited expansion—is informed by research on distributed practice and retrieval spacing:

- [Cepeda et al. (2006), distributed-practice meta-analysis](https://pubmed.ncbi.nlm.nih.gov/16719566/)
- [Cepeda et al. (2008), spacing and retention horizon](https://pubmed.ncbi.nlm.nih.gov/19076480/)
- [Karpicke & Roediger (2007), expanding versus equal retrieval](https://doi.org/10.1037/0278-7393.33.4.704)
- [Bahrick et al. (1993), long-term foreign-vocabulary maintenance](https://doi.org/10.1111/j.1467-9280.1993.tb00571.x)

Those studies support the general scheduling shape, not this app's exact hour and day values. The concrete intervals are product judgments for a passive, five-minute desktop rotation that receives no correctness input.

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

Tests need one extra dependency, kept separate so that simply running the app does not install it:

```
.venv\Scripts\python -m pip install -r requirements-dev.txt
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
- The opportunity intervals are initial product judgments and are expected to be tuned through real use
- Words marked as learned are not shown unless the user unchecks them
- No standalone executable or Windows startup registration yet

---

## 日本語

### 何のためのツールか

覚えたいと思った単語を簡単に登録すると、あとは間隔を空けた想起機会として、デスクトップのウィジェットにシンプルに表示し続けます。「復習しよう」と決める手間なく、別の作業をしている間に単語に触れられます。

表示するのは単語だけです。単語に出会う回数を増やすことが役割で、意味は管理パネルでいつでも確認できます。

単語が持つのは自由記述のメモ1つだけです。品詞や発音といった項目は特定言語の文法に属するため、「対象1つ＋メモ1つ」に留めることで、学習する言語が変わっても同じ形のまま使えます。単語に限らず、覚えておきたいこと全般にも応用できます。

### 機能

- 常に最前面の小さなウィジェット（240×72）に単語を1語だけ表示し、5分ごとに切り替える
- ウィジェットのクリックで管理パネルを開く（**登録／未学習／学習済み**）
- 単語には自由記述の「内容」を1つだけ持たせる（意味・例文・メモなど何でも）。品詞や読みに分割しないのは、覚えるために本当に役立つことを自由に書けるようにするため
- リストの単語をクリックすると編集できる。登録日は自動で記録され、読み取り専用で表示される
- チェックすると学習済みになり表示対象から外れる。**チェックを外しても学習の経緯は破棄されない**
- ライト／ダークはパネルのヘッダーのボタンで切り替えられる。初回起動時は OS の設定に従い、以降は選んだ状態を記憶する
- **ウィジェットを右クリック**すると、パネルを開く／終了のメニューが出る。ウィジェットにはタイトルバーがないため、これが終了の導線になる

### 出題の仕組み

このアプリは、**記憶の強さ、保持率、想起の成功・失敗を推定しません**。画面に単語が出たという事実は「思い出す機会を提供した」ことだけを表し、復習成功とはみなしません。

正式な想起機会は、次の最小間隔で提供します。

**すぐ → 2時間 → 4時間 → 8時間 → 1日 → 3日（以後3日固定）**

- 「すぐ」は次の通常の5分選出で候補になるという意味です。登録や編集操作から追加の選出は行いません
- 新規語と過去語は同じ候補時刻の基準で扱い、通常は候補時刻を最も超過した語を選びます
- 新規語が2回連続し、期限を迎えた過去語がある場合は、次に過去語を挟みます。これは偏り防止であり、固定の新規・過去比率ではありません
- ウィジェット自体は約5分ごとに切り替わります。正式候補がない場合は別の語をフィラー表示しますが、**正式な想起機会の履歴は進めません**
- 他の語がある場合、現在表示中の同じ語をすぐ次の正式機会として数えません
- 管理パネルを開く、内容を見る、編集する、といった操作はスケジューリングに影響しません。覚えていた・忘れていたという証拠には利用しません
- 学習済み語は表示対象外です。チェックを外した場合は、以前の想起機会履歴を保持したまま復帰します

集中提示を避けて間隔を空けること、初期に間隔を広げること、無制限に拡張しないことは、分散学習と検索間隔に関する次の研究を参考にしています。

- [Cepeda et al. (2006)：分散学習のメタ分析](https://pubmed.ncbi.nlm.nih.gov/16719566/)
- [Cepeda et al. (2008)：保持期間と有効な学習間隔](https://pubmed.ncbi.nlm.nih.gov/19076480/)
- [Karpicke & Roediger (2007)：拡張間隔と等間隔の検索練習](https://doi.org/10.1037/0278-7393.33.4.704)
- [Bahrick et al. (1993)：外国語語彙の長期維持](https://doi.org/10.1111/j.1467-9280.1993.tb00571.x)

これらの研究はスケジュールの形を支持する根拠であり、本アプリの具体的な時間値を直接導出したものではありません。具体値は、正誤入力を求めず約5分で表示を切り替えるデスクトップアプリに合わせた判断値です。

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

テストには追加の依存が1つ必要です。アプリを動かすだけの人に入らないよう分けてあります。

```
.venv\Scripts\python -m pip install -r requirements-dev.txt
.venv\Scripts\python -m pytest
```

### 構成

上の English セクションの表を参照してください。

### 既知の制約・今後の候補

- 能動的な想起練習の代替ではなく、接触回数を増やすための補助です
- 想起機会の間隔は初期判断値であり、実運用しながらの調整を前提としています
- 学習済みにした単語は、ユーザーがチェックを外すまで表示されません
- 単体実行ファイル化と Windows 自動起動への登録は未対応です

---

## License

MIT License. Copyright (c) 2026 katarit. See [LICENSE](LICENSE).

Third-party dependencies are distributed under their respective licenses. In particular, PySide6 (Qt for Python) is **not** covered by this repository's MIT license — it is available under LGPL v3, GPL, or a commercial Qt license. This repository distributes source code only. If you build and redistribute a standalone binary, review the Qt and PySide6 licensing terms separately.

MIT ライセンスで公開しています。詳細は [LICENSE](LICENSE) を参照してください。

依存ライブラリはそれぞれのライセンスに従います。とくに PySide6（Qt for Python）は本リポジトリの MIT ライセンスの対象**ではなく**、LGPL v3 / GPL / 商用 Qt ライセンスのいずれかで提供されています。本リポジトリはソースコードのみを配布しています。実行ファイルをビルドして再配布する場合は、Qt および PySide6 のライセンス条件を別途確認してください。

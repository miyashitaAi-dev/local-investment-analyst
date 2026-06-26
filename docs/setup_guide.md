# セットアップ手順

## 前提

- Docker Desktop（Open WebUI用）
- Ollama（モデル実行エンジン・ホストOSに直接インストール推奨）
- Tavily APIキー（[tavily.com](https://tavily.com)で取得）

## 構成図

```
[Open WebUI コンテナ(Docker)] ⇄ [Ollama(ホストOSにネイティブインストール)] ⇄ Qwen3-14B
        ↓
[Tavily Web Search（Native Tool Calling）]
```

OllamaはDockerの中に入れず、ホストOSに直接インストールするとGPU認識・モデル管理が楽になります。

## 手順

### 1. Open WebUIコンテナを起動

```bash
docker run -d -p 3000:8080 --add-host=host.docker.internal:host-gateway \
  -v open-webui:/app/backend/data --name open-webui \
  ghcr.io/open-webui/open-webui:main
```

ブラウザで `http://localhost:3000` を開く。

### 2. Ollamaをインストールしてモデルを取得

[ollama.com/download](https://ollama.com/download) からインストール後：

```bash
ollama pull qwen3:14b
```

14Bモデルは量子化次第でVRAM/RAM 10〜12GB程度が目安。

### 3. Open WebUIからOllamaに接続

`Admin Panel > Settings > Connections` で、Ollama接続先URLを設定：

- Open WebUIがDocker内、Ollamaがホスト側の場合 → `http://host.docker.internal:11434`

### 4. Function Callingを「Native」に設定（重要）

`Admin Panel > Settings > Models` の設定アイコンから、**Function Calling = Native** に変更。

Default Modeのままだと、モデルが自律的にツールを呼べず、旧来のRAG注入の挙動に留まる。

### 5. TavilyをWeb Searchプロバイダとして設定

`Admin Panel > Settings > Web Search` を開き：
- Web Search：ON
- Web Search Engine：Tavily
- APIキーを入力

### 6. カスタムモデルを作成し、本リポジトリの内容を反映

1. `Workspace > Skills > インポート` で `skills/` 配下の3ファイルをインポート
2. `Workspace > モデル > + Create a model`
   - Base Model：`qwen3:14b`
   - System Prompt：`core/system_prompt.md` の内容を貼り付け
   - Skills：インポートした3つ全てにチェック
3. 推奨パラメータ（下記参照）を設定して保存

### 7. 推奨モデルパラメータ

| パラメータ | 推奨値 | 理由 |
|---|---|---|
| Function呼び出し | Native | ツール呼び出しを自律的に行わせるため必須 |
| think (Ollama) | ON（デフォルト） | OFFにすると検索を省略し内部知識で創作するリスクが上がる（詳細は`known_issues_and_fixes.md`） |
| Temperature | 0.3〜0.5 | 判定のブレ（買い/売りが頻繁に反転する）を抑える |
| max_tokens | 8192以上 | 長いレポート生成が途中で切れないようにする |
| num_ctx (Ollama) | 16384〜32768 | Skill本文＋検索結果を収容するための最低限の目安 |
| 組み込みツール | **必要最小限に絞る（後述）** | Ollamaのツール定義シリアライズ不具合を回避するため |

### 8. 組み込みツールを最小化する（最重要・既知の不具合への対処）

モデル編集画面の「機能」「組み込みツール」セクションで、**ウェブ検索以外を全てOFF**にする：

- ❌ Time & Calculation、メモリ、チャット履歴、ノート、ナレッジベース、チャンネル、画像生成、コードインタプリタ、Task Management、オートメーション、カレンダー、Terminal
- ✅ ウェブ検索（これだけ残す）

理由：Ollamaには、複数のツール定義を同時に渡すとツール定義のシリアライズが壊れ、モデルが「思考だけ書いて実行に進まない」不具合が報告されている（詳細は`known_issues_and_fixes.md`）。ツール数を絞ることで発生条件を減らせる。

## 動作確認

新規チャットでカスタムモデルを選び、「トヨタ分析」のように送信。`Explored search_web`のようなツール実行表示が複数回出てから、Markdown形式のレポートが返ってくれば成功。

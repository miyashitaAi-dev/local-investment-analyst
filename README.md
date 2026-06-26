# Local Investment Analyst (Open WebUI × Local LLM × Tool Calling)

ローカルLLM（Qwen3-14B等）+ Open WebUI + Tavily Web検索を使った、投資分析（株式・FX・暗号資産・コモディティ）特化のシステムプロンプート／Skill集です。

学習目的で構築したプロジェクトであり、**この構成自体を「ローカルLLMでハルシネーションを抑え、ツール呼び出しを安定させるための実践的なノウハウ集」**として公開しています。投資助言ではありません。

## なぜこれが必要だったか

ローカルLLM（特にQwen3のような思考＋ネイティブツール呼び出しを併用するモデル）をOpen WebUI経由で運用すると、以下のような問題が頻発します。

- 検索を実行せず、それっぽい数値を生成する（ハルシネーション）
- 計画だけ書いて、実際のツール呼び出しに進まずに終わる
- Ollama側のツール定義シリアライズ不具合により、ツール呼び出し自体が機能しない
- 「今日の日付」をうまく確定できず、古い情報を「最新」として扱う

このリポジトリは、これらを1つずつ潰していった結果のプロンプト・Skill・知見をまとめたものです。詳しい経緯は[`docs/known_issues_and_fixes.md`](docs/known_issues_and_fixes.md)を参照してください。

## 検証結果（再現性・正確性）

実際にQwen3-14B＋Tavilyで再現性検証（同一銘柄を複数回実行）・多様性検証（複数事業セグメント企業／単一事業企業／情報の少ない中小型株）を行った結果：

| 項目 | 結果 |
|---|---|
| 直近期の主要指標（株価・PER・PBR・時価総額等） | 概ね正確（計算式による導出方式が有効） |
| 決算表の年度重複 | 約33%の確率で発生（既知の残存リスク） |
| 事業部門別利益率／決算の「実績・予想」の区別 | プロンプトでの明示的禁止後も再発することがある（モデルの確率的な限界に近いと判断） |
| MACD | 専門サイト指定後も精度が不安定（RSIは概ね定性的に妥当） |
| 情報が極端に薄い銘柄での挙動 | テンプレート構成を維持しつつ`N/A`処理する設計だが、プロンプトの保存ミスがあると崩れやすい（運用時は1文字単位の保存確認を推奨） |

**実用に使う場合は、決算数値・実績/予想の区別について、人間による最終確認を運用に組み込むことを推奨します。** 詳細は[`docs/verification_checklist.md`](docs/verification_checklist.md)を参照してください。

## 構成

```
core/                  全Skill共通のシステムプロンプート（ハルシネーション防止・出力形式・進行管理ルール）
skills/                資産クラス別の検索ワークフロー＋レポートテンプレート（Open WebUI Skills機能用）
  stock-analysis.md               株式（日本株・米国株）
  fx-crypto-commodity-analysis.md FX・暗号資産・コモディティ
  position-checkup.md             保有中ポジションの中間チェック
docs/
  setup_guide.md             Open WebUI + Ollama + Qwen3 + Tavilyの環境構築手順
  known_issues_and_fixes.md  実際にハマった不具合と対処の記録（全14件）
  verification_checklist.md 再現性・正確性の検証チェックリストと結果
roadmap/
  future_fund_flow_skill.md 将来構想メモ（資金フロー・ポジショニング系Skill、未着手）
```

## 動作環境

- Open WebUI（Docker）
- Ollama + Qwen3-14B（Native Function Calling対応モデル推奨）
- Tavily API（Web検索プロバイダ）

詳細な構築手順は[`docs/setup_guide.md`](docs/setup_guide.md)を参照してください。

## 使い方（概要）

1. `core/system_prompt.md`の内容を、Open WebUIの`Workspace > モデル`でカスタムモデルのSystem Promptに貼り付ける
2. `skills/`配下の各ファイルを、`Workspace > Skills`にインポートする（YAMLフロントマターのname/descriptionで自動認識される）
3. 作成したカスタムモデルに、インポートした全Skillを添付する
4. モデルパラメータ：`Function呼び出し=Native`、`think=ON`、`num_ctx`は最低16384以上を推奨（詳細は`docs/setup_guide.md`）

## 今後の方向性

検証フェーズが完了し、次はファインチューニング（LoRA/QLoRA）用の教師データ収集に進む予定です。資金フロー・ポジショニング系の新Skillの構想は[`roadmap/future_fund_flow_skill.md`](roadmap/future_fund_flow_skill.md)を参照してください。

## 重要な注意点

- **APIキー・チャット履歴・個人データはこのリポジトリに含まれていません。** TavilyのAPIキー等は各自の環境で設定してください。
- 本リポジトリのプロンプト・Skillは情報提供を目的としたものであり、投資助言ではありません。生成される分析結果は検索結果に基づくものであり、正確性・最新性を保証するものではありません。
- ローカルLLM・Ollama・Open WebUIの組み合わせには既知の不具合（ツール呼び出し関連）が存在します。`docs/known_issues_and_fixes.md`で詳細と回避策を確認してください。

## ライセンス

MIT License（[`LICENSE`](LICENSE)を参照）。プロンプト・Skillの内容は自由に改変・再配布・商用利用可能です。

"""
title: Citation Validator (出典検証フィルター)
author: miyashitaAi-dev (with Claude)
version: 1.0.0
required_open_webui_version: 0.5.0
description: >
  不具合18対応。レポート本文中の「事業部門別損益」「複数年決算分析」テーブルについて、
  出典マーカー（[出典：...]、（出典：...）、ハイパーリンク等）が付いていない数値セルを
  機械的に検出し、⚠️マークを付与する。LLMの自己規律（ルールを自発的に守るかどうか）に
  依存せず、生成後にコードで強制的に検証する後処理レイヤー。

  これは「気づいているのに書かない／推定値を出典なしで書く」という不具合17・18の根本対策。
  LLMにルールを守らせる努力（プロンプト修正）には限界があるため、検証自体を
  確率に依存しないコード側の仕組みに移す、という設計判断に基づく。

  検出対象セクション：
    - ## 🏢 事業部門別損益
    - ## 📑 複数年決算分析
  対象外（意図的）：
    - 総合スコア表（元々出典不要というルールがあるため対象外）
    - 強気/弱気の根拠、戦略、判断系のセクション（推定OK領域のため対象外。不具合18のルール参照）
"""

import re
from typing import Optional
from pydantic import BaseModel, Field


# 出典が明記されていると判断するためのパターン群。
# Skillのレポートテンプレートで実際に使われている表記ゆれに合わせて、複数パターンを許容する。
CITATION_PATTERNS = [
    r"出典",                # 「（出典：◯◯）」「[出典：◯◯]」等
    r"\[.*?(?:ファイナンス|証券|Yahoo|Monex|Matsui|松井|FISCO|Kabuyoho|StockWeather|investing|Reuters|Bloomberg).*?\]",
    r"https?://",           # ハイパーリンク形式の出典
    r"検索結果に記載",
    r"N/A",                 # N/Aは正しい挙動なので警告対象から除外する
]
CITATION_REGEX = re.compile("|".join(CITATION_PATTERNS), re.IGNORECASE)

# 警告対象とする数値パターン（カンマ区切りの3桁以上の数字、または小数点付きの数字）
NUMERIC_REGEX = re.compile(r"-?\d{1,3}(?:,\d{3})+(?:\.\d+)?|(?<![\w.])-?\d+\.\d+(?![\w])")

# 監視対象セクションの見出し（このセクションの直後から、次の "##" 見出しまでを検査範囲とする）
TARGET_SECTION_HEADINGS = [
    r"##\s*.*事業部門別損益",
    r"##\s*.*複数年決算分析",
]

WARNING_TAG = " ⚠️未検証"


def _extract_section(text: str, heading_pattern: str) -> Optional[tuple]:
    """指定見出しから次の見出し（## または ---）までの範囲を (start, end) で返す。"""
    m = re.search(heading_pattern, text)
    if not m:
        return None
    start = m.end()
    rest = text[start:]
    next_heading = re.search(r"\n##\s|\n---", rest)
    end = start + next_heading.start() if next_heading else len(text)
    return (start, end)


def _validate_table_block(block: str) -> tuple[str, int]:
    """Markdownテーブルの各行について、数値セルに出典マーカーがあるかを確認する。
    出典マーカーがない数値セルが見つかった行には、行全体にWARNING_TAGを付与する。
    戻り値: (修正後のブロック文字列, 警告を付けた行数)
    """
    lines = block.split("\n")
    warned_count = 0
    new_lines = []

    for line in lines:
        stripped = line.strip()

        # テーブル行（| で始まる）以外、区切り行（|---|---|）はそのまま通す
        if not stripped.startswith("|"):
            new_lines.append(line)
            continue
        if re.match(r"^\|[\s\-:|]+\|$", stripped):
            new_lines.append(line)
            continue

        has_number = bool(NUMERIC_REGEX.search(line))
        has_citation = bool(CITATION_REGEX.search(line))
        already_warned = WARNING_TAG in line

        if has_number and not has_citation and not already_warned:
            # 行の末尾（最後の "|" の直前）に警告タグを挿入する
            if line.rstrip().endswith("|"):
                idx = line.rstrip().rfind("|")
                line = line.rstrip()[:idx] + WARNING_TAG + " " + line.rstrip()[idx:]
            else:
                line = line + WARNING_TAG
            warned_count += 1

        new_lines.append(line)

    return "\n".join(new_lines), warned_count


def validate_citations(content: str) -> tuple[str, int]:
    """レポート全文を受け取り、対象セクション内の出典なし数値セルに警告を付けて返す。
    戻り値: (修正後の本文, 警告を付けた合計セル数)
    """
    total_warned = 0
    for heading_pattern in TARGET_SECTION_HEADINGS:
        section = _extract_section(content, heading_pattern)
        if section is None:
            continue
        start, end = section
        block = content[start:end]
        new_block, warned = _validate_table_block(block)
        if warned:
            content = content[:start] + new_block + content[end:]
            total_warned += warned
    return content, total_warned


class Filter:
    class Valves(BaseModel):
        enabled: bool = Field(
            default=True,
            description="出典検証フィルターを有効にする。",
        )
        append_summary_note: bool = Field(
            default=True,
            description="警告を1件以上付けた場合、レポート末尾に件数のサマリー注記を追加する。",
        )

    def __init__(self):
        self.valves = self.Valves()
        self.toggle = True  # ユーザーがチャットごとにON/OFFできるようにする

    async def outlet(self, body: dict, __user__: Optional[dict] = None) -> dict:
        if not self.valves.enabled:
            return body

        messages = body.get("messages", [])
        if not messages:
            return body

        last = messages[-1]
        if last.get("role") != "assistant":
            return body

        content = last.get("content", "")
        if not content:
            return body

        new_content, warned_count = validate_citations(content)

        if warned_count > 0 and self.valves.append_summary_note:
            new_content += (
                f"\n\n---\n"
                f"🔍 **出典検証フィルター（自動チェック）**：事業部門別損益・複数年決算分析の表で、"
                f"出典マーカーが見つからない数値セルが**{warned_count}件**ありました（上記`⚠️未検証`を参照）。"
                f"これらの数値は検索結果から確認できなかった可能性があるため、利用前に元の検索結果と照合してください。"
            )

        last["content"] = new_content
        return body

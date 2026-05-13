from __future__ import annotations

from datetime import datetime
from typing import Iterable


def rows_to_markdown(rows: Iterable[dict], title: str = "待学习词汇") -> str:
    rows = list(rows)
    lines: list[str] = []
    lines.append(f"# {title}")
    lines.append("")
    lines.append(f"生成时间：{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    lines.append(f"词数：{len(rows)}")
    lines.append("")

    if not rows:
        lines.append("未发现符合条件的词汇。")
        lines.append("")
        return "\n".join(lines)

    for idx, row in enumerate(rows, start=1):
        word = row.get("lemma") or row.get("word") or ""
        surface = row.get("word") or word
        lines.append(f"## {idx}. {word}")
        lines.append("")
        if surface and surface != word:
            lines.append(f"- 原文形式：`{surface}`")
        lines.append(f"- CEFR：`{row.get('cefr') or '未知'}`")
        lines.append(f"- 中文释义：{row.get('meaning_zh') or '暂无释义'}")
        if row.get("score") not in (None, ""):
            lines.append(f"- 系统评分：`{row.get('score')}`")
        sentence = (row.get("sentence") or "").strip()
        if sentence:
            lines.append(f"- 原文句子：{sentence}")
        lines.append("")
    return "\n".join(lines)

from __future__ import annotations

from typing import Iterable


def rows_to_markdown(rows: Iterable[dict], title: str = "待学习词汇") -> str:
    lines: list[str] = []
    for row in rows:
        word = row.get("lemma") or row.get("word") or ""
        if word:
            lines.append(word)
    return "\n".join(lines)

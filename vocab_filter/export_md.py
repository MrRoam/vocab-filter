from __future__ import annotations

from datetime import datetime
from html import escape
from typing import Iterable


def rows_to_markdown(rows: Iterable[dict], title: str = "Likely Unknown Words") -> str:
    rows = list(rows)
    lines: list[str] = []
    lines.append(f"# {title}")
    lines.append("")
    lines.append(f"Generated at: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    lines.append("")
    lines.append(f"Total: {len(rows)}")
    lines.append("")

    if not rows:
        lines.append("No words found.")
        lines.append("")
        return "\n".join(lines)

    for idx, row in enumerate(rows, start=1):
        word = row.get("lemma") or row.get("word") or ""
        surface = row.get("word") or word
        lines.append(f"## {idx}. {word}")
        lines.append("")
        if surface and surface != word:
            lines.append(f"- Original: `{surface}`")
        lines.append(f"- CEFR: `{row.get('cefr') or 'unknown'}`")
        lines.append(f"- Score: `{row.get('score', '')}`")
        lines.append(f"- Label: `{row.get('label', '')}`")
        lines.append(f"- Zipf: `{row.get('zipf', '')}`")
        lines.append(f"- Reason: {row.get('reason', '')}")
        sentence = (row.get("sentence") or "").strip()
        if sentence:
            lines.append(f"- Context: {sentence}")
        lines.append("")
    return "\n".join(lines)

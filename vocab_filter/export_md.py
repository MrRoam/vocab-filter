from __future__ import annotations

from pathlib import Path
from typing import Iterable


def rows_to_markdown(rows: list[dict], title: str = "Likely Unknown Words") -> str:
    lines: list[str] = [f"# {title}", ""]

    if not rows:
        lines.append("没有筛出大概率不熟的词。")
        lines.append("")
        return "\n".join(lines)

    for idx, row in enumerate(rows, start=1):
        word = str(row.get("lemma") or row.get("word") or "").strip()
        surface = str(row.get("word") or "").strip()
        cefr = str(row.get("cefr") or "Unknown")
        score = str(row.get("score") or "")
        zipf = str(row.get("zipf") or "")
        reason = str(row.get("reason") or "")
        sentence = str(row.get("sentence") or "").strip()

        heading = word if surface.lower() == word.lower() or not surface else f"{word} ({surface})"
        lines.append(f"## {idx}. {heading}")
        lines.append("")
        lines.append(f"- CEFR: {cefr}")
        lines.append(f"- Score: {score}")
        if zipf:
            lines.append(f"- Zipf frequency: {zipf}")
        if reason:
            lines.append(f"- Reason: {reason}")
        if sentence:
            lines.append(f"- Sentence: {sentence}")
        lines.append("")

    return "\n".join(lines)


def write_markdown(path: str | Path, rows: list[dict], title: str = "Likely Unknown Words") -> None:
    Path(path).write_text(rows_to_markdown(rows, title=title), encoding="utf-8")

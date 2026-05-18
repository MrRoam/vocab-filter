from __future__ import annotations


QUICK_PLACEMENT_SOURCE = "快速测评结果"


def should_show_level_settings_placement(level_source: str | None, show_placement: bool) -> bool:
    return level_source == QUICK_PLACEMENT_SOURCE and show_placement

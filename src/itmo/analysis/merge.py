"""合并四份分析片段为一个 analysis.json。

拆成四份是为了让每个阶段能独立重跑——复述稿不满意时只重跑 retelling，
不用重新提取观点。合并时按 id 对账，缺漏和多余都必须报出来。
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

FRAGMENT_FILES = {
    "viewpoints": "viewpoints.json",
    "retellings": "retellings.json",
    "expressions": "expressions.json",
    "socratic": "socratic.json",
}


class MergeError(RuntimeError):
    """片段缺失或对不上账。"""


def _load_fragment(directory: Path, filename: str) -> dict[str, Any]:
    path = directory / filename
    if not path.exists():
        raise MergeError(f"缺少分析片段：{path}")
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        raise MergeError(f"{path} 不是合法 JSON：{exc}") from exc
    if not isinstance(payload, dict):
        raise MergeError(f"{path} 顶层必须是对象。")
    return payload


def merge_fragments(directory: Path) -> dict[str, Any]:
    """读取四份片段并合并。"""
    viewpoints_doc = _load_fragment(directory, FRAGMENT_FILES["viewpoints"])
    retellings_doc = _load_fragment(directory, FRAGMENT_FILES["retellings"])
    expressions_doc = _load_fragment(directory, FRAGMENT_FILES["expressions"])
    socratic_doc = _load_fragment(directory, FRAGMENT_FILES["socratic"])

    viewpoints = viewpoints_doc.get("viewpoints")
    if not isinstance(viewpoints, list) or not viewpoints:
        raise MergeError("viewpoints.json 里没有 viewpoints 数组。")

    retellings = {
        item.get("id"): item
        for item in retellings_doc.get("retellings", [])
        if isinstance(item, dict)
    }

    viewpoint_ids = {v.get("id") for v in viewpoints}
    missing = viewpoint_ids - set(retellings)
    extra = set(retellings) - viewpoint_ids
    if missing:
        raise MergeError(
            f"retellings.json 缺少这些观点的复述稿：{', '.join(sorted(map(str, missing)))}"
        )
    if extra:
        raise MergeError(
            f"retellings.json 有多余的条目，id 对不上任何观点："
            f"{', '.join(sorted(map(str, extra)))}"
        )

    merged_viewpoints = []
    for viewpoint in viewpoints:
        retelling = retellings[viewpoint["id"]]
        merged_viewpoints.append(
            {
                **viewpoint,
                "retelling_30s": retelling.get("retelling_30s", ""),
                "retelling_2min": retelling.get("retelling_2min", ""),
            }
        )

    return {
        "meta": viewpoints_doc.get("meta", {}),
        "viewpoints": merged_viewpoints,
        "expressions": expressions_doc.get("expressions", []),
        "socratic_questions": socratic_doc.get("socratic_questions", []),
    }

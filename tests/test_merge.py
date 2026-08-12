"""片段合并测试。重点是 id 对账。"""

from __future__ import annotations

import json

import pytest

from itmo.analysis.merge import MergeError, merge_fragments


@pytest.fixture
def fragments_dir(tmp_path, analysis):
    """把完整 analysis 拆回四份片段，模拟四步 prompt 的产物。"""
    viewpoints = []
    retellings = []
    for viewpoint in analysis["viewpoints"]:
        stripped = {k: v for k, v in viewpoint.items() if not k.startswith("retelling_")}
        viewpoints.append(stripped)
        retellings.append(
            {
                "id": viewpoint["id"],
                "retelling_30s": viewpoint["retelling_30s"],
                "retelling_2min": viewpoint["retelling_2min"],
            }
        )

    (tmp_path / "viewpoints.json").write_text(
        json.dumps({"meta": analysis["meta"], "viewpoints": viewpoints}), encoding="utf-8"
    )
    (tmp_path / "retellings.json").write_text(
        json.dumps({"retellings": retellings}), encoding="utf-8"
    )
    (tmp_path / "expressions.json").write_text(
        json.dumps({"expressions": analysis["expressions"]}), encoding="utf-8"
    )
    (tmp_path / "socratic.json").write_text(
        json.dumps({"socratic_questions": analysis["socratic_questions"]}), encoding="utf-8"
    )
    return tmp_path


def test_merges_fragments_into_full_analysis(fragments_dir, analysis, transcript):
    from itmo.analysis.validator import validate_analysis

    merged = merge_fragments(fragments_dir)
    assert merged["meta"] == analysis["meta"]
    assert merged["viewpoints"][0]["retelling_30s"] == analysis["viewpoints"][0]["retelling_30s"]
    assert validate_analysis(merged, transcript).ok


def test_missing_fragment_file_is_reported(fragments_dir):
    (fragments_dir / "socratic.json").unlink()
    with pytest.raises(MergeError, match="缺少分析片段"):
        merge_fragments(fragments_dir)


def test_malformed_json_is_reported(fragments_dir):
    (fragments_dir / "expressions.json").write_text("{not json", encoding="utf-8")
    with pytest.raises(MergeError, match="不是合法 JSON"):
        merge_fragments(fragments_dir)


def test_retelling_missing_for_a_viewpoint_is_reported(fragments_dir):
    (fragments_dir / "retellings.json").write_text(
        json.dumps({"retellings": []}), encoding="utf-8"
    )
    with pytest.raises(MergeError, match="缺少这些观点的复述稿"):
        merge_fragments(fragments_dir)


def test_orphan_retelling_is_reported(fragments_dir):
    payload = json.loads((fragments_dir / "retellings.json").read_text(encoding="utf-8"))
    payload["retellings"].append(
        {"id": "ghost-viewpoint", "retelling_30s": "x", "retelling_2min": "y"}
    )
    (fragments_dir / "retellings.json").write_text(json.dumps(payload), encoding="utf-8")
    with pytest.raises(MergeError, match="对不上任何观点"):
        merge_fragments(fragments_dir)


def test_empty_viewpoints_is_reported(fragments_dir):
    (fragments_dir / "viewpoints.json").write_text(
        json.dumps({"meta": {}, "viewpoints": []}), encoding="utf-8"
    )
    with pytest.raises(MergeError, match="没有 viewpoints 数组"):
        merge_fragments(fragments_dir)

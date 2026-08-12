"""分析产物校验。

Schema 只能保证形状，保证不了诚实。业务规则这一层负责后者：引文必须真实、
id 必须对得上、例句不能照抄原文。任何一条不过就拒绝写入 vault。
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from ..transcript.models import Transcript
from .quotes import DEFAULT_MIN_COVERAGE, canonical, check_quote

SCHEMA_PATH = Path(__file__).resolve().parents[3] / "skill" / "schemas" / "analysis_schema.json"


class ValidationFailed(RuntimeError):
    """校验未通过。"""


@dataclass
class ValidationReport:
    errors: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)

    @property
    def ok(self) -> bool:
        return not self.errors

    def raise_if_failed(self) -> None:
        if self.errors:
            lines = "\n".join(f"  - {e}" for e in self.errors)
            raise ValidationFailed(f"分析产物有 {len(self.errors)} 处问题：\n{lines}")


def load_schema() -> dict[str, Any]:
    return json.loads(SCHEMA_PATH.read_text(encoding="utf-8"))


def _validate_schema(analysis: dict[str, Any], report: ValidationReport) -> None:
    import jsonschema

    validator = jsonschema.Draft202012Validator(load_schema())
    for error in sorted(validator.iter_errors(analysis), key=lambda e: list(e.path)):
        location = "/".join(str(p) for p in error.path) or "(根)"
        report.errors.append(f"schema {location}: {error.message}")


def _validate_quotes(
    analysis: dict[str, Any],
    transcript: Transcript,
    report: ValidationReport,
    min_coverage: float,
) -> None:
    """核对每一条引文都真实出现在文字稿中。"""
    haystack = transcript.full_text

    for viewpoint in analysis.get("viewpoints", []):
        quote = viewpoint.get("evidence_quote", "")
        result = check_quote(quote, haystack, min_coverage=min_coverage)
        if not result.found:
            report.errors.append(
                f"观点 {viewpoint.get('id', '?')!r} 的 evidence_quote 在文字稿中找不到"
                f"（{result.summary}）：{quote[:80]!r}"
            )

    for index, expression in enumerate(analysis.get("expressions", [])):
        sentence = expression.get("source_sentence", "")
        result = check_quote(sentence, haystack, min_coverage=min_coverage)
        if not result.found:
            report.errors.append(
                f"表达 {expression.get('text', '?')!r} 的 source_sentence 在文字稿中找不到"
                f"（{result.summary}）：{sentence[:80]!r}"
            )


def _validate_expressions(analysis: dict[str, Any], report: ValidationReport) -> None:
    """例句必须是新写的，照抄原句就失去了练习价值。"""
    for expression in analysis.get("expressions", []):
        example = canonical(expression.get("your_example", ""))
        source = canonical(expression.get("source_sentence", ""))
        if example and source and (example in source or source in example):
            report.errors.append(
                f"表达 {expression.get('text', '?')!r} 的 your_example 照抄了原句，需要重写"
            )

        text = canonical(expression.get("text", ""))
        if text and example and text not in example:
            report.warnings.append(
                f"表达 {expression.get('text', '?')!r} 没有出现在自己的例句里"
            )


def _validate_paragraph_refs(
    analysis: dict[str, Any], transcript: Transcript, report: ValidationReport
) -> None:
    limit = len(transcript.paragraphs)
    for viewpoint in analysis.get("viewpoints", []):
        index = viewpoint.get("paragraph_index")
        if index is not None and index >= limit:
            report.errors.append(
                f"观点 {viewpoint.get('id', '?')!r} 的 paragraph_index={index} 越界"
                f"（文字稿只有 {limit} 段）"
            )


def _validate_ids(analysis: dict[str, Any], report: ValidationReport) -> None:
    ids = [v.get("id") for v in analysis.get("viewpoints", [])]
    duplicates = {i for i in ids if ids.count(i) > 1}
    if duplicates:
        report.errors.append(f"观点 id 重复：{', '.join(sorted(duplicates))}")

    titles = [v.get("title_en") for v in analysis.get("viewpoints", [])]
    duplicate_titles = {t for t in titles if titles.count(t) > 1}
    if duplicate_titles:
        # 标题会成为文件名，重复会导致原子笔记互相覆盖
        report.errors.append(
            f"观点 title_en 重复（会导致笔记互相覆盖）：{', '.join(sorted(duplicate_titles))}"
        )


def _report_attribution(
    analysis: dict[str, Any], report: ValidationReport, threshold: float
) -> None:
    """低置信度不是错误，但要让用户知道有多少条需要人工确认。"""
    low = [
        v.get("id", "?")
        for v in analysis.get("viewpoints", [])
        if v.get("speaker_confidence", 1.0) < threshold
    ]
    if low:
        report.warnings.append(
            f"{len(low)} 条观点的说话人归属置信度低于 {threshold:.0%}，"
            f"笔记中会标注待确认：{', '.join(low)}"
        )

    interviewee = analysis.get("meta", {}).get("interviewee", "")
    if interviewee.lower() in {"unknown speaker", "unknown", ""}:
        report.warnings.append("未能确定被访谈人姓名，建议用 --interviewee 显式指定。")


def validate_analysis(
    analysis: dict[str, Any],
    transcript: Transcript,
    *,
    attribution_threshold: float = 0.7,
    min_quote_coverage: float = DEFAULT_MIN_COVERAGE,
) -> ValidationReport:
    """完整校验。schema 不过就不再跑业务规则，避免刷屏。"""
    report = ValidationReport()

    _validate_schema(analysis, report)
    if not report.ok:
        return report

    _validate_ids(analysis, report)
    _validate_paragraph_refs(analysis, transcript, report)
    _validate_quotes(analysis, transcript, report, min_quote_coverage)
    _validate_expressions(analysis, report)
    _report_attribution(analysis, report, attribution_threshold)

    return report

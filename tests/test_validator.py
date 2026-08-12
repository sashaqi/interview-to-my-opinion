"""分析产物校验测试。重点是引文防编造。"""

from __future__ import annotations

from itmo.analysis.quotes import check_quote
from itmo.analysis.validator import ValidationFailed, validate_analysis


def test_valid_analysis_passes(analysis, transcript):
    report = validate_analysis(analysis, transcript)
    assert report.ok, report.errors


def test_fabricated_quote_is_rejected(analysis, transcript):
    analysis["viewpoints"][0]["evidence_quote"] = (
        "The single biggest mistake teams make is hiring too fast in the first year."
    )
    report = validate_analysis(analysis, transcript)
    assert not report.ok
    assert any("evidence_quote" in e for e in report.errors)


def test_quote_survives_filler_and_punctuation_cleanup(analysis, transcript):
    """去掉口头禅、补标点的真实引文不应被误杀。"""
    analysis["viewpoints"][0]["evidence_quote"] = (
        "The load-bearing assumption there is, you know, that evaluation is cheap — it never is!"
    )
    report = validate_analysis(analysis, transcript)
    assert report.ok, report.errors


def test_quote_stitched_from_distant_fragments_is_rejected(transcript):
    """把散落各处的词拼成的伪引文必须被拦下。"""
    stitched = "The load-bearing assumption is that you cannot buy taste about which part was hard"
    result = check_quote(stitched, transcript.full_text)
    assert not result.found


def test_fabricated_source_sentence_is_rejected(analysis, transcript):
    analysis["expressions"][0]["source_sentence"] = (
        "The load-bearing assumption is that hiring solves everything."
    )
    report = validate_analysis(analysis, transcript)
    assert not report.ok
    assert any("source_sentence" in e for e in report.errors)


def test_example_copied_from_source_is_rejected(analysis, transcript):
    analysis["expressions"][0]["your_example"] = (
        "The load-bearing assumption there is that evaluation is cheap."
    )
    report = validate_analysis(analysis, transcript)
    assert not report.ok
    assert any("照抄" in e for e in report.errors)


def test_out_of_range_paragraph_index_is_rejected(analysis, transcript):
    analysis["viewpoints"][0]["paragraph_index"] = 99
    report = validate_analysis(analysis, transcript)
    assert not report.ok
    assert any("越界" in e for e in report.errors)


def test_duplicate_viewpoint_titles_are_rejected(analysis, transcript):
    duplicate = dict(analysis["viewpoints"][0])
    duplicate["id"] = "another-id"
    analysis["viewpoints"].append(duplicate)
    report = validate_analysis(analysis, transcript)
    assert not report.ok
    assert any("title_en 重复" in e for e in report.errors)


def test_duplicate_viewpoint_ids_are_rejected(analysis, transcript):
    duplicate = dict(analysis["viewpoints"][0])
    duplicate["title_en"] = "A different title entirely here"
    analysis["viewpoints"].append(duplicate)
    report = validate_analysis(analysis, transcript)
    assert not report.ok
    assert any("id 重复" in e for e in report.errors)


def test_schema_violation_is_reported(analysis, transcript):
    del analysis["viewpoints"][0]["claim_en"]
    report = validate_analysis(analysis, transcript)
    assert not report.ok
    assert any("schema" in e for e in report.errors)


def test_low_confidence_produces_warning_not_error(analysis, transcript):
    analysis["viewpoints"][0]["speaker_confidence"] = 0.4
    report = validate_analysis(analysis, transcript, attribution_threshold=0.7)
    assert report.ok
    assert any("置信度" in w for w in report.warnings)


def test_unknown_speaker_produces_warning(analysis, transcript):
    analysis["meta"]["interviewee"] = "Unknown speaker"
    analysis["viewpoints"][0]["speaker"] = "Unknown speaker"
    report = validate_analysis(analysis, transcript)
    assert report.ok
    assert any("被访谈人姓名" in w for w in report.warnings)


def test_raise_if_failed_lists_every_problem(analysis, transcript):
    analysis["viewpoints"][0]["evidence_quote"] = "Completely made up sentence about nothing."
    analysis["expressions"][0]["source_sentence"] = "Another invented sentence entirely here."
    report = validate_analysis(analysis, transcript)
    try:
        report.raise_if_failed()
    except ValidationFailed as exc:
        assert "2 处问题" in str(exc)
    else:
        raise AssertionError("应当抛出 ValidationFailed")

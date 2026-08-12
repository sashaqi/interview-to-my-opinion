"""共享 fixture。"""

from __future__ import annotations

import copy

import pytest

from itmo.transcript.models import Paragraph, SourceMeta, Transcript

TRANSCRIPT_TEXT = [
    "The load-bearing assumption there is that evaluation is cheap. It never is. "
    "Every team I have watched underestimates how long it takes to know whether "
    "the thing actually works.",
    "So people keep adding capacity when the real constraint is somewhere else "
    "entirely. You can buy more compute in an afternoon. You cannot buy taste.",
    "I would walk back my earlier position on that. A year ago I thought the "
    "bottleneck was model quality, and I was wrong about which part was hard.",
]


@pytest.fixture
def transcript() -> Transcript:
    paragraphs = [
        Paragraph(text=text, start_ms=index * 60_000, index=index)
        for index, text in enumerate(TRANSCRIPT_TEXT)
    ]
    return Transcript(
        meta=SourceMeta(
            source_url="https://www.youtube.com/watch?v=test123",
            source_type="youtube",
            source_id="test123",
            title="How Teams Get the Bottleneck Wrong",
            channel="Test Channel",
            published="2026-08-01",
            duration_seconds=1800,
        ),
        paragraphs=paragraphs,
        has_timestamps=True,
    )


VALID_ANALYSIS = {
    "meta": {
        "interviewee": "Jane Doe",
        "interviewer": "Sam Host",
        "thesis_en": "Teams misidentify their real constraint and buy capacity instead of judgment.",
        "thesis_zh": "团队常常认错瓶颈，用买算力代替培养判断力。",
        "domain_tags": ["engineering", "decision-making"],
    },
    "viewpoints": [
        {
            "id": "evaluation-is-never-cheap",
            "title_en": "Evaluation is the hidden cost nobody budgets for",
            "title_zh": "没人给评估留预算",
            "claim_en": "Evaluation cost, not model quality, is what actually gates progress.",
            "reasoning_en": (
                "Teams can ship a change in a day but need weeks to know whether it helped, "
                "so the feedback loop rather than the build loop sets the pace."
            ),
            "evidence_quote": "The load-bearing assumption there is that evaluation is cheap. It never is.",
            "paragraph_index": 0,
            "speaker": "Jane Doe",
            "attribution": "inferred",
            "speaker_confidence": 0.85,
            "retelling_30s": (
                "Here is the part that stuck with me. Everyone budgets for building the thing. "
                "Almost nobody budgets for finding out whether it worked. And that second cost "
                "is the one that actually sets your pace."
            ),
            "retelling_2min": (
                "So there is this idea I keep coming back to. When a team feels slow, the "
                "instinct is to add people or add compute. But the thing that actually gates "
                "you is usually how long it takes to know whether a change helped. You can ship "
                "in a day and still wait three weeks for a read. That gap is where the time "
                "goes. And here is why it hides so well. Building is visible, so it gets "
                "budgeted. Evaluation is invisible until it blocks you, so it never makes it "
                "into the plan. The result is teams that keep buying capacity they do not need. "
                "Now, the honest counterpoint is that some problems really are compute bound, "
                "and in those cases this framing sends you the wrong way. I am still working "
                "out how to tell the two apart quickly. Have you seen it break down differently?"
            ),
            "counterpoint_en": (
                "In genuinely compute-bound problems this framing misleads, and the fix really "
                "is more capacity."
            ),
            "tags": ["evaluation"],
        }
    ],
    "expressions": [
        {
            "text": "load-bearing assumption",
            "type": "collocation",
            "meaning_zh": "支撑整个论证的关键假设，垮了结论就垮。用于拆解别人方案时。",
            "source_sentence": "The load-bearing assumption there is that evaluation is cheap.",
            "your_example": "Before I sign off on this plan, I want to know which assumption is load-bearing.",
        }
    ],
    "socratic_questions": [
        {
            "question_en": "Isn't that just survivorship bias? We only hear from teams that made it work.",
            "why_hard_zh": "直接质疑论据采样方式，只会复述原案例的人会被噎住。",
            "angle_en": (
                "Grant the bias openly, then narrow the claim from 'this causes success' to "
                "'its absence predicts failure', which survivorship bias does not undermine."
            ),
        },
        {
            "question_en": "So what would you actually do differently on Monday morning?",
            "why_hard_zh": "要求把抽象判断落到具体动作，抽象派会卡在这里。",
            "angle_en": (
                "Pick one concrete measurement you would add before writing any code, and say "
                "what decision that measurement would change."
            ),
        },
        {
            "question_en": "But plenty of teams do fine without measuring any of this — how do you square that?",
            "why_hard_zh": "举反例逼你承认适用边界，硬扛会显得教条。",
            "angle_en": (
                "Concede the counterexample first, then name the conditions that make their "
                "situation different rather than defending the claim universally."
            ),
        },
    ],
}


@pytest.fixture
def analysis() -> dict:
    return copy.deepcopy(VALID_ANALYSIS)

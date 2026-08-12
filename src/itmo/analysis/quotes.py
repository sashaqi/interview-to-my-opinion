"""引文核对。

分析层允许清理口头禅和补标点，所以严格子串匹配会误杀大量真实引文。
这里先试精确匹配，失败后退到词级覆盖率：引文的词有多少能在原文的同一处
按序找到。既容忍合理清理，又拦得住编造。

刻意用词而不是字符做比对单位。字符级比对下，编造出来的尾巴能靠散落的
单个字母凑满覆盖率，编造就查不出来。
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from difflib import SequenceMatcher

from ..transcript.models import normalize_for_match

# 词级覆盖率低于此值判定为编造
DEFAULT_MIN_COVERAGE = 0.85

# 转写常见的口头禅，比对前剔除，避免因清理与否产生差异
FILLERS = re.compile(
    r"\b(?:uh|um|uh+m|er|ah|you know|i mean|sort of|kind of|like)\b",
    re.IGNORECASE,
)
_PUNCT = re.compile(r"[^\w\s]")
_SPACES = re.compile(r"\s+")


def canonical(text: str) -> str:
    """比对用的规范形式：去标点、去口头禅、折叠空白、小写。"""
    text = normalize_for_match(text)
    text = FILLERS.sub(" ", text)
    text = _PUNCT.sub(" ", text)
    return _SPACES.sub(" ", text).strip()


def tokenize(text: str) -> list[str]:
    """规范化后按空白切词。"""
    canonical_text = canonical(text)
    return canonical_text.split() if canonical_text else []


@dataclass(frozen=True)
class QuoteCheck:
    found: bool
    coverage: float
    method: str

    @property
    def summary(self) -> str:
        return f"{self.method} 覆盖率 {self.coverage:.0%}"


def check_quote(
    quote: str, haystack: str, *, min_coverage: float = DEFAULT_MIN_COVERAGE
) -> QuoteCheck:
    """核对引文是否真实出现在原文中。"""
    needle_words = tokenize(quote)
    hay_words = tokenize(haystack)

    if not needle_words:
        return QuoteCheck(found=False, coverage=0.0, method="空引文")
    if not hay_words:
        return QuoteCheck(found=False, coverage=0.0, method="原文为空")

    # 精确匹配走词序列子串，避免标点和口头禅差异造成误判
    needle_joined = " ".join(needle_words)
    if needle_joined in " ".join(hay_words):
        return QuoteCheck(found=True, coverage=1.0, method="精确匹配")

    # 只在最佳锚点附近的窗口内计算覆盖率。若放开到全文，一句由散落各处的
    # 词拼出来的伪引文也能凑够覆盖率。
    matcher = SequenceMatcher(None, needle_words, hay_words, autojunk=False)
    anchor = matcher.find_longest_match(0, len(needle_words), 0, len(hay_words))
    if anchor.size == 0:
        return QuoteCheck(found=False, coverage=0.0, method="模糊匹配")

    span = len(needle_words)
    start = max(0, anchor.b - anchor.a - span // 2)
    window = hay_words[start : start + 2 * span]

    windowed = SequenceMatcher(None, needle_words, window, autojunk=False)
    matched = sum(block.size for block in windowed.get_matching_blocks())
    coverage = matched / len(needle_words)
    return QuoteCheck(
        found=coverage >= min_coverage, coverage=coverage, method="模糊匹配"
    )

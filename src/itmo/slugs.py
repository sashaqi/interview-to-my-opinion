"""文件名生成。

两套命名，用途不同：

- `slugify` 用连字符，给 data/ 下的中间产物用，便于命令行操作。
- `note_title` 保留空格，给 vault 里的笔记用。**wikilink 靠文件名解析**，
  所以笔记文件名必须和 `[[链接]]` 里的文字逐字一致，否则双链全断。
"""

from __future__ import annotations

import re
import unicodedata

# macOS/iCloud 与 Obsidian wikilink 都会被这些字符坑到
_UNSAFE = re.compile(r'[\\/:*?"<>|\[\]#^]')
_SPACES = re.compile(r"[\s_]+")
_DASHES = re.compile(r"-{2,}")

MAX_SLUG_LENGTH = 80


def slugify(text: str, *, max_length: int = MAX_SLUG_LENGTH) -> str:
    """转成安全的文件名片段，保留中文与英文单词。"""
    text = unicodedata.normalize("NFC", text).strip()
    text = _UNSAFE.sub(" ", text)
    text = text.replace(".", " ")
    text = _SPACES.sub("-", text)
    text = _DASHES.sub("-", text).strip("-")

    if len(text) > max_length:
        # 尽量在连字符处截断，避免把单词劈成两半
        cut = text[:max_length]
        if "-" in cut[max_length // 2 :]:
            cut = cut[: cut.rindex("-")]
        text = cut.strip("-")

    return text or "untitled"


def note_title(text: str, *, max_length: int = MAX_SLUG_LENGTH) -> str:
    """vault 笔记的文件名，保留空格以便直接用作 wikilink 文字。

    只剔除会破坏文件系统或 wikilink 语法的字符（`[` `]` `#` `^` `|` 等），
    逗号、括号这类 Obsidian 能正常处理的字符原样保留。
    """
    text = unicodedata.normalize("NFC", text).strip()
    text = _UNSAFE.sub(" ", text)
    text = _SPACES.sub(" ", text).strip(" -")

    if len(text) > max_length:
        cut = text[:max_length]
        if " " in cut[max_length // 2 :]:
            cut = cut[: cut.rindex(" ")]
        text = cut.strip(" -")

    return text or "untitled"


def _date_prefix(published: str) -> str:
    return published if re.fullmatch(r"\d{4}-\d{2}-\d{2}", published or "") else ""


def interview_filename(published: str, title: str) -> str:
    """中间产物文件名：YYYY-MM-DD-<slug>。published 为空时省略日期前缀。"""
    slug = slugify(title)
    prefix = _date_prefix(published)
    return f"{prefix}-{slug}" if prefix else slug


def interview_note_name(published: str, title: str) -> str:
    """vault 主笔记文件名：YYYY-MM-DD <标题>。"""
    prefix = _date_prefix(published)
    name = note_title(title)
    return f"{prefix} {name}" if prefix else name

"""生成区与用户区的边界。

产品的核心价值是用户在笔记里写下的东西。重跑分析必须重写生成内容，
但绝不能碰用户写的字。规则：

- 只有 `itmo:generated` 标记之间的内容会被替换
- 标记之外的正文（包括用户区）逐字节保留
- 标记缺失或损坏时**拒绝写入**，不做猜测性合并
- frontmatter 按 key 分级处理：itmo 拥有的键覆盖，用户可改的键写一次，
  itmo 不认识的键原样保留

宁可报错让用户来处理，也不要自作聪明地合并——猜错一次就毁掉用户的手写内容。
"""

from __future__ import annotations

import re
from dataclasses import dataclass

GENERATED_START = "<!-- itmo:generated:start -->"
GENERATED_END = "<!-- itmo:generated:end -->"
MINE_START = "<!-- itmo:mine:start -->"
MINE_END = "<!-- itmo:mine:end -->"

FRONTMATTER_FENCE = "---"

# itmo 拥有：每次重跑都以最新分析为准
OWNED_KEYS = frozenset(
    {
        "title",
        "interviewee",
        "interviewer",
        "source_url",
        "channel",
        "published",
        "duration",
        "type",
        "source",
        "viewpoint_id",
        "attribution",
        "speaker_confidence",
        "speaker",
        "timestamp",
        "itmo_version",
    }
)

# 写一次就交给用户：之后 itmo 不再覆盖
WRITE_ONCE_KEYS = frozenset({"status", "tags", "captured"})

# frontmatter 里 key 行的形状；缩进行和 `- ` 行属于上一个 key
_KEY_LINE = re.compile(r"^(?P<key>[A-Za-z_][\w-]*)\s*:")


class MarkerError(RuntimeError):
    """标记缺失或损坏，拒绝写入。"""


@dataclass(frozen=True)
class NoteParts:
    frontmatter: str | None
    body: str


def split_frontmatter(text: str) -> NoteParts:
    """切出 frontmatter 与正文。没有 frontmatter 时返回 None。"""
    if not text.startswith(FRONTMATTER_FENCE):
        return NoteParts(frontmatter=None, body=text)

    lines = text.split("\n")
    for index in range(1, len(lines)):
        if lines[index].strip() == FRONTMATTER_FENCE:
            return NoteParts(
                frontmatter="\n".join(lines[1:index]),
                body="\n".join(lines[index + 1 :]).lstrip("\n"),
            )
    # 只有开头的 --- 没有闭合，当作没有 frontmatter，避免吞掉正文
    return NoteParts(frontmatter=None, body=text)


def _chunk_frontmatter(frontmatter: str) -> list[tuple[str | None, list[str]]]:
    """把 frontmatter 按 key 切块，续行归给上一个 key。

    不解析 YAML 语义，只做分块，这样用户写的嵌套结构和注释都能原样留住。
    """
    chunks: list[tuple[str | None, list[str]]] = []
    for line in frontmatter.split("\n"):
        match = _KEY_LINE.match(line)
        if match:
            chunks.append((match.group("key"), [line]))
        elif chunks:
            chunks[-1][1].append(line)
        else:
            # key 之前的游离行（注释等）
            chunks.append((None, [line]))
    return chunks


def _render_value(value: object) -> str:
    if isinstance(value, bool):
        return "true" if value else "false"
    if isinstance(value, (int, float)):
        return str(value)
    if isinstance(value, (list, tuple)):
        return "[" + ", ".join(str(item) for item in value) + "]"

    text = str(value)
    # 含特殊字符的字符串加引号，避免破坏 YAML
    if text == "" or re.search(r'^[\[\{>|*&!%@`"\']|:\s|#|\n', text):
        escaped = text.replace('"', '\\"')
        return f'"{escaped}"'
    return text


def render_frontmatter(values: dict[str, object]) -> str:
    """渲染成 frontmatter 文本块（不含首尾 ---）。"""
    lines = [f"{key}: {_render_value(value)}" for key, value in values.items()]
    return "\n".join(lines)


def merge_frontmatter(existing: str | None, new_values: dict[str, object]) -> str:
    """按 key 分级合并 frontmatter。"""
    if existing is None:
        return render_frontmatter(new_values)

    chunks = _chunk_frontmatter(existing)
    seen: set[str] = set()
    merged: list[str] = []

    for key, lines in chunks:
        if key is None:
            merged.extend(lines)
            continue

        seen.add(key)
        if key in OWNED_KEYS and key in new_values:
            merged.append(f"{key}: {_render_value(new_values[key])}")
        else:
            # 用户可改的键和 itmo 不认识的键都原样保留
            merged.extend(lines)

    for key, value in new_values.items():
        if key not in seen:
            merged.append(f"{key}: {_render_value(value)}")

    return "\n".join(merged)


def _find_generated_region(body: str) -> tuple[int, int]:
    start = body.find(GENERATED_START)
    end = body.find(GENERATED_END)

    if start == -1 or end == -1:
        raise MarkerError(
            "笔记中找不到 itmo 生成区标记，拒绝写入以免覆盖你的内容。\n"
            f"需要同时存在 {GENERATED_START} 和 {GENERATED_END}。\n"
            "如果这个文件不是 itmo 生成的，请改用别的文件名；"
            "如果标记被误删，请手动加回或删除该文件后重跑。"
        )
    if end < start:
        raise MarkerError("生成区标记顺序颠倒（end 在 start 之前），拒绝写入。")
    if body.count(GENERATED_START) > 1 or body.count(GENERATED_END) > 1:
        raise MarkerError("生成区标记出现多次，无法确定替换范围，拒绝写入。")

    return start, end + len(GENERATED_END)


def wrap_generated(content: str) -> str:
    """给生成内容套上标记。"""
    return f"{GENERATED_START}\n{content.strip()}\n{GENERATED_END}"


def wrap_mine(heading: str, placeholder: str = "") -> str:
    """渲染一个用户区。只在文件首次创建时写入。"""
    return f"{heading}\n{MINE_START}\n{placeholder}\n{MINE_END}"


def has_user_content(text: str, placeholders: tuple[str, ...] = ()) -> bool:
    """用户区里是否已经写了东西。

    首次创建时写入的提示文字不算用户内容，否则每次重跑都会误报「已保留」。
    """
    ignored = {p.strip() for p in placeholders}
    for match in re.finditer(
        re.escape(MINE_START) + r"(.*?)" + re.escape(MINE_END), text, re.DOTALL
    ):
        content = match.group(1).strip()
        if content and content not in ignored:
            return True
    return False


def compose_note(frontmatter: str, body: str) -> str:
    """拼成完整笔记文本。"""
    return f"{FRONTMATTER_FENCE}\n{frontmatter}\n{FRONTMATTER_FENCE}\n\n{body.strip()}\n"


def merge_note(existing_text: str, new_values: dict[str, object], new_generated: str) -> str:
    """把新生成内容合并进已有笔记，保留用户写的一切。

    标记之外的正文逐字节保留，这是用户区不会丢的根本保证。
    """
    parts = split_frontmatter(existing_text)
    start, end = _find_generated_region(parts.body)

    before = parts.body[:start]
    after = parts.body[end:]
    body = f"{before}{wrap_generated(new_generated)}{after}"

    frontmatter = merge_frontmatter(parts.frontmatter, new_values)
    return compose_note(frontmatter, body)

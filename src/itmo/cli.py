"""itmo 命令行入口。

设计原则：每个阶段的产物落成文件，阶段之间可独立重跑。分析质量出问题时
只需重跑分析，不用重新抓字幕。
"""

from __future__ import annotations

import argparse
import json
import os
import shutil
import sys
from pathlib import Path

from .analysis.merge import merge_fragments
from .analysis.validator import validate_analysis
from .config import Config, ConfigError, load_config
from .fetch.pipeline import build_transcript
from .slugs import interview_filename
from .transcript.models import Transcript
from .vault.writer import write_notes


def _write_transcript(transcript: Transcript, config: Config, out_dir: Path | None) -> Path:
    target_dir = out_dir or config.transcripts_dir
    target_dir.mkdir(parents=True, exist_ok=True)
    name = interview_filename(transcript.meta.published, transcript.meta.title or "transcript")
    path = target_dir / f"{name}.json"
    path.write_text(
        json.dumps(transcript.to_dict(), ensure_ascii=False, indent=2), encoding="utf-8"
    )
    return path


def cmd_fetch(args: argparse.Namespace, config: Config) -> int:
    source = args.transcript_file or args.source
    if not source:
        print("需要提供一个来源：URL 位置参数，或 --transcript-file 路径。", file=sys.stderr)
        return 2

    transcript = build_transcript(source, config, episode_title=args.episode)
    path = _write_transcript(transcript, config, args.out_dir)

    meta = transcript.meta
    print(f"标题     : {meta.title or '(无)'}")
    print(f"频道     : {meta.channel or '(无)'}")
    print(f"来源     : {meta.source_url or source}")
    print(f"时间戳   : {'有' if transcript.has_timestamps else '无'}")
    print(f"段落 / 词: {len(transcript.paragraphs)} / {transcript.word_count()}")
    print(f"已写入   : {path}")
    return 0


def _load_transcript(path: Path) -> Transcript:
    if not path.exists():
        raise ConfigError(f"文字稿不存在：{path}\n先运行 `itmo fetch`。")
    return Transcript.from_dict(json.loads(path.read_text(encoding="utf-8")))


def cmd_build(args: argparse.Namespace, config: Config) -> int:
    """合并四份分析片段，对着文字稿校验，产出 analysis.json。"""
    transcript = _load_transcript(args.transcript)
    analysis = merge_fragments(args.fragments)

    report = validate_analysis(
        analysis, transcript, attribution_threshold=config.attribution_threshold
    )

    for warning in report.warnings:
        print(f"提醒：{warning}")

    if not report.ok:
        for error in report.errors:
            print(f"错误：{error}", file=sys.stderr)
        print(
            f"\n校验未通过（{len(report.errors)} 处），未写出 analysis.json。"
            "\n重跑对应阶段的 prompt 修正后再试。",
            file=sys.stderr,
        )
        return 1

    out_path = args.out or config.analysis_dir / f"{args.transcript.stem}.json"
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(analysis, ensure_ascii=False, indent=2), encoding="utf-8")

    print(f"观点 / 表达 / 追问: {len(analysis['viewpoints'])} / "
          f"{len(analysis['expressions'])} / {len(analysis['socratic_questions'])}")
    print(f"校验通过，已写入: {out_path}")
    return 0


def cmd_publish(args: argparse.Namespace, config: Config) -> int:
    """把 analysis.json 渲染成笔记写进 vault。"""
    transcript = _load_transcript(args.transcript)
    if not args.analysis.exists():
        raise ConfigError(f"分析产物不存在：{args.analysis}\n先运行 `itmo build`。")
    analysis = json.loads(args.analysis.read_text(encoding="utf-8"))

    # 写 vault 前再校验一次。analysis.json 可能被手动改过。
    report = validate_analysis(
        analysis, transcript, attribution_threshold=config.attribution_threshold
    )
    if not report.ok:
        for error in report.errors:
            print(f"错误：{error}", file=sys.stderr)
        print("\n校验未通过，未写入 vault。", file=sys.stderr)
        return 1

    if args.out_dir:
        interview_dir = args.out_dir
        viewpoint_dir = args.out_dir / "Viewpoints"
    else:
        interview_dir = config.interview_path()
        viewpoint_dir = config.viewpoint_path()

    result = write_notes(
        analysis,
        transcript,
        interview_dir=interview_dir,
        viewpoint_dir=viewpoint_dir,
        threshold=config.attribution_threshold,
        dry_run=args.dry_run,
    )

    prefix = "[dry-run] " if args.dry_run else ""
    for path in result.created:
        print(f"{prefix}新建 {path}")
    for path in result.updated:
        note = "（已保留你写的内容）" if path in result.preserved else ""
        print(f"{prefix}更新 {path} {note}".rstrip())
    for path in result.orphans:
        print(f"提醒：{path} 是这期访谈的旧观点笔记，本次分析里已不存在。未删除，请自行处理。")

    return 0


def cmd_doctor(args: argparse.Namespace, config: Config) -> int:
    """环境自检。不修改任何东西，只报告。"""
    ok = True

    def report(label: str, passed: bool, detail: str) -> None:
        nonlocal ok
        ok = ok and passed
        print(f"[{'ok' if passed else 'FAIL'}] {label}: {detail}")

    try:
        import yt_dlp

        report("yt-dlp", True, f"版本 {yt_dlp.version.__version__}")
    except ModuleNotFoundError:
        report("yt-dlp", False, "未安装，运行 `uv sync`")

    try:
        import jsonschema  # noqa: F401

        report("jsonschema", True, "已安装")
    except ModuleNotFoundError:
        report("jsonschema", False, "未安装，运行 `uv sync`")

    if config.vault_path is None:
        report("vault 路径", False, "未配置 ITMO_VAULT_PATH（复制 .env.example 为 .env）")
    elif not config.vault_path.is_dir():
        report("vault 路径", False, f"目录不存在：{config.vault_path}")
    elif not os.access(config.vault_path, os.W_OK):
        report("vault 路径", False, f"不可写：{config.vault_path}")
    else:
        report("vault 路径", True, str(config.vault_path))

        # iCloud 会把不常用文件逐出本地，只留 .icloud 占位符
        placeholders = list(config.vault_path.glob("**/.*.icloud"))
        if placeholders:
            report(
                "iCloud 本地副本",
                False,
                f"有 {len(placeholders)} 个文件未下载到本地，先在 Finder 里下载",
            )
        else:
            report("iCloud 本地副本", True, "vault 文件均在本地")

    free_gb = shutil.disk_usage(config.data_dir.parent).free / 1024**3
    report("磁盘空间", free_gb > 1, f"剩余 {free_gb:.1f} GB")

    print()
    print("自检通过。" if ok else "存在问题，先修复上面标 FAIL 的项。")
    return 0 if ok else 1


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="itmo",
        description="把访谈转成可用英文复述的 Obsidian 笔记",
    )
    subparsers = parser.add_subparsers(dest="command", required=True)

    fetch = subparsers.add_parser("fetch", help="采集字幕并归一化为 transcript.json")
    fetch.add_argument("source", nargs="?", help="YouTube 视频链接或播客 RSS 地址")
    fetch.add_argument(
        "--transcript-file",
        help="直接使用本地文字稿（.txt/.md/.vtt/.srt/.json3），绕过字幕抓取",
    )
    fetch.add_argument(
        "--episode", help="播客 RSS 专用：按标题关键词选单集，默认取最新一期"
    )
    fetch.add_argument("--out-dir", type=Path, help="输出目录，默认 data/transcripts")
    fetch.set_defaults(handler=cmd_fetch)

    build = subparsers.add_parser("build", help="合并分析片段并校验，产出 analysis.json")
    build.add_argument("--transcript", type=Path, required=True, help="transcript.json 路径")
    build.add_argument(
        "--fragments",
        type=Path,
        required=True,
        help="含 viewpoints/retellings/expressions/socratic.json 的目录",
    )
    build.add_argument("--out", type=Path, help="输出路径，默认 data/analysis/<name>.json")
    build.set_defaults(handler=cmd_build)

    publish = subparsers.add_parser("publish", help="渲染笔记并写入 Obsidian vault")
    publish.add_argument("--transcript", type=Path, required=True, help="transcript.json 路径")
    publish.add_argument("--analysis", type=Path, required=True, help="analysis.json 路径")
    publish.add_argument(
        "--out-dir",
        type=Path,
        help="改写到指定目录而非 vault，用于先看效果再入库",
    )
    publish.add_argument("--dry-run", action="store_true", help="只报告将写哪些文件，不落盘")
    publish.set_defaults(handler=cmd_publish)

    doctor = subparsers.add_parser("doctor", help="检查依赖与 vault 可用性")
    doctor.set_defaults(handler=cmd_doctor)

    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)

    try:
        config = load_config()
        return args.handler(args, config)
    except (ConfigError, RuntimeError) as exc:
        print(f"错误：{exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())

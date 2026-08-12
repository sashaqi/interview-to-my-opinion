"""运行时配置。

配置只从 .env 和环境变量读取。vault 路径在使用前显式校验，
因为 vault 在 iCloud 里，路径存在不代表文件已经下载到本地。
"""

from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path

from dotenv import load_dotenv

DEFAULT_SUB_LANGS = ("en", "en-orig", "en-US", "en-GB")
DEFAULT_INTERVIEW_DIR = "06-Interviews"
DEFAULT_VIEWPOINT_DIR = "06-Interviews/Viewpoints"
DEFAULT_DATA_DIR = "data"
DEFAULT_ATTRIBUTION_THRESHOLD = 0.7


class ConfigError(RuntimeError):
    """配置缺失或不可用。"""


def project_root() -> Path:
    """返回项目根目录（src/itmo/config.py 往上三层）。"""
    return Path(__file__).resolve().parents[2]


@dataclass(frozen=True)
class Config:
    vault_path: Path | None
    interview_dir: str
    viewpoint_dir: str
    data_dir: Path
    sub_langs: tuple[str, ...]
    attribution_threshold: float

    @property
    def transcripts_dir(self) -> Path:
        return self.data_dir / "transcripts"

    @property
    def analysis_dir(self) -> Path:
        return self.data_dir / "analysis"

    @property
    def raw_dir(self) -> Path:
        return self.data_dir / "raw"

    def require_vault(self) -> Path:
        """返回 vault 路径，未配置或不可写时抛错。

        写入 vault 前必须过这一关，避免把笔记写到不存在的目录里。
        """
        if self.vault_path is None:
            raise ConfigError(
                "未配置 ITMO_VAULT_PATH。复制 .env.example 为 .env 并填写 vault 绝对路径。"
            )
        if not self.vault_path.is_dir():
            raise ConfigError(f"vault 路径不存在或不是目录：{self.vault_path}")
        if not os.access(self.vault_path, os.W_OK):
            raise ConfigError(f"vault 目录不可写：{self.vault_path}")
        return self.vault_path

    def interview_path(self) -> Path:
        return self.require_vault() / self.interview_dir

    def viewpoint_path(self) -> Path:
        return self.require_vault() / self.viewpoint_dir


def _parse_sub_langs(raw: str | None) -> tuple[str, ...]:
    if not raw:
        return DEFAULT_SUB_LANGS
    langs = tuple(item.strip() for item in raw.split(",") if item.strip())
    return langs or DEFAULT_SUB_LANGS


def _parse_threshold(raw: str | None) -> float:
    if not raw:
        return DEFAULT_ATTRIBUTION_THRESHOLD
    try:
        value = float(raw)
    except ValueError as exc:
        raise ConfigError(f"ITMO_ATTRIBUTION_THRESHOLD 不是数字：{raw!r}") from exc
    if not 0.0 <= value <= 1.0:
        raise ConfigError(f"ITMO_ATTRIBUTION_THRESHOLD 必须在 0 到 1 之间，得到 {value}")
    return value


def load_config(env_file: Path | None = None) -> Config:
    """加载配置。env_file 未指定时读取项目根的 .env。"""
    root = project_root()
    load_dotenv(env_file or root / ".env")

    raw_vault = os.getenv("ITMO_VAULT_PATH", "").strip()
    vault_path = Path(raw_vault).expanduser() if raw_vault else None

    raw_data = os.getenv("ITMO_DATA_DIR", DEFAULT_DATA_DIR).strip() or DEFAULT_DATA_DIR
    data_dir = Path(raw_data).expanduser()
    if not data_dir.is_absolute():
        data_dir = root / data_dir

    return Config(
        vault_path=vault_path,
        interview_dir=os.getenv("ITMO_INTERVIEW_DIR", DEFAULT_INTERVIEW_DIR).strip()
        or DEFAULT_INTERVIEW_DIR,
        viewpoint_dir=os.getenv("ITMO_VIEWPOINT_DIR", DEFAULT_VIEWPOINT_DIR).strip()
        or DEFAULT_VIEWPOINT_DIR,
        data_dir=data_dir,
        sub_langs=_parse_sub_langs(os.getenv("ITMO_SUB_LANGS")),
        attribution_threshold=_parse_threshold(os.getenv("ITMO_ATTRIBUTION_THRESHOLD")),
    )

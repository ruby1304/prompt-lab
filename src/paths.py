# src/paths.py
"""集中维护项目中的路径常量，避免在脚本里硬编码。"""

from __future__ import annotations

from pathlib import Path


ROOT_DIR = Path(__file__).resolve().parent.parent
DATA_DIR = ROOT_DIR / "data"
PROMPT_DIR = ROOT_DIR / "prompts"

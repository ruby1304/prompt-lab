# src/config.py
from __future__ import annotations

import os
from dotenv import load_dotenv

# 加载 .env
load_dotenv()

def get_openai_model_name() -> str:
    return os.getenv("OPENAI_MODEL_NAME", "gpt-4.1-mini")

def get_openai_temperature() -> float:
    try:
        return float(os.getenv("OPENAI_TEMPERATURE", "0.3"))
    except ValueError:
        return 0.3

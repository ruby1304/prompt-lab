# src/config.py
from __future__ import annotations

import os
from dotenv import load_dotenv

# 加载 .env
load_dotenv()

def get_openai_model_name() -> str:
    model = os.getenv("OPENAI_MODEL_NAME")
    if not model:
        raise EnvironmentError(
            "OPENAI_MODEL_NAME environment variable is required to select an OpenAI model"
        )
    return model

def get_openai_temperature() -> float:
    try:
        return float(os.getenv("OPENAI_TEMPERATURE", "0.3"))
    except ValueError:
        return 0.3

"""Settings loaded from the environment, with a small .env reader (no extra dependency)."""
from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent


def load_dotenv(path: Path = ROOT / ".env") -> None:
    if not path.exists():
        return
    for line in path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        os.environ.setdefault(key.strip(), value.strip().strip('"').strip("'"))


@dataclass(frozen=True)
class Settings:
    base_url: str
    api_key: str
    model: str
    price_input_per_m: float
    price_output_per_m: float

    @property
    def configured(self) -> bool:
        return bool(self.base_url and self.model)


def get_settings() -> Settings:
    load_dotenv()
    return Settings(
        base_url=os.environ.get("LLM_BASE_URL", "").rstrip("/"),
        api_key=os.environ.get("LLM_API_KEY", ""),
        model=os.environ.get("LLM_MODEL", ""),
        price_input_per_m=float(os.environ.get("PRICE_INPUT_PER_M", "0") or 0),
        price_output_per_m=float(os.environ.get("PRICE_OUTPUT_PER_M", "0") or 0),
    )

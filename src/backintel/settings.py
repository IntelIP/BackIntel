"""Runtime configuration. Values come from the environment (Doppler in practice); no .env files."""

from __future__ import annotations

import os
from dataclasses import dataclass, field
from pathlib import Path

DEFAULT_MODEL = "openrouter/openai/gpt-6-luna"
DEFAULT_JUDGE_MODEL = "openrouter/anthropic/claude-haiku-5.5"


def repo_root() -> Path:
    return Path(__file__).resolve().parents[2]


@dataclass(frozen=True)
class Settings:
    data_dir: Path
    model: str
    judge_model: str
    sandbox: str  # "docker" or "subprocess"
    langsmith_project: str
    extra: dict[str, str] = field(default_factory=dict)

    @classmethod
    def from_env(cls, env: dict[str, str] | None = None) -> Settings:
        env = dict(os.environ if env is None else env)
        return cls(
            data_dir=Path(env.get("BACKINTEL_DATA_DIR") or repo_root() / "data").resolve(),
            model=env.get("BACKINTEL_MODEL") or DEFAULT_MODEL,
            judge_model=env.get("BACKINTEL_JUDGE_MODEL") or DEFAULT_JUDGE_MODEL,
            sandbox=env.get("BACKINTEL_SANDBOX") or "docker",
            langsmith_project=env.get("LANGSMITH_PROJECT") or "backintel-v2-dev",
        )

    @property
    def raw_dir(self) -> Path:
        return self.data_dir / "raw"

    @property
    def canonical_dir(self) -> Path:
        return self.data_dir / "canonical"

    @property
    def stores_dir(self) -> Path:
        return self.data_dir / "stores"

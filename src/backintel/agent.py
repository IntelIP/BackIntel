"""Assemble the BackIntel analyst: one Deep Agents lead, no sub-agents, four domain tools.

Sub-agents are added only when a LangSmith trace shows a specific failure and a before/after
experiment improves the score (owner decision, 2026-11-09). Number checking stays in code.
"""

from __future__ import annotations

import hashlib
from pathlib import Path

from deepagents import (
    FilesystemPermission,
    HarnessProfile,
    create_deep_agent,
    register_harness_profile,
)
from deepagents._models import get_model_identifier, get_model_provider
from deepagents.backends import FilesystemBackend
from langchain.agents.structured_output import ToolStrategy
from langchain_core.language_models import BaseChatModel

from backintel.answer_validation import FinishRepeatedReadMiddleware, answer_schema
from backintel.sandbox import PythonSandbox
from backintel.stores.base import Store
from backintel.tools import build_tools

AGENT_FILES = Path(__file__).resolve().parent / "agent_files"
# Built-ins the analyst does not need: it cannot write files, has no shell, and has no subagents.
EXCLUDED_BUILTINS = frozenset({"execute", "write_file", "edit_file", "task"})
# Skill directories: common skills plus the one matching the store kind.
STORE_SKILLS = {
    "sqlite": "sqlite",
    "lake-parquet": "duckdb",
    "lake-iceberg": "duckdb",
    "postgres": "postgres",
    "files": "files",
    "clickhouse": "clickhouse",
    "ferretdb": "ferretdb",
}


def skill_sources(store: Store) -> list[str]:
    kinds = [part.kind for part in store.parts.values()] if store.kind == "multi" else [store.kind]
    return [f"/skills/by_store/{STORE_SKILLS.get(kind, kind)}/" for kind in dict.fromkeys(kinds)]


def method_version(root: Path = AGENT_FILES) -> str:
    """Hash of the prompt and skills; recorded on every run so experiments are comparable."""
    digest = hashlib.sha256()
    for path in sorted(root.rglob("*.md")):
        digest.update(str(path.relative_to(root)).encode())
        digest.update(path.read_bytes())
    return digest.hexdigest()[:12]


def system_prompt(store: Store, root: Path = AGENT_FILES) -> str:
    return (root / "lead.md").read_text().format(store_id=store.id, query_language=store.query_language)


def build_agent(model: BaseChatModel, store: Store, sandbox: PythonSandbox, *, root: Path = AGENT_FILES):
    identifier, provider = get_model_identifier(model), get_model_provider(model)
    key = f"{provider}:{identifier}" if provider and identifier else identifier
    if key:
        register_harness_profile(key, HarnessProfile(excluded_tools=EXCLUDED_BUILTINS))
    return create_deep_agent(
        model=model,
        tools=build_tools(store, sandbox),
        system_prompt=system_prompt(store, root),
        backend=FilesystemBackend(root_dir=root, virtual_mode=True),
        skills=["/skills/common/", *skill_sources(store)],
        permissions=[FilesystemPermission(operations=["write"], paths=["/**"], mode="deny")],
        response_format=ToolStrategy(answer_schema(store, sandbox)),
        middleware=[FinishRepeatedReadMiddleware()],
        name="backintel-analyst",
    )

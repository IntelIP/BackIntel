"""Opt-in analytical coding specialist; the benchmark analyst remains independent.

The orchestrator owns the brief, sources, model and limits. The specialist can revise
programs and artifacts inside one Docker workspace, never its own runtime or release.
"""

from __future__ import annotations

import asyncio
import base64
import hashlib
import json
import math
import time
import uuid
from datetime import UTC, datetime
from pathlib import Path
from typing import Literal

from deepagents import FilesystemPermission, HarnessProfile, create_deep_agent, register_harness_profile
from deepagents._models import get_model_identifier, get_model_provider
from deepagents.backends import FilesystemBackend
from deepagents.middleware.filesystem import FilesystemMiddleware
from langchain.agents.middleware import ModelCallLimitMiddleware, ToolCallLimitMiddleware
from langchain.agents.structured_output import ToolStrategy
from langchain_core.language_models import BaseChatModel
from langchain_core.tools import ToolException, tool
from pydantic import BaseModel, ConfigDict, Field, model_validator

from backintel.agent import AGENT_FILES, EXCLUDED_BUILTINS, method_version, skill_sources
from backintel.analysis_sandbox import AnalysisSandbox
from backintel.bench.usage import PlanRunBudget, RunBudget, UsageTracker
from backintel.sandbox import PythonSandbox
from backintel.stores.base import Store
from backintel.tools import build_tools


class AnalysisBrief(BaseModel):
    """Business context supplied by the orchestrator, not inferred from hidden eval truth."""

    model_config = ConfigDict(extra="forbid")
    objective: str = Field(min_length=1, max_length=8000)
    business_context: str = Field(default="", max_length=12000)
    audience: str = Field(default="Business owner", max_length=500)
    metric_definitions: dict[str, str] = Field(default_factory=dict)
    time_window: str = Field(default="Use the assigned data's documented coverage", max_length=2000)
    known_limitations: list[str] = Field(default_factory=list)
    required_outputs: list[str] = Field(default_factory=lambda: ["report", "charts", "workbook"])


class AnalysisCompletion(BaseModel):
    model_config = ConfigDict(extra="forbid")
    status: Literal["completed", "cannot_answer"]
    summary: str = Field(min_length=1)
    reason: str | None = None
    caveats: list[str] = Field(default_factory=list)

    @model_validator(mode="after")
    def explain_refusal(self):
        if self.status == "cannot_answer" and not (self.reason or "").strip():
            raise ValueError("A refusal must explain the missing inputs or unresolved constraint.")
        return self


def _safe_text(text: str, env: dict[str, str]) -> str:
    # Source access stays inside Docker; do not return connection secrets in tool traces.
    for key, value in env.items():
        if len(value) >= 8 and any(
            part in key.upper() for part in ("PASSWORD", "TOKEN", "SECRET", "DSN", "URI")
        ):
            text = text.replace(value, "[redacted source credential]")
    return text


def _source_identity(store: Store, run_id: str) -> dict:
    """Hash local assigned files once; remote sources are explicitly live, not snapshots."""
    digest = hashlib.sha256()
    paths = [Path(p) for p in store.python_mounts()]
    count = 0
    for root in sorted(paths):
        files = sorted(root.rglob("*")) if root.is_dir() else [root]
        for path in files:
            if path.is_file():
                digest.update(str(path).encode())
                with path.open("rb") as stream:
                    digest.update(hashlib.file_digest(stream, "sha256").digest())
                count += 1
    snapshot = f"sha256:{digest.hexdigest()}" if count else f"live-observation:{run_id}"
    return {
        "id": "assigned",
        "snapshot": snapshot,
        "description": f"{store.id}; {count} assigned local files hashed. "
        "Remote services, if connected, are live observations, not immutable snapshots.",
    }


def _same_cells(actual, expected) -> bool:
    if isinstance(actual, list) and isinstance(expected, list):
        return len(actual) == len(expected) and all(
            _same_cells(a, b) for a, b in zip(actual, expected, strict=True)
        )
    if type(actual) in (int, float) and type(expected) in (int, float):
        return math.isclose(actual, expected, rel_tol=1e-9, abs_tol=1e-8)
    return type(actual) is type(expected) and actual == expected


def reproduce_report(spec: dict, store: Store, sandbox: AnalysisSandbox) -> dict:
    """Execute citations and reconcile tables. This is reproducibility, not oracle truth."""
    observed, checked = {}, []
    for evidence in spec["evidence"]:
        if evidence["kind"] in ("sql", "query"):
            result = store.query(evidence["code"], max_rows=10001)
            if result.truncated:
                raise ValueError(f"Evidence {evidence['id']} exceeds the report row limit.")
            observed[evidence["id"]] = result.to_dict()
        else:
            result = sandbox.run_python(evidence["code"])
            if result.exit_code != 0:
                raise ValueError(f"Evidence {evidence['id']} failed: {result.stderr[:1000]}")
            try:
                observed[evidence["id"]] = json.loads(result.stdout)
            except json.JSONDecodeError:
                observed[evidence["id"]] = None
        checked.append(evidence["id"])
    for table in spec["tables"]:
        if not any(
            isinstance(observed.get(key), dict)
            and observed[key].get("columns") == table["columns"]
            and _same_cells(observed[key].get("rows"), table["rows"])
            for key in table["evidence_ids"]
        ):
            raise ValueError(
                f"Table {table['id']} does not match a cited result. Python evidence must print "
                "one JSON object with columns and rows; use aggregated, bounded tables."
            )
    return {
        "executed_evidence": checked,
        "tables_reproduced": [t["id"] for t in spec["tables"]],
        "scope": "Executable table reproduction; independent business truth is evaluated separately.",
    }


def build_analysis_tools(store: Store, sandbox: AnalysisSandbox, identity: dict, rendered: dict) -> list:
    from backintel.artifacts import validate_report

    def checked(operation, *args):
        try:
            return operation(*args)
        except (ValueError, OSError) as error:
            raise ToolException(_safe_text(str(error), sandbox.env)) from error

    def execute(result) -> str:
        return _safe_text(json.dumps(result.to_dict()), sandbox.env)

    @tool
    def run_shell(command: str) -> str:
        """Run bash inside the isolated analytical container, never on the host.

        /workspace persists between commands. Sources and /docs are read-only. /artifacts
        holds deliverables. Use preinstalled tools only; there is no public network.
        Returns bounded stdout/stderr, exit code, elapsed time and timeout status.
        """
        return execute(sandbox.run_shell(command))

    @tool
    def run_python(code: str) -> str:
        """Run Python in the persistent Docker workspace with assigned read-only sources.

        Use installed analytical/plotting packages. Save programs in /workspace; save
        final outputs through render_report. Print bounded results, not entire raw datasets.
        """
        return execute(sandbox.run_python(code))

    @tool
    def write_analysis_file(path: str, content: str) -> str:
        """Write a UTF-8 script or specification in /workspace or /artifacts (up to 256 KiB)."""
        return execute(checked(sandbox.write_file, path, content))

    @tool
    def read_analysis_file(path: str) -> str:
        """Read a bounded UTF-8 workspace/artifact file. Use shell tools for source/doc discovery."""
        return _safe_text(checked(sandbox.read_file, path), sandbox.env)

    @tool
    def inspect_chart(path: str) -> list[dict]:
        """Inspect an actual PNG chart from /artifacts, not an invented chart description.

        Returns the image to the model. Maximum 2 MiB. Check layout/labels/units and
        supported conclusions; source numerical correctness still requires calculations.
        """
        if not path.startswith("/artifacts/") or not path.lower().endswith(".png"):
            raise ToolException("Inspect a PNG under /artifacts.")
        data = checked(sandbox.read_bytes, path)
        if not data.startswith(b"\x89PNG\r\n\x1a\n"):
            raise ToolException("The artifact is not a PNG image.")
        return [
            {
                "type": "image_url",
                "image_url": {"url": "data:image/png;base64," + base64.b64encode(data).decode()},
            }
        ]

    @tool
    def render_report(spec_path: str) -> str:
        """Render the report specification in a workspace JSON file into /artifacts.

        Read /docs/artifact-contract.md first. Metrics, charts and sheets share table IDs.
        Host-owned run/source identity overrides supplied identity. This checks structure
        and consistency, not independent business truth. Fix reported errors and retry.
        """
        # A failed revision must not publish an earlier successful specification.
        rendered.clear()
        spec = checked(json.loads, checked(sandbox.read_file, spec_path))
        if not isinstance(spec, dict):
            raise ToolException("Report specification must be a JSON object.")
        spec.update(identity)
        spec = checked(validate_report, spec)
        try:
            reproduction = reproduce_report(spec, store, sandbox)
        except Exception as error:
            raise ToolException(str(error)) from error
        prepared = sandbox.write_file("/workspace/render-spec.json", json.dumps(spec, allow_nan=False))
        if prepared.exit_code != 0:
            raise ToolException(prepared.stderr)
        result = sandbox.run_python(
            "import json, shutil\nfrom backintel.artifacts import render_report\n"
            "spec=json.load(open('/workspace/render-spec.json'))\n"
            "shutil.rmtree('/artifacts/report', ignore_errors=True)\n"
            "manifest=render_report(spec, '/artifacts/report')\n"
            "print(json.dumps(manifest))"
        )
        if result.exit_code == 0:
            rendered.update(
                {
                    "spec": spec,
                    "reproduction": reproduction,
                    "spec_sha256": hashlib.sha256(json.dumps(spec, sort_keys=True).encode()).hexdigest(),
                }
            )
        return execute(result)

    # Reuse native read-only schema/query tools; replace the old ephemeral Python tool.
    domain = [t for t in build_tools(store, PythonSandbox("docker")) if t.name != "run_python"]
    selected = [
        *domain,
        run_shell,
        run_python,
        write_analysis_file,
        read_analysis_file,
        inspect_chart,
        render_report,
    ]
    for item in selected:
        item.handle_tool_error = True
    return selected


def build_analysis_agent(
    model: BaseChatModel,
    store: Store,
    sandbox: AnalysisSandbox,
    identity: dict,
    rendered: dict,
    *,
    max_model_calls: int = 24,
    max_tool_calls: int = 50,
):
    """One specialist graph, callable by an orchestrator without changing the baseline."""
    if min(max_model_calls, max_tool_calls) < 1:
        raise ValueError("Model and tool limits must be positive.")
    identifier, provider = get_model_identifier(model), get_model_provider(model)
    key = f"{provider}:{identifier}" if provider and identifier else identifier
    if key:
        register_harness_profile(key, HarnessProfile(excluded_tools=EXCLUDED_BUILTINS))
    backend = FilesystemBackend(root_dir=AGENT_FILES, virtual_mode=True)
    prompt = (AGENT_FILES / "analysis.md").read_text()
    prompt += "\n\nHost context:\n" + json.dumps(
        {
            **identity,
            "store": store.id,
            "query_language": store.query_language,
            "source_access": store.python_environment().get("BACKINTEL_STORE_NOTE", ""),
            "limits": sandbox.resource_usage()["profile"],
        }
    )
    return create_deep_agent(
        model=model,
        tools=build_analysis_tools(store, sandbox, identity, rendered),
        system_prompt=prompt,
        backend=backend,
        skills=["/skills/analysis/", "/skills/common/", *skill_sources(store)],
        permissions=[FilesystemPermission(operations=["write"], paths=["/**"], mode="deny")],
        middleware=[
            FilesystemMiddleware(backend=backend, tools=["ls", "read_file", "glob", "grep"]),
            ModelCallLimitMiddleware(run_limit=max_model_calls, exit_behavior="error"),
            ToolCallLimitMiddleware(run_limit=max_tool_calls, exit_behavior="error"),
        ],
        response_format=ToolStrategy(AnalysisCompletion),
        name="backintel-analysis-specialist",
    )


async def run_analysis(
    brief: AnalysisBrief,
    *,
    model: BaseChatModel,
    model_id: str,
    store: Store,
    output: Path,
    profile: str = "analysis",
    budget: RunBudget | PlanRunBudget | None = None,
    max_model_calls: int = 24,
    max_tool_calls: int = 50,
    timeout_s: int = 900,
    scripted: bool = False,
) -> dict:
    """Execute one bounded brief and persist its record and collected artifact bundle.

    `scripted` identifies offline integration runs; they never establish model capability.
    The caller owns closing the Store. CLI callers supply a finite inference budget.
    """
    from backintel.artifacts import verify_bundle
    from backintel.bench.run import git_sha, source_version

    if not scripted and budget is None:
        raise ValueError("Live analysis requires an explicit finite inference budget.")
    if not scripted and isinstance(budget, PlanRunBudget) != model_id.startswith("chatgpt-plan/"):
        raise ValueError("The admission budget must match the model's billing mode.")
    if scripted:
        from langchain_core.language_models.fake_chat_models import FakeMessagesListChatModel

        if not isinstance(model, FakeMessagesListChatModel):
            raise ValueError("Only an offline fake model may be labelled as scripted integration.")
    output = Path(output)
    if output.exists():
        raise ValueError("Use a new output directory; prior runs are immutable.")
    output.mkdir(parents=True, mode=0o700)
    run_id = "run-" + uuid.uuid4().hex
    identity = {
        "run_id": run_id,
        "sources": [_source_identity(store, run_id)],
        "candidate": source_version(),
        "created_at": datetime.now(UTC).isoformat(),
    }
    usage = UsageTracker(budget)
    record = {
        "run_id": identity["run_id"],
        "brief": brief.model_dump(),
        "model": model_id,
        "method_version": method_version(),
        "git_sha": git_sha(),
        "source_version": identity["candidate"],
        "execution": "scripted integration; not a model evaluation" if scripted else "model",
        "billing_mode": "chatgpt_plan" if isinstance(budget, PlanRunBudget) else "api",
        "status": "failed",
        "artifacts": None,
    }
    rendered, state = {}, {}
    started = time.monotonic()
    sandbox = AnalysisSandbox(
        env=store.python_environment(),
        mounts=store.python_mounts(),
        network=store.sandbox_network(),
        profile=profile,
        timeout_s=timeout_s,
    )
    try:
        with sandbox:
            graph = build_analysis_agent(
                model,
                store,
                sandbox,
                identity,
                rendered,
                max_model_calls=max_model_calls,
                max_tool_calls=max_tool_calls,
            )
            async with asyncio.timeout(timeout_s):
                async for update in graph.astream(
                    {"messages": [{"role": "user", "content": brief.model_dump_json()}]},
                    config={
                        "callbacks": [usage],
                        # Middleware introduces graph steps; the explicit model/tool
                        # limits enforce workload admission, not this framework fuse.
                        "recursion_limit": 12 * max_model_calls + 50,
                        "metadata": {
                            "backintel_run_id": identity["run_id"],
                            "model": model_id,
                            "source_version": identity["candidate"],
                            "scripted": scripted,
                            "billing_mode": record["billing_mode"],
                        },
                    },
                    stream_mode="values",
                ):
                    state = update
            completion = AnalysisCompletion.model_validate(state.get("structured_response"))
            record["completion"] = completion.model_dump()
            if completion.status == "completed":
                if not rendered:
                    raise ValueError("The specialist claimed completion without a successful render_report.")
                record["render_spec_sha256"] = rendered["spec_sha256"]
                record["reproduction"] = rendered["reproduction"]
            else:
                record["status"] = "cannot_answer"
            record["resources"] = sandbox.resource_usage()
        if completion.status == "completed":
            # The agent has a shell and can forge checksums/HTML. Publish only a clean
            # deterministic render of the host-retained spec, without source credentials
            # or agent-controlled files. Never serve arbitrary shell output as trusted HTML.
            remaining = int(timeout_s - (time.monotonic() - started))
            if remaining < 1:
                raise TimeoutError("Whole-run deadline reached before final artifact rendering.")
            with AnalysisSandbox(profile=profile, timeout_s=min(remaining, 180)) as publisher:
                saved = publisher.write_file("/workspace/spec.json", json.dumps(rendered["spec"]))
                if saved.exit_code:
                    raise ValueError("Could not stage the report for publication.")
                result = publisher.run_python(
                    "import json\nfrom backintel.artifacts import render_report, verify_bundle\n"
                    "render_report(json.load(open('/workspace/spec.json')), '/artifacts/report')\n"
                    "verify_bundle('/artifacts/report')\nprint('bundle verified')"
                )
                if result.exit_code:
                    raise ValueError(f"Final rendering failed: {result.stderr[:1000]}")
                publisher.export_artifacts(output / "artifacts")
                record["render_resources"] = publisher.resource_usage()
            record["artifacts"] = verify_bundle(output / "artifacts" / "report")
            record["status"] = "completed"
    except asyncio.CancelledError:
        record.update(status="cancelled", error="Run cancelled; sandbox stopped.")
        raise
    except Exception as error:
        record.update(
            status="failed", error=_safe_text(f"{type(error).__name__}: {error}", sandbox.env)[:2000]
        )
    finally:
        sandbox.close()
        record.setdefault("resources", sandbox.resource_usage())
        record["usage"] = usage.report()
        record["budget"] = budget.report() if budget else None
        record["latency_s"] = round(time.monotonic() - started, 3)
        record["messages"] = [m.model_dump(mode="json") for m in state.get("messages", [])]
        (output / "run.json").write_text(json.dumps(record, indent=2, default=str))
    return record

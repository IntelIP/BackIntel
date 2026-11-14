"""Runtime checks and a stop signal for repeated reads, independent of benchmark truth.

The persisted AnalystAnswer remains permissive so historical failures can still be graded.
Only the model's finalization schema uses these checks: LangChain returns validation errors
to the analyst for repair before accepting a final response.
"""

from __future__ import annotations

import json
import math
import re
from collections.abc import Sequence

from langchain.agents.middleware import AgentMiddleware, ModelRequest
from langchain_core.messages import AIMessage, BaseMessage, HumanMessage, SystemMessage, ToolMessage
from pydantic import model_validator

from backintel.contracts import AnalystAnswer
from backintel.sandbox import PythonSandbox
from backintel.stores.base import QueryRefused, Store
from backintel.stores.multi import DIRECTIVE, MultiStore

DOMAIN_READS = frozenset({"list_tables", "describe_table", "run_sql", "run_query", "run_python"})
NUMERIC_OUTPUT = re.compile(r"(?<![\w.])[+-]?(?:\d+(?:,\d{3})*(?:\.\d*)?|\.\d+)(?:[eE][+-]?\d+)?(?![\w.])")
FINISH_REPEATED_READ = (
    "The last three reads used identical arguments and returned the same successful result. "
    "Further identical reads add no information. Finalize using the structured answer tool now: "
    "answer if the observed data supports the requested calculation; otherwise explain the specific "
    "missing inputs with status='cannot_answer'. Do not invent a value or substitute another metric."
)


def repeated_successful_read(messages: Sequence[BaseMessage]) -> bool:
    """Recognize three consecutive identical completed reads within this question only.

    One repeat remains available for a sanity check. Changed results, failed reads, different
    work, parallel tool batches, and a new user turn reset the signal. No mutable per-agent
    counter is shared between concurrent benchmark runs.
    """
    results: dict[str, ToolMessage] = {}
    signatures = []
    for message in reversed(messages):
        if isinstance(message, HumanMessage):
            break
        if isinstance(message, ToolMessage):
            results[message.tool_call_id] = message
        elif isinstance(message, AIMessage):
            if len(message.tool_calls) != 1:
                return False
            call = message.tool_calls[0]
            result = results.get(call["id"])
            if call["name"] not in DOMAIN_READS or result is None or result.status == "error":
                return False
            try:
                payload = json.loads(result.content)
            except (TypeError, ValueError):
                return False
            if not isinstance(payload, dict) or payload.get("exit_code", 0) != 0:
                return False
            stable_result = {k: v for k, v in payload.items() if k != "elapsed_ms"}
            signatures.append(json.dumps([call["name"], call["args"], stable_result], sort_keys=True))
            if len(signatures) == 3:
                return len(set(signatures)) == 1
    return False


class FinishRepeatedReadMiddleware(AgentMiddleware):
    """Keep structured finalization available when a read loop stops making progress."""

    @staticmethod
    def _request(request: ModelRequest) -> ModelRequest:
        if not repeated_successful_read(request.messages):
            return request
        blocks = list(request.system_message.content_blocks) if request.system_message else []
        blocks.append({"type": "text", "text": FINISH_REPEATED_READ})
        # ToolStrategy adds its finalization tool after this list. It still validates and
        # retries malformed answers; the middleware never assigns a refusal or a value.
        return request.override(tools=[], system_message=SystemMessage(content=blocks))

    def wrap_model_call(self, request, handler):
        return handler(self._request(request))

    async def awrap_model_call(self, request, handler):
        return await handler(self._request(request))


def validate_answer_shape(answer: AnalystAnswer) -> None:
    """Check the answer contract without consulting a question's hidden expected result."""
    fields = {"value": answer.value, "text": answer.text, "items": answer.items, "rows": answer.rows}
    if answer.status == "cannot_answer":
        if not answer.reason or not answer.reason.strip():
            raise ValueError("A declined answer must explain which required information is missing.")
        if any(value not in (None, [], "") for value in fields.values()):
            raise ValueError("A declined answer must not also return an unsupported result.")
        return
    expected_field = {
        "number": "value",
        "text": "text",
        "ranked_list": "items",
        "table": "rows",
        "report": "rows",
    }.get(answer.answer_type)
    if expected_field is None or fields[expected_field] is None:
        raise ValueError("An answered response must populate the field matching its answer_type.")
    if any(value is not None for name, value in fields.items() if name != expected_field):
        raise ValueError("Populate only the value field matching answer_type.")
    if answer.value is not None and not math.isfinite(answer.value):
        raise ValueError("A numeric answer must be finite.")
    if answer.answer_type == "report":
        names = []
        for row in answer.rows or []:
            metric = row.get("metric")
            if not isinstance(metric, str) or not metric.strip() or "value" not in row or "unit" not in row:
                raise ValueError("Each report row requires a nonempty metric identifier, value, and unit.")
            names.append(" ".join(metric.split()).casefold())
        if not names or len(names) != len(set(names)):
            raise ValueError("Report metric identifiers must be unique: return exactly one row per metric.")
    if not answer.evidence:
        raise ValueError("An answered response must cite the exact executable evidence.")


def validate_answer_evidence(answer: AnalystAnswer, store: Store, sandbox: PythonSandbox) -> None:
    """Execute every cited item under the same read-only bindings used by analysis tools.

    Numeric answers must also appear in executed output, allowing display rounding.
    This does not establish correctness or lineage: independent evaluators still check
    reference values, missing/extra requested metrics, and unsupported claims.
    """
    problems = []
    numeric_output = []
    for index, item in enumerate(answer.evidence, 1):
        try:
            if item.kind == "python":
                result = sandbox.run(
                    item.code,
                    env=store.python_environment(),
                    mounts=store.python_mounts(),
                    network=store.sandbox_network(),
                )
                if result.exit_code != 0:
                    problems.append(f"Evidence {index}: program failed: {result.stderr[-300:]}")
                else:
                    numeric_output.extend(NUMERIC_OUTPUT.findall(result.stdout))
            else:
                code = item.code
                if isinstance(store, MultiStore):
                    directive = DIRECTIVE.match(code)
                    if item.store is not None:
                        store.resolve(item.store)
                        if directive and directive.group(1) != item.store:
                            raise QueryRefused("Evidence store disagrees with its SQL store directive.")
                    if directive is None:
                        store.resolve(item.store)
                        code = f"-- store: {item.store}\n{code}"
                elif item.store is not None and item.store != store.id:
                    raise QueryRefused("Evidence names a store that is not connected.")
                result = store.query(code)
                numeric_output.extend(cell for row in result.rows for cell in row)
        except (QueryRefused, NotImplementedError) as error:
            problems.append(f"Evidence {index}: query failed: {str(error)[:300]}")
    if problems:
        raise ValueError("; ".join(problems))
    if answer.status == "answered" and answer.answer_type == "number":
        for cell in numeric_output:
            if cell is None or isinstance(cell, bool):
                continue
            try:
                value = float(cell.replace(",", "") if isinstance(cell, str) else cell)
            except (ValueError, TypeError, OverflowError):
                continue
            # Same display-rounding allowance as the existing independent evidence check.
            if math.isfinite(value) and math.isclose(value, answer.value, rel_tol=1e-4, abs_tol=0.011):
                return
        raise ValueError(
            "Cited evidence executes but does not output the reported numeric value in its "
            "reported units. Include any unit conversion or rounding in the executable "
            "evidence and output the final value."
        )


def answer_schema(store: Store, sandbox: PythonSandbox) -> type[AnalystAnswer]:
    """Bind runtime-only validation to the native structured-output retry mechanism."""

    class VerifiedAnalystAnswer(AnalystAnswer):
        """Return unique metrics, executable evidence and numeric values present in its output."""

        @model_validator(mode="after")
        def verify_before_returning(self):
            validate_answer_shape(self)
            validate_answer_evidence(self, store, sandbox)
            return self

    return VerifiedAnalystAnswer

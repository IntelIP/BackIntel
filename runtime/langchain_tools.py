"""Expose one permitted saved workflow as a LangChain tool; no model is created here."""
from langchain_core.tools import ToolException, tool

from runtime.workflow_client import WorkflowClientError, saved_workflow_runner


def saved_workflow_tool(client, workflow_version, *, input_ref=None, wait_seconds=300):
    """Bind credentials and workflow outside model arguments; retain the full API receipt."""
    run = saved_workflow_runner(client, workflow_version, input_ref=input_ref, wait_seconds=wait_seconds)

    @tool(response_format='content_and_artifact')
    def run_backintel_workflow() -> tuple[dict, dict]:
        """Run or resume the approved retail workflow. Return its checked answer and evidence.

        This tool cannot change the objective, source, permissions, or spending limits.
        A queued/running response is unfinished; retry the same tool to recover it.
        Only a succeeded response contains an accepted answer. Do not invent missing results.
        """
        try:
            return run()
        except WorkflowClientError as error:
            raise ToolException(str(error)) from None

    run_backintel_workflow.handle_tool_error = True
    return run_backintel_workflow

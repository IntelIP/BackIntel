"""Optional Agno adapter; the application retains full receipts outside model messages."""
import json

from agno.tools.function import Function

from runtime.workflow_client import WorkflowClientError, saved_workflow_runner


def saved_workflow_tool(client, workflow_version, *, receipts, input_ref=None, wait_seconds=300):
    """Bind one permitted workflow and a caller-owned receipt list outside model arguments."""
    run = saved_workflow_runner(client, workflow_version, input_ref=input_ref, wait_seconds=wait_seconds)

    def run_backintel_workflow() -> str:
        """Run or resume the approved retail workflow and return its checked answer and evidence.

        Only succeeded means an accepted answer. Queued or running means unfinished.
        Cannot change the objective, source, permissions, or spending limits.
        """
        try:
            content, receipt = run()
        except WorkflowClientError as error:
            raise RuntimeError(str(error)) from None
        receipts.append(receipt)
        return json.dumps(content)

    return Function(name='run_backintel_workflow', entrypoint=run_backintel_workflow,
                    description=run_backintel_workflow.__doc__, cache_results=False)

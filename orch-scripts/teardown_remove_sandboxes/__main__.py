from cloudshell.workflow.orchestration.sandbox import Sandbox
from cloudshell.workflow.orchestration.teardown.default_teardown_orchestrator import DefaultTeardownWorkflow
from tear_down_sandboxes import tear_down_sandboxes_flow

sandbox = Sandbox()

DefaultTeardownWorkflow().register(sandbox)
sandbox.workflow.add_to_teardown(tear_down_sandboxes_flow, None)
sandbox.execute_teardown()

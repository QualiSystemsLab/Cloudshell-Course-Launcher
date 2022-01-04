from cloudshell.workflow.orchestration.setup.default_setup_orchestrator import DefaultSetupWorkflow
from cloudshell.workflow.orchestration.sandbox import Sandbox
from launch_sandboxes import launch_sandboxes_flow

sandbox = Sandbox()

DefaultSetupWorkflow().register(sandbox)
sandbox.workflow.on_configuration_ended(launch_sandboxes_flow, None)
sandbox.execute_setup()

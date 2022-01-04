from cloudshell.workflow.orchestration.sandbox import Sandbox
from cloudshell.helpers.scripts.cloudshell_dev_helpers import attach_to_cloudshell_as
from credentials import credentials
from extend_sandboxes import extend_sandboxes_flow

LIVE_SANDBOX_ID = "25d3b09a-5b1a-4433-8688-5311044a64ec"

attach_to_cloudshell_as(user=credentials["user"],
                        password=credentials["password"],
                        domain=credentials["domain"],
                        reservation_id=LIVE_SANDBOX_ID,
                        server_address=credentials['server'])

sandbox = Sandbox()
extend_sandboxes_flow(sandbox=sandbox, components=None)

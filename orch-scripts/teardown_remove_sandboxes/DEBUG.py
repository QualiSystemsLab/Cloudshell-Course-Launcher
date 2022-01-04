from cloudshell.helpers.scripts.cloudshell_dev_helpers import \
    attach_to_cloudshell_as
from cloudshell.workflow.orchestration.sandbox import Sandbox
from credentials import credentials
from tear_down_sandboxes import tear_down_sandboxes_flow

LIVE_SANDBOX_ID = "741e5d0d-a518-427a-a51f-6786c59f8347"

attach_to_cloudshell_as(
    user=credentials["user"],
    password=credentials["password"],
    domain=credentials["domain"],
    reservation_id=LIVE_SANDBOX_ID,
    server_address=credentials["server"],
)

sandbox = Sandbox()
tear_down_sandboxes_flow(sandbox=sandbox, components=None)

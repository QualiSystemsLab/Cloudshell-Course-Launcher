from cloudshell.helpers.scripts.cloudshell_dev_helpers import attach_to_cloudshell_as
from cloudshell.workflow.orchestration.sandbox import Sandbox
from credentials import credentials
from launch_sandboxes import launch_sandboxes_flow

LIVE_SANDBOX_ID = "f7216ce4-cebc-4928-bb25-20841f8b9d62"

attach_to_cloudshell_as(
    user=credentials["user"],
    password=credentials["password"],
    domain=credentials["domain"],
    reservation_id=LIVE_SANDBOX_ID,
    server_address=credentials["server"],
)

sandbox = Sandbox()
launch_sandboxes_flow(sandbox=sandbox, components=None)

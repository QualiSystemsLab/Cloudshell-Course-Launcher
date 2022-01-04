import time

import SB_GLOBALS as sb_globals
from cloudshell.api.cloudshell_api import CloudShellAPISession
from cloudshell.workflow.orchestration.sandbox import Sandbox
from helper_code.execute_async_helper import execute_commands_async
from helper_code.SandboxReporter import SandboxReporter


def _sync_sandboxes_wrapper(api, res_id, reporter, targeted_components_list):
    """
    function to be passed to threading implementation
    :param CloudShellAPISession api:
    :param str res_id:
    :param str service_name:
    :return:
    """
    # SYNC REMAINING TIME
    _, sync_sandbox_exceptions = execute_commands_async(
        api=api,
        res_id=res_id,
        target_components_list=targeted_components_list,
        target_type="Service",
        command_name=sb_globals.SYNC_REMAINING_TIME_COMMAND,
    )
    if sync_sandbox_exceptions:
        failed_sandboxes = [result[0] for result in sync_sandbox_exceptions]
        err_msg = "Failed Sandbox Extensions: {}".format(failed_sandboxes)
        reporter.err_out(err_msg)
        return failed_sandboxes
    reporter.sb_warn_print("Parent Sandbox time synced up with child sandboxes.")
    return None


# ========== Primary Function ==========
def extend_sandboxes_flow(sandbox, components=None):
    """
    Functions passed into orchestration flow MUST have (sandbox, components) signature
    :param Sandbox sandbox:
    :param components
    :return:
    """
    api = sandbox.automation_api
    res_id = sandbox.id
    logger = sandbox.logger
    reporter = SandboxReporter(api, res_id, logger)
    duration_minutes_input = sandbox.get_user_param(sb_globals.EXTEND_SANDBOXES_DURATION_PARAM)
    duration_minutes = int(duration_minutes_input)

    reporter.warn_out("Extending Parent Launcher Sandbox {} minutes".format(duration_minutes))
    extend_parent_res = api.ExtendReservation(reservationId=res_id, minutesToAdd=duration_minutes)
    time.sleep(10)

    # GET CURRENT SERVICES ON CANVAS
    all_services = api.GetReservationDetails(res_id).ReservationDescription.Services
    curr_services = [s for s in all_services if s.ServiceName == sb_globals.SANDBOX_CONTROLLER_MODEL]

    def _is_sb_id(s):
        attrs = s.Attributes
        sb_id_val = [attr for attr in attrs if attr.Name == sb_globals.SANDBOX_ID_ATTR][0].Value
        if sb_id_val:
            return True
        else:
            return False

    services_with_populated_sb_id = [s.Alias for s in curr_services if _is_sb_id(s)]
    sorted_service_names = sorted(services_with_populated_sb_id)

    # ASYNC flow
    reporter.warn_out("Starting extension syncing with children sandboxes...")
    failed_extensions = _sync_sandboxes_wrapper(api, res_id, reporter, sorted_service_names)
    if failed_extensions:
        exc_msg = "Extensions failed for: {}".format(failed_extensions)
        reporter.err_out(exc_msg)
        raise Exception(exc_msg)

    reporter.success_out("ALL Sandboxes Extended SUCCESSFULLY")

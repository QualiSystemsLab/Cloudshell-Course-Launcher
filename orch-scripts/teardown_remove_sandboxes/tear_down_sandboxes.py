import SB_GLOBALS as sb_globals
from cloudshell.api.cloudshell_api import (
    AttributeNameValue,
    CloudShellAPISession,
    InputNameValue,
)
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
def tear_down_sandboxes_flow(sandbox, components=None):
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

    # VALIDATE GLOBAL INPUTS
    global_inputs_dict = sandbox.global_inputs

    is_async_deploy = global_inputs_dict.get(
        sb_globals.DEPLOY_CONCURRENTLY_BOOL_INPUT, True
    )
    if isinstance(is_async_deploy, str):
        if is_async_deploy.lower() in ["true", "y", "yes", "[any]", "any"]:
            is_async_deploy = True
        else:
            is_async_deploy = False

    # type conversion for deploy batch count
    concurrent_deploy_limit = global_inputs_dict.get(
        sb_globals.CONCURRENT_DEPLOY_LIMIT_INPUT, 0
    )
    if isinstance(concurrent_deploy_limit, str):
        if concurrent_deploy_limit.lower() in [
            "false",
            "f",
            "off",
            "no",
            "n",
            "[any]",
            "any",
        ]:
            concurrent_deploy_limit = 0
        elif concurrent_deploy_limit.isdigit():
            concurrent_deploy_limit = int(concurrent_deploy_limit)
        else:
            exc_msg = "Concurrent Deploy Limit should be set to 'off', or set to an integer. Received: {}".format(
                concurrent_deploy_limit
            )
            reporter.err_out(exc_msg)
            raise Exception(exc_msg)

    # GET CURRENT SERVICES ON CANVAS
    all_services = api.GetReservationDetails(res_id).ReservationDescription.Services
    curr_services = [
        s for s in all_services if s.ServiceName == sb_globals.SANDBOX_CONTROLLER_MODEL
    ]

    def _is_sb_id(s):
        attrs = s.Attributes
        sb_id_val = [attr for attr in attrs if attr.Name == sb_globals.SANDBOX_ID_ATTR][
            0
        ].Value
        if sb_id_val:
            return True
        else:
            return False

    services_with_populated_sb_id = [s.Alias for s in curr_services if _is_sb_id(s)]
    sorted_service_names = sorted(services_with_populated_sb_id)

    # IF ASYNC SWITCH OFF RUN SEQUENTIALLY AND RETURN
    if not is_async_deploy:
        reporter.warn_out("Starting sequential teardown of sandboxes...")
        failed_sequential = []
        for service_name in sorted_service_names:
            try:
                api.ExecuteCommand(
                    reservationId=res_id,
                    targetName=service_name,
                    targetType="Service",
                    commandName=sb_globals.END_SANDBOX_COMMAND,
                    printOutput=True,
                )
            except Exception as e:
                failed_sequential.append(service_name)
                exc_msg = "'{}' teardown failed: '{}'".format(service_name, str(e))
                reporter.err_out(exc_msg)
        if failed_sequential:
            exc_msg = "Deployments failed for: {}".format(failed_sequential)
            reporter.err_out(exc_msg)
            raise Exception(exc_msg)
        return

    # ASYNC flow
    reporter.warn_out("Starting ASYNC teardown of sandboxes...")
    _, teardown_sandbox_exceptions = execute_commands_async(
        api=api,
        res_id=res_id,
        target_components_list=sorted_service_names,
        target_type="Service",
        command_name=sb_globals.END_SANDBOX_COMMAND,
        max_thread_count=concurrent_deploy_limit,
    )
    if teardown_sandbox_exceptions:
        failed_sandboxes = [result[0] for result in teardown_sandbox_exceptions]
        err_msg = "Failed Sandbox Teardowns: {}".format(failed_sandboxes)
        reporter.err_out(err_msg)
        raise Exception(err_msg)

    reporter.success_out("ALL Sandboxes Torn Down SUCCESSFULLY")

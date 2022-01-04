import time

import SB_GLOBALS as sb_globals
from cloudshell.api.cloudshell_api import (AttributeNameValue,
                                           CloudShellAPISession,
                                           InputNameValue)
from cloudshell.workflow.orchestration.sandbox import Sandbox
from helper_code.execute_async_helper import execute_commands_async
from helper_code.is_blueprint_in_domain import is_blueprint_in_domain
from helper_code.SandboxReporter import SandboxReporter
from helper_code.util_helpers import sandbox_name_truncater
from helper_code.validate_participants_list import validate_user_list
from set_services_on_canvas import set_services


def _validate_required_global_input(input_key, input_val):
    if not input_val:
        raise Exception("'{}' input is required by setup script automation".format(input_key))


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
def launch_sandboxes_flow(sandbox, components=None):
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
    res_details = api.GetReservationDetails(res_id).ReservationDescription
    current_sandbox_name = res_details.Name

    # VALIDATE GLOBAL INPUTS
    global_inputs_dict = sandbox.global_inputs
    target_blueprint_input_val = global_inputs_dict.get(sb_globals.TARGET_BLUEPRINT_INPUT)
    _validate_required_global_input(sb_globals.TARGET_BLUEPRINT_INPUT, target_blueprint_input_val)

    # prevent rename when re-running setup
    if target_blueprint_input_val.lower() not in current_sandbox_name.lower():
        # rename sandbox
        new_name = "{} - {}".format(current_sandbox_name, target_blueprint_input_val)
        new_name = sandbox_name_truncater(new_name)
        api.UpdateReservationName(reservationId=res_id, name=new_name)

    # inputs to be forwarded to service launcher of child sandboxes
    child_sb_globals = global_inputs_dict.get(sb_globals.GLOBAL_INPUTS_INPUT, "")
    child_sb_globals = None if child_sb_globals.lower() in ["0", ""] else child_sb_globals

    # inputs to generate users list of child sandboxes
    participants_list_input = global_inputs_dict.get(sb_globals.PARTICIPANTS_LIST_INPUT, "")
    participants_list_input = (
        None if participants_list_input.lower() in ["", "0", "none", "na", "n/a"] else participants_list_input
    )
    cloudshell_group_input = global_inputs_dict.get(sb_globals.CLOUDSHELL_GROUP_INPUT, "")
    cloudshell_group_input_exists = cloudshell_group_input and cloudshell_group_input.lower() not in ["none", "[any]", "any"]
    if not participants_list_input and not cloudshell_group_input_exists:
        exc_msg = "Either '{}' or '{}' inputs need to populated to have users".format(
            sb_globals.PARTICIPANTS_LIST_INPUT, sb_globals.CLOUDSHELL_GROUP_INPUT
        )
        reporter.err_out(exc_msg)
        raise ValueError(exc_msg)

    health_check_first_input_val = global_inputs_dict.get(sb_globals.HEALTH_CHECK_SANDBOX_INPUT)
    is_health_check = True if health_check_first_input_val.lower() in ["true", "t", "yes", "y"] else False

    async_deploy_input_val = global_inputs_dict.get(sb_globals.DEPLOY_CONCURRENTLY_BOOL_INPUT, True)
    if isinstance(async_deploy_input_val, str):
        if async_deploy_input_val.lower() in ["true", "y", "yes", "[any]", "any"]:
            async_deploy_input_val = True
        else:
            async_deploy_input_val = False

    # type conversion for deploy batch count
    concurrent_deploy_limit = global_inputs_dict.get(sb_globals.CONCURRENT_DEPLOY_LIMIT_INPUT, 0)
    if isinstance(concurrent_deploy_limit, str):
        if concurrent_deploy_limit.lower() in ["false", "f", "off", "no", "n", "[any]", "any"]:
            concurrent_deploy_limit = 0
        elif concurrent_deploy_limit.isdigit():
            concurrent_deploy_limit = int(concurrent_deploy_limit)
        else:
            exc_msg = "Concurrent Deploy Limit should be set to 'off', or set to an integer. Received: {}".format(
                concurrent_deploy_limit
            )
            reporter.err_out(exc_msg)
            raise Exception(exc_msg)

    # VALIDATE THAT BLUEPRINT NAME IS VALID AND IN DOMAIN
    if not is_blueprint_in_domain(api, target_blueprint_input_val):
        exc_msg = "Validation Failed. Check spelling and Blueprint domain for '{}'".format(target_blueprint_input_val)
        reporter.err_out(exc_msg)
        raise Exception(exc_msg)

    # VALIDATE THAT USERS ARE REAL
    if not participants_list_input:
        participants_list_set = set()
    else:
        participants_list = [x.strip() for x in participants_list_input.split(",")]
        validate_user_list(api, participants_list)
        participants_list_set = set(participants_list)

    # VALIDATE THAT GROUP IS REAL
    if not cloudshell_group_input or cloudshell_group_input.lower() == "none":
        target_group_users_set = set()
    else:
        all_groups = api.GetGroupsDetails().Groups
        target_group_search = [group for group in all_groups if group.Name == cloudshell_group_input]
        if not target_group_search:
            exc_msg = "Group '{}' does not exist in system".format(cloudshell_group_input)
            reporter.err_out(exc_msg)
            raise Exception(exc_msg)

        target_group = target_group_search[0]
        target_group_users = target_group.Users
        target_group_users_set = {user.Name for user in target_group_users}

    # COMBINE GROUP AND AD-HOC USERS
    all_users_set = participants_list_set.union(target_group_users_set)

    # GET CURRENT SERVICES ON CANVAS
    all_services = api.GetReservationDetails(res_id).ReservationDescription.Services
    curr_controller_services = [s.Alias for s in all_services if s.ServiceName == sb_globals.SANDBOX_CONTROLLER_MODEL]

    # ADD SERVICES TO CANVAS IF EMPTY ELSE USE EXISTING
    if not curr_controller_services:
        sorted_students = sorted(all_users_set)
        service_attributes = [
            AttributeNameValue(sb_globals.TARGET_BLUEPRINT_ATTR, target_blueprint_input_val),
            AttributeNameValue(sb_globals.GLOBAL_INPUTS_ATTR, child_sb_globals),
        ]
        reporter.warn_out("Adding Sandbox Controllers To Launcher Sandbox...")
        time.sleep(2)
        set_services(
            api=api,
            res_id=res_id,
            reporter=reporter,
            student_list=sorted_students,
            target_blueprint_name=target_blueprint_input_val,
            attributes_list=service_attributes,
        )
    else:
        reporter.warn_out("Services already exist, skipping add step")

    # GET CURRENT SERVICES ON CANVAS
    time.sleep(5)
    all_services = api.GetReservationDetails(res_id).ReservationDescription.Services
    curr_service_names = [s.Alias for s in all_services if s.ServiceName == sb_globals.SANDBOX_CONTROLLER_MODEL]
    sorted_service_names = sorted(curr_service_names)
    service_launch_list = sorted_service_names if not is_health_check else sorted_service_names[1:]

    # START EXECUTION
    remaining_minutes = api.GetReservationRemainingTime(res_id).RemainingTimeInMinutes
    start_sandbox_inputs = [InputNameValue(sb_globals.START_SANDBOX_DURATION_PARAM, str(int(remaining_minutes)))]
    if is_health_check:
        first_service_name = sorted_service_names[0]
        reporter.warn_out("Starting HEALTH CHECK deploy...".format(first_service_name))
        try:
            api.ExecuteCommand(
                reservationId=res_id,
                targetName=first_service_name,
                targetType="Service",
                commandName=sb_globals.START_SANDBOX_COMMAND,
                commandInputs=start_sandbox_inputs,
                printOutput=True,
            )
        except Exception as e:
            exc_msg = "HEALTH CHECK launch for blueprint '{}' FAILED: {}".format(first_service_name, str(e))
            reporter.err_out(exc_msg)
            raise Exception(exc_msg)

    # IF ASYNC SWITCH OFF RUN SEQUENTIALLY AND RETURN
    if not async_deploy_input_val:
        reporter.warn_out("Starting sequential deploy of sandboxes...")
        failed_sequential = []
        for service_name in service_launch_list:
            try:
                api.ExecuteCommand(
                    reservationId=res_id,
                    targetName=service_name,
                    targetType="Service",
                    commandName=sb_globals.START_SANDBOX_COMMAND,
                    commandInputs=start_sandbox_inputs,
                    printOutput=True,
                )
            except Exception as e:
                failed_sequential.append(service_name)
                exc_msg = "Sandbox failed for '{}'".format(service_name)
                reporter.err_out(exc_msg)
        failed_extensions = _sync_sandboxes_wrapper(api, res_id, reporter, sorted_service_names)
        if failed_sequential:
            exc_msg = "Deployments failed for: {}".format(failed_sequential)
            reporter.err_out(exc_msg)
            raise Exception(exc_msg)
        if failed_extensions:
            exc_msg = "Extensions failed for: {}".format(failed_extensions)
            reporter.err_out(exc_msg)
            raise Exception(exc_msg)
        return

    # ASYNC flow
    reporter.warn_out("Starting ASYNC deploy of sandboxes...")
    _, start_sandbox_exceptions = execute_commands_async(
        api=api,
        res_id=res_id,
        target_components_list=service_launch_list,
        target_type="Service",
        command_name=sb_globals.START_SANDBOX_COMMAND,
        command_inputs=start_sandbox_inputs,
        max_thread_count=concurrent_deploy_limit,
    )
    if start_sandbox_exceptions:
        failed_sandboxes = [result[0] for result in start_sandbox_exceptions]
        err_msg = "Failed Sandboxes: {}".format(failed_sandboxes)
        reporter.err_out(err_msg)
        raise Exception(err_msg)

    failed_extensions = _sync_sandboxes_wrapper(api, res_id, reporter, sorted_service_names)
    if failed_extensions:
        exc_msg = "Extensions failed for: {}".format(failed_extensions)
        reporter.err_out(exc_msg)
        raise Exception(exc_msg)

    reporter.success_out("ALL Sandboxes Deployed SUCCESSFULLY")

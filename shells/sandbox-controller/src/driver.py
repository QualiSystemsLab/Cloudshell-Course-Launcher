from time import sleep

from cloudshell.api.cloudshell_api import AttributeNameValue, CloudShellAPISession
from cloudshell.logging.qs_logger import get_qs_logger
from cloudshell.shell.core.driver_context import (
    AutoLoadAttribute,
    AutoLoadDetails,
    AutoLoadResource,
    CancellationContext,
    InitCommandContext,
    ResourceCommandContext,
)
from cloudshell.shell.core.resource_driver_interface import ResourceDriverInterface
from cloudshell.shell.core.session.cloudshell_session import CloudShellSessionContext
from data_model import *  # run 'shellfoundry generate' to generate data model classes
from helper_code.SandboxReporter import SandboxReporter
from helper_code.util_helpers import sandbox_name_truncater
from parse_global_inputs import get_global_input_request_from_semicolon_sep_str
from poll_sandbox import (
    poll_setup_for_provisioning_status,
    poll_teardown_for_completion_status,
)


class SandboxControllerDriver(ResourceDriverInterface):
    def __init__(self):
        """
        ctor must be without arguments, it is created with reflection at run time
        """
        pass

    def initialize(self, context):
        """
        Initialize the driver session, this function is called everytime a new instance of the driver is created
        This is a good place to load and cache the driver configuration, initiate sessions etc.
        :param InitCommandContext context: the context the command runs on
        """
        pass

    def cleanup(self):
        """
        Destroy the driver session, this function is called everytime a driver instance is destroyed
        This is a good place to close any open sessions, finish writing to log files
        """
        pass

    @staticmethod
    def _get_sandbox_reporter(context, api):
        """
        helper method to get sandbox reporter instance
        :param ResourceCommandContext context:
        :param CloudShellAPISession api:
        :return:
        """
        res_id = context.reservation.reservation_id
        model = context.resource.model
        service_name = context.resource.name
        logger = get_qs_logger(
            log_group=res_id, log_category=model, log_file_prefix=service_name
        )
        reporter = SandboxReporter(api, res_id, logger)
        return reporter

    def _raise_exception_flow(self, context, exc_msg):
        """
        1. Log error message
        2. Print to sandbox console
        3. Set Error live status with exc_msg
        4. raise Exception
        :param ResourceCommandContext context:
        :param str exc_msg:
        :return:
        """
        api = CloudShellSessionContext(context).get_api()
        res_id = context.reservation.reservation_id
        service_name = context.resource.name
        reporter = self._get_sandbox_reporter(context, api)
        reporter.err_out(message=exc_msg, target_func_stack_index=3)
        api.SetServiceLiveStatus(
            reservationId=res_id,
            serviceAlias=service_name,
            liveStatusName="Error",
            additionalInfo=exc_msg,
        )
        raise Exception(exc_msg)

    def start_sandbox(self, context, duration_minutes):
        """
        :param ResourceCommandContext context:
        :param str duration_minutes: will be converted to int
        :return:
        """
        api = CloudShellSessionContext(context).get_api()
        master_sandbox_id = context.reservation.reservation_id
        model = context.resource.model
        service_name = context.resource.name
        service_name = sandbox_name_truncater(service_name)

        reporter = self._get_sandbox_reporter(context, api)

        resource = SandboxController.create_from_context(context)

        launcher_sandbox_owner = context.reservation.owner_user
        blueprint_name = resource.blueprint_name
        is_notify_val = resource.email_notifications
        is_notify = True if is_notify_val == "True" else False
        global_inputs_val = resource.global_inputs
        global_input_requests = get_global_input_request_from_semicolon_sep_str(
            global_inputs_val
        )
        permitted_users_comma_separated = resource.permitted_users
        permitted_users_list = [
            s.strip() for s in permitted_users_comma_separated.split(",")
        ]

        if not duration_minutes:
            exc_msg = "'{}' duration_minutes input not populated".format(service_name)
            self._raise_exception_flow(context, exc_msg)

        duration_minutes = int(duration_minutes)

        if not blueprint_name:
            exc_msg = "Please populate Blueprint Name attribute"
            self._raise_exception_flow(context, exc_msg)

        service_sandbox_id_val = resource.sandbox_id
        if service_sandbox_id_val:
            warn_msg = "'{}' sandbox already exists".format(service_name)
            reporter.warn_out(warn_msg)
            return

        reporter.info_out(
            "starting {}. polling provisioning status...".format(service_name)
        )

        try:
            response = api.CreateImmediateTopologyReservation(
                reservationName=service_name,
                owner=launcher_sandbox_owner,
                durationInMinutes=duration_minutes,
                notifyOnStart=is_notify,
                notifyOnEnd=is_notify,
                notificationMinutesBeforeEnd=10,
                topologyFullPath=blueprint_name,
                globalInputs=global_input_requests,
                notifyOnSetupComplete=is_notify,
            ).Reservation
        except Exception as e:
            exc_msg = "'{}' sandbox start failed. {}".format(service_name, str(e))
            self._raise_exception_flow(context, exc_msg)
            return

        # Update sandbox id value
        response_sandbox_id = response.Id
        sb_id_attr_key = "{}.Sandbox Id".format(model)
        attr_requests = [AttributeNameValue(sb_id_attr_key, response_sandbox_id)]
        api.SetServiceAttributesValues(
            reservationId=master_sandbox_id,
            serviceAlias=service_name,
            attributeRequests=attr_requests,
        )
        sleep(10)
        # add permitted users to sandbox
        try:
            api.AddPermittedUsersToReservation(
                reservationId=response_sandbox_id, usernames=permitted_users_list
            )
        except Exception as e:
            exc_msg = (
                "Issue adding permitted users. Sandbox: '{}', Users: {}. {}".format(
                    service_name, permitted_users_list, str(e)
                )
            )
            reporter.err_out(exc_msg)
            raise Exception(exc_msg)

        # poll setup status for 15 minutes max
        provisioning_status, elapsed_time = poll_setup_for_provisioning_status(
            api, response_sandbox_id
        )
        if provisioning_status.lower() == "error":
            exc_msg = "'{}' provisioning status '{}' after {} minutes".format(
                service_name, provisioning_status, elapsed_time
            )
            self._raise_exception_flow(context, exc_msg)

        success_msg = "'{}' status '{}' after {} minutes".format(
            service_name, provisioning_status, elapsed_time
        )
        api.SetServiceLiveStatus(
            reservationId=master_sandbox_id,
            serviceAlias=service_name,
            liveStatusName="Online",
            additionalInfo=success_msg,
        )
        reporter.info_out(success_msg, log_only=True)
        return success_msg

    def end_sandbox(self, context):
        """
        :param ResourceCommandContext context:
        :return:
        """
        api = CloudShellSessionContext(context).get_api()
        service_name = context.resource.name
        resource = SandboxController.create_from_context(context)
        master_reservation_id = context.reservation.reservation_id
        service_sandbox_id_val = resource.sandbox_id
        blueprint_name = resource.blueprint_name
        reporter = self._get_sandbox_reporter(context, api)

        if not blueprint_name:
            exc_msg = "No Blueprint Name attribute populated"
            self._raise_exception_flow(context, exc_msg)

        if not service_sandbox_id_val:
            exc_msg = "No sandbox Id attribute populated"
            self._raise_exception_flow(context, exc_msg)

        api = CloudShellSessionContext(context).get_api()

        try:
            api.EndReservation(reservationId=service_sandbox_id_val)
        except Exception as e:
            exc_msg = "'{}' Sandbox ending command FAILED. {}".format(
                service_name, str(e)
            )
            self._raise_exception_flow(context, exc_msg)

        polling_results = poll_teardown_for_completion_status(
            api=api, res_id=service_sandbox_id_val
        )
        elapsed_time = polling_results.elapsed_polling_minutes
        status_msg = (
            "Sandbox teardown completed SUCCESSFULLY after '{}' minutes".format(
                elapsed_time
            )
        )
        api.SetServiceLiveStatus(
            reservationId=master_reservation_id,
            serviceAlias=service_name,
            liveStatusName="Offline",
            additionalInfo=status_msg,
        )
        reporter.info_out(status_msg, log_only=True)
        return status_msg

    def _extend_sandbox(self, context, duration_minutes):
        """
        :param ResourceCommandContext context:
        :param int duration_minutes:
        :return:
        """
        api = CloudShellSessionContext(context).get_api()
        res_id = context.reservation.reservation_id
        resource = SandboxController.create_from_context(context)
        service_name = context.resource.name
        service_sandbox_id = resource.sandbox_id
        reporter = self._get_sandbox_reporter(context, api)

        try:
            api.ExtendReservation(
                reservationId=service_sandbox_id, minutesToAdd=int(duration_minutes)
            )
        except Exception as e:
            exc_msg = "'{}' failed to extend. {}".format(service_name, str(e))
            self._raise_exception_flow(context, exc_msg)

        success_msg = "'{}' sandbox extended {} minutes".format(
            service_name, duration_minutes
        )
        api.SetServiceLiveStatus(
            reservationId=res_id,
            serviceAlias=service_name,
            liveStatusName="Online",
            additionalInfo=success_msg,
        )
        reporter.info_out(success_msg, log_only=True)
        return success_msg

    def extend_sandbox(self, context, duration_minutes):
        """
        :param ResourceCommandContext context:
        :param str duration_minutes:
        :return:
        """
        return self._extend_sandbox(context, int(duration_minutes))

    def sync_remaining_time(self, context):
        """
        sync time of child sandbox with controller sandbox ONLY if less time in child sandbox
        :param ResourceCommandContext context:
        :return:
        """
        api = CloudShellSessionContext(context).get_api()
        resource = SandboxController.create_from_context(context)
        service_name = context.resource.name
        master_reservation_id = context.reservation.reservation_id
        service_sandbox_id = resource.sandbox_id
        if not service_sandbox_id:
            exc_msg = "Can't sync time on '{}'. No sandbox id attr populated".format(
                service_name
            )
            self._raise_exception_flow(context, exc_msg)

        parent_sb_remaining_minutes = api.GetReservationRemainingTime(
            master_reservation_id
        ).RemainingTimeInMinutes
        service_sb_remaining_minutes = api.GetReservationRemainingTime(
            service_sandbox_id
        ).RemainingTimeInMinutes

        if parent_sb_remaining_minutes >= service_sb_remaining_minutes:
            difference = parent_sb_remaining_minutes - service_sb_remaining_minutes
            return self._extend_sandbox(context, int(difference))

    def update_permitted_users(self, context):
        """
        :param ResourceCommandContext context:
        :param str duration_minutes: will be converted to int
        :return:
        """
        api = CloudShellSessionContext(context).get_api()
        service_name = context.resource.name
        reporter = self._get_sandbox_reporter(context, api)

        resource = SandboxController.create_from_context(context)

        permitted_users_comma_separated = resource.permitted_users
        permitted_users_list = [
            s.strip() for s in permitted_users_comma_separated.split(",")
        ]

        service_sandbox_id_val = resource.sandbox_id
        if not service_sandbox_id_val:
            exc_msg = "'{}' has no active sandbox id yet".format(service_name)
            self._raise_exception_flow(context, exc_msg)

        try:
            api.AddPermittedUsersToReservation(
                reservationId=service_sandbox_id_val, usernames=permitted_users_list
            )
        except Exception as e:
            exc_msg = "Issue adding permitted users. Sandbox: '{}', Users: {}".format(
                service_name, permitted_users_list
            )
            reporter.err_out(exc_msg)

        success_msg = "added permitted users '{}' to sandbox '{}'".format(
            permitted_users_list, service_name
        )
        reporter.info_out(success_msg, log_only=True)
        return success_msg

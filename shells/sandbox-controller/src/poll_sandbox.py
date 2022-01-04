from cloudshell.api.cloudshell_api import CloudShellAPISession
from retrying import retry, RetryError
from time import time
from collections import namedtuple

PollingResults = namedtuple("PollingResults", ["sandbox_provisioning_status", "elapsed_polling_minutes"])


class PollSandboxTimeoutError(Exception):
    pass


def _validate_setup_status(status_data):
    """
    :param str provisioning_status:
    :return:
    """
    sandbox_status, provisioning_status = status_data
    if provisioning_status.lower() == "ready":
        return False
    if provisioning_status.lower() == "error":
        return False
    return True


def _validate_teardown_status(status_data):
    """
    :param tuple(str, str) status_data: (sandbox_status, provisioning_status)
    :return:
    """
    sandbox_status, provisioning_status = status_data
    if sandbox_status.lower() == "completed":
        return False
    return True


def _poll_sandbox_for_status(api, res_id, validation_func, max_polling_minutes=45, polling_frequency_seconds=10):
    """
    poll setup and teardown for status
    :param CloudShellAPISession api:
    :param str res_id:
    :param func validation_func: function that will validate status
    :param int max_polling_minutes:
    :param int polling_frequency_seconds:
    :return:
    :rtype: PollingResults
    """
    total_polling_ms = max_polling_minutes * 60 * 1000
    polling_frequency_ms = polling_frequency_seconds * 1000
    sandbox_name = api.GetReservationDetails(res_id).ReservationDescription.Name

    @retry(wait_fixed=polling_frequency_ms, stop_max_delay=total_polling_ms, retry_on_result=validation_func)
    def _poll_sandbox():
        res_details = api.GetReservationDetails(res_id).ReservationDescription
        sandbox_status = res_details.Status
        provisioning_status = res_details.ProvisioningStatus
        return sandbox_status, provisioning_status

    start_time = time()
    try:
        sandbox_status, provisioning_status = _poll_sandbox()
    except RetryError:
        exc_msg = "Polling '{}' timed out after {} minutes".format(sandbox_name, str(max_polling_minutes))
        raise PollSandboxTimeoutError(exc_msg)

    elapsed_seconds = time() - start_time
    float_minutes = elapsed_seconds / 60.0
    formatted_elapsed = "{:.2f}".format(float_minutes)
    float_converted = float(formatted_elapsed)
    return PollingResults(sandbox_provisioning_status=provisioning_status, elapsed_polling_minutes=float_converted)


def poll_setup_for_provisioning_status(api, res_id, max_polling_minutes=45, polling_frequency_seconds=10):
    """
    wrapper for polling setup
    :param CloudShellAPISession api:
    :param str res_id:
    :param int max_polling_minutes:
    :param int polling_frequency_seconds:
    :return:
    :rtype: PollingResults
    """
    return _poll_sandbox_for_status(api, res_id, _validate_setup_status, max_polling_minutes,
                                    polling_frequency_seconds)


def poll_teardown_for_completion_status(api, res_id, max_polling_minutes=45, polling_frequency_seconds=10):
    """
    wrapper for polling teardown
    :param CloudShellAPISession api:
    :param str res_id:
    :param int max_polling_minutes:
    :param int polling_frequency_seconds:
    :return:
    :rtype: PollingResults
    """
    return _poll_sandbox_for_status(api, res_id, _validate_teardown_status, max_polling_minutes,
                                    polling_frequency_seconds)


if __name__ == "__main__":
    LIVE_SANDBOX_ID = "12f96a6c-d993-4ca1-ab08-6839b9f95b18"
    session = CloudShellAPISession("localhost", "admin", "admin", "Global")
    results = poll_teardown_for_completion_status(session, LIVE_SANDBOX_ID)
    result, polling_time = results
    print(result, polling_time)

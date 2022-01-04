from multiprocessing.pool import ThreadPool

from cloudshell.api.cloudshell_api import CloudShellAPISession, InputNameValue


# Define the function which will be executed within the ThreadPool
def _execute_command_wrapper(
    api, res_id, target_name, target_type, command_name, command_inputs=None
):
    """
    function to be passed to threading implementation
    :param CloudShellAPISession api:
    :param str res_id:
    :param str target_name:
    :param str target_type: "Resource" or "Service"
    :param str command_name:
    :param list[InputNameValue] command_inputs:
    :return:
    """
    command_inputs = command_inputs if command_inputs else []
    res = api.ExecuteCommand(
        reservationId=res_id,
        targetName=target_name,
        targetType=target_type,
        commandName=command_name,
        commandInputs=command_inputs,
        printOutput=True,
    ).Output
    return res


def execute_commands_async(
    api,
    res_id,
    target_components_list,
    target_type,
    command_name,
    command_inputs=None,
    max_thread_count=0,
):
    """
    execute commands async and return tuple of result lists (success_list, exceptions_list)
    each list contains tuples of (component_name, async_response)
    :param CloudShellAPISession api:
    :param str res_id:
    :param list[str] target_components_list:
    :param str target_type:
    :param str command_name:
    :param list[InputNameValue] command_inputs:
    :param int max_thread_count:
    :return:
    """
    max_thread_count = (
        max_thread_count if max_thread_count else len(target_components_list)
    )
    thread_pool = ThreadPool(processes=max_thread_count)

    async_results = []
    for target_name in target_components_list:
        execute_command_tuple_inputs = (
            api,
            res_id,
            target_name,
            target_type,
            command_name,
            command_inputs,
        )
        async_result = thread_pool.apply_async(
            _execute_command_wrapper, execute_command_tuple_inputs
        )
        async_results.append((target_name, async_result))
    thread_pool.close()
    thread_pool.join()

    # COLLECT FAILURES FROM ASYNC RESULTS
    success_responses = []
    exception_responses = []
    for component_name, async_response in async_results:
        try:
            response_output = async_response.get()
        except Exception as e:
            exception_responses.append((component_name, str(e)))
        else:
            success_responses.append((component_name, response_output))
    return success_responses, exception_responses


if __name__ == "__main__":
    # Sample usage. Generally used for running health check commands in parallel and validating all results.
    LIVE_SANDBOX_ID = ""
    target_component_names = ["resourceA", "resourceB", "resourceC"]
    component_type = "Service"
    command_name = "my_command"
    command_inputs = [InputNameValue("param1", "val1")]
    max_thread_count = 0

    api = CloudShellAPISession(
        host="localhost", username="admin", password="admin", domain="localhost"
    )

    my_success_responses, my_exception_responses = execute_commands_async(
        api=api,
        res_id=LIVE_SANDBOX_ID,
        target_components_list=target_component_names,
        target_type=component_type,
        command_name=command_name,
        command_inputs=command_inputs,
        max_thread_count=max_thread_count,
    )
    if my_exception_responses:
        # each response in list is tuple of (component name, error message string)
        failed_component_names = [result[0] for result in my_exception_responses]
        err_msg = "Failed execution for following: {}".format(failed_component_names)
        raise Exception(err_msg)

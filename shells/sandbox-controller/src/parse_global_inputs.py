from cloudshell.api.cloudshell_api import UpdateTopologyGlobalInputsRequest


def _get_global_input_request(key_value_input_str):
    """
    parse, clean, and add to request object
    :param str key_value_input_str: expected 'input1, val1'
    :return:
    """
    split = key_value_input_str.split(",")
    cleaned = [s.strip() for s in split]
    if len(cleaned) > 2:
        raise Exception("Parsed Key-pair is greater than 2")
    return UpdateTopologyGlobalInputsRequest(ParamName=cleaned[0], Value=cleaned[1])


def get_global_input_request_from_semicolon_sep_str(input_str):
    """
    "input1, val1; input2, val2; input 3, val3" --> [UpdateTopologyGlobalInputsRequest(input1, val1),..]
    :param input_str: "input1, val1; input2, val2; input 3, val3"
    :return:
    :rtype: list[UpdateTopologyGlobalInputsRequest]
    """
    if not input_str:
        return []
    split = input_str.split(";")
    requests = [_get_global_input_request(s) for s in split]
    return requests


if __name__ == "__main__":
    input_str = "input1, val1; input2, val2; input 3, val3"
    output = get_global_input_request_from_semicolon_sep_str(input_str)
    pass

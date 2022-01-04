def sandbox_name_truncater(input_str):
    """
    :param int max_characters:
    :return:
    """
    sandbox_max_characters = 60
    max_minus_ellipses = sandbox_max_characters - 2
    if len(input_str) > sandbox_max_characters:
        return input_str[:max_minus_ellipses] + ".."
    else:
        return input_str

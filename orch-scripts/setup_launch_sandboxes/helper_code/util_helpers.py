import re


def sandbox_name_truncater(input_str):
    """
    :param int max_characters:
    :return:
    """
    sandbox_max_characters = 60
    max_minus_ellipses = sandbox_max_characters - 2
    if len(input_str) > sandbox_max_characters:
        return input_str[:max_minus_ellipses] + '..'
    else:
        return input_str


def replace_illegal_sandbox_name_chars(student_user_name):
    """
    non-alphanumeric characters illegal, except for ][-_.|
    :param str student_user_name:
    :return:
    """
    return re.sub(r'[^\s0-9a-zA-Z\|\.\[\]-_]', '-', student_user_name)
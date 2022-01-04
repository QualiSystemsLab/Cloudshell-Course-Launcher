from cloudshell.api.cloudshell_api import CloudShellAPISession


def validate_user_list(api, user_list):
    """
    :param CloudShellAPISession api:
    :param list[str] user_list:
    :return:
    """
    invalid_users = []
    for user in user_list:
       try:
           api.GetUserDetails(user)
       except Exception as e:
           invalid_users.append(user)

    if invalid_users:
        raise Exception("The following users are invalid - '{}'".format(invalid_users))


if __name__ == "__main__":
    user_list = ["admin", "xcvb", "asdfasdf"]
    session = CloudShellAPISession("localhost", "admin", "admin", "Global")
    validate_user_list(session, user_list)
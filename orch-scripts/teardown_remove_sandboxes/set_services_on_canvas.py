import SB_GLOBALS
from cloudshell.api.cloudshell_api import (AttributeNameValue,
                                           CloudShellAPISession)


def _get_chunks(input_list, chunk_size):
    chunk_size = max(1, chunk_size)
    return (input_list[i : i + chunk_size] for i in xrange(0, len(input_list), chunk_size))


def set_services(api, res_id, student_list, target_blueprint_name, attributes_list=None):
    """
    add resources to sandbox in different quadrants. choose stacking order
    :param CloudShellAPISession api:
    :param list[str] student_list:
    :param str target_blueprint_name:
    :param list[AttributeNameValue] attributes_list:
    :return:
    """
    attributes_list = [] if not attributes_list else attributes_list

    start_x = 200
    start_y = 100
    curr_y = start_y

    x_offset = 300
    y_offset = 150

    chunks = _get_chunks(student_list, 5)
    for chunk in chunks:
        curr_x = start_x
        for student_name in chunk:
            service_alias = "{} - {}".format(student_name, target_blueprint_name)
            attributes_list.append(AttributeNameValue(SB_GLOBALS.SANDBOX_OWNER_ATTR, student_name))
            api.AddServiceToReservation(
                reservationId=res_id,
                serviceName=SB_GLOBALS.SANDBOX_CONTROLLER_MODEL,
                alias=service_alias,
                attributes=attributes_list,
            )
            api.SetReservationServicePosition(reservationId=res_id, serviceAlias=service_alias, x=curr_x, y=curr_y)
            attributes_list.pop()
            curr_x += x_offset
        curr_y += y_offset


if __name__ == "__main__":
    import time

    LIVE_SANDBOX_ID = "108463c3-028b-4e66-8753-acc1b708069e"
    session = CloudShellAPISession("localhost", "admin", "admin", "Global")
    my_list = [
        "a",
        "b",
        "c",
        "d",
        "e",
        "f",
        "g",
        "H",
        "i",
        "j",
        "k",
        "l",
        "m",
        "n",
        "o",
        "p",
        "q",
        "r",
        "s",
        "t",
        "u",
        "v",
        "w",
        "x",
        "y",
        "z",
    ]
    set_services(session, LIVE_SANDBOX_ID, my_list, "my bp")

    # clean up test
    time.sleep(20)
    all_services = session.GetReservationDetails(LIVE_SANDBOX_ID).ReservationDescription.Services
    session.RemoveServicesFromReservation(LIVE_SANDBOX_ID, [s.Alias for s in all_services])

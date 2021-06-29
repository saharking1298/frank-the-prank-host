from datetime import datetime


def show_header(title):
    """
    This function shows a Frank The Prank header logging information.
    Header Foramt: "-- Ping Information --"
    :param title: The title of the header
    :type title: str
    :return: None
    """
    print(f"-- {title} --")


def show_variable_information(var_name, var_value):
    """
    This function shows logging information on the following format:
    "- [Variable_Name]: [Variable_Value] -" --> "- Ping Sender: user123 -"
    :param var_name: The name of the variable to show
    :param var_value: The value of the variable to show
    :return: None
    """
    print(f"- {var_name}: {var_value} -")


def show_message(message):
    """
    This function shows logging information on the following format:
    "- [Message] -" --> "- Error occurred on line 59 -"
    :param message: The message to display
    :return: None
    """
    print(f"- {message} -")


def show_current_time():
    """
    This function displays the current time in the right logging format.
    :return: None
    """
    time = datetime.now().strftime("%H:%M:%S")
    show_variable_information("Current time", time)


def show_paragraph(title, logging_information, show_time=True):
    """
    This function shows off a whole logging paragraph in the following format:
    -- Frank The Prank V1.3.2 - Debugging Log --
    - Operation Time: 12:35:14 -
    - Current Host Username: test -
    - Current Host Password: test123 -
    :param title: The paragraph title
    :param logging_information: A dict with the variables names and values, or just list of messages to display.
    :param show_time: If ot is true, the current time will be logged too.
    :return:
    """
    show_header(title)
    if show_time:
        show_current_time()
    if type(logging_information) == dict:
        for var_name in logging_information:
            show_variable_information(var_name, logging_information[var_name])
    elif type(logging_information) in (list, tuple):
        for message in logging_information:
            show_message(message)
    else:
        show_message(logging_information)
    print()

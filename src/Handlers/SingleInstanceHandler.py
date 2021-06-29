from Handlers import PathsHandler
import tempfile
import os


def get_running_instances():
    """
    This function checks if a temporary file exist in .../FrankThePrank/Temp/FtpTemp...
    The reason - Checking if Ftp is already running .
    :return: The count of the running instances of Ftp
    :rtype: int
    """
    running_instances = 0
    tempfiles = os.listdir(tempfile.gettempdir())
    for file in tempfiles:
        if file.startswith("FtpTemp_"):
            running_instances += 1
    return running_instances


def ftp_already_running():
    """
    This function checks if FrankThePrank is already running on another instance.
    :return: True if Ftp is running, False if not.
    :rtype: bool
    """
    instances = get_running_instances()
    if instances > 1:
        return True
    return False


def reset_planned():
    """
    This function checks in the config if FrankThePrank is running twice and this instance suppose to be
    eliminated, or a restart is planned.
    :return: True if reset planned, False if not.
    :rtype: bool
    """
    return os.path.isfile(PathsHandler.join(PathsHandler.temp_dir, "reset.tmp"))


def enable_reset():
    """
    This function will create a tmp file named "reset.tmp" to allow another instance to open while this one is active.
    :return: None
    """
    open(PathsHandler.join(PathsHandler.temp_dir, "reset.tmp"), "w")


def disable_reset():
    """
    This function will remove the tmp file created by enable_reset() to not allow duplicates of Ftp.
    :return: None
    """
    os.remove(PathsHandler.join(PathsHandler.temp_dir, "reset.tmp"))

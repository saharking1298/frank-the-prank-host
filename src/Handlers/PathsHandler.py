import tempfile
import os.path
import sys


def join(path, *paths):
    """
    Just a clone of the os.path.join() function
    :param path: The base path
    :type path: str
    :param paths: All the other paths to join
    :type paths: str
    :return: The joined path
    :rtype: str
    """
    return os.path.join(path, *paths)


def running_on_exe():
    """
    This function checks if the current program is running from a python file or from exe,
    Then return a bool.
    :return: Bool (True if the program running on exe, False if not)
    :rtype: bool
    """
    return getattr(sys, 'frozen', False)


def get_application_path():
    """
    This function gets the current file of Frank The Prank being executed.
    :return: Frank The Prank working file
    """
    if running_on_exe():
        return sys.executable
    else:
        return os.path.sep.join(__file__.split(os.path.sep))


def get_global_path():
    """
    This function gets the global directory of "Frank The Prank".
    :return: Frank The Prank global directory
    """
    if not running_on_exe():  # if not
        return os.path.dirname(application_path)
    else:
        return os.path.sep.join(os.path.dirname(application_path).split(os.path.sep))


# .../FrankThePrank/[FrankThePrank.exe / FrankThePrank.py]
application_path = get_application_path()
# .../FrankThePrank
global_path = get_global_path()
# .../FrankThePrank/FtpResources
resources_dir = join(global_path, "FtpResources")
# .../FrankThePrank/FtpResources/Extensions
extensions_dir = join(resources_dir, "Extensions")
# .../FrankThePrank/FtpResources/Media
media_dir = join(resources_dir, "Media")
# .../FrankThePrank/FtpResources/Music
music_dir = join(resources_dir, "Music")
# .../FrankThePrank/FtpResources/Temp
temp_dir = join(resources_dir, "Temp")
# .../FrankThePrank/FtpResources/FtpConfig.json
config_path = join(resources_dir, "FtpConfig.json")
# .../%Temp%/FtpAdminSDK.json
admin_sdk_path = join(tempfile.gettempdir(), "FtpAdminSDK.json")

from Handlers import PathsHandler
import requests
import json
import os

config_content = {"hostId": "", "authToken": "", "securityPassword": "", "remote-whitelist": []}
version_requirements = {
    "nircmd.exe": "https://api.saharscript.dev/downloads/ftp-host/plugins/nircmd.exe",
    "DisplaySwitch.exe": "https://api.saharscript.dev/downloads/ftp-host/plugins/DisplaySwitch.exe"
}
ftp_meta_url = "https://api.saharscript.dev/meta/FtpMeta.json"


def create_required_directories():
    """
    This function checks if all the base directories of FrankThePrank exist.
    If not, It creates them.
    :return: None
    """
    required_directories = [PathsHandler.resources_dir, PathsHandler.extensions_dir, PathsHandler.temp_dir,
                            PathsHandler.media_dir, PathsHandler.music_dir]
    for directory in required_directories:
        if not os.path.isdir(directory):
            os.mkdir(directory)


def create_config():
    """
    This function checks if the config of FrankThePrank exist.
    If not, It creates it.
    :return: None
    """
    if not os.path.isfile(PathsHandler.config_path):
        with open(PathsHandler.config_path, "w") as config_file:
            json.dump(config_content, config_file)


def local_files_setup():
    """
    This function is the main function of SetupHandler.
    It do it all together - Creates the main directories, creates the config,
    creates the temporary admin_sdk, and downloading the extensions.
    :return: None
    """
    # Create required local directories and files
    create_required_directories()
    create_config()


def required_extensions_setup():
    """
    This function downloads the required extensions for FrankThePrank, if at least one is missing.
    :return: None
    """
    for requirement_name in version_requirements:
        full_path = PathsHandler.join(PathsHandler.extensions_dir, requirement_name)
        download_url = version_requirements[requirement_name]
        if not os.path.isfile(full_path):
            r = requests.get(download_url)
            open(full_path, 'wb').write(r.content)

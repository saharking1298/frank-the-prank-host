from Handlers import PathsHandler
import requests
import json
import os

config_content = {"hostId": "", "authToken": "", "securityPassword": "", "remote-whitelist": []}
data_file_content = {"files.favorites": {}}
required_plugins = ["nircmd.exe", "DisplaySwitch.exe"]
# meta_url = "https://saharscript.dev/api/frankThePrank/meta"
meta_url = "http://localhost:3000/api/frankThePrank/meta"


def create_required_directories():
    """
    This function checks if all the base directories of FrankThePrank exist.
    If not, It creates them.
    :return: None
    """
    required_directories = [PathsHandler.resources_dir, PathsHandler.extensions_dir, PathsHandler.temp_dir,
                            PathsHandler.media_dir, PathsHandler.music_dir, PathsHandler.data_dir]
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


def create_data_file():
    """
    This function checks if the program's data file exists in appdata.
    If not, It creates it.
    :return: None
    """
    if not os.path.isfile(PathsHandler.data_file):
        with open(PathsHandler.data_file, "w") as data_file:
            json.dump(data_file_content, data_file)


def local_files_setup():
    """
    This function set up local files.
    Files: Required directories, and FTP config.
    :return: None
    """
    # Create required local directories and files
    create_required_directories()
    create_config()
    create_data_file()


def required_extensions_setup():
    """
    This function downloads the required extensions for FrankThePrank, if at least one is missing.
    :return: None
    """
    meta = None
    for plugin in required_plugins:
        full_path = PathsHandler.join(PathsHandler.extensions_dir, plugin)
        if not os.path.isfile(full_path):
            if meta is None:
                meta = requests.get(meta_url).json()
            url = meta["plugins"][plugin.split(".")[0]].replace("https://saharscript.dev", "http://localhost:3000")
            r = requests.get(url)
            open(full_path, 'wb').write(r.content)

from Handlers import PathsHandler
import json


def get_config():
    """
    This function returns the json of Ftp config.
    :return: json of the Ftp config
    :rtype: dict
    """
    return json.load(open(PathsHandler.config_path))


def get_host_id():
    """
    This function returns the host Id in the "hostId" tab in Ftp config.
    :return: user's username
    :rtype: str
    """
    return get_config()["hostId"]


def get_password():
    """
    This function returns the password in the "securityPassword" tab in Ftp config.
    :return: user's password
    :rtype: str
    """
    return get_config()["securityPassword"].strip()


def get_auth_token():
    """
    This function returns the authenticator function in the "authToken" tab in Ftp config.
    :return: user's authenticator token
    :rtype: str
    """
    return get_config()["authToken"]


def get_whitelist():
    """
    This function returns the remote whitelist in the "remote-whitelist" tab in Ftp config.
    :return: user's remote whitelist
    :rtype: list
    """
    return get_config()["remote-whitelist"]


def set_config_item(item, value):
    """
    This function sets a config item by its value.
    example: set_config_item("username", "user123") will change the username in the config to "user123".
    :param item: the config item name
    :type item: str
    :param value: the value for the item
    :return: None
    """
    config = get_config()
    config[item] = value
    json.dump(config, open(PathsHandler.config_path, "w"))

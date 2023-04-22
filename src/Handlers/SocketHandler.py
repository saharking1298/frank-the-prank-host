from Handlers import ConfigHandler, LoggingHandler, FileManagerHandler
from Features import DynamicFetchers
import socketio
import time


class SocketHandler:
    def __init__(self, respond_function):
        """
        This is the init function of Ftp socket handler.
        """
        self.respond_function = respond_function
        self.fetchers = DynamicFetchers()
        self.file_manager = FileManagerHandler.FileManager()
        # Development only. Production URL: "https://saharscript.dev/"
        self.socket_url = "http://localhost:3000/"
        # self.socket_url = "https://saharscript.dev/"
        self.connect_error = None
        self.event_delay = 0.01
        self.event_storage = {}
        self.remote_connected = ""
        self.io = socketio.Client()
        self.callbacks()

    def callbacks(self):
        @self.io.on("connect_error", namespace='/frankThePrank')
        def connect_error(data):
            self.connect_error = data["message"]

        @self.io.on("host:connectionRequest", namespace='/frankThePrank')
        def event_connection_request(pinger, password):
            status = self.on_connection_request(pinger, password)
            return status

        @self.io.on("host:remoteConnected", namespace='/frankThePrank')
        def event_remote_connected(remote_username):
            self.update_remote_connected(remote_username)

        @self.io.on("partnerStatus", namespace='/frankThePrank')
        def event_partner_status(status):
            if status == "terminated":
                self.remote_connected = ""
                print("Connection terminated.")

        @self.io.on("directTalkMessage", namespace='/frankThePrank')
        def event_direct_talk(data):
            if "event" in data:
                event = data["event"]
            else:
                event = None
            return self.handle_direct_talk(data["name"], event)

    def on_connection_request(self, pinger, security_password):
        """
        This function is called when a remote connection request is sent from the server.
        It checks two things: the pinger is in the whitelist if whitelist enabled,
        and the security password match the password in FtpConfig file.
        :param pinger: The username of the remote user trying to log in.
        :type pinger: str
        :param security_password: The password (optional).
        :type security_password: str
        :return: None
        """
        whitelist = ConfigHandler.get_whitelist()
        local_password = ConfigHandler.get_password()
        approved = True
        message = "Host is online. Connected successfully."
        if len(whitelist) > 0:
            if pinger not in whitelist:
                approved = False
                message = "Remote is not whitelisted. Connection failed."
        if approved and local_password != "" and local_password != security_password:
            approved = False
            message = "Password doesn't match. Connection failed."

        if approved:
            self.update_remote_connected(pinger)

        return {"success": approved, "error": message}

    def update_remote_connected(self, remote_username):
        """
        This function is activated when a new remote took over the host.
        :param remote_username: The remote connected
        :type remote_username: str
        :return: None
        """
        if remote_username != self.remote_connected:
            self.remote_connected = remote_username
            LoggingHandler.show_message(f"New Remote Is Now Controlling Host: '{self.remote_connected}'")

    def get_callback(self, callback_name):
        """
        This function waits for a value in event_storage to change, and returns the 'callback'.
        :param callback_name: The callback name
        :type callback_name: str
        :return: The callback value
        """
        while self.event_storage[callback_name] is None:
            time.sleep(self.event_delay)
        return self.event_storage[callback_name]

    def init_callback(self, callback_name):
        """
        This clears a callback value in event storage.
        :param callback_name: The callback name
        :return: None
        """
        self.event_storage[callback_name] = None

    def listen(self, event, *args):
        """
        This function sends an event to the server and return the callback.
        :param event: The name of the event to send.
        :type event: str
        :param args: The event argument(s) to be emitted.
        :return: The event callback (output from the server).
        """
        callback = event
        self.init_callback(callback)

        def on_callback(*output):
            if len(output) == 1:
                output = output[0]
            self.event_storage[callback] = output

        data = None
        if len(args) == 1:
            data = args[0]
        elif len(args) > 1:
            data = args
        self.io.emit(event, data=data, callback=on_callback, namespace='/frankThePrank')
        return self.get_callback(callback)

    def login(self):
        """
        This function sends a login request to the server, with the credentials inserted in config,
        then return the request status.
        :return: Request status
        """
        auth = {
            "actionType": "login",
            "clientType": "host",
            "username": ConfigHandler.get_host_id(),
            "password": ConfigHandler.get_auth_token()
        }
        try:
            self.io.connect(
                self.socket_url,
                namespaces=["/frankThePrank"],
                auth=auth
            )
            return {"approved": True}
        except:
            while self.connect_error is None:
                time.sleep(self.event_delay)
            return {"approved": False, "message": self.connect_error}

    def disconnect(self):
        """
        This function disconnects from the server
        :return: None
        """
        self.io.disconnect()

    def handle_direct_talk(self, name, event):
        print("Received directTalk:", name)
        if name == "features.activate":
            feature = event["featureName"]
            args = event["featureArgs"]
            if args is None:
                args = ()
            elif type(args) not in (tuple, list):
                args = (args,)
            self.respond_function(feature, *args)

        elif name == "arguments.dynamic.fetch":
            return self.fetchers.get(event)
        elif name.startswith("files."):
            return self.file_manager.handle(name, event, self.remote_connected)

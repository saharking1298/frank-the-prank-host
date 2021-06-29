from Handlers import ConfigHandler, LoggingHandler
import socketio
import time


class SocketHandler:
    def __init__(self, respond_function):
        """
        This is the init function of Ftp socket handler.
        """
        self.respond_function = respond_function
        # Development only. Production URL: "https://api.saharscript.dev/projects/ftp-server"
        self.socket_url = "http://localhost:3000"
        self.event_delay = 0.01
        self.event_storage = {}
        self.remote_connected = ""
        self.io = socketio.Client()
        self.callbacks()
        self.io.connect(self.socket_url)

    def callbacks(self):
        @self.io.on("connectionRequest")
        def event_connection_request(request_data):
            pinger = request_data["pinger"]
            password = request_data["password"]
            status = self.on_connection_request(pinger, password)
            return status

        @self.io.on("remoteConnected")
        def event_remote_connected(remote_username):
            self.update_remote_connected(remote_username)

        @self.io.on("remoteDisconnected")
        def event_remote_disconnected():
            pass

        @self.io.on("directTalkMessage")
        def event_direct_talk(data):
            self.handle_direct_talk(data)

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
                message = "Remote is not in whitelist. Connection failed."
        if approved and local_password != "" and local_password != security_password:
            approved = False
            message = "Password doesn't match. Connection failed."

        if approved:
            self.update_remote_connected(pinger)

        return {"approved": approved, "message": message}

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
        self.io.emit(event, data=data, callback=on_callback)
        return self.get_callback(callback)

    def login(self):
        """
        This function sends a login request to the server, with the credentials inserted in config,
        then return the request status.
        :return: Request status
        """
        host_id = ConfigHandler.get_host_id()
        auth_token = ConfigHandler.get_auth_token()
        data = ("host", {"hostId": host_id, "authToken": auth_token})
        login_status = self.listen("login", data)
        return login_status

    def disconnect(self):
        """
        This function disconnects from the server
        :return: None
        """
        self.io.disconnect()

    def handle_direct_talk(self, data):
        print("Received directTalk:", data)
        namespace = data["namespace"]
        event = data["eventName"]
        args = data["eventArgs"]
        if namespace == "feature":
            if args is None:
                args = ()
            elif type(args) not in (tuple, list):
                args = (args,)
            self.respond_function(event, *args)

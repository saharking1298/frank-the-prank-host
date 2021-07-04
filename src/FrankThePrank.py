from Handlers import SingleInstanceHandler, RulesCreationHandler, SocketHandler
from Handlers import LoggingHandler, ConfigHandler, SetupHandler
import threading
import Features
import tempfile
import sys


class FrankThePrank:
    def __init__(self):
        # ------------ Initializing Frank The Prank ------------

        # Defining version information
        self.FtpVersion = "1.4.1"
        self.rules = RulesCreationHandler.build_rules()

        # Checking that FrankThePrank has all the required files to start working.
        SetupHandler.local_files_setup()
        SetupHandler.required_extensions_setup()

        # Looking for other instances
        self.instance_setup()

        # Initializing Socket.IO connection
        self.serverScript = SocketHandler.SocketHandler(self.respond)

        # Initializing features
        self.features = Features.Features(self.serverScript, self.respond)

        # Checking host credentials
        self.login()

        # ------------ Initializing Cloud Components ------------
        self.username = ConfigHandler.get_host_id()

        # Show debug information
        self.show_debug_information()

    def instance_setup(self):
        """
        Checking if this instance of Ftp is suppose to run (If there are no other instances).
        One possible situation is another instance is running, bit a reset is planned. In that case, the other
        instance will be eliminated, and this one will be active.
        :return: None
        """
        if SingleInstanceHandler.ftp_already_running():
            if SingleInstanceHandler.reset_planned():
                SingleInstanceHandler.disable_reset()
            else:
                print("Detected another instance, exiting!")
                sys.exit(0)

    def login(self):
        """
        This function sends login request to the server, using credentials in config file.
        It authentication fails, Ftp will display an error and terminate itself.
        :return:
        """
        login_status = self.serverScript.login()
        if not login_status["approved"]:
            error_msg = login_status["message"]
            self.features.msgbox("Ftp Login Error", "Error message: " + error_msg)
            self.serverScript.disconnect()
            sys.exit(0)

    def show_debug_information(self):
        """
        This function just prints some debug information to the user.
        :return: None
        """
        LoggingHandler.show_paragraph(f"Frank The Prank V{self.FtpVersion} - Debugging Log",
                                      {"Current Host Username": self.username,
                                       "Current Host Password": ConfigHandler.get_password()})

    def respond(self, action, *args):
        """
        This function connects between the database call to the features class.
        It checks what is the action, and then activate it with the wanted arguments.
        :param action: The action name
        :type action: str
        :param args: The arguments to activate the action
        :return: None
        """
        action = action.replace(" ", "_")
        func = getattr(self.features, action)
        t = threading.Thread(target=func, args=args, daemon=True)
        t.start()


if __name__ == '__main__':
    # Creating a temp file that will allow other instances of Ftp to detect this one
    instance_temp_file = tempfile.TemporaryFile(prefix="FtpTemp_")
    # running Frank The Prank
    ftp = FrankThePrank()

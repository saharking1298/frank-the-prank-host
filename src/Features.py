from Handlers import SingleInstanceHandler, LoggingHandler, PathsHandler
import win32com.client
import mutagen.mp3
import subprocess
import webbrowser
import pywinauto
import threading
import win32api
import pynput
import psutil
import random
import time
import sys
import os
import re
os.environ['PYGAME_HIDE_SUPPORT_PROMPT'] = "hide"
from pygame import mixer


class DynamicArgumentsHandler:
    def __init__(self, serverScript):
        """
        This class is the Ftp dynamic arguments handler.
        Dynamic arguments, are feature arguments that the remote is sending before the actual feature request is sent.
        Example: launch feature has two dynamic arguments - the name to search, and the result to choose.
        The name is sent to the host, the host searches and gives a list of options the remote user can choose,
        and the feature request is being sent. That's a dynamic argument.
        :param serverScript: ServerScript class to handle database events.
        """
        self.serverScript = serverScript
        self.session_variables = []

    def clear_session_variables(self):
        """
        This function clears all the variables of the current session.
        It is used after a feature with dynamic arguments has been executed.
        :return: None
        """
        self.session_variables = []

    def save_session_variable(self, var_value):
        """
        This functions saves a variable to the local session storage.
        :param var_value: The variable value
        :return: None
        """
        self.session_variables.append(var_value)
        self.serverScript.send_continue_signal()

    def anti_error_encoder(self, result_to_send):
        """
        Firebase cant have special characters, such as $ # [ ] / or ., to be in the key value.
        This function encodes the result the host is suppose to send, to prevent errors in server logic level.
        NOTE: The result should be decoded also at the remote.
        :param result_to_send: The result that should be sent to the remote user
        :return: The same result, decoded.
        """
        special_chars_replacements = {'$': "%DoLlAr%",
                                      '#': "%HaShTaG%",
                                      '[': "%RiHgT-BrAcKeTSs%",
                                      ']': "%LeFt-BrAcKeTSs%",
                                      '/': "%SlAsH%",
                                      '.': "%PoInT%"}
        if type(result_to_send) == dict:
            encoded_result = {}
            for key in result_to_send:
                encoded_key = key
                for char in special_chars_replacements:
                    encoded_key = encoded_key.replace(char, special_chars_replacements[char])
                encoded_result[encoded_key] = result_to_send[key]
            return encoded_result
        else:
            return result_to_send

    def get_dynamic_choice(self, choice_id, referring_feature):
        """
        This function returns a list of valid choices for any dynamic choice case.
        Example, if the feature name is: "win", and the argument number is: 2, all of the opened windows titles
        will be returned.
        :param choice_id: The name of the choice function (with '-' instead of '_')
        :param referring_feature: The name of the
        :return: A tuple of all
        """
        choice_id = choice_id.replace("-", "_").strip()
        choice_function = getattr(DynamicChoiceFunctions, choice_id)
        if choice_function is not None:
            return_values = choice_function(referring_feature, self.session_variables)
            if len(return_values) == 2:
                return_type, output = return_values
                return return_type, self.anti_error_encoder(output)
            elif len(return_values) == 3:
                return_type, output, assign_value = return_values
                return return_type, self.anti_error_encoder(output), assign_value


class DynamicChoiceFunctions:
    @staticmethod
    def target_window_dialog(referring_feature, session_storage):
        """
        This function gets and returns a dict with all opened windows names and title (in a string) as keys,
        and the window process IDs as values.
        It is designed for the dynamic choice feature.
        :return:
        """
        dynamic_choice = []
        try:
            for title, name, process_name in WindowsApiHandler.get_open_windows():
                if len(title) > 80:
                    title = title[:80] + "..."
                dynamic_choice.append(f"[{name}] {title}")
            if len(dynamic_choice) > 0:
                return "choice", dynamic_choice
            elif len(dynamic_choice) == 1:
                return "value-message", "An open window was automatically selected: \n" + dynamic_choice[0]
            else:
                return "abort-message", "Info: The host has no open windows."
        except:
            return "abort-message", "A certain window is causing FrankThePrank window handler to crash. \n" \
                                    "These windows are usually steam apps or other full screen programs. \n" \
                                    "Please find the the responsible window and close it manually. " \
                                    "This is a known bug of Ftp, and we are working hard to get if fixed."

    @staticmethod
    def music_file_dialog(referring_feature, session_storage):
        """
        This function gets and returns a list of all audio files in Music directory,
        so it can be played by the remote.
        :return: A list of all music files in Music dir
        :rtype: list
        """
        valid_file_extensions = (".mp3", ".wav", ".ogg", ".m4a")
        music_files = []
        for file in os.listdir(PathsHandler.music_dir):
            for extension in valid_file_extensions:
                if file.endswith(extension):
                    music_files.append(file)
                    break
        if len(music_files) > 0:
            return "choice", music_files
        else:
            return "abort-message", "There are no music files in your FTP Music folder."

    @staticmethod
    def launch_program_dialog(referring_feature, session_storage):
        """
        This function searches for programs that match the given program name.
        :param referring_feature: The referring feature (the one that is calling the function)
        :param session_storage: The session storage (All the session variables)
        :return: A dict with all the program names and paths.
        """
        search_name = ""
        if referring_feature in ("launch",):
            search_name = session_storage[0]
        program_finder = ProgramFinder()
        relevant_programs = program_finder.search_program(search_name)
        if len(relevant_programs) == 0:
            return "abort-message", f"Frank The Prank could't find program {search_name}"
        elif len(relevant_programs) == 1:
            program_name = list(relevant_programs.keys())[0]
            program_path = list(relevant_programs.values())[0]
            return "value-message", f"Automatically selected {program_name}, launching...", program_path
        else:
            return "choice", relevant_programs


class ProgramFinder:
    def __init__(self):
        """
        This class is the main class of Ftp program finder -
        an easy and powerful solution to find an installed program on a windows PC.
        """
        self.searching_places = (r"C:\ProgramData\Microsoft\Windows\Start Menu\Programs",
                                 os.path.join(os.getenv("APPDATA"), r"Microsoft\Windows\Start Menu\Programs"))
        self.url_patterns = ("steam://", "uplay://")

    def get_installed_programs(self):
        """
        This function finds almost (about 90%) of all the installed programs of the host machine.
        It returns a dict with the names of the programs as keys, and their paths as the values.
        :return: A  dict with the names of the programs and their paths.
        """
        shell = win32com.client.Dispatch("WScript.Shell")
        installed_programs = {}
        for search_dir in self.searching_places:
            for path, dirs, files in os.walk(search_dir):
                for file in files:
                    file_path = os.path.join(path, file)
                    if file.endswith(".exe"):
                        installed_programs[file.replace(".exe", "")] = file_path
                    elif file.endswith(".lnk"):
                        shortcut = shell.CreateShortCut(file_path)
                        shortcut_target = shortcut.TargetPath
                        if shortcut_target.lower().endswith(".exe"):
                            installed_programs[file.replace(".lnk", "")] = shortcut_target
                    elif file.endswith(".url"):
                        file_content = open(file_path, "r").readlines()
                        url = ""
                        for line in file_content:
                            if line.startswith("URL"):
                                url = line[4:]

                        for pattern in self.url_patterns:
                            if url.startswith(pattern):
                                installed_programs[file.replace(".url", "")] = file_path
                                break
        return installed_programs

    def search_program(self, program_name):
        """
        This function gets a full or half name of a program, and return all programs that match the syntax.
        :param program_name: The name of the program (can be a part of the name, too)
        :type program_name: str
        :return: A dict with all the relevant program names and paths.
        """
        program_name = re.sub(" +", " ", program_name.strip().lower())
        relevant_programs = {}
        for name, path in self.get_installed_programs().items():
            if program_name in name.lower() or program_name in os.path.basename(path).lower():
                if not name.lower().startswith("uninstall"):
                    relevant_programs[name] = path
        return relevant_programs


class WindowsApiHandler:
    @staticmethod
    def get_open_windows():
        """
        This function gets all open window names, titles, and process names.
        It returns a tuple built of these tuples: (WINDOW_TITLE, WINDOW_NAME, PROCESS_NAME)
        :return: A tuple made of tuples with window title, name and process name (exe) each one.
        """
        windows = pywinauto.Desktop(backend="uia").windows()
        valid_windows = []
        for window in windows:
            # Getting window title
            title = window.window_text()
            if title not in ("Taskbar", "Program Manager", ""):
                # Window process PID and executable file required to get the window name
                pid = window.process_id()
                exe = psutil.Process(pid).exe()
                # Doing Low Level Stuff
                langs = win32api.GetFileVersionInfo(exe, r'\VarFileInfo\Translation')
                key = r'StringFileInfo\%04x%04x\FileDescription' % (langs[0][0], langs[0][1])
                process_name = win32api.GetFileVersionInfo(exe, key)
                if process_name is None:
                    # Steam apps has a known problem with win32api, so they don't get recognized as windows.
                    # Even through that, the prediction will probably is not 100% accurate -
                    # there might be other programs that have the same problem as well.
                    process_name = "Steam"
                exe = os.path.basename(exe)
                valid_windows.append((title, process_name, exe))
        return valid_windows


class AudioPlayer:
    def __init__(self):
        self.playing = False
        mixer.init()
        
    def play_sound(self, sound_file):
        """
        This function plays a sound file using pygame mixer.
        :param sound_file: The path to the sound file
        :type sound_file: str
        :return: None
        """
        mp3 = mutagen.mp3.MP3(sound_file)
        mixer.music.stop()
        mixer.init(frequency=mp3.info.sample_rate)
        mixer.music.load(sound_file)
        mixer.music.play()
        self.playing = True

    def pause(self):
        """
        This function pause / resume the pygame music mixer.
        :return: None
        """
        if self.playing:
            mixer.music.pause()
            self.playing = False
        else:
            mixer.music.unpause()

    def stop_playing(self):
        """
        This function stops the pygame music mixer from playing music.
        :return: None
        """
        mixer.music.stop()

    def set_volume(self, volume):
        """
        This function sets the volume of pygame volume mixer to a number between 0-100.
        :param volume: The wanted volume (0-100)
        :type volume: int
        :return: None
        """
        mixer.music.set_volume(float(volume)/100)  # Pygame mixer volume is between 0.0 - 1.0


class MouseKeyboardController:
    def __init__(self):
        """
        This class is suppose to take care of handling the mouse and keyboard
        """
        self.mouse = pynput.mouse.Controller()
        self.keyboard = pynput.keyboard.Controller()
        self.keyboard_keys = pynput.keyboard.Key
        self.crazy_enabled = False

    def mouse_click(self, button):
        """
        This function clicks the specified mouse button.
        Optional buttons: right, left, and middle.
        :param button: The button to click
        :type button: str
        :return: None
        """
        buttons = {'right': pynput.mouse.Button.right, 'left': pynput.mouse.Button.left, 'middle': pynput.mouse.Button.middle}
        self.mouse.click(buttons[button])

    def mouse_scroll(self, pixels):
        """
        This function scrolls the page according to the scrolling amount.
        Formula for scrolling: pixels * 20
        :param pixels: How many pixels up or down to scroll. Will be multiplied by 20.
        :type pixels: int
        :return: None
        """
        self.mouse.scroll(0, pixels * 20)

    def mouse_set(self, x, y):
        """
        This function moves the mouse cursor to a specific location using x and y values.
        :param x: The x value for The mouse cursor
        :type x: int
        :param y: The y value for The mouse cursor
        :type y: int
        :return:
        """
        self.mouse.position = (x, y)

    def mouse_move(self, direction, pixels):
        """
        This function moves the mouse cursor with a specific direction.
        Optional directions: right, left, up, down.
        :param direction: The moving direction
        :type direction: str
        :param pixels: The amount of pixels to move
        :type pixels: int
        :return:
        """
        x, y = 0, 0
        if direction == "right":
            x += pixels
        elif direction == "left":
            x -= pixels
        elif direction == "up":
            y -= pixels
        elif direction == "down":
            y += pixels
        self.mouse.move(x, y)

    def keyboard_type(self, text):
        """
        This function types a string with the keyboard.
        :param text: The text to type
        :type text: str
        :return: None
        """
        self.keyboard.type(text)

    def keyboard_press(self, *keys):
        """
        This function can press on several keyboard buttons.
        Optional keys: a-z, 0-9, special characters.
        :param keys: The
        :return:
        """
        valid_keys = []
        for key in keys:
            if len(key) == 1:
                valid_keys.append(key)
            else:
                key = getattr(self.keyboard_keys, key)
                valid_keys.append(key)
        for key in valid_keys:
            self.keyboard.press(key)
        for key in valid_keys:
            self.keyboard.release(key)

    def get_mouse_coordinates(self):
        """
        This function returns the current coordinates of the mouse cursor.
        :return: A tuple of the x cords and y cords of the mouse
        """
        return self.mouse.position

    def enable_crazy_mode(self, sensitivity):
        """
        This function enables crazy mode and cause the mouse cursor
        to move in a strange way, until it stopped.
        :param sensitivity: The sensitivity of crazy mode (how smooth or wild the movement will be)
        :return: None
        """
        self.disable_crazy_mode()
        self.crazy_enabled = True
        while self.crazy_enabled:
            x, y = self.mouse.position
            x += random.randint(-1 * sensitivity, sensitivity)
            y += random.randint(-1 * sensitivity, sensitivity)
            self.mouse.position = (x, y)
            time.sleep(0.01)

    def disable_crazy_mode(self):
        """
        This function disable and stops crazy mode.
        :return: None
        """
        self.crazy_enabled = False


class CmdCommandHandler:
    def __init__(self):
        """
        This class is suppose to take care of handling CMD calls in their different variations
        """
        pass

    def execute(self, command, location=None):
        """
        This function launches a single cmd command, with no error or output handling.
        :param command: The cmd command to call
        :type command: str
        :param location: The starting location path (where to cd)
        :type location: str
        :return: None
        """
        try:
            if location is not None:
                command = 'cd /D "{1}" & "{0}"'.format(command, location)
            subprocess.call(command, shell=True)
        except:
            pass

    def check_output(self, command, location=None):
        """
        This function launches a single cmd command, and returns the output from the command line
        :param command: The cmd command to call
        :type command: str
        :param location: The starting location path (where to cd)
        :type location: str
        :return: the output from the cmd.
        """
        try:
            if location is not None:
                command = 'cd /D "{1}" & "{0}"'.format(command, location)
            output = subprocess.check_output(command, shell=True, stderr=subprocess.STDOUT).decode("utf-8")
            return output
        except subprocess.CalledProcessError as e:
            output = e.output.decode("utf-8")
            return output

    def launch_executable(self, file, arguments=""):
        """
        This function launches an exe using the command line. arguments are also an option.
        :param file: The path of the exe
        :type file: str
        :param arguments: String of all the arguments for the launch
        :type arguments: str
        :return: None
        """
        command = 'cd /D "{}" & start {} {}'.format(*os.path.split(file), arguments)
        self.execute(command)


class NirCmdHandler:
    def __init__(self):
        self.nircmd_path = PathsHandler.join(PathsHandler.extensions_dir, "nircmd.exe")
        self.commandHandler = CmdCommandHandler()

    def nircmd_command(self, command):
        """
        This function launches a nircmd command with the nircmd utility.
        :param command: The nircmd command
        :type command: str
        :return: None
        """
        self.commandHandler.launch_executable(self.nircmd_path, command)


class AdvancedControlHandler:
    def __init__(self, features):
        """
        This function initialize the FTP loops handler, using the respond function, to process the command,
        and features class, to activate it.
        :param features: The features class
        :type features: Features
        """
        self.features = features

    def loop(self, amount_of_times, delay_time, feature):
        """
        This function runs a feature over and over again by the amount of times,
        and the delay between them.
        :param amount_of_times: The amount of times to run the action
        :param delay_time: The delay between each run
        :param feature: The feature to activate
        :return: None
        """
        action, arguments = feature
        feature_function = getattr(self.features, action)
        for i in range(amount_of_times):
            feature_function(*arguments)
            time.sleep(delay_time)
    
    def tloop(self, amount_of_seconds, delay_time, feature):
        """
        This function runs a feature over and over again until a certain number of seconds is passed.
        :param amount_of_seconds: The amount of seconds until the looped is stopped
        :param delay_time: The delay between each run
        :param feature: The feature to activate 
        :return: None
        """
        action, arguments = feature
        feature_function = getattr(self.features, action)
        times_to_run = int(amount_of_seconds / delay_time)
        for i in range(times_to_run):
            feature_function(*arguments)
            time.sleep(delay_time)
    
    def timed(self, delay_time, feature):
        """
        This function runs a feature after a certain amount of time
        :param delay_time: The amount of seconds until the action is activated
        :param feature: The feature to activate
        :return: None
        """
        action, arguments = feature
        feature_function = getattr(self.features, action)
        time.sleep(delay_time)
        feature_function(*arguments)

    def f(self, function_content):
        """
        This function activate a cloud function.
        It works based on the function content, already received by previous functions.
        Example content ==> [{"feature": "move", "arguments": [1920, 1080]}, {{"feature": "click", "arguments": ["left"]}]
        :param function_content: The content of the function
        :return: None
        """
        for func in function_content:
            action = func["feature"]
            arguments = func["arguments"]
            feature_function = getattr(self.features, action)
            feature_function(*arguments)


class Features:
    def __init__(self, serverScript, respond):
        """
        This feature initializing FrankThePrank features class
        :param serverScript: ServerScript to work with server-side code
        :type serverScript: DatabaseHandler.ServerScript
        :param respond: The respond function, to get a function with
        """
        self.serverScript = serverScript
        self.respond_function = respond
        self.input_controller = MouseKeyboardController()
        self.cmd_handler = CmdCommandHandler()
        self.nircmd_handler = NirCmdHandler()
        self.audio_player = AudioPlayer()
        self.advanced_control_handler = AdvancedControlHandler(self)
    
    def move(self, x_position, y_position):
        """
        This feature moves the mouse cursor to a specific point on the screen, by x and y axis location given.
        Category: Mouse & Keyboard
        Echo: No
        :param x_position: The x position [int]
        :param y_position: The y position [int]
        :return: None
        """
        self.input_controller.mouse_set(x_position, y_position)

    def click(self, mouse_button):
        """
        This feature clicks the mouse with a specific button - right, left or middle.
        Category: Mouse & Keyboard
        Echo: No
        :param mouse_button: The key to click [choice][left, right, middle]
        :return: None
        """
        self.input_controller.mouse_click(mouse_button)

    def mright(self, pixels):
        """
        This feature moves the mouse cursor to the right, according to the the number of pixels given.
        Category: Mouse & Keyboard
        Echo: No
        :param pixels: The number of pixels [int]
        :return: None
        """
        self.input_controller.mouse_move("right", pixels)
    
    def mleft(self, pixels):
        """
        This feature moves the mouse cursor to the left, according to the the number of pixels given.
        Category: Mouse & Keyboard
        Echo: No
        :param pixels: The number of pixels [int]
        :return: None
        """
        self.input_controller.mouse_move("left", pixels)
    
    def mup(self, pixels):
        """
        This feature moves the mouse cursor to the up, according to the the number of pixels given.
        Category: Mouse & Keyboard
        Echo: No
        :param pixels: The number of pixels [int]
        :return: None
        """
        self.input_controller.mouse_move("up", pixels)
    
    def mdown(self, pixels):
        """
        This feature moves the mouse cursor to the right, according to the the number of pixels given.
        Category: Mouse & Keyboard
        Echo: No
        :param pixels: The number of pixels [int]
        :return: None
        """
        self.input_controller.mouse_move("down", pixels)

    def scroll(self, direction, pixels):
        """
        This feature scrolls the page up or down, according the amount of pixels and the scrolling direction.
        Category: Mouse & Keyboard
        Echo: No
        :param direction: The direction of scrolling [choice][up, down]
        :param pixels: The amount of pixels to scroll [int]
        :return: None
        """
        if direction == "down":
            pixels *= -1
        self.input_controller.mouse_scroll(pixels)

    def key(self, key):
        """
        This feature presses on one specific key on the keyboard.
        Category: Mouse & Keyboard
        Echo: No
        :param key: The key to press [string]
        :return: None
        """
        try:
            self.input_controller.keyboard_press(key)
        except:
            message = "The key entered is not valid"
            self.serverScript.update_communication_channel("Error", message)

    def keys(self, keys):
        """
        This feature presses on several keys on the keyboard.
        Category: Mouse & Keyboard
        Echo: No
        :param keys: The list of keys to press [text]
        :return: None
        """
        replace_keys = {"windows": "cmd", "win": "cmd", "capslock": "caps_lock", "caps": "caps_lock",
                "escape": "esc", "del": "delete", "bs": "backspace", "ins": "insert"}
        for i in range(len(keys)):
            if keys[i] in replace_keys:
                keys[i] = replace_keys[keys[i]]
        if "cmd" in keys:
            keys.remove("cmd")
            keys.insert(0, "cmd")
        try:
            self.input_controller.keyboard_press(*keys)
        except:
            message = "Some of the keys entered may not been valid."
            # self.serverScript.update_communication_channel("Error", message)

    def type(self, text):
        """
        This feature virtually types a specific string to the screen.
        Category: Mouse & Keyboard
        Echo: No
        :param text: The text to type [string]
        :return: None
        """
        self.input_controller.keyboard_type(text)

    def url(self, url):
        """
        This feature opens a specific url in your default browser.
        Category: Web & Browsing
        Echo: No
        :param url: The url to open [string]
        :return: None
        """
        webbrowser.open(url)
        self.win("chrome", "focus", True)

    def loop(self, times, delay, action):
        """
        This feature runs a feature over and over again by the amount of times,
        and the delay between them.
        Category: Advanced Control
        Echo: No
        :param times: The amount of times to run the action [int]
        :param delay: The delay between each run [float]
        :param action: The feature to activate [function]
        :return: None
        """
        if times < 0 or delay < 0:
            message = "Cannot activate loop because either the delay or the number of times given is negative."
            self.serverScript.update_communication_channel("Warning", message)
        else:
            loop = threading.Thread(target=self.advanced_control_handler.loop, args=(times, delay, action), daemon=True)
            loop.start()
    
    def tloop(self, seconds, delay, action):
        """
        This feature runs an action over and over again until a certain number of seconds is passed.
        Category: Advanced Control
        Echo: No
        :param seconds: The amount of seconds until the looped is stopped [float]
        :param delay: The delay between each run [float]
        :param action: The feature to activate [function]
        :return: None
        """
        if seconds < 0 or delay < 0:
            message = "Cannot activate loop because either the delay or the number of seconds given is negative."
            self.serverScript.update_communication_channel("Warning", message)
        else:
            loop = threading.Thread(target=self.advanced_control_handler.tloop, args=(seconds, delay, action), daemon=True)
            loop.start()
    
    def timed(self, delay, action):
        """
        This feature runs an action a certain number of seconds after it called.
        and the delay between them.
        Category: Advanced Control
        Echo: No
        :param delay: The delay (in seconds) [float]
        :param action: The feature to activate [function]
        :return: None
        """
        if delay < 0:
            message = "Can't start timed feature, delay given is negative."
            self.serverScript.update_communication_channel("Warning", message)
        else:
            t = threading.Thread(target=self.advanced_control_handler.timed, args=(delay, action), daemon=True)
            t.start()

    def f(self, func_name):
        """
        This feature runs a custom function the user made.
        To build custom functions, open the cloud function manger in Ftp Remote.
        Category: Advanced Control
        Echo: No
        :param func_name: The name of the custom function [string]
        :return: None
        """
        func_content = self.serverScript.get_cloud_function(func_name)
        self.advanced_control_handler.f(func_content)

    def wait(self, num_of_seconds):
        """
        This feature is used only inside custom functions, to create delay between two different commands.
        Category: Advanced Control
        Echo: No
        :param num_of_seconds: The number of seconds to wait [float]
        :return: None
        """
        time.sleep(num_of_seconds)

    def msgbox(self, title, content):
        """
        This feature creates a message box using title and content.
        Category: Hacks & Tricks
        Echo: No
        :param title: The message box title [string]
        :param content: The content of the messagebox [string]
        :return: None
        """
        command = 'infobox "{}" "{}"'.format(content, title)
        self.nircmd_handler.nircmd_command(command)

    def cmd(self, command):
        """
        This feature runs a custom cmd command on windows command line prompt.
        It doesn't return anything. If you want to get a specific command's output, please use the feature "cmdget"
        Category: Advanced Control
        Echo: No
        :param command: The cmd command [string]
        :return: None
        """
        threading.Thread(target=self.cmd_handler.execute, args=(command,), daemon=True).start()

    def cmdget(self, command):
        """
        This feature runs a custom cmd command on windows command line prompt.
        It returns the cmd output as an echo.
        Category: Echoing & Information
        Echo: Yes [Getting output from command line...]
        :param command: The cmd command [string]
        :return: None
        """
        output = self.cmd_handler.check_output(command)
        self.serverScript.send_echo(output)

    def nircmd(self, command):
        """
        This feature is for developers only, and lunch a certain nircmd command.
        Nircmd is a command line utility Frank The Prank is using, and you can check its docs any time on the web.
        :param command: The nircmd command [string]
        :return: None
        """
        self.nircmd_handler.nircmd_command(command)

    def mget(self):
        """
        This feature is echoing the coordinates of the mouse cursor back to the remote.
        Category: Echoing & Information
        Echo: Yes [Getting mouse coordinates...]
        :return: None
        """
        cords = self.input_controller.get_mouse_coordinates()
        echo_message = "Current mouse coordinates are: ({0}, {1})".format(*cords)
        self.serverScript.send_echo(echo_message)

    def cd(self):
        """
        This feature ejects the cd-rom drive (if there is one on the host computer).
        Category: Power Control
        Echo: No
        :return: None
        """
        self.cmd('powershell (New-Object -com "WMPlayer.OCX.7").cdromcollection.item(0).eject()')

    def shutdown(self):
        """
        This feature will shut down the host computer.
        Warning: Frank The Prank will no longer be active after you will use this feature.
        Category: Power Control
        Echo: No
        :return: None
        """
        self.cmd("Shutdown.exe -s -t 00")

    def restart(self):
        """
        This feature will restart the host computer.
        Warning: Frank The Prank will no longer be active after you will use this feature.
        Category: Power Control
        Echo: No
        :return: None
        """
        self.cmd("Shutdown.exe -r -t 00")

    def logout(self):
        """
        This feature will cause the current user in the host's computer to log out.
        Category: Power Control
        Echo: No
        :return: None
        """
        self.cmd("shutdown.exe -l")

    def notepad(self, text):
        """
        This feature will open a blank notepad file, and type down whatever the user inserted in the "text" argument.
        Category: Hacks & Tricks
        Echo: No
        :param text: The text to type [text]
        :return:
        """
        text = "\n".join(text)
        threading.Thread(target=self.cmd, args=("notepad.exe", ), daemon=True).start()
        self.win("notepad", "focus", True)
        self.type(text)

    def screen(self, display_option):
        """
        This feature will switch the display settings, with the following options:
        Main - Only main display working
        Second - Only second display working
        Extend - The second screen will extend the main one
        Duplicate - Both screens will present the same picture
        Category: Power Control
        Echo: No
        :param display_option: The display option [choice] [Main, Second, Extend, Duplicate]
        :return: None
        """
        display_options = {"Main": "/internal", "Second": "/external", "Duplicate": "/clone", "Extend": "/extend"}
        displayswitch = PathsHandler.join(PathsHandler.extensions_dir, "DisplaySwitch.exe")
        if display_option in display_options.keys():
            self.cmd_handler.launch_executable(displayswitch, display_options[display_option])

    def say(self, text_to_speech):
        """
        This feature is causing the host computer to say a message out loud - in a real woman voice.
        Category: Hacks & Tricks
        Echo: No
        :param text_to_speech: The text to say [string]
        :return: None
        """
        command = 'PowerShell -Command "Add-Type -AssemblyName System.Speech; $S = New-Object -TypeName System.Speech.Synthesis.SpeechSynthesizer; $S.SelectVoice('
        command += f"'Microsoft Zira Desktop'); $S.Speak('{text_to_speech}');" + '"'
        self.cmd(command)

    def crazy(self, crazy_state):
        """
        This function enables or disables crazy mode.
        In crazy mode, the host mouse cursor will move in a strange way until it stopped.
        Category: Hacks & Tricks
        Echo: No
        :param crazy_state: The wanted crazy state [choice] [on, off]
        :return: None
        """
        if crazy_state == "on":
            self.input_controller.enable_crazy_mode(10)
        elif crazy_state == "off":
            self.input_controller.disable_crazy_mode()

    def setvol(self, volume, target="System volume"):
        """
        This feature sets the system volume or Ftp Sound Player volume to a specific volume, from 0 to 100.
        Category: Power Control
        Echo: No
        :param target: The volume target [choice] [System volume, Ftp sound player]
        :param volume: The system volume (1-100)[int]
        :return: None
        """
        if 0 <= volume <= 100:
            if target == "System volume":
                vol = int(655.35 * volume)
                self.nircmd("setsysvolume " + str(vol))
            else:
                self.audio_player.set_volume(volume)
        else:
            self.serverScript.update_communication_channel("Error", "The volume entered is invalid (not between 1 - 100)")

    def volup(self, volume):
        """
        This feature increases the system volume.
        Category: Power Control
        Echo: No
        :param volume: The volume to increase [int]
        :return: None
        """
        vol = int(655.35 * volume)
        self.nircmd("changesysvolume " + str(vol))

    def voldown(self, volume):
        """
        This feature decreases the system volume.
        Category: Power Control
        Echo: No
        :param volume: The volume to decrease [int]
        :return: None
        """
        vol = int(-655.35 * volume)
        self.nircmd("changesysvolume " + str(vol))

    def exit(self):
        """
        This feature cause Frank The Prank to stop working on the host computer.
        Category: Uncategorized
        Echo: No
        :return: None
        """
        self.serverScript.disconnect()
        sys.exit()

    def reset(self):
        """
        This feature resets Frank The Prank - Stops the current running process and starts another one.
        If something unexpected bug is happening, or you want to stop an active loop - this is the fix.
        Category: Uncategorized
        Echo: No
        :return: None
        """
        if PathsHandler.running_on_exe():
            SingleInstanceHandler.enable_reset()
            threading.Thread(target=self.cmd_handler.launch_executable,
                             args=(PathsHandler.application_path,),
                             daemon=False).start()
            self.exit()
        else:
            LoggingHandler.show_paragraph("Warning Information",
                                          "Frank The Prank Running in a .py file doesn't support 'reset' feature")

    def desktop(self):
        """
        This feature shows windows desktop, using Windows + d keyboard shortcut.
        Category: Shortcuts & Productivity
        Echo: No
        :return:
        """
        self.input_controller.keyboard_press(("cmd", "d"))

    def play(self, music=None):
        """
        This feature plays a sound file located in Ftp Music directory.
        Category: Apps & Multimedia
        Echo: No
        :param music: The sound track [dynamic: choice(music-file-dialog)]
        :return: None
        """
        if music is None:
            self.serverScript.update_communication_channel("Warning", "There are no music tracks in Ftp Music folder.")
        else:
            sound_file = PathsHandler.join(PathsHandler.music_dir, music)
            self.audio_player.play_sound(sound_file)

    def pause(self):
        """
        This feature pause / resume the music played in the background.
        If you want to stop the music completely, use stop feature.
        Category: Apps & Multimedia
        Echo: No
        :return: None
        """
        self.audio_player.pause()

    def stop(self):
        """
        This feature pause stop the musics music played in the background (that started with play feature).
        Category: Apps & Multimedia
        Echo: No
        :return: None
        """
        self.audio_player.stop_playing()

    def win(self, window_title, action, search_by_name=False):
        """
        This feature affects a certain window by its title (or part of it).
        Window modes (actions available):
        - focus: focus the target window
        - close: close the target window
        - min: minimize the target window
        - max: maximize the target window
        - enable: enables the target window
        - disable: disables the target window
        - flash: cause the target window to flash
        Category: Hacks & Tricks
        Echo: No
        :param window_title: The target window [dynamic: choice(target-window-dialog)]
        :param action: The window mode action [choice] [focus, close, min, max, enable, disable, flash]
        :return: None
        """
        right_title = ""
        windows = WindowsApiHandler.get_open_windows()
        if search_by_name:
            for title, name, exe in windows:
                if window_title.lower() in name.lower():
                    right_title = title
                    break
        else:
            window_name = window_title.split("]")[0].replace("[", "").strip()
            window_title = window_title.split("]")[1].strip().split("...")[0]
            for title, name, exe in windows:
                if window_name.lower() == name.lower():
                    right_title = title.split("...")[0]
                    break
            for title, name, exe in windows:
                if window_title.lower() in title.lower():
                    right_title = title.split("...")[0]
                    break
        if action == "focus":
            self.nircmd(f'win activate ititle "{right_title}"')
            self.nircmd(f'win max ititle "{right_title}"')
        else:
            self.nircmd(f'win {action} ititle "{right_title}"')

    def launch(self, search_name, program_path=""):
        """
        This feature allows the user to search for a specific program and launch it.
        Category: Apps & Multimedia
        Echo: No
        :param search_name: The program name [dynamic: string]
        :param program_path: The wanted program [dynamic: choice(launch-program-dialog)]
        :return: None
        """
        if program_path != "":
            os.startfile(program_path, "open")

    def back(self):
        """
        This feature launches alt + f4 to exit all kinds of focused applications
        Category: Apps & Multimedia
        Echo: No
        :return: None
        """
        self.keys(["alt", "f4"])

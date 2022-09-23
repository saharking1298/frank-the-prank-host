from Features import CmdCommandHandler
from Handlers import PathsHandler
import json
import os


class Favorites:
    @staticmethod
    def load_file():
        return json.load(open(PathsHandler.data_file, "r"))

    @staticmethod
    def load_all():
        return Favorites.load_file()["files.favorites"]

    @staticmethod
    def load(partner):
        data = Favorites.load_all()
        if partner in data:
            return data[partner]
        else:
            return []

    @staticmethod
    def update(items, partner):
        data = Favorites.load_all()
        data[partner] = items
        content = Favorites.load_file()
        content["files.favorites"] = data
        json.dump(content, open(PathsHandler.data_file, "w"))

    @staticmethod
    def exist(path, partner):
        items = Favorites.load(partner)
        return path in items

    @staticmethod
    def add(path, partner):
        items = Favorites.load(partner)
        items.append(path)
        Favorites.update(items, partner)

    @staticmethod
    def remove(path, partner):
        items = Favorites.load(partner)
        items.remove(path)
        Favorites.update(items, partner)


class FileManager:
    def __init__(self):
        self.partner = ""
        self.cmd = CmdCommandHandler()
        self.size_limit = 1000 ** 2  # 1MB

    def get_drives(self):
        # Getting all drive letters on the host machine
        output = self.cmd.check_output("fsutil fsinfo drives")
        drives = output.split("\n")[1].split(" ")[1:-1]
        return drives

    def listdir(self, path):
        result = []
        if path == "":
            drives = self.get_drives()
            for drive in drives:
                result.append({"name": drive, "type": "drive"})
        else:
            folders = []
            files = []
            try:
                entries = os.listdir(path)
            except (FileNotFoundError, PermissionError):
                return "Error"
            for entry in entries:
                if os.path.isfile(os.path.join(path, entry)):
                    files.append({"name": entry, "type": "." + entry.split(".")[-1]})
                elif os.path.isdir(os.path.join(path, entry)):
                    folders.append({"name": entry, "type": "folder"})
            result = folders + files
        return result

    def toggle_favorite(self, path, partner):
        favorite = False
        if path.startswith("\\"):
            path = path[1:]
        if Favorites.exist(path, partner):
            Favorites.remove(path, partner)
        else:
            favorite = True
            Favorites.add(path, partner)
        return {"success": True, "isFavorite": favorite}

    def get_favorites(self, partner):
        result = []
        items = Favorites.load(partner)
        for item in items:
            print(item)
            if os.path.isfile(item):
                result.append({"path": item, "type": "." + item.split("\\")[-1].split(".")[-1]})
            elif os.path.isdir(item):
                if len(item) > 3:
                    result.append({"path": item, "type": "folder"})
                else:
                    result.append({"path": item, "type": "drive"})
            else:
                result.append({"path": item, "type": "unknown"})
        return result

    def get_file_details(self, file):
        if os.path.isfile(file):
            stats = os.stat(file)
            return {
                "success": True,
                "details": {"size": stats.st_size, "lastModified": stats.st_mtime}
            }
        else:
            return {"success": False}

    def action_launch(self, event):
        try:
            os.startfile(event["file"])
            return {"success": True}
        except:
            return {"success": False}

    def action_fetch(self, file):
        if os.path.isfile(file):
            file_size = os.stat(file).st_size
            if file_size > 1000 ** 2:
                return {"success": False, "error": "File is too large"}
            else:
                try:
                    content = open(file, "rb").read()
                    return {"success": True, "file": content}
                except (PermissionError, IOError, FileNotFoundError):
                    return {"success": False, "error": "Couldn't read file"}
        return {"success": False, "error": "File does not exist"}

    def action_edit(self, event):
        if type(event) == dict and "path" in event and "content" in event:
            try:
                with open(event["path"], "w+", encoding="utf-8") as file:
                    file.read()  # Check if file is plain text
                    file.write(event["content"])
            except (UnicodeEncodeError, IOError, PermissionError, FileNotFoundError):
                return {"success": False, "error": "Couldn't read file"}
        return {"success": False, "error": "Request incomplete"}

    def action_delete(self, event):
        if type(event) == dict and "file" in event:
            if os.path.isfile(event["file"]):
                return {"success": False, "error": "Can't delete file"}
            else:
                return {"success": False, "error": "File does not exist"}
        else:
            return {"success": False, "error": "Request incomplete"}

    def action_rename(self, event, partner):
        print(event)
        if type(event) == dict and "src" in event and "dst" in event:
            if "\\" in event["dst"]:
                return {"success": False, "error": "Can't rename file"}
            src = event["src"]
            dst = os.path.join(os.path.dirname(src), event["dst"])
            if os.path.isfile(src):
                try:
                    os.rename(src, dst)
                    if Favorites.exist(src, partner):
                        Favorites.remove(src, partner)
                        Favorites.add(dst, partner)
                    return {"success": True}
                except (IOError, FileNotFoundError, PermissionError) as e:
                    print(e)
                    return {"success": False, "error": "Can't rename file"}
            else:
                return {"success": False, "error": "File does not exist"}
        else:
            return {"success": False, "error": "Request incomplete"}

    def action_move(self, event):
        if type(event) == dict and "src" in event and "dst" in event:
            src = event["src"]
            dst = event["dst"]
            if os.path.isfile(src) and os.path.isdir(dst):
                try:
                    raise Exception  # Disabling file moving feature
                    os.rename(src, dst)
                    return {"success": True}
                except (IOError, FileNotFoundError, PermissionError):
                    return {"success": False, "error": "Can't rename file"}
            else:
                return {"success": False, "error": "Can't rename file"}
        else:
            return {"success": False, "error": "Request incomplete"}

    def handle(self, command, event, partner):
        result = None
        if command == "files.listDir":
            result = self.listdir(event)
        elif command == "files.toggleFavorite":
            result = self.toggle_favorite(event, partner)
        elif command == "files.getFavorites":
            result = self.get_favorites(partner)
        elif command == "files.getDetails":
            result = self.get_file_details(event)
        elif command == "files.launch":
            result = self.action_launch(event)
        elif command == "files.fetch":
            result = self.action_fetch(event)
        elif command == "files.edit":
            result = self.action_edit(event)
        elif command == "files.delete":
            result = self.action_delete(event)
        elif command == "files.rename":
            result = self.action_rename(event, partner)
        elif command == "files.move":
            result = self.action_move(event)
        return result


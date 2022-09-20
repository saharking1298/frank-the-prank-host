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
        self.cmd = CmdCommandHandler()

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
                result.append({"path": item, "type": ".".join(item.split(".")[:-1])})
            elif os.path.isdir(item):
                if len(item) > 3:
                    result.append({"path": item, "type": "folder"})
                else:
                    result.append({"path": item, "type": "drive"})
            else:
                result.append({"path": item, "type": "unknown"})
        return result

    def handle(self, command, event, partner):
        result = None
        if command == "files.listDir":
            result = self.listdir(event)
        elif command == "files.toggleFavorite":
            result = self.toggle_favorite(event, partner)
        elif command == "files.getFavorites":
            result = self.get_favorites(partner)
        return result


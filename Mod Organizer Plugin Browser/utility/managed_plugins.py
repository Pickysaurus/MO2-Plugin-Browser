import json
import logging
from pathlib import Path
from typing import Iterable, Dict
from PyQt6.QtCore import QCoreApplication, QObject, pyqtSignal, QThread # type: ignore
from ..nexusmods_api import NexusModsAPI
from ..utility.update_checker import UpdateChecker
from ..constants import VERSION
from .plugin_types import ManagedPlugin

this_plugin: ManagedPlugin = {
    "uid": "9856949946062",
    "name": "Plugin Browser for Mod Organizer 2",
    "mod_id": 1742,
    "version": VERSION.displayString(),
    "group_id": 7243541,
    "files": None
}

class ManagedPlugins:

    def __init__(self, api: NexusModsAPI) -> None:
        app_dir = Path(QCoreApplication.applicationDirPath())
        plugins_meta = app_dir / "plugins" / "managed_plugins.json"
        self.logger = logging.getLogger("MO2PluginsInstalledManager")
        self.file_path = plugins_meta
        self.managed = self.get_installed_from_file()
        self.check_for_updates_async(api)

    def get_installed_from_file(self) -> Dict[str, ManagedPlugin]:
        result = {}
        result[this_plugin["uid"]] = this_plugin
        if not self.file_path.exists():
            return result
        
        try:
            raw = self.file_path.read_text(encoding="utf-8")
            if not raw:
                return result
            parsed = json.loads(raw)
            parsed[this_plugin["uid"]] = this_plugin
            self.logger.debug(f"Loaded plugins from JSON {parsed}")
            return parsed
        except (json.JSONDecodeError, Exception) as e:
            self.logger.error(f"Failed to load managed plugins: {e}")
            return result

    def add_managed_plugin(self, plugin: ManagedPlugin):
        """Adds or updates a plugin in the managed list."""
        uid = plugin.get("uid")
        self.logger.debug(f"Adding managed plugin ({uid}) {plugin}")
        if uid:
            self.managed[uid] = plugin
            self._save_to_disk()

    def remove_managed_plugin(self, uid: str):
        self.logger.debug(f"Removing managed plugin ({uid})")
        if uid in self.managed:
            del self.managed[uid]
            self._save_to_disk()

    def get_managed_plugin(self, uid: str) -> ManagedPlugin | None:
        return self.managed[uid]

    def is_managed(self, uid: str) -> bool:
        """Quick check if a mod is currently managed."""
        return uid in self.managed
    
    def set_update_available(self, uid: str, version: str, file_id: int):
        self.logger.debug(f"Adding update info to managed plugin ({uid})")
        if uid in self.managed:
            self.managed[uid]["latest_file_id"] = file_id
            self.managed[uid]["latest_version"] = version
            self._save_to_disk()

    def clear_update(self, uid: str):
        self.logger.debug(f"Clearing update info to managed plugin ({uid})")
        if uid in self.managed:
            del self.managed[uid]["latest_file_id"]
            del self.managed[uid]["latest_version"]
            self._save_to_disk()

    def _save_to_disk(self):
        """Internal helper to sync the dictionary to the JSON file."""
        self.logger.debug(f"Saving to disk at {self.file_path} :: {self.managed}")
        try:
            self.file_path.write_text(
                json.dumps(self.managed, indent=4), 
                encoding="utf-8"
            )
        except Exception as e:
            self.logger.error(f"Could not save managed plugins to disk: {e}")

    def get_all(self) -> Iterable[ManagedPlugin]:
        return self.managed.values()
    
    def check_for_updates_async(self, api: NexusModsAPI):
        """Spins up a background thread to check for updates."""
        self._thread = QThread()
        self._worker = UpdateWorker(api, self)

        self._worker.moveToThread(self._thread)

        self._thread.started.connect(self._worker.run)
        self._worker.finished.connect(self._thread.quit)
        self._worker.finished.connect(self._worker.deleteLater)
        self._thread.finished.connect(self._thread.deleteLater)

        from ..messenger import BUS
        self._worker.update_found.connect(
            lambda uid, file, plugin: BUS.update_available.emit(uid, file, plugin)
        )

        self._thread.start()
        print(f"Thread is running: {self._thread.isRunning()}")
        print(f"Thread priority: {self._thread.priority()}")



    
class UpdateWorker(QObject):
    finished = pyqtSignal()
    update_found = pyqtSignal(str, dict, object) # uid, latest_file_data

    def __init__(self, api: NexusModsAPI, manager: ManagedPlugins):
        super().__init__()
        self.api = api
        self.manager = manager
        self.update_checker = UpdateChecker(api)

    def run(self):
        """The main loop that runs inside the QThread."""
        self.api.check_thread_affinity()
        for plugin in self.manager.get_all():
            self.manager.logger.info(f"Checking for update on {plugin['name']}")
            uid = plugin["uid"]
            mod_id = plugin["mod_id"]
            group_id = plugin["group_id"]
            version = plugin["version"]

            try:
                # Get all files in the group
                latest_file = self.update_checker.check_plugin_for_update(plugin=plugin)
                if latest_file: 
                    self.manager.set_update_available(
                        uid, 
                        version=latest_file["file"]["version"],
                        file_id=int(latest_file["file"]["game_scoped_id"])
                    )
                    self.update_found.emit(uid, latest_file, plugin)
            except Exception as e:
                self.manager.logger.warning(f"Update check failed for {plugin['name']}: {e}")
        self.finished.emit()
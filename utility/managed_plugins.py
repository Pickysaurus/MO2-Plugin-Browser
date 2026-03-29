import json
import logging
import mobase # type: ignore
from pathlib import Path
from typing import TypedDict, Iterable, Dict, Optional, List, NotRequired
from PyQt6.QtCore import QCoreApplication, QObject, pyqtSignal, QThread # type: ignore
from ..nexusmods_api import NexusModsAPI

class ManagedPlugin(TypedDict):
    uid: str
    name: str
    mod_id: int
    version: str
    group_id: int
    files: Optional[List[str]]
    latest_version: NotRequired[str]
    latest_file_id: NotRequired[int]

this_plugin: ManagedPlugin = {
    "uid": "9856949946062",
    "name": "Plugin Browser for Mod Organizer 2",
    "mod_id": 1742,
    "version": mobase.VersionInfo(1, 0, 0, mobase.ReleaseType.CANDIDATE).displayString(),
    "group_id": 0,
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

    def run(self):
        """The main loop that runs inside the QThread."""
        self.api.check_thread_affinity()
        self.manager.logger.info("Background update check started.")
        for plugin in self.manager.get_all():
            self.manager.logger.info(f"Checking for update on {plugin['name']}")
            uid = plugin["uid"]
            mod_id = plugin["mod_id"]
            group_id = plugin["group_id"]
            version = plugin["version"]

            try:
                # 1. Fetch files from Nexus
                resp = self.api.get_mod_files(mod_id)
                if not resp or "modFiles" not in resp:
                    continue

                # 2. Filter by group and sort by newest timestamp
                group_files = [f for f in resp["modFiles"] if f.get("groupId") == group_id]
                if not group_files:
                    continue

                latest = sorted(group_files, key=lambda x: x.get("date", 0), reverse=True)[0]
                
                # 3. Compare timestamps
                if latest.get("version") != version:
                    self.manager.logger.info(f"Found update on {plugin['name']}")
                    # Update local data and notify UI
                    self.manager.set_update_available(
                        uid, 
                        latest["version"], 
                        latest["fileId"]
                    )
                    self.update_found.emit(uid, latest, plugin)

            except Exception as e:
                self.manager.logger.warning(f"Update check failed for {plugin['name']}: {e}")

        self.finished.emit()
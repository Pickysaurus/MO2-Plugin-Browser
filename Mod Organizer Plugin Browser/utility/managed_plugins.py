import json
import logging
from pathlib import Path
from typing import Iterable, Dict
from PyQt6.QtCore import QCoreApplication, QObject, pyqtSignal, QThread # type: ignore
from ..nexusmods_api import NexusModsAPI
from ..utility.update_checker import UpdateChecker
from ..constants import VERSION
from .plugin_types import ManagedPlugin, ManagedVersion, AllManagedPlugins

this_plugin: ManagedPlugin = {
    "uid": "9856949946062",
    "versions": { 
        "724341": {
        "name": "Plugin Browser for Mod Organizer 2",
        "version": VERSION.displayString(),
        "mod_file_id": 7243541,
        "files": None
        }
    },
}

class ManagedPlugins:

    def __init__(self, api: NexusModsAPI) -> None:
        app_dir = Path(QCoreApplication.applicationDirPath())
        plugins_meta = app_dir / "plugins" / "managed_plugins.json"
        self.logger = logging.getLogger("MO2PluginsInstalledManager")
        self.file_path = plugins_meta
        self.api = api
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
            parsed = self.valid_or_migrate_stored(parsed) 
            return parsed
        except (json.JSONDecodeError, Exception) as e:
            self.logger.error(f"Failed to load managed plugins: {e}")
            return result
    
    def valid_or_migrate_stored(self, raw: Dict[str, dict]) -> Dict[str, ManagedPlugin]:
        mods = raw.items()
        result = {}
        updated = False
        for mod in mods:
            [mod_uid, plugin] = mod
            # if these fields exist, we've got an older manifest
            mod_name = plugin.get("name")
            mod_version = plugin.get("version")
            group_id = plugin.get("group_id")
            latest_version = plugin.get("latest_version")
            latest_file_id = plugin.get("latest_file_id")
            if mod_name and mod_version and group_id:
                self.logger.info(f"Migrating plugin data to new format: {mod_uid}: {plugin}")
                extra_metadata = None
                # We need some data from the API to complete the new object.
                try:
                    api_versions = self.api.get_versions_for_file(group_id)
                    if not api_versions: raise Exception("No data returned from API")
                    matches = [v for v in api_versions if v["version"] == mod_version]
                    if len(matches): extra_metadata = matches[0]
                    else: raise Exception(f"No matching versions for {mod_version} in {api_versions}")
                except Exception as e: 
                    self.logger.warning(f"Could not fetch metadata for {group_id}: {e}")
                # Build the new plugin data
                new_format: ManagedPlugin = {
                    "uid": mod_uid,
                    "versions": {
                        str(group_id): {
                            "name": mod_name,
                            "version": mod_version,
                            "mod_file_id": group_id,
                            "file_uid": extra_metadata.get("id") if extra_metadata else "",
                            "files": plugin.get("files")
                        }
                    }
                }
                if latest_version: new_format["latest_version"] = latest_version
                if latest_file_id: new_format["latest_file_id"] = latest_file_id
                result[mod_uid] = new_format
                updated = True
            else: result[mod_uid] = plugin

        if updated: self._save_to_disk()
        
        assert result is AllManagedPlugins
        return result

    def add_managed_plugin(self, mod_uid: str, mod_file_id: str, version: ManagedVersion):
        """Adds or updates a plugin in the managed list."""
        self.logger.debug(f"Adding managed plugin {mod_uid} -> {mod_file_id} -> {version}")
        if mod_uid in self.managed:
            self.managed[mod_uid]["versions"][mod_file_id] = version
        else:
            mod_entry: ManagedPlugin = { "uid": mod_uid,"versions": { mod_file_id: version } }
            self.logger.debug(f"Creating new mod entry {self.managed}, {mod_uid}:{mod_entry},")
            self.managed[mod_uid] = mod_entry
        
        self._save_to_disk()

    def remove_managed_plugin(self, mod_uid: str, mod_file_id):
        self.logger.debug(f"Removing managed plugin ({mod_uid}-{mod_file_id})")

        mod = self.managed.get(mod_uid)
        if not mod: return

        versions = mod.get("versions", {})
        if mod_file_id in versions:
            self.logger.debug(f"Removing version ({versions[mod_file_id]})")
            del versions[mod_file_id]
        
        if not versions:
            self.logger.debug(f"Removing mod entry ({mod})")
            self.managed.pop(mod_uid, None)

        self._save_to_disk()

    def get_managed_plugin(self, uid: str) -> ManagedPlugin | None:
        return self.managed[uid]

    def is_managed(self, uid: str) -> bool:
        """Quick check if a mod is currently managed."""
        return uid in self.managed
    
    def is_file_managed(self, file_id: str) -> list[str]:
        """Check if the mod file ID passed is one of the installed plugins. Returns an array of UIDs."""
        matches = []

        for plugin in self.managed.values():
            if plugin.get("versions", {}).get(file_id, None): 
                if plugin["versions"][file_id].get("file_uid"): 
                    matches.append(plugin["versions"][file_id].get("file_uid"))

        return matches
    
    def set_update_available(self, uid: str, mod_file_id: str, version: str, file_id: int):
        self.logger.debug(f"Adding update info to managed plugin ({uid}-{mod_file_id})")
        mod = self.managed[uid]
        if not mod:
            return
        
        mod_file = mod["versions"][mod_file_id]

        if not mod_file:
            return

        mod_file["latest_file_id"] = file_id
        mod_file["latest_version"] = version
        
        self._save_to_disk()

    def clear_update(self, mod_uid: str, mod_file_id: str):
        self.logger.debug(f"Clearing update info to managed plugin ({mod_uid})")
        version = self.managed[mod_uid][mod_file_id]
        if version:
            del version["latest_file_id"]
            del version["latest_version"]
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
            for version in (plugin["versions"] or {}).items():
                [key, ver] = version
                self.manager.logger.debug(f"Checking for update on MO2 plugin '{ver.get("name", "Unknown Plugin")}'")
                uid = plugin["uid"]

                try:
                    # Get all files in the group
                    latest_file = self.update_checker.check_plugin_for_update(ver)
                    if latest_file: 
                        self.manager.set_update_available(
                            uid=uid, 
                            mod_file_id=key,
                            version=latest_file["version"],
                            file_id=int(latest_file["id"])
                        )
                        self.update_found.emit(uid, latest_file, ver)
                except Exception as e:
                    self.manager.logger.warning(f"Update check failed for {ver['name']}: {e}")
        self.finished.emit()
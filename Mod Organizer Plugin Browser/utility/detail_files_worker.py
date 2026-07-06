import logging
from PyQt6.QtCore import QObject, pyqtSignal # type: ignore
from ..nexusmods.nexus_mods_types import ModNode, NexusModsFilesInGroup
from ..nexusmods_api import NexusModsAPI

LOGGER = logging.getLogger("DetailFilesWorker")

class DetailFilesWorker(QObject):
    finished = pyqtSignal()
    files_loaded = pyqtSignal(list)
    error = pyqtSignal(str)

    def __init__(self, api: NexusModsAPI, mod: ModNode):
        super().__init__()
        self.api = api
        self.mod_uid = mod["uid"]
        self.mod_id = mod["modId"]
        self.mod = mod

    def run(self):
        try:
            mod_files = self.api.get_mod_files_v3(self.mod_uid)
            if not mod_files:
                self.error.emit(f"No files returned for this mod. {mod_files or "None"}")
                return

            file_list = self.api.get_mod_files(self.mod_id)

            if not file_list or "modFiles" not in file_list:
                self.error.emit(f"No files returned for this mod. {file_list or "None"}")
                return

            # Example of a second request per file group:
            for file_obj in mod_files:
                group_id = file_obj["id"]
                filtered = [f for f in file_list["modFiles"] if str(f["groupId"]) == str(group_id)] if group_id else []
                filtered.sort(key=lambda x: int(x.get("fileId", "999.0")), reverse=True)
                LOGGER.debug(f"Filtered version for group {group_id}: {len(filtered)}")
                file_obj["versions"] = filtered

            self.files_loaded.emit(mod_files)

        except Exception as exc:
            self.error.emit(str(exc))
        finally:
            self.finished.emit()
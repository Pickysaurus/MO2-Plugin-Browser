import logging
from ..nexusmods_api import NexusModsAPI
from .managed_plugins import ManagedPlugins
from .maintenence_manager import BUS

LOGGER = logging.getLogger("MO2PluginUpdateChecker")

class UpdateChecker:
    def __init__(self, api: NexusModsAPI, manager: ManagedPlugins) -> None:
        self.api = api
        self.manager = manager

    def check_plugin_for_update(self, uid: str):
        managed = self.manager.get_managed_plugin(uid)
        if not managed: return

        current_group = managed['group_id']

        try:
            files_resp = self.api.get_mod_files(managed['mod_id'])
            if not files_resp or 'modFiles' not in files_resp:
                raise Exception(f"No files for MO2 plugin: {managed['name']}")
            group_files = [
                f for f in files_resp['modFiles']
                if f.get("groupId") == current_group
            ]

            if not group_files:
                LOGGER.warning(f"No files found in group {current_group} for {managed['name']}")
                return None

            sorted_files = sorted(
                group_files, 
                key=lambda x: x.get('date', 0), 
                reverse=True
            )

            latest_file = sorted_files[0]

            if latest_file['version'] != managed['version']:
                LOGGER.info(f"Update found for {managed['name']}: {managed['version']} -> {latest_file.get('version')}")
                self.manager.set_update_available(uid, latest_file["version"], latest_file["fileId"])
                BUS.update_available.emit(uid, latest_file, managed)
                return latest_file
            else:
                return None
        except Exception as e:
            LOGGER.error(f"Failed to check for updates on {managed['name']}: {e}")
            return None


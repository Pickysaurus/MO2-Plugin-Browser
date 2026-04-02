import logging
import re
from typing import Literal
from ..nexusmods_api import NexusModsAPI
from .plugin_types import ManagedPlugin
from .maintenence_manager import BUS
from ..nexusmods.nexus_mods_types import NexusModsFilesInGroup

LOGGER = logging.getLogger("MO2PluginUpdateChecker")

class UpdateChecker:
    def __init__(self, api: NexusModsAPI) -> None:
        self.api = api

    def check_plugin_for_update(self, plugin: ManagedPlugin) -> NexusModsFilesInGroup | None:
        if not plugin: return

        group_id = plugin['group_id']
        version = plugin['version']

        try:
            grouped_files = self.api.get_files_in_group(group_id)
            if not grouped_files:
                LOGGER.warning(f"No grouped files found for {plugin['name']}")
                return None
            filtered = [f for f in grouped_files if f["file"]["category"] == "main"]
            filtered.sort(key=lambda x: float(x.get("position", "999.0")))
            LOGGER.debug(f"Update filtered files result {filtered}") 
            if filtered:
                latest_file = filtered[0]
                latest_version = latest_file["file"]["version"]
                is_update = compare_versions(latest_version, version)
                if is_update == 1:
                    LOGGER.info(f"Found update on {plugin['name']}")
                    # Update local data
                    return latest_file
                elif is_update == 0: 
                    LOGGER.info(f"No update for {plugin['name']}")
                    return None
                else:
                    LOGGER.info(f"Installed version of {plugin['name']} is newer than the version on Nexus Mods: Current ({version}) -> Nexus Mods ({latest_version})")
                    
        except Exception as e:
            LOGGER.error(f"Failed to check for updates on {plugin['name']}: {e}")
            return None

def parse_version(version_str: str) -> tuple[int, ...]:
    """Cleans a version string for comparison"""
    cleaned = version_str.lower().lstrip('v').strip()
    return tuple(map(int, re.findall(r'\d+', cleaned)))#

def compare_versions(version_a: str, version_b: str) -> Literal[-1, 1, 0]:
    """
    Compares two version strings.
    Returns:
    1 if version_a is newer than version_b
    0 if they are the same
    -1 if version_a is older than version_b
    """
    # 1. Extract digits and convert to tuples of integers
    # This handles 'v1.0.1' -> (1, 0, 1)
    t1 = parse_version(version_a)
    t2 = parse_version(version_b)

    # 2. Pad the shorter tuple with zeros so they are the same length
    # This ensures 1.1 == 1.1.0
    max_len = max(len(t1), len(t2))
    t1_padded = t1 + (0,) * (max_len - len(t1))
    t2_padded = t2 + (0,) * (max_len - len(t2))

    # 3. Perform comparison
    if t1_padded > t2_padded:
        return 1
    elif t1_padded < t2_padded:
        return -1
    else:
        return 0
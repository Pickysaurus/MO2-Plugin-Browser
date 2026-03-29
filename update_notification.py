import logging
from PyQt6.QtCore import QCoreApplication # type: ignore
import mobase # type: ignore
from .messenger import BUS
from .utility.managed_plugins import ManagedPlugin

LOGGER = logging.getLogger("MO2PluginBrowserUpdateNotice")

class PluginBrowserUpdates(mobase.IPluginDiagnose):
    __outdated_plugins: dict[str, ManagedPlugin] = {}
    __organizer: mobase.IOrganizer
    __problem_id: int = 0

    def __init__(self):
        super().__init__()

    def init(self, organizer: mobase.IOrganizer):
        self.__organizer = organizer
        BUS.update_available.connect(self._on_update_found)
        BUS.update_installed.connect(self._on_update_installed)
        return True
    
    def name(self) -> str: return "Plugin Browser Updates"
    def localizedName(self) -> str: return "Plugin Browser Updates"
    def author(self) -> str: return "Pickysaurus"
    def description(self) -> str: return "Monitors for plugin updates"
    def version(self) -> mobase.VersionInfo: return mobase.VersionInfo(1, 0, 0)
    def settings(self) -> list: return []

    def activeProblems(self) -> list[int]:
        if self.__outdated_plugins:
            return [self.__problem_id]
        return []
    
    def shortDescription(self, problem_id: int) -> str: return "Mod Organizer plugins have updates available."

    def fullDescription(self, problem_id: int) -> str:
        count = len(self.__outdated_plugins)
        list = ""
        for p in self.__outdated_plugins.values():
            list += f"- <b>{p["name"]}</b>: {p["version"]} -> {p.get("latest_version", "???")}<br>" 
        return f"New versions of {count} installed Mod Organizer 2 extensions are available.<br><br>{list}"
    
    def hasGuidedFix(self, problem_id: int) -> bool: return False

    def startGuidedFix(self, problem_id: int):
        """This triggers when the user clicks 'Fix' in the warning list."""
        BUS.focus_plugin_browser.emit()

    def tr(self, value: str): return QCoreApplication.translate("PluginBrowserUpdates", value)

    # Custom code
    
    def _on_update_found(self, uid: str, latest_file, managed_plugin):
        LOGGER.info(f"Plugin Update notice update found {uid}: {managed_plugin['name']} {managed_plugin['version']} -> {latest_file['version']}")
        if uid not in self.__outdated_plugins:
            self.__outdated_plugins[uid] = managed_plugin

    def _on_update_installed(self, uid: str):
        if uid in self.__outdated_plugins:
            del self.__outdated_plugins[uid]
    
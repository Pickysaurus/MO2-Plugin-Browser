import logging
import mobase # type: ignore
from PyQt6.QtGui import QIcon # type: ignore
from PyQt6.QtCore import QCoreApplication # type: ignore

from .nexusmods_api import NexusModsAPI
from .nexusmods.nexus_mods_types import PluginCategoryType, ModSortType
from .ui.ui_main import BrowserDialog
from .utility.managed_plugins import ManagedPlugins
from .utility.maintenence_manager import MaintenanceManager
from .messenger import BUS

LOGGER = logging.getLogger("MO2Plugins")

class PluginBrowser(mobase.IPluginTool):
    def __init__(self):
        super().__init__()
        self.__organizer = None
        self.main_window = None
        self.dialog = None
        self.api = None
        self.last_error = None
        
        self.maintenence_manager = MaintenanceManager()
        BUS.focus_plugin_browser.connect(self.focus_browser)
    
    def __tr(self, text: str) -> str:
        return QCoreApplication.translate(self.name(), text)

    def init(self, organizer: mobase.IOrganizer) -> bool:
        self.__organizer = organizer
        self.__organizer.onUserInterfaceInitialized(self.onUserInterfaceInitializedCallback)
        self.api = NexusModsAPI(organizer)
        self.installed_handler = ManagedPlugins(self.api)
        return True

    def displayName(self) -> str:
        return "Plugin Browser"
    
    def name(self) -> str:
        return "Plugin Browser"

    def author(self) -> str:
        return "Pickysaurus"

    def description(self) -> str:
        return "Install and manage plugins for MO2"
    
    def tooltip(self) -> str:
        return "Install and manage plugins for MO2"

    def version(self) -> mobase.VersionInfo:
        return mobase.VersionInfo(1, 0, 0, mobase.ReleaseType.FINAL)

    def isActive(self):
        try:
            return self.__organizer.pluginSetting(self.name(), "enabled") # pyright: ignore[reportOptionalMemberAccess]
        except Exception:
            return True

    def settings(self) -> list[mobase.PluginSetting]:
        return [
            mobase.PluginSetting("enabled", self.__tr("Enables the plugin"), True),
            mobase.PluginSetting("api_key", self.__tr("Nexus Mods API Key"), "")
        ]

    def display(self):
        """This function runs when the user clicks the tool in MO2."""
        if self.main_window is None:
            return
        
        if self.dialog is None:
            assert self.api is not None
            assert self.__organizer is not None
            self.dialog = BrowserDialog( 
                load_callback = self.fetch_and_display,
                api=self.api,
                organizer=self.__organizer,
                installed_manager=self.installed_handler
            )
            self.load_initial_results()
        self.dialog.show()
        self.dialog.raise_()

    def icon(self):
        return QIcon()
    
    def onUserInterfaceInitializedCallback(self, main_window):
        self.main_window = main_window

    def load_initial_results(self):
        assert self.api is not None
        searchRes = self.api.get_mo2_extensions()
        plugins = self.get_installed_plugins()
        uids = [plugin['uid'] for plugin in plugins] if plugins else []

        if self.dialog and searchRes:
            self.dialog.display_mods(searchRes.get("mods", {}), uids)
        
        if plugins:
            LOGGER.debug(f"Found plugins: {plugins}")

    def fetch_and_display(self, offset=0, filter_category: PluginCategoryType="All", sort: ModSortType ="Endorsements", search_term=None):
        """ This is the 'Load Callback' function. """

        assert self.api is not None

        if filter_category == "Installed":
            installed = self.get_installed_plugins()
            uids = [install["uid"] for install in installed] if installed else []
            LOGGER.debug(f"Installed plugin UIDs: {uids}")
            data = self.api.get_mods_by_uid(
                uids=uids,
                offset=offset
            )
            LOGGER.debug(f"Mods by UID lookup: {data.get("modsByUid") if data else "BLANK"}")
            data = data.get("modsByUid") if data else None
        else: 
            # 1. Fetch data from your NexusAPI class
            # Ensure your get_mo2_extensions method accepts these arguments
            data = self.api.get_mo2_extensions(
                offset=offset, 
                filter_category=filter_category, 
                sort=sort,
                search_term=search_term
            )
            data = data.get("mods") if data else None
        
        # 2. Get the current list of installed mods from MO2
        if self.__organizer:
            installed = self.get_installed_plugins()
        
        uids = [plugin['uid'] for plugin in installed] if installed else []
        
        # 3. Push the data into the Dialog's display method
        if self.dialog and data:
            self.dialog.display_mods(data, uids)
    
    def get_installed_plugins(self):
        if self.__organizer is None:
            return
        plugin_list = self.installed_handler.get_all()
        return plugin_list
    
    def focus_browser(self):
        LOGGER.info("Focus requested pluginbrowser")
        self.display()
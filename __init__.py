import mobase # type: ignore
from .plugin_browser import PluginBrowser
from .update_notification import PluginBrowserUpdates

def createPlugins() -> list[mobase.IPlugin]:
    return [
        PluginBrowser(),
        PluginBrowserUpdates()
    ]
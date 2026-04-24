from PyQt6.QtCore import QObject, pyqtSignal # type: ignore

class SignalBus(QObject):
    relaunch_required = pyqtSignal(bool)
    relaunch_mo2 = pyqtSignal()
    queue_delete_on_restart_op = pyqtSignal(str)
    queue_move_on_restart_op = pyqtSignal(str, str)
    error_occurred = pyqtSignal(str, str, object) # Title, detail, exception
    focus_plugin_browser = pyqtSignal()
    update_available = pyqtSignal(str, object, object)
    update_installed = pyqtSignal(str)

# Export out a bus we can use to trigger such events from anywhere.
BUS = SignalBus()
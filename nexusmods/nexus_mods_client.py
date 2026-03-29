import json
import logging
import mobase # type: ignore
from typing import Optional, Any, Dict
from PyQt6.QtNetwork import QNetworkAccessManager, QNetworkRequest, QNetworkReply # type: ignore
from PyQt6.QtCore import QUrl, QEventLoop, Qt, QThread # type: ignore
from PyQt6.QtWidgets import QApplication # type: ignore

from .nexus_mods_errors import NexusModsAPIKeyMissingError, NexusModsAuthError, NexusModsRateLimitError, NexusModsNetworkError, NexusModsAPIError

LOGGER = logging.getLogger("MO2PluginsNexusClient")

class NexusClient:
    def __init__(self, organizer: mobase.IOrganizer, base_url: str = "https://api.nexusmods.com/"):
        self.manager = QNetworkAccessManager()
        self._organizer = organizer
        self.base_url = base_url.rstrip("/")
        self._organizer.onUserInterfaceInitialized(self.on_ui_ready)
        self.api_key: str | None = None
        self.api_key_validated: bool = False

    def on_ui_ready(self, main_window):
        """Perform validation once when the UI starts, rather than inside the getter."""
        key = self._get_api_key()
        if key and not self.api_key_validated:
            try:
                self.validate_api_key(key)
                self.api_key_validated = True
                LOGGER.debug("Validated saved API key successfully!")
            except Exception as e:
                LOGGER.warning(f"Saved API key is invalid: {e}")
                self.api_key = None
                self.api_key_validated = False
    
    def check_thread_affinity(self):
        """Ensures the NetworkManager belongs to the current execution thread."""
        current_thread = QThread.currentThread()
        if self.manager.thread() != current_thread:
            LOGGER.debug(f"Re-initializing NetworkManager for thread: {current_thread}")
            # Create a new manager specifically for this background thread
            self.manager = QNetworkAccessManager()

    def _get_api_key(self) -> Optional[str]:
        """Get's the user's API key if we already have it."""
        if self.api_key:
            return self.api_key
        
        saved_api_key = self._organizer.pluginSetting("Plugin Browser", "api_key")
        if isinstance(saved_api_key, str) and saved_api_key.strip():
            self.api_key = saved_api_key.strip()
            # Log the variable, not the method!
            LOGGER.debug(f"Loaded API key from settings: {self.api_key[:5]}***")
            return self.api_key
        
        return None
    
    def validate_api_key(self, api_key: str) -> dict[str, str]:
        path = "v1/users/validate.json"
        url = QUrl(f"{self.base_url}/{path}")
        response = self.send_request("GET", url, requires_auth=False, override_headers={ b'apikey' : api_key.encode("utf8") })
        if api_key != self.api_key:
            self.save_api_key(api_key)
        assert response
        return response
    
    def save_api_key(self, api_key: str, validated: bool = True):
        self.api_key = api_key
        self.api_key_validated = validated
        self._organizer.setPluginSetting("Plugin Browser", "api_key", str(api_key))
        LOGGER.info("API key saved to Plugin Browser -> api_key")


    def _build_request(self, url: QUrl, requires_auth: bool, override_headers: Optional[Dict[bytes, bytes]] = None) -> Optional[QNetworkRequest]:
        """Creates a QNetworkRequest with standard headers and API Key."""
        request = QNetworkRequest(url)
        request.setRawHeader(b"User-Agent", b"MO2-PluginBrowser/1.0")
        request.setRawHeader(b"Content-Type", b"application/json")
        request.setRawHeader(b"Accept", b"application/json")

        if override_headers:
            for key, value in override_headers.items():
                request.setRawHeader(key, value)

        api_key = self._get_api_key()
        if requires_auth and not api_key:
            LOGGER.error("Nexus Client: Authentication required but no API Key found.")
            raise NexusModsAPIKeyMissingError("User API Key is missing")
        
        if api_key:
            request.setRawHeader(b"apikey", api_key.encode("utf-8"))
        
        return request

    def send_request(self, method: str, url: QUrl, body: Any = None, requires_auth: bool = False, override_headers: Optional[Dict[bytes, bytes]] = None) -> Optional[dict]:
        """Sends a synchronous request using a local QEventLoop."""
        self.check_thread_affinity()

        request = self._build_request(url, requires_auth, override_headers)
        if not request:
            return None

        application_instance = QApplication.instance()
        is_main_thread = QThread.currentThread() == (application_instance.thread() if application_instance else None)
        if is_main_thread:
            QApplication.setOverrideCursor(Qt.CursorShape.WaitCursor)
        reply = None

        LOGGER.debug(f"Sending {method} request. Body: {body}, URL: {url}")
        
        try:
            # Determine method
            if method == "GET":
                reply = self.manager.get(request)
            elif method in ["POST", "PUT"]:
                data = json.dumps(body or {}).encode("utf-8")
                reply = self.manager.post(request, data) if method == "POST" else self.manager.put(request, data)

            if not reply:
                return None

            # Synchronous wait
            loop = QEventLoop()
            reply.finished.connect(loop.quit)
            loop.exec()

            return self._process_reply(reply)
        finally:
            if reply:
                reply.deleteLater()
            if is_main_thread:
                QApplication.restoreOverrideCursor()

    def _process_reply(self, reply: QNetworkReply) -> Optional[dict]:
        """Handles error checking and JSON parsing for the network reply."""
        if reply.error() != QNetworkReply.NetworkError.NoError:
            LOGGER.error(f"Network Error ({reply.error()}): {reply.errorString()}")
            return None

        status = reply.attribute(QNetworkRequest.Attribute.HttpStatusCodeAttribute)
        if status in [401, 403]:
            LOGGER.error("Nexus API: Access Denied (401/403).")
            raise NexusModsAuthError(f"Permissions error: {status}")
        if status == 429:
            LOGGER.warning("Nexus API: Rate limit exceeded (429).")
            raise NexusModsRateLimitError("Rate limited")
        if status >= 500:
            LOGGER.warning("Nexus Mods API: Server Error")
            raise NexusModsNetworkError(f"Unexpected error: {status}")

        try:
            raw = reply.readAll().data().decode("utf-8")
            return json.loads(raw) if raw else None
        except (json.JSONDecodeError, UnicodeDecodeError) as e:
            LOGGER.error(f"Failed to parse response: {e}")
            assert NexusModsAPIError(f"Failed to parse response {e}")
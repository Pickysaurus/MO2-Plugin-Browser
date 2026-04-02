import logging
from mobase import IOrganizer # type: ignore
from PyQt6.QtWidgets import ( # type: ignore
    QDialog, QWidget, QVBoxLayout, QPushButton, QScrollArea, QLabel, QFrame, QHBoxLayout,
    QGraphicsOpacityEffect
)
from PyQt6.QtCore import Qt, QUrl # type: ignore
from PyQt6.QtGui import QPixmap, QDesktopServices # type: ignore

from ..nexusmods.nexus_mods_types import ModNode
from ..nexusmods_api import NexusModsAPI
from ..nexusmods.nexus_mods_errors import NexusModsAPIKeyMissingError
from ..utility.image_loader import ImageManager
from ..utility.managed_plugins import ManagedPlugins
from ..utility.plugin_installer import PluginInstaller
from .ui_api_key_entry import APIKeyEntry
from ..messenger import BUS
from ..utility.update_checker import UpdateChecker

LOGGER = logging.getLogger("MO2PluginsDetailView")

class DetailView(QWidget):
    def __init__(
            self, back_callback, 
            organizer: IOrganizer, 
            image_manager: ImageManager, 
            api: NexusModsAPI, 
            installManager: ManagedPlugins,
            pluginInstaller: PluginInstaller,
            parent=None
    ):
        super().__init__(parent)
        self.api = api
        self._organizer = organizer
        self.installed_manager = installManager
        self.installer = pluginInstaller
        self.image_manager = image_manager
        self.update_checker_temp = UpdateChecker(api)
        self.mod_node: ModNode | None = None
        layout = QVBoxLayout(self)

        # Connect to the installer events
        self.installer.download_started.connect(self._on_download_started)
        self.installer.install_complete.connect(self._on_install_finished)
        self.installer.error_occurred.connect(self._on_error)

        # Back Button
        self.back_button = QPushButton("← Back to Results")
        self.back_button.setFixedWidth(150)
        self.back_button.clicked.connect(back_callback)
        layout.addWidget(self.back_button)

        # Scroll Area Setup
        detail_scroll = QScrollArea()
        detail_scroll.setWidgetResizable(True)
        detail_scroll.setFrameShape(QFrame.Shape.NoFrame)
        
        self.content = QWidget()
        self.content_layout = QVBoxLayout(self.content)
        
        # Mod page title
        self.title = QLabel("Mod Name")
        self.title.setStyleSheet("font-size: 20pt; font-weight: bold;")

        # UID
        self.uid_label = QLabel("UID: ")

        # Top section including image and buttons
        self.top_section = self.setup_top_section()

        # Avatar
        uploader_by_label = QLabel("Uploaded by")
        uploader_by_label.setStyleSheet("font-size: 16px; font-weight: bold;")
        self.uploader_layout = QHBoxLayout()
        self.uploader_layout.setAlignment(Qt.AlignmentFlag.AlignLeft)
        self.avatar_label = QLabel()
        self.avatar_label.setFixedSize(30, 30)
        self.avatar_label.setCursor(Qt.CursorShape.PointingHandCursor)
        self.author_name = QLabel("Unknown author")
        self.author_name.setStyleSheet("font-size: 16px; font-weight: bold; color: palette(link)")
        self.author_name.setCursor(Qt.CursorShape.PointingHandCursor)
        self.author_name.setOpenExternalLinks(True)
        self.author_name.setTextInteractionFlags(Qt.TextInteractionFlag.LinksAccessibleByMouse)

        self.uploader_layout.addWidget(uploader_by_label)
        self.uploader_layout.addWidget(self.avatar_label)
        self.uploader_layout.addWidget(self.author_name)
        
        # Plugin Summary
        self.summary = QLabel("Summary...")
        self.summary.setWordWrap(True)

        self.content_layout.addWidget(self.title)
        self.content_layout.addWidget(self.uid_label)
        self.content_layout.addWidget(self.top_section)
        self.content_layout.addLayout(self.uploader_layout)
        self.content_layout.addWidget(self.summary)
        self.content_layout.addStretch()
        
        detail_scroll.setWidget(self.content)
        layout.addWidget(detail_scroll)

    def setup_top_section(self):
        top_section = QWidget()
        top_section.setStyleSheet("""
            background: palette(mid);
            border-radius: 4px;                           
        """)
        top_section_layout = QHBoxLayout(top_section)

        # Feature Image
        self.image_label = QLabel("Loading...")
        self.image_label.setFixedSize(320, 180)
        self.image_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.image_label.setStyleSheet("background-color: #222; border-radius: 4px; color: #fff;")

        # Buttons
        button_layout = QVBoxLayout()
        button_styles = """
            font-size: 16px;
            font-weight: bold;
            border-radius: 4px;
            background: palette(highlight);
            color: palette(highlight-text);
            padding: 4px;
        """
        button_layout.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.endorse_btn = QPushButton("👍ENDORSE")
        self.endorse_btn.setVisible(False)
        self.endorse_btn.setStyleSheet(button_styles)
        self.endorse_btn.clicked.connect(self.handle_endorse_clicked)
        self.download_btn = QPushButton("DOWNLOAD")
        self.download_btn.setDisabled(True)
        self.download_btn.setFixedWidth(200)
        self.download_btn.setStyleSheet(button_styles)
        self.download_btn.clicked.connect(self.handle_download_clicked)
        self.update_btn = QPushButton("UPDATE")
        self.update_btn.setFixedWidth(200)
        self.update_btn.setStyleSheet(button_styles)
        self.update_btn.setVisible(False)
        self.update_btn.clicked.connect(self.handle_update_clicked)
        self.uninstall_btn = QPushButton("UNINSTALL")
        self.uninstall_btn.setFixedWidth(200)
        self.uninstall_btn.setStyleSheet(button_styles)
        self.uninstall_btn.clicked.connect(self.handle_uninstall_clicked)
        self.nexus_mods_btn = QPushButton("VIEW ON NEXUS MODS")
        self.nexus_mods_btn.setFixedWidth(200)
        self.nexus_mods_btn.setStyleSheet(button_styles)
        self.nexus_mods_btn.setDisabled(True)
        self.nexus_mods_btn.clicked.connect(self.open_mod_page)

        button_layout.addWidget(self.endorse_btn)
        button_layout.addWidget(self.download_btn)
        button_layout.addWidget(self.update_btn)
        button_layout.addWidget(self.uninstall_btn)
        button_layout.addWidget(self.nexus_mods_btn)

        top_section_layout.addWidget(self.image_label)
        top_section_layout.addSpacing(20)
        top_section_layout.addLayout(button_layout)
        top_section_layout.addSpacing(20)

        return top_section


    def update_data(self, mod_node: ModNode):
        self.mod_node = mod_node
        if mod_node["modId"]:
            self.nexus_mods_btn.setEnabled(True)
        uid = mod_node["uid"]
        self.title.setText(mod_node.get('name', 'Unknown'))
        self.uid_label.setText(f"UID: {mod_node.get("uid", "UID Not Available")}")
        self.summary.setText(mod_node.get('summary', 'No summary available.'))
        self.download_btn.setEnabled(True)
        uploader = mod_node.get("uploader", {})
        uploader_name = uploader.get("name", "Invalid User")
        uploader_id = uploader.get("memberId")
        
        if uploader_id:
            # Set the text as an HTML link
            link = f'<a href="https://www.nexusmods.com/users/{uploader_id}" style="color: palette(link); text-decoration: none;">{uploader_name}</a>'
            self.author_name.setText(link)
        else:
            self.author_name.setText(uploader_name)
        
        thumbnail = mod_node.get('thumbnailUrl')
        if thumbnail:
            self.image_manager.fetch(thumbnail, self._set_image)
        else:
            self.image_label.setText("No Thumbnail")
        
        author_avatar = uploader.get("avatar", None)
        if author_avatar:
            self.image_manager.fetch(author_avatar, self._set_avatar, True)
        
        if self.installed_manager.is_managed(str(uid)):
            installed_data = self.installed_manager.get_managed_plugin(str(uid))
            if installed_data is not None:
                version_installed = installed_data.get("version", "Unknown")
                self.download_btn.setText(f"INSTALLED (v {version_installed})")
                if installed_data.get("latest_version") is not None:
                    self.update_btn.setEnabled(True)
                    self.update_btn.setVisible(True)
                    self.update_btn.setText(f"UPDATE (v{installed_data.get("latest_version")})")
            self.download_btn.setDisabled(True)
            self.endorse_btn.setVisible(True)
            if mod_node["viewerEndorsed"] == True:
                self.endorse_btn.setText("✅ ENDORSED")
            else:
                self.endorse_btn.setText("👍 ENDORSE")
        else:
            self.download_btn.setText(f"DOWNLOAD")
            self.set_button_enabled(self.download_btn)
            self.update_btn.setVisible(False)
            self.endorse_btn.setVisible(False)
            self.endorse_btn.setEnabled(True)

    def _set_image(self, pixmap: QPixmap | None, url: str):
        if pixmap and not self.isHidden():
            self.image_label.setPixmap(pixmap.scaled(
                self.image_label.size(), 
                Qt.AspectRatioMode.KeepAspectRatioByExpanding,
                Qt.TransformationMode.SmoothTransformation
            ))

    def _set_avatar(self, pixmap: QPixmap | None, url: str):
        if pixmap and not self.isHidden():
            self.avatar_label.setPixmap(pixmap.scaled(
                self.avatar_label.size(), 
                Qt.AspectRatioMode.KeepAspectRatioByExpanding,
                Qt.TransformationMode.SmoothTransformation
            ))
    
    def open_mod_page(self):
        if not self.mod_node:
            return
        
        mod_id = self.mod_node.get("modId")
        url = QUrl(f"https://nexusmods.com/site/mods/{mod_id}")
        QDesktopServices.openUrl(url)
    
    def handle_download_clicked(self):
        if not self.mod_node: return
    
        try:
            self.installer.start_install(self.mod_node, "install", None)
        except NexusModsAPIKeyMissingError:
            api_key_entry = APIKeyEntry(self.api, self.content)
            if api_key_entry.exec() == QDialog.DialogCode.Accepted:
                LOGGER.debug("API key entry successful")
                return self.handle_download_clicked()
            else:
                LOGGER.warning("User did not provide API key, download cancelled")
                return None
            
    def handle_update_clicked(self):
        if not self.mod_node: return

        plugin = self.installed_manager.get_managed_plugin(self.mod_node.get("uid"))
        newId = plugin.get("latest_file_id", None) if plugin else None
    
        try:
            self.installer.start_install(self.mod_node, "update", newId)
        except NexusModsAPIKeyMissingError:
            api_key_entry = APIKeyEntry(self.api, self.content)
            if api_key_entry.exec() == QDialog.DialogCode.Accepted:
                LOGGER.debug("API key entry successful")
                return self.handle_download_clicked()
            else:
                LOGGER.warning("User did not provide API key, download cancelled")
                return None
    
    def handle_uninstall_clicked(self):
        if not self.mod_node: return

        installed_data = self.installed_manager.get_managed_plugin(self.mod_node["uid"])
        if not installed_data or not installed_data["files"]: return

        for file in installed_data["files"]:
            BUS.queue_delete_on_restart_op.emit(file)
        
        BUS.relaunch_required.emit(True)
        
        self.installed_manager.remove_managed_plugin(installed_data["uid"])
        self.uninstall_btn.setEnabled(False)

    def handle_endorse_clicked(self):
        if not self.mod_node: return
        id = self.mod_node["modId"]
        if not id: return

        prev_state = self.mod_node["viewerEndorsed"]

        self.endorse_btn.setEnabled(False)
        success = self.api.endorse_mod("site", id) if prev_state != True else self.api.abstain_mod("site", id)
        if success:
            if prev_state == True:
                self.endorse_btn.setText("👍 ENDORSE")
                self.mod_node["viewerEndorsed"] = False
            else:
                self.endorse_btn.setText("✅ ENDORSED")
                self.mod_node["viewerEndorsed"] = True
        else:
            LOGGER.warning(f"Failed to endorse {self.mod_node["name"]}")
            
        self.endorse_btn.setEnabled(True)

    def _on_download_started(self, dl_id):
        self.download_btn.setEnabled(False)

    def _on_install_finished(self, uid):
        self.download_btn.setVisible(False)

    def _on_error(self, message, e):
        if isinstance(e, NexusModsAPIKeyMissingError):
            api_key_entry = APIKeyEntry(self.api, self.content)
            if api_key_entry.exec() == QDialog.DialogCode.Accepted:
                LOGGER.debug("API key entry successful")
                return self.handle_download_clicked()
            else:
                LOGGER.warning("User did not provide API key, download cancelled")
                return None
        LOGGER.error(f"Error downloading mod: {message}, {str(e)}");
        self.download_btn.setEnabled(True)
        self.download_btn.setVisible(True)

    def set_button_enabled(self, button: QPushButton, enabled: bool = True):
        opacity = 0.7 if not enabled else 1
        effect = QGraphicsOpacityEffect(button)
        effect.setOpacity(opacity)
        button.setEnabled(enabled)
        button.setGraphicsEffect(effect)
import logging
from typing import Callable
from PyQt6.QtCore import Qt # type: ignore
from PyQt6.QtWidgets import ( # type: ignore
    QComboBox,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QSizePolicy,
    QToolButton,
    QVBoxLayout,
    QWidget,
)

from ..nexusmods.nexus_mods_types import NexusModsV3ModFile, ModFilesResult

LOGGER = logging.getLogger("MO2PluginsTile")

class FileCard(QWidget):
    def __init__(
        self,
        mod_file: NexusModsV3ModFile,
        handle_download: Callable[[int], None],
        handle_update: Callable[[int], None],
        has_installed: list[str] = [],
        has_update: bool = False,
        parent=None,
    ):
        LOGGER.debug(f"Creating file card for {mod_file or file_name}")
        super().__init__(parent)

        # Data props
        self.focused_version = mod_file["versions"][0] if mod_file["versions"] and mod_file["versions"][0] else None
        self.installed_uids = has_installed
        self.install_action = handle_download
        self.update_action = handle_update
        self.mod_file_id = mod_file["id"]

        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
        self.setAttribute(Qt.WidgetAttribute.WA_StyledBackground, True)
        self.setStyleSheet("""
            background-color: palette(mid);
            border-radius: 4px;
        """)

        self._main_layout = QVBoxLayout(self)
        self._main_layout.setContentsMargins(8, 8, 8, 8)
        self._main_layout.setSpacing(6)

        row_layout = QHBoxLayout()
        row_layout.setContentsMargins(0, 0, 0, 0)
        row_layout.setSpacing(8)

        self.expand_btn = QToolButton()
        self.expand_btn.setText("▸")
        self.expand_btn.setCheckable(True)
        self.expand_btn.setFixedSize(24, 24)
        self.expand_btn.clicked.connect(self._toggle_changelog)

        self.version_selector = QComboBox()
        self.version_selector.setMinimumWidth(140)
        self.version_selector.setSizeAdjustPolicy(QComboBox.SizeAdjustPolicy.AdjustToContents)

        if mod_file and mod_file["versions"]:
            for file in mod_file["versions"]: 
                self.version_selector.addItem(str(file["version"]), file)
        else: self.version_selector.addItem("Latest")

        ## Connect the selector
        self.version_selector.currentIndexChanged.connect(self._handle_version_change)

        self.install_btn = QPushButton("Install")
        self.install_btn.setStyleSheet( """
            font-weight: bold;
            border-radius: 4px;
            background: palette(highlight);
            color: palette(highlight-text);
            padding: 4px;
        """)
        self.install_btn.setFixedWidth(80)
        self.install_btn.clicked.connect(self._on_install)

        file_name = (mod_file.get("name") if mod_file else "Unknown file")
        if len(has_installed) > 0: file_name = f"✓ {file_name}"
        if has_update: file_name = f"🔄️ {file_name}"
        self.name_label = QLabel(file_name)
        self.name_label.setStyleSheet("font-size: 16px; font-weight: bold; border: 0;")
        self.name_label.setWordWrap(True)
        self.name_label.setAlignment(Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter)
        self.name_label.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)

        row_layout.addWidget(self.name_label)
        row_layout.addStretch()
        row_layout.addWidget(self.expand_btn)
        row_layout.addWidget(self.version_selector)
        row_layout.addWidget(self.install_btn)
        

        self._main_layout.addLayout(row_layout)

        self.changelog_container = QWidget(self)
        self.changelog_container.setStyleSheet("""
            border-top: 1px solid palette(base);
            background-color: palette(alt);                     
            padding-top: 8px;
        """)
        self.changelog_container.setVisible(False)
        self.changelog_layout = QVBoxLayout(self.changelog_container)
        self.changelog_layout.setContentsMargins(0, 0, 0, 0)
        self.changelog_layout.setSpacing(4)

        intialChanglog = mod_file["versions"][0]["changelogText"] if mod_file["versions"] else ["No changelog available"]
        self.changelog_label = QLabel("".join(intialChanglog))
        self.changelog_label.setWordWrap(True)
        self.changelog_layout.addWidget(self.changelog_label)
        self._main_layout.addWidget(self.changelog_container)

        if mod_file and mod_file["versions"]: self._handle_version_change(0)

    def _toggle_changelog(self):
        self.changelog_container.setVisible(self.expand_btn.isChecked())
        self.expand_btn.setText("▾" if self.expand_btn.isChecked() else "▸")

    def _handle_version_change(self, index: int):
        selected: ModFilesResult = self.version_selector.itemData(index)
        if selected is None:
            selected = self.version_selector.currentData()
        if selected:
            version = selected.get("version")
            file_id = selected.get("fileId")
            uid = selected["uid"]
            self.focused_version = selected
            LOGGER.info(f"Selected version: {version} file id: {file_id} for {self.mod_file_id}")
            changelog = selected["changelogText"] or ["No changelog available"]
            self.changelog_label.setText(''.join(changelog))
            if uid in self.installed_uids: 
                self.install_btn.setText("Installed")
                self.install_btn.setEnabled(False)
            elif len(self.installed_uids) > 0:
                self.install_btn.setText("Switch")
                self.install_btn.setEnabled(True)
            else:
                self.install_btn.setText("Install")
                self.install_btn.setEnabled(True)

    def _on_install(self):
        self.install_btn.setText("Queued")
        self.install_btn.setEnabled(False)
        if self.focused_version:
            file_id = self.focused_version["fileId"]
            if len(self.installed_uids) > 0:
                self.update_action(file_id)
            else: 
                self.install_action(file_id)
        
    def _on_install_finished(self):
        self.install_btn.setText("Installed")
    
    def _on_install_failed(self):
        self.install_btn.setText("Failed")
    
    def _reset_install_btn(self):
        self.install_btn.setText("Install")
        self.install_btn.setEnabled(True)

    def set_changelog(self, text: str | None):
        if text:
            self.changelog_label.setText(text)
        else:
            self.changelog_label.setText("No changelog available")
        self.changelog_container.setVisible(bool(text) and self.expand_btn.isChecked())

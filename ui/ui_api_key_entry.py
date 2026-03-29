from typing import Optional
from PyQt6.QtWidgets import ( # type: ignore
    QDialog, QWidget, QVBoxLayout, QPushButton, QLabel,
    QLineEdit, QDialogButtonBox, QHBoxLayout, QGraphicsOpacityEffect
)
from PyQt6.QtCore import QUrl # type: ignore
from PyQt6.QtGui import QDesktopServices # type: ignore
from ..nexusmods_api import NexusModsAPI


class APIKeyEntry(QDialog):
    def __init__(self, api: NexusModsAPI, parent: Optional[QWidget] = None):
        super().__init__(parent)
        self.api = api
        self.setWindowTitle("API Key Required")
        self.setMinimumWidth(400)
        self.setStyleSheet("""
            QDialog {
                background-color: #2d2d2d;
                border: 1px solid #3f3f3f;
            }
            QLabel {
                color: #e0e0e0;
                font-size: 12px;
                margin-bottom: 4px;
            }
            QLabel#Header {
                font-size: 14px;
                font-weight: bold;
                color: #ffffff;
            }
            QLineEdit {
                background-color: #1e1e1e;
                color: #ffffff;
                border: 1px solid #555555;
                border-radius: 3px;
                padding: 8px;
                selection-background-color: #444444;
            }
            QLineEdit:focus {
                border: 1px solid #0078d4;
            }
            QPushButton {
                background-color: #454545;
                color: white;
                border: none;
                padding: 6px 15px;
                border-radius: 2px;
                min-width: 80px;
            }
            QPushButton:disabled, QPushButton[role="primary"]:disabled {
                opacity: 0.7;
            }
            QPushButton:hover {
                background-color: #505050;
            }
            QPushButton[role="primary"] {
                background-color: #0078d4;
            }
            QPushButton[role="primary"]:hover {
                background-color: #2b88d8;
            }
        """)

        layout = QVBoxLayout(self)
        layout.setSpacing(12)
        layout.setContentsMargins(20, 20, 20, 20)

        # Header
        header = QLabel("Nexus Mods API key required")
        header.setObjectName("Header")
        layout.addWidget(header)


        # Subtext
        body = QLabel("Due to a bug in Mod Organizer 2's plugins API, you need to manually enter your API key.")
        body.setWordWrap(True)
        layout.addWidget(body)

        # Input
        self.line_edit = QLineEdit(self)
        self.line_edit.setPlaceholderText("Paste your MO2 API key here...")
        self.line_edit.setEchoMode(QLineEdit.EchoMode.Password)
        layout.addWidget(self.line_edit)

        # Validation and get key Buttons
        button_group = QHBoxLayout()
        btn_opn_settings = QPushButton("Get API key")
        btn_opn_settings.clicked.connect(self.open_api_key_settings_page)
        button_group.addWidget(btn_opn_settings)
        btn_validate = QPushButton("Verify Key")
        button_group.addWidget(btn_validate)
        layout.addLayout(button_group)

        # Validate feedback
        status_label = QLabel("")
        status_label.setWordWrap(True)
        layout.addWidget(status_label)

        # Buttons
        buttons = QDialogButtonBox(QDialogButtonBox.StandardButton.Save | QDialogButtonBox.StandardButton.Cancel)
        save_button = buttons.button(QDialogButtonBox.StandardButton.Save)
        if save_button:
            save_button.setEnabled(False)
            save_button.setProperty("role", "primary")
            save_button.setText("Save API Key")
            self.set_button_opacity(save_button, 0.7)
        
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)

        def validate_key():
            key_to_test = self.line_edit.text().strip()
            if not key_to_test:
                status_label.setText("Please enter an API key first")
                return
            try:
                user_data = self.api.validate_api_key(key_to_test)
                name = user_data.get("name", "User")
                status_label.setText(f"✅ Success! Hello, {name}.")
                status_label.setStyleSheet("color: #58c4dd; font-weight: bold;")
                if save_button: 
                    save_button.setEnabled(True)
                    self.set_button_opacity(save_button, 1.0)
            except Exception as e:
                status_label.setText(f"❌ Invalid Key: {str(e)}")
                status_label.setStyleSheet("color: #ff6b6b;")

        btn_validate.clicked.connect(validate_key)
    
    def get_api_key(self) -> str:
        """Helper to return the text after the dialog is accepted."""
        return self.line_edit.text().strip() 
    
    def set_button_opacity(self, button, opacity):
        effect = QGraphicsOpacityEffect(button)
        effect.setOpacity(opacity)
        button.setGraphicsEffect(effect)
    
    def open_api_key_settings_page(self):
        url = QUrl(f"https://www.nexusmods.com/settings/api-keys#:~:text=Request%20Api%20Key-,Mod%20Organizer%202,-Mod%20Organizer%202")
        QDesktopServices.openUrl(url)
from PyQt6.QtWidgets import QFrame, QVBoxLayout, QLabel, QLineEdit, QPushButton, QListWidget # type: ignore
from PyQt6.QtCore import QTimer # type: ignore

class Sidebar(QFrame):
    def __init__(self, on_search, on_reset, on_category, on_check_for_updates, parent=None):
        super().__init__(parent)
        self.on_check_for_updates = on_check_for_updates
        self.setFixedWidth(200)
        self.setStyleSheet("""
            Sidebar { 
                border-radius: 4px;
                border-right: 1px solid palette(mid);
                background: palette(mid);
            }
            QLabel { 
                color: palette(highlighted-text); 
                font-weight: bold;
                margin-top: 10px;
            }
        """)
        layout = QVBoxLayout(self)

        layout.addWidget(QLabel("Search Keywords:"))
        self.search_input = QLineEdit()
        self.search_input.clearFocus()
        self.search_input.setStyleSheet("""
            QLineEdit {
                background-color: palette(base);
                color: palette(text);
                border: 1px solid palette(mid);
                border-radius: 4px;
                padding: 4px;
            }
            QLineEdit:focus {
                border: 1px solid palette(highlight);
            }                            
        """)
        self.search_input.returnPressed.connect(on_search)
        layout.addWidget(self.search_input)

        self.reset_btn = QPushButton('Clear Search')
        self.reset_btn.clicked.connect(on_reset)
        self.reset_btn.setEnabled(False)

        # Prevent this button triggering when the user presses enter on the search
        self.reset_btn.setAutoDefault(False)
        self.reset_btn.setDefault(False)

        layout.addWidget(self.reset_btn)

        layout.addSpacing(20)
        layout.addWidget(QLabel("Browse Plugins"))
        self.category_list = QListWidget()
        self.category_list.setStyleSheet("""
            QListWidget {
                background-color: transparent;
                border: none;
                outline: none;
            }
            QListWidget::item {
                padding: 5px;
                border-radius: 4px;
            }
            QListWidget::item:selected {
                background-color: palette(highlight);
                color: palette(highlighted-text);
            }               
        """)
        self.category_list.addItems(["All", "Plugins", "Themes", "Installed"])
        self.category_list.setCurrentItem(self.category_list.item(0))
        self.category_list.itemClicked.connect(on_category)
        layout.addWidget(self.category_list)
        layout.addStretch()
        self.update_check_btn = QPushButton("Check for Updates")
        self.update_check_btn.clicked.connect(self.handle_update_check_press)
        layout.addWidget(self.update_check_btn)

    def handle_update_check_press(self):
        self.update_check_btn.setDisabled(True)
        update_count: int = self.on_check_for_updates()
        self.update_check_btn.setText(f"{update_count} updates available")
        QTimer.singleShot(60000, self.reset_update_button)

    def reset_update_button(self):
        self.update_check_btn.setDisabled(False)
        self.update_check_btn.setText("Check for updates")
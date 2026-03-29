from PyQt6.QtWidgets import (  # type: ignore
    QGridLayout, QWidget, QVBoxLayout, QHBoxLayout,
    QPushButton, QScrollArea, QLabel, QFrame, QComboBox
) 
from PyQt6.QtCore import Qt # type: ignore


class PluginGridView(QWidget):
    def __init__(self, next_page, prev_page, refresh, parent=None):
        super().__init__(parent)

        self.setStyleSheet("background-color: transparent;")
        
        # 1. Set the layout DIRECTLY on 'self' (the PluginGridView widget)
        self.main_layout = QVBoxLayout(self)
        self.main_layout.setContentsMargins(10, 10, 10, 10)

        # 2. Setup and add the Header row
        # We pass the layout directly to the helper
        self.setup_header(self.main_layout, refresh)

        # 3. Scroll Area Setup
        self.scroll_area = QScrollArea()
        self.scroll_area.setWidgetResizable(True)
        self.scroll_area.setFrameShape(QFrame.Shape.NoFrame)
        self.scroll_area.setStyleSheet("background-color: transparent;")

        self.container = QWidget()
        self.container.setStyleSheet("background-color: transparent;")
        self.grid = QGridLayout(self.container)
        self.grid.setAlignment(Qt.AlignmentFlag.AlignTop | Qt.AlignmentFlag.AlignLeft)

        self.scroll_area.setWidget(self.container)
        self.main_layout.addWidget(self.scroll_area)

        # 4. Pagination Setup
        # We call the setup and then add the resulting layout
        self.setup_pagination(next_page, prev_page)
        self.main_layout.addLayout(self.nav_layout)
    
    def setup_header(self, parent_layout, refresh):
        header_widget = QFrame()
        header_widget.setStyleSheet("""
            QFrame {
                border-bottom: 1px solid palette(mid);
                margin-bottom: 5px;
            }
            QLabel {
                color: palette(highlighted-text);
                font-weight: bold;
                border: none;
            }
        """)
        header_row_layout = QHBoxLayout(header_widget)

        # Total Label (left side)
        self.totalPlugins = 0
        self.totalDisplay = QLabel(f"Total Plugins: {self.totalPlugins}")
        self.totalDisplay.setStyleSheet("font-weight: bold; padding: 5px; color: #555;")
        
        # Add to the horizontal row, NOT the grid_page_layout
        header_row_layout.addWidget(self.totalDisplay)

        # Spacer to push the next part to the right side
        header_row_layout.addStretch()

        # Combobox for sorting
        self.sort_dropdown = QComboBox()
        self.sort_dropdown.addItems([
            "Endorsements",
            "Downloads",
            "Created At",
            "Updated At"
        ])
        self.sort_dropdown.setFixedWidth(150)
        self.sort_dropdown.setStyleSheet("""
            QComboBox {
                background-color: palette(base);
                color: palette(text);
                border: 1px solid palette(mid);
                padding: 3px;
                border-radius: 4px;
            }
        """)
        self.sort_dropdown.currentTextChanged.connect(lambda: refresh(True))
        header_row_layout.addWidget(self.sort_dropdown)

        parent_layout.addWidget(header_widget)
    
    def setup_pagination(self, next_page, prev_page):
        self.nav_layout = QHBoxLayout()
        self.prev_button = QPushButton("< Previous")
        self.next_button = QPushButton("Next >")
        self.page_label = QLabel("Page 1")

        button_style = """
            QPushButton {
                padding: 5px 15px;
                background-color: palette(button);
                color: palette(button-text);
                border: 1px solid palette(mid);
                border-radius: 4px;
            }
            QPushButton:hover {
                background-color: palette(highlight);
                color: palette(highlighted-text);
            }
            QPushButton:disabled {
                color: palette(mid);
                background-color: palette(window);
            }
        """

        self.prev_button.setStyleSheet(button_style)
        self.next_button.setStyleSheet(button_style)
        self.page_label.setStyleSheet("color: palette(window-text); font-weight: bold;")
        
        self.prev_button.setFixedWidth(120)
        self.next_button.setFixedWidth(120)
        self.prev_button.setEnabled(False)
        
        self.prev_button.clicked.connect(prev_page)
        self.next_button.clicked.connect(next_page)

        self.nav_layout.addStretch()
        self.nav_layout.addWidget(self.prev_button)
        self.nav_layout.addSpacing(20)
        self.nav_layout.addWidget(self.page_label)
        self.nav_layout.addSpacing(20)
        self.nav_layout.addWidget(self.next_button)
        self.nav_layout.addStretch()
from PyQt6.QtWidgets import QWidget, QHBoxLayout, QLabel, QPushButton # type: ignore
from PyQt6.QtCore import pyqtSlot, Qt # type: ignore

from ..messenger import BUS

class ErrorBanner(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setVisible(False)

        self.setAttribute(Qt.WidgetAttribute.WA_StyledBackground, True)

        self.setObjectName("ErrorBanner")

        self.setStyleSheet("""
            #ErrorBanner {
                background-color: #4d0b0b;
                border-bottom: 2px solid #ff4d4d;
            }
            QLabel {
                color: #ffcccc;
                font-weight: bold;
                background: transparent;
                padding: 10px;
            }
            QPushButton {
                background-color: #ff4d4d;
                color: #ffffff;
                border-radius: 4px;
                padding: 5px 15px;
                margin: 5px;
                font-weight: bold;
            }
            QPushButton:hover {
                background-color: #ff6666;
            }
        """)

        layout = QHBoxLayout(self)
        layout.setContentsMargins(15, 0, 15, 0)
        layout.setSpacing(10)
        
        self.label = QLabel("No error")
        layout.addWidget(self.label)
        
        layout.addStretch()
        
        btn_dismiss = QPushButton("Dismiss")
        btn_dismiss.clicked.connect(self.hide_banner)
        layout.addWidget(btn_dismiss)

        BUS.error_occurred.connect(self.show_banner)

    @pyqtSlot(str, str, object)
    def show_banner(self, error_name, error_detail, exception: object):
        self.label.setText(f"🛑 {error_name}: {error_detail}")
        self.setVisible(True)

    def hide_banner(self):
        self.setVisible(False)
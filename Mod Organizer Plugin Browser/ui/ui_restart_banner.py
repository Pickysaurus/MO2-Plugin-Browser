from PyQt6.QtWidgets import QWidget, QHBoxLayout, QLabel, QPushButton # type: ignore
from PyQt6.QtCore import pyqtSlot, Qt # type: ignore

from ..messenger import BUS

class RestartBanner(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setVisible(False)

        self.setAttribute(Qt.WidgetAttribute.WA_StyledBackground, True)

        self.setObjectName("RestartBanner")

        self.setStyleSheet("""
            #RestartBanner {
                background-color: #3d2b00;
                border-bottom: 2px solid #ffb347;
            }
            QLabel {
                color: #ffb347;
                font-weight: bold;
                background: transparent;
                padding: 10px;
            }
            QPushButton {
                background-color: #ffb347;
                color: #1a1a1a;
                border-radius: 4px;
                padding: 5px 15px;
                margin: 5px;
                font-weight: bold;
            }
            QPushButton:hover {
                background-color: #ffcc80;
            }
        """)

        layout = QHBoxLayout(self)
        layout.setContentsMargins(15, 0, 15, 0)
        layout.setSpacing(10)
        
        self.label = QLabel("⚠️ Restart Required: New plugins will not be active until MO2 is restarted.")
        layout.addWidget(self.label)
        
        layout.addStretch()
        
        btn_restart = QPushButton("Restart Now")
        btn_restart.clicked.connect(lambda: BUS.relaunch_mo2.emit())
        layout.addWidget(btn_restart)

        BUS.relaunch_required.connect(self.show_banner)

    @pyqtSlot()
    def show_banner(self):
        self.setVisible(True)
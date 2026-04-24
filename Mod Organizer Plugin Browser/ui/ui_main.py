import logging
from mobase import IOrganizer # type: ignore
from typing import ( Callable, Iterable )
from PyQt6.QtWidgets import ( # type: ignore
    QDialog, QVBoxLayout, QStackedWidget,
    QHBoxLayout, QLabel
)
from PyQt6.QtCore import Qt # type: ignore
from PyQt6.QtGui import QPixmap # type: ignore
from PyQt6 import sip # type: ignore
from .ui_tiles import ModTile
from ..utility.image_loader import ImageManager
from .ui_sidebar import Sidebar
from .ui_detail_view import DetailView
from .ui_grid_view import PluginGridView
from ..nexusmods_api import NexusModsAPI
from ..nexusmods.nexus_mods_types import ModsResult, ModNode, PluginCategoryType, ModSortType
from ..utility.managed_plugins import ManagedPlugins
from .ui_restart_banner import RestartBanner
from .ui_error_banner import ErrorBanner
from ..utility.plugin_installer import PluginInstaller
from ..utility.update_checker import UpdateChecker
from ..messenger import BUS

class BrowserDialog(QDialog):
    def __init__(
            self,
            load_callback: Callable[[int, PluginCategoryType, ModSortType, str | None], None], 
            api: NexusModsAPI, 
            organizer: IOrganizer, 
            installed_manager: ManagedPlugins,
            parent=None
    ):
        super().__init__(parent)
        self.api = api
        self._organizer = organizer
        self.installed_manager = installed_manager
        self.image_manager = ImageManager(self)
        self.plugin_installer = PluginInstaller(organizer, api, installed_manager)
        self.update_checker = UpdateChecker(api)
        self.current_offset = 0
        self.page_size = 12
        self.load_callback = load_callback
        self.logging = logging.getLogger("MO2PluginBrowserUIMain")
        self.setWindowTitle("Plugins Browser for Mod Organizer 2")
        self.resize(1100, 800)
        self.setStyleSheet("""
            QStackedWidget {
                background-color: transparent;
            }
            QScrollArea {
                border: none;
                background-color: transparent;
            }
            QScrollBar:vertical {
                border: none;
                background: palette(base);
                width: 12px;
                margin: 0px;
            }
            QScrollBar::handle:vertical {
                background: palette(mid);
                min-height: 20px;
                border-radius: 6px;
            }
        """)
        
        # Root layout: Vertical (Header on top, Content below)
        self.root_layout = QVBoxLayout(self) # The overall root of the modal
        self.content_layout = QHBoxLayout() # This is the split view for the sidebar and content

        # 1. Top Text Area (Header) added to the root layout at the top
        self.header_text = QLabel("Browse and install Mod Organizer 2 extensions directly from Nexus Mods.")
        self.header_text.setStyleSheet("""
            QLabel {
                font-size: 14px; 
                padding: 12px; 
                background-color: palette(mid); 
                color: palette(hightlighted=text);
                border: 1px solid palette(base);
                border-radius: 6px;
                margin-bottom: 2px;
            };
        """)
        self.header_text.setWordWrap(True)

        # Restart notification
        self.error_banner = ErrorBanner()
        self.restart_banner = RestartBanner()

        # Add the header and body area to the root_layout
        self.root_layout.addWidget(self.header_text)
        self.root_layout.addWidget(self.restart_banner)
        self.root_layout.addWidget(self.error_banner)
        self.root_layout.addLayout(self.content_layout)

        # Sidebar
        self.sidebar = Sidebar(
            on_search=self.on_search_submitted,
            on_reset=self.on_search_reset,
            on_category=self.on_category_clicked,
            on_check_for_updates=self.on_check_for_updates
        )

        # Swappable pages to live inside the main_stack
        self.detail_view = DetailView(
            self.show_grid, 
            self._organizer, 
            self.image_manager, 
            self.api,
            self.installed_manager,
            self.plugin_installer
        )
        self.grid_page = PluginGridView(self.load_next_page, self.load_prev_page, self.trigger_filter_refresh)

        # Add stacked pages and main_stack to contain them
        self.main_stack = QStackedWidget()
        self.main_stack.setStyleSheet("background-color: transparent;")
        self.main_stack.addWidget(self.grid_page)
        self.main_stack.addWidget(self.detail_view)

        # Build the layouts
        self.content_layout.addWidget(self.sidebar)
        self.content_layout.addWidget(self.main_stack)

    def show_grid(self):
        self.main_stack.setCurrentIndex(0)

    def show_details(self, mod_node: ModNode):
        """Populates the detail view and flips the stack."""
        self.detail_view.update_data(mod_node)
        self.main_stack.setCurrentIndex(1)
    
    def set_thumbnail(self, pixmap: QPixmap | None, url: str):
        if not pixmap: return
        self.detail_view.image_label.setPixmap(pixmap.scaled(
            self.detail_view.image_label.size(), 
            Qt.AspectRatioMode.KeepAspectRatioByExpanding,
            Qt.TransformationMode.SmoothTransformation
        ))

    def display_mods(self, data: ModsResult, installed_names: Iterable[str]):
        if sip.isdeleted(self.grid_page):
            return

        # Safely clear existing tiles
        while self.grid_page.grid and self.grid_page.grid.count():
            item = self.grid_page.grid.takeAt(0)
            if item and (widget := item.widget()):
                widget.setParent(None)
                widget.deleteLater()
    
        # Update totals
        
        total = data["totalCount"] if data["totalCount"] else 0
        self.grid_page.totalDisplay.setText(f"Total Plugins: {total}")

        # Update pagination
        current_page = (self.current_offset // self.page_size) + 1
        self.grid_page.page_label.setText(f"Page {current_page}")
        self.grid_page.prev_button.setEnabled(self.current_offset > 0)
        self.grid_page.next_button.setEnabled(self.current_offset + self.page_size < total)

        # Add new tiles
        cols = 4
        nodes = data.get("nodes", [])
        total = data.get("totalCount", 0)
        # log_msg = f"{total} Mods: {nodes}, Data: {data}"
        # self.logging.info(log_msg)
        for index, node in enumerate(nodes):
            uid = node.get("uid", "")
            is_installed = uid in installed_names
            has_update = False
            if is_installed:
                managed = self.installed_manager.get_managed_plugin(uid)
                has_update = "latest_version" in managed.keys() if managed else False
            tile = ModTile(node, self.image_manager, is_installed, has_update)

            tile.clicked.connect(self.show_details)

            row, col = divmod(index, cols)
            self.grid_page.grid.addWidget(tile, row, col)

    def on_category_clicked(self):
        """Triggered when a user clicks a sidebar category."""
        # The 'item' is the QListWidgetItem that was clicked.
        # It stays highlighted automatically by QListWidget.
        self.main_stack.setCurrentIndex(0)
        self.trigger_filter_refresh()

    def on_search_submitted(self):
        """Triggered when user presses Enter in search box."""
        self.logging.info("Search submitted")
        self.sidebar.reset_btn.setEnabled(True)
        self.trigger_filter_refresh()
    
    def on_search_reset(self):
        self.logging.info("Search reset")
        self.sidebar.search_input.clear()
        self.sidebar.reset_btn.setEnabled(False)

        self.sidebar.category_list.setFocus()

        if not self.sidebar.category_list.selectedItems():
           self.sidebar.category_list.setCurrentItem(self.sidebar.category_list.item(0))

        self.trigger_filter_refresh(reset_pagination=True)
    
    def on_check_for_updates(self) -> int:
        update_count = 0
        plugins = self.installed_manager.get_all()
        for p in plugins:
            new_version = self.update_checker.check_plugin_for_update(p)
            if not new_version: continue
            uid = p["uid"]
            self.installed_manager.set_update_available(
                uid, 
                version=new_version["file"]["version"],
                file_id=int(new_version["file"]["game_scoped_id"])
            )
            BUS.update_available.emit(uid, new_version, p)
            update_count += 1
        return update_count

    
    def load_next_page(self):
        self.current_offset += self.page_size
        self.trigger_filter_refresh(reset_pagination=False)

    def load_prev_page(self):
        self.current_offset = max(0, self.current_offset - self.page_size)
        self.trigger_filter_refresh(reset_pagination=False)

    def trigger_filter_refresh(self, reset_pagination=True):
        """Collects current UI state and calls the backend."""
        if reset_pagination:
            self.current_offset = 0
        
        # Get the currently selected item's text
        search_term = self.sidebar.search_input.text().strip() or None
        selected = self.sidebar.category_list.selectedItems()
        category: PluginCategoryType = selected[0].text() if selected else "All" # type: ignore
        sort_dropdown = self.grid_page.sort_dropdown.currentText()
        sort: ModSortType = sort_dropdown if sort_dropdown else "Endorsements" # type: ignore
                
        # Execute the load callback
        self.load_callback(
            self.current_offset, 
            category, 
            sort,
            search_term
        )
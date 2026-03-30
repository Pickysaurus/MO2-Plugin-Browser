import logging
from PyQt6.QtCore import Qt, QUrl # type: ignore
from PyQt6.QtWidgets import QHBoxLayout, QVBoxLayout, QLabel, QFrame # type: ignore
from PyQt6.QtNetwork import QNetworkReply, QNetworkAccessManager, QNetworkRequest # type: ignore
from PyQt6.QtCore import QUrl, Qt, pyqtSignal # type: ignore
from PyQt6.QtGui import QMouseEvent, QPixmap, QPainter, QPainterPath, QFontMetrics # type: ignore

from ..utility.image_loader import ImageManager
from ..nexusmods.nexus_mods_types import ModNode
from datetime import datetime, timezone

LOGGER = logging.getLogger("MO2PluginsTile")

class ModTile(QFrame):

    clicked = pyqtSignal(dict)

    def __init__(self, mod_node: ModNode, image_manager: ImageManager, is_installed=False, has_update = False, parent=None):
        super().__init__(parent)
        self.mod_node = mod_node
        # self.image_manager = image_manager
        self.setFixedSize(200, 260)
        self.setFrameStyle(QFrame.Shape.StyledPanel | QFrame.Shadow.Raised)
        self.setStyleSheet("""
            ModTile { 
                background-color: palette(mid); 
                border: 1px solid palette(window);
                border-radius: 6px; 
            }
            ModTile:hover { 
                background-color: palette(mid); 
                opacity: 0.7;
                border: 1px solid palette(highlight); 
            }
        """)
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        
        layout = QVBoxLayout(self)
        layout.setContentsMargins(8, 8, 8, 8)
        
        # Image Display (Thumbnail)
        self.image_label = QLabel("Loading...")
        self.image_label.setFixedSize(180, 110)
        self.image_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.image_label.setStyleSheet("background-color: #222; border-radius: 4px; color: #fff;")
        layout.addWidget(self.image_label)
        
        # Mod Name (max 2 lines)
        full_name = mod_node.get("name", "Unknown")
        self.name_label = QLabel()
        self.name_label.setToolTip(full_name)
        self.name_label.setWordWrap(True)
        self.name_label.setStyleSheet("font-weight: bold; font-size: 10pt; padding: 1px; color: palette(window-text);")

        # Use the helper to set elided text (approx 180px width for 2 lines)
        elide_multiline_text(self.name_label, full_name, 180, 2)

        # Set a fixed height for 2 lines to keep tiles perfectly aligned
        metrics = QFontMetrics(self.name_label.font())
        line_height = metrics.lineSpacing()
        vertical_buffer = 8 # Prevent the bottom of letters like g being cut off.
        self.name_label.setFixedHeight((line_height * 2) + vertical_buffer)

        layout.addWidget(self.name_label)

        # Author
        author_section = QHBoxLayout()
        self.author_avatar = QLabel("!")
        self.author_avatar.setStyleSheet("background-color: palette(mid); border-radius: 12px;")
        self.author_avatar.setFixedSize(20, 20)
        author_label = QLabel(mod_node.get('uploader', {}).get('name', 'Unknown'))
        author_label.setWordWrap(True)
        author_label.setStyleSheet("font-size: 9pt; color: palette(window-text);")

        author_section.addWidget(self.author_avatar)
        author_section.addWidget(author_label)
        author_section.addStretch()

        layout.addLayout(author_section)

        # Updated and created
        date_row = QHBoxLayout()
        updated = mod_node.get("updatedAt", "Never")
        created = mod_node.get("createdAt")
        dt = datetime.fromisoformat(created.replace("Z", "+00:00"))
        updated_label = QLabel(f"🔄️ {get_relative_date(updated)}")
        updated_label.setStyleSheet("font-size: 8pt; color: #555;")
        created_label = QLabel(f"🚀 {dt.date()}")
        created_label.setStyleSheet("font-size: 8pt; color: #555;")
        date_row.addWidget(updated_label)
        date_row.addWidget(created_label)
        layout.addLayout(date_row)


        # Stats to show
        stats_row = QHBoxLayout()
        stats_row.setSpacing(0)
        endorsements = mod_node.get("endorsements", 0)
        endorsements_label = QLabel(f"👍 {format_stat(endorsements)}")
        endorsements_label.setToolTip(f"Endorsements: {endorsements}")
        downloads = mod_node.get("downloads", 0)
        downloads_label = QLabel(f"⬇️ {format_stat(downloads)}")
        downloads_label.setToolTip(f"Downloads: {downloads}")
        size = mod_node.get("fileSize", 0)
        size_label = QLabel(f"💽 {format_stat(size)}KB")
        size_label.setToolTip(f"File Size: {size}KB")
        labels = [
            endorsements_label,
            downloads_label,
            size_label
        ]
        for label in labels:
            label.setStyleSheet("font-size: 8pt; color: palette(window-text); opacity: 0.7;")
            label.setAlignment(Qt.AlignmentFlag.AlignLeft)
            stats_row.addWidget(label, 1)
        layout.addLayout(stats_row)
        
        # Status Badge
        if is_installed and not has_update:
            status = QLabel("✓ INSTALLED")
            status.setStyleSheet("""
                color: palette(link); 
                font-weight: bold; 
                font-size: 8pt;
                background-color: palette(base);
                border-radius: 2px;
                padding: 2px;
            """)
            layout.addWidget(status)
        elif has_update:
            status = QLabel("UPDATE AVAILABLE")
            status.setStyleSheet("""
                color: palette(link); 
                font-weight: bold; 
                font-size: 8pt;
                background-color: palette(base);
                border-radius: 2px;
                padding: 2px;
            """)
            layout.addWidget(status)
        else:
            layout.addSpacing(18)
        
        # Start background image download
        self.manager = QNetworkAccessManager(self)
        self.manager.finished.connect(self._on_download_finished)
        self.thumb_url = mod_node.get('thumbnailUrl')
        self.avatar_url = mod_node.get('uploader', {}).get("avatar")
        # if self.thumb_url:
        #     self.image_manager.fetch(self.thumb_url, self._apply_thumb)
        # if self.avatar_url:
        #     self.image_manager.fetch(self.avatar_url, self._apply_avatar)
        if self.thumb_url:
            self._get_image(mod_node.get('thumbnailUrl'))
        else:
            self.image_label.setText("No Thumbnail")
        if self.avatar_url:
            self._get_image(mod_node.get('uploader', {}).get("avatar"))
    
    def _apply_thumb(self, pixmap: QPixmap | None, url: str):
        LOGGER.info(f"Applying thumbnail: {url}. Is visible {self.isVisible()} Parent: {self.parent()} Attrib: {self.image_label}")
        try:
            if not self.isVisible(): return
            if pixmap is None or not self.parent(): return

            if self.image_label.width() <= 0:
                return

            scaled_pixmap = pixmap.scaled(
                self.image_label.size(),
                Qt.AspectRatioMode.KeepAspectRatioByExpanding,
                Qt.TransformationMode.SmoothTransformation
            )
            LOGGER.info(f"Scaled Pixmap for: {self.image_label} {scaled_pixmap} - {url} Size:{self.image_label.size()}")
            
            self.image_label.setPixmap(scaled_pixmap)
            LOGGER.info("Thumbnail set")
        except (RuntimeError, AttributeError): 
            LOGGER.warning('Failed to load thumbnail with RuntimeError or AttributeError')
            pass # Widget was deleted

    def _apply_avatar(self, pixmap: QPixmap | None, url: str):    
        LOGGER.info(f"Applying avatar: {url}. Is visible {self.isVisible()} Parent: {self.parent()} Attrib: {self.author_avatar}")
        try:
            if not self.isVisible(): return
            if pixmap is None or not self.parent(): return
            # Note: width() might be 0 if the widget isn't shown yet, 
            # so use the fixed size 20 we set in __init__
            rounded = self.get_rounded_pixmap(pixmap, 20)
            LOGGER.info(f"Rounded Pixmap for: {self.image_label} {rounded} - {url} - Size:{self.author_avatar.size()}")
            self.author_avatar.setPixmap(rounded)
            LOGGER.info("Avatar set")
        except (RuntimeError, AttributeError):
            LOGGER.warning('Failed to load avatar with RuntimeError or AttributeError')
            pass
    
    def get_rounded_pixmap(self, src_pixmap, size):
        """Crops a square pixmap into a circle."""
        if (src_pixmap.isNull()):
            return QPixmap()
        # 1. Create a transparent canvas
        target = QPixmap(size, size)
        target.fill(Qt.GlobalColor.transparent)
        
        # 2. Scale the source image to fill the target size
        scaled_src = src_pixmap.scaled(
            size, size, 
            Qt.AspectRatioMode.KeepAspectRatioByExpanding, 
            Qt.TransformationMode.SmoothTransformation
        )
        
        # 3. Paint the circle
        painter = QPainter(target)

        # Ensure painter opened before proceeding
        if not painter.isActive():
            return target

        try: 
            painter.setRenderHint(QPainter.RenderHint.Antialiasing)
            
            path = QPainterPath()
            path.addEllipse(0, 0, size, size)
            painter.setClipPath(path)
            
            # Draw the image into the circular clip
            painter.drawPixmap(0, 0, scaled_src)
        finally:
            painter.end()
        
        return target
    
    def _on_download_finished(self, reply):
        if reply.error() != QNetworkReply.NetworkError.NoError:
            return

        original_url = reply.request().url().toString()
        
        pixmap = QPixmap()
        pixmap.loadFromData(reply.readAll())

        if original_url == self.thumb_url:
            self.image_label.setPixmap(pixmap.scaled(
                self.image_label.size(), 
                Qt.AspectRatioMode.KeepAspectRatioByExpanding, 
                Qt.TransformationMode.SmoothTransformation
            ))

        elif original_url == self.avatar_url:
            rounded = self.get_rounded_pixmap(pixmap, self.author_avatar.width())
            self.author_avatar.setPixmap(rounded)
        
    def _get_image(self, url_string):
        if not url_string:
            return
            
        request = QNetworkRequest(QUrl(url_string))
        # This tells Qt to automatically follow the 301/302 to the "missing" avatar
        request.setAttribute(
            QNetworkRequest.Attribute.RedirectPolicyAttribute, 
            QNetworkRequest.RedirectPolicy.NoLessSafeRedirectPolicy
        )
        self.manager.get(request)
    
    def mousePressEvent(self, event: QMouseEvent | None) -> None:
        if event and event.button() == Qt.MouseButton.LeftButton:
            self.clicked.emit(self.mod_node)
        super().mousePressEvent(event)

def format_stat(value: int) -> str:
    """Adds commas and shortens large numbers (e.g., 1,200 -> 1.2k)."""
    if value >= 1000:
        return f"{value/1000:.1f}k".replace(".0k", "k")
    return f"{value:,}"

def get_relative_date(date_str: str) -> str:
    """Converts an ISO date string into a relative format (e.g., '2 days ago')."""
    if date_str == "Never":
        return date_str
        
    try:
        # Nexus API typically returns ISO 8601 strings
        dt = datetime.fromisoformat(date_str.replace("Z", "+00:00"))
        now = datetime.now(timezone.utc)
        diff = now - dt

        if diff.days > 365:
            return f"{diff.days // 365} year(s) ago"
        if diff.days > 30:
            return f"{diff.days // 30} month(s) ago"
        if diff.days > 0:
            return f"{diff.days} day(s) ago"
        if diff.seconds > 3600:
            return f"{diff.seconds // 3600} hour(s) ago"
        return "Just now"
    except Exception:
        return date_str
    
def elide_multiline_text(label: QLabel, text: str, width: int, max_lines: int):
    """Truncates text to fit within a specific number of lines with an ellipsis."""
    metrics = QFontMetrics(label.font())
    line_height = metrics.lineSpacing()
    max_height = line_height * max_lines
    
    # Check if the original text already fits
    rect = metrics.boundingRect(0, 0, width, 1000, Qt.TextFlag.TextWordWrap, text)
    if rect.height() <= max_height:
        label.setText(text)
        return

    # Iteratively shorten the text until it fits within the max height
    for i in range(len(text), 0, -1):
        truncated = text[:i].strip() + "..."
        rect = metrics.boundingRect(0, 0, width, 1000, Qt.TextFlag.TextWordWrap, truncated)
        if rect.height() <= max_height:
            label.setText(truncated)
            break
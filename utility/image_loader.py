import logging
from typing import Callable
from collections import deque
from PyQt6.QtNetwork import QNetworkAccessManager, QNetworkRequest, QNetworkReply # type: ignore
from PyQt6.QtCore import QUrl, QObject, pyqtSignal, Qt # type: ignore
from PyQt6.QtGui import QPixmap, QImage, QPainter, QPainterPath # type: ignore
from PyQt6 import sip # type: ignore

LOGGER = logging.getLogger("MO2PluginsImageManager")

class ImageManager(QObject):
    """A shared utility to handle network image requests."""

    image_loaded = pyqtSignal(object, object, str, bool)
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.manager = QNetworkAccessManager(self)
        self.image_loaded.connect(self._dispatch_callback)

        # Set up a queue
        self.queue = deque()
        self.is_processing = False
    
    def fetch(self, url: str, callback: Callable, circular: bool = False):
        if not url:
            return
        # Store the circular preference in the queue
        self.queue.append((url, callback, circular))
        self.__process_next()
    
    def __process_next(self):
        if self.is_processing or not self.queue:
            return
        
        self.is_processing = True
        url, callback, circular = self.queue.popleft() # Unpack circular

        request = QNetworkRequest(QUrl(url))
        request.setAttribute(
            QNetworkRequest.Attribute.RedirectPolicyAttribute,
            QNetworkRequest.RedirectPolicy.NoLessSafeRedirectPolicy
        )

        reply = self.manager.get(request)
        if reply:
            # Pass the circular flag through the handler
            reply.finished.connect(lambda: self._handle_finished(reply, callback, url, circular))

    def _handle_finished(self, reply: QNetworkReply, callback: Callable, original_url: str, circular: bool):
        try:
            data = None
            if reply.error() == QNetworkReply.NetworkError.NoError:
                data = reply.readAll() 
            # Emit circular flag to dispatch
            self.image_loaded.emit(data, callback, original_url, circular)
        except Exception:
            pass 
        finally:
            reply.deleteLater()
            self.is_processing = False
            self.__process_next()

    def _dispatch_callback(self, data, callback, url, circular):
        try:
            if hasattr(callback, '__self__') and sip.isdeleted(callback.__self__):
                return

            if data is not None:
                image = QImage()
                image.loadFromData(data) 
                
                if not image.isNull():
                    pixmap = QPixmap.fromImage(image)
                    
                    # APPLY ROUNDING HERE
                    if circular:
                        pixmap = self.process_circular(pixmap)
                        
                    callback(pixmap, url)
        except Exception as e:
            LOGGER.error(f"Callback dispatch failed: {e}")
    
    def process_circular(self, src_pixmap: QPixmap) -> QPixmap:
        """Helper to crop image into a circle within the manager."""
        # Use the smallest dimension to ensure a perfect circle
        size = min(src_pixmap.width(), src_pixmap.height())
        
        target = QPixmap(size, size)
        target.fill(Qt.GlobalColor.transparent)
        
        painter = QPainter(target)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        
        path = QPainterPath()
        path.addEllipse(0, 0, size, size)
        painter.setClipPath(path)
        
        # Center the image crop
        offset_x = (src_pixmap.width() - size) // 2
        offset_y = (src_pixmap.height() - size) // 2
        painter.drawPixmap(-offset_x, -offset_y, src_pixmap)
        painter.end()
        
        return target
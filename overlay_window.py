import sys
import ctypes
from PyQt6.QtWidgets import QApplication, QWidget
from PyQt6.QtCore import Qt, QTimer, QPoint, QRectF, pyqtSignal
from PyQt6.QtGui import (
    QPainter, QPen, QColor, QPixmap, QImage, QBitmap, QPainterPath,
)

_SNAP_PX = 18


# ──────────────────────────────────────────────────────────────────────────────
# Full-screen green crosshair guide shown while dragging
# ──────────────────────────────────────────────────────────────────────────────

class _SnapGuide(QWidget):
    def __init__(self, screen):
        super().__init__()
        geo = screen.geometry()
        self._cx = geo.width()  // 2
        self._cy = geo.height() // 2
        self.setWindowFlags(
            Qt.WindowType.FramelessWindowHint
            | Qt.WindowType.WindowStaysOnTopHint
            | Qt.WindowType.Tool
            | Qt.WindowType.WindowTransparentForInput
        )
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        self.setAttribute(Qt.WidgetAttribute.WA_ShowWithoutActivating)
        self.setGeometry(geo)
        self.show()

    def paintEvent(self, event):
        p = QPainter(self)
        p.setPen(QPen(QColor(0, 220, 70, 200), 1))
        p.drawLine(self._cx, 0, self._cx, self.height())
        p.drawLine(0, self._cy, self.width(), self._cy)


# ──────────────────────────────────────────────────────────────────────────────
# Overlay window
# ──────────────────────────────────────────────────────────────────────────────

def _dwm_fix(hwnd: int) -> None:
    """Enable per-pixel alpha transparency and remove DWM rounded corners."""
    if sys.platform != "win32":
        return
    try:
        # Per-pixel alpha: extend DWM glass frame to cover entire client area
        MARGINS = ctypes.c_int * 4
        ctypes.windll.dwmapi.DwmExtendFrameIntoClientArea(
            hwnd, ctypes.byref(MARGINS(-1, -1, -1, -1))
        )
        # Square corners (Windows 11)
        DWMWA_WINDOW_CORNER_PREFERENCE = 33
        DWMWCP_DONOTROUND = 1
        ctypes.windll.dwmapi.DwmSetWindowAttribute(
            hwnd,
            DWMWA_WINDOW_CORNER_PREFERENCE,
            ctypes.byref(ctypes.c_int(DWMWCP_DONOTROUND)),
            ctypes.sizeof(ctypes.c_int),
        )
    except Exception:
        pass


class SourceCoverWindow(QWidget):
    """Solid-color window drawn over the capture region to hide it."""

    def __init__(self, config):
        super().__init__()
        self.config = config
        self.setWindowFlags(
            Qt.WindowType.FramelessWindowHint
            | Qt.WindowType.WindowStaysOnTopHint
            | Qt.WindowType.Tool
            | Qt.WindowType.NoDropShadowWindowHint
        )
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        self.setAttribute(Qt.WidgetAttribute.WA_ShowWithoutActivating)

    def showEvent(self, event) -> None:
        super().showEvent(event)
        hwnd = int(self.winId())
        _dwm_fix(hwnd)
        # Invisible to screen capture (mss/BitBlt) but visible on physical display
        WDA_EXCLUDEFROMCAPTURE = 0x00000011
        ctypes.windll.user32.SetWindowDisplayAffinity(hwnd, WDA_EXCLUDEFROMCAPTURE)

    def apply_config(self) -> None:
        self.setGeometry(
            self.config.capture_x,
            self.config.capture_y,
            self.config.capture_w,
            self.config.capture_h,
        )
        self.update()

    def paintEvent(self, event) -> None:
        painter = QPainter(self)
        painter.setCompositionMode(QPainter.CompositionMode.CompositionMode_Source)
        painter.fillRect(self.rect(), QColor(0, 0, 0, 0))
        painter.setCompositionMode(QPainter.CompositionMode.CompositionMode_SourceOver)
        painter.setBrush(QColor(self.config.source_cover_color))
        painter.setPen(Qt.PenStyle.NoPen)
        painter.drawRect(self.rect())


class OverlayWindow(QWidget):
    position_changed = pyqtSignal(int, int)   # cx, cy — emitted after drag

    def __init__(self, config, capture_thread):
        super().__init__()
        self.config  = config
        self.capture = capture_thread

        self._drag_pos:   QPoint     | None = None
        self._snap_guide: _SnapGuide | None = None
        self._snapped_x = False
        self._snapped_y = False
        self._pixmap:   QPixmap | None = None

        self.setWindowFlags(
            Qt.WindowType.FramelessWindowHint
            | Qt.WindowType.WindowStaysOnTopHint
            | Qt.WindowType.Tool
            | Qt.WindowType.NoDropShadowWindowHint
        )
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)

        self._timer = QTimer(self)
        self._timer.timeout.connect(self._refresh)
        self.apply_config()

    def showEvent(self, event) -> None:
        super().showEvent(event)
        hwnd = int(self.winId())
        _dwm_fix(hwnd)
        self._update_mask()
        self._set_click_through(self.config.locked)

    # ------------------------------------------------------------------ #
    # Public API                                                           #
    # ------------------------------------------------------------------ #

    def apply_config(self) -> None:
        bw = self.config.border_width
        w  = int(self.config.capture_w * self.config.overlay_scale) + 2 * bw
        h  = int(self.config.capture_h * self.config.overlay_scale) + 2 * bw
        x  = self.config.overlay_cx - w // 2
        y  = self.config.overlay_cy - h // 2
        self.setGeometry(x, y, w, h)
        self.setWindowOpacity(self.config.overlay_opacity)
        self._timer.start(max(1, 1000 // self.config.fps))
        self._update_mask()
        self.update()
        if self.isVisible():
            self._set_click_through(self.config.locked)

    def _set_click_through(self, enabled: bool) -> None:
        if sys.platform != 'win32':
            return
        try:
            hwnd = int(self.winId())
            GWL_EXSTYLE       = -20
            WS_EX_TRANSPARENT = 0x00000020
            WS_EX_LAYERED     = 0x00080000
            style = ctypes.windll.user32.GetWindowLongW(hwnd, GWL_EXSTYLE)
            if enabled:
                style |= WS_EX_TRANSPARENT | WS_EX_LAYERED
            else:
                style = (style | WS_EX_LAYERED) & ~WS_EX_TRANSPARENT
            ctypes.windll.user32.SetWindowLongW(hwnd, GWL_EXSTYLE, style)
        except Exception:
            pass

    # ------------------------------------------------------------------ #
    # Mask for click-through in transparent corners                       #
    # ------------------------------------------------------------------ #

    def _update_mask(self) -> None:
        if self.width() <= 0 or self.height() <= 0:
            return
        r = int(self.config.corner_radius / 100.0 * min(self.width(), self.height()) / 2)
        if r <= 0:
            self.clearMask()
            return
        bmp = QBitmap(self.size())
        bmp.fill(Qt.GlobalColor.color0)
        p = QPainter(bmp)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        p.setBrush(Qt.GlobalColor.color1)
        p.setPen(Qt.PenStyle.NoPen)
        p.drawRoundedRect(self.rect(), r, r)
        p.end()
        self.setMask(bmp)

    def resizeEvent(self, event) -> None:
        self._update_mask()

    # ------------------------------------------------------------------ #
    # Frame rendering                                                      #
    # ------------------------------------------------------------------ #

    def _refresh(self) -> None:
        frame = self.capture.get_frame()
        if frame is None:
            return
        bw = self.config.border_width
        w  = int(self.config.capture_w * self.config.overlay_scale)
        h  = int(self.config.capture_h * self.config.overlay_scale)
        if frame.size != (w, h):
            from PIL.Image import Resampling
            frame = frame.resize((w, h), Resampling.BILINEAR)
        rgb = frame.tobytes("raw", "RGB")
        self._qimg   = QImage(rgb, w, h, 3 * w, QImage.Format.Format_RGB888)
        self._pixmap = QPixmap.fromImage(self._qimg)
        self.update()

    # ------------------------------------------------------------------ #
    # Paint                                                                #
    # ------------------------------------------------------------------ #

    def paintEvent(self, event) -> None:
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)

        # Clear entire surface to transparent (CompositionMode_Source writes
        # alpha=0 directly, bypassing DWM default background)
        painter.setCompositionMode(
            QPainter.CompositionMode.CompositionMode_Source
        )
        painter.fillRect(self.rect(), QColor(0, 0, 0, 0))
        painter.setCompositionMode(
            QPainter.CompositionMode.CompositionMode_SourceOver
        )

        bw = self.config.border_width
        r  = int(self.config.corner_radius / 100.0 * min(self.width(), self.height()) / 2)

        if self._pixmap:
            if r > 0:
                path = QPainterPath()
                path.addRoundedRect(QRectF(self.rect()), r, r)
                painter.setClipPath(path)
            painter.drawPixmap(bw, bw, self._pixmap)
            painter.setClipping(False)

        if bw > 0:
            painter.setPen(QPen(QColor(self.config.border_color), bw))
            painter.setBrush(Qt.BrushStyle.NoBrush)
            rect = QRectF(bw / 2, bw / 2, self.width() - bw, self.height() - bw)
            if r > 0:
                painter.drawRoundedRect(rect, r, r)
            else:
                painter.drawRect(rect)

    # ------------------------------------------------------------------ #
    # Drag with snap                                                       #
    # ------------------------------------------------------------------ #

    def mousePressEvent(self, event) -> None:
        if self.config.locked:
            return
        if event.button() == Qt.MouseButton.LeftButton:
            self._drag_pos = (
                event.globalPosition().toPoint() - self.frameGeometry().topLeft()
            )
            screen = (QApplication.screenAt(event.globalPosition().toPoint())
                      or QApplication.primaryScreen())
            self._snap_guide = _SnapGuide(screen)

    def mouseMoveEvent(self, event) -> None:
        if self.config.locked or not self._drag_pos:
            return
        if not event.buttons() & Qt.MouseButton.LeftButton:
            return

        new_pos = event.globalPosition().toPoint() - self._drag_pos
        screen  = (QApplication.screenAt(event.globalPosition().toPoint())
                   or QApplication.primaryScreen())
        sg = screen.geometry()

        snap_x = sg.x() + (sg.width()  - self.width())  // 2
        snap_y = sg.y() + (sg.height() - self.height()) // 2

        self._snapped_x = abs(new_pos.x() - snap_x) < _SNAP_PX
        self._snapped_y = abs(new_pos.y() - snap_y) < _SNAP_PX
        if self._snapped_x:
            new_pos.setX(snap_x)
        if self._snapped_y:
            new_pos.setY(snap_y)

        self.move(new_pos)

    def mouseReleaseEvent(self, event) -> None:
        if event.button() == Qt.MouseButton.LeftButton:
            self._drag_pos  = None
            self._snapped_x = False
            self._snapped_y = False
            if self._snap_guide:
                self._snap_guide.close()
                self._snap_guide = None
            self.config.overlay_cx = self.x() + self.width()  // 2
            self.config.overlay_cy = self.y() + self.height() // 2
            self.position_changed.emit(self.config.overlay_cx, self.config.overlay_cy)

from PyQt6.QtWidgets import QApplication, QWidget
from PyQt6.QtCore import Qt, QRect, QPoint, pyqtSignal
from PyQt6.QtGui import QPainter, QColor, QPen, QFont


class RegionSelector(QWidget):
    """Full-screen translucent overlay that lets the user drag-select a region."""

    region_selected = pyqtSignal(int, int, int, int)   # x, y, w, h (global coords)

    def __init__(self, screen_index: int = 0):
        super().__init__()
        self._start: QPoint | None = None
        self._end:   QPoint | None = None
        self._selecting = False

        screens = QApplication.screens()
        screen = screens[min(screen_index, len(screens) - 1)]
        geo = screen.geometry()
        self._screen_offset = geo.topLeft()

        self.setWindowFlags(
            Qt.WindowType.FramelessWindowHint
            | Qt.WindowType.WindowStaysOnTopHint
            | Qt.WindowType.Tool
        )
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        self.setCursor(Qt.CursorShape.CrossCursor)
        self.setGeometry(geo)
        self.showFullScreen()

    # ------------------------------------------------------------------ #
    # Painting                                                             #
    # ------------------------------------------------------------------ #

    def paintEvent(self, event):
        painter = QPainter(self)

        # Dark overlay
        painter.fillRect(self.rect(), QColor(0, 0, 0, 100))

        if self._start and self._end:
            rect = QRect(self._start, self._end).normalized()

            # Cut-out: erase the dark overlay inside the selection
            painter.setCompositionMode(
                QPainter.CompositionMode.CompositionMode_Clear
            )
            painter.fillRect(rect, QColor(0, 0, 0, 0))
            painter.setCompositionMode(
                QPainter.CompositionMode.CompositionMode_SourceOver
            )

            # Yellow border around selection
            pen = QPen(QColor(255, 220, 0), 2, Qt.PenStyle.SolidLine)
            painter.setPen(pen)
            painter.drawRect(rect)

            # Dimension label
            font = QFont("Segoe UI", 11, QFont.Weight.Bold)
            painter.setFont(font)
            label = f"  {rect.width()} × {rect.height()}  "
            label_y = rect.top() - 22 if rect.top() > 30 else rect.bottom() + 22
            painter.setPen(QColor(255, 220, 0))
            painter.drawText(rect.left(), label_y, label)

        # Instructions
        font = QFont("Segoe UI", 12)
        painter.setFont(font)
        painter.setPen(QColor(255, 255, 255, 200))
        painter.drawText(
            self.rect().adjusted(0, 20, 0, 0),
            Qt.AlignmentFlag.AlignHCenter | Qt.AlignmentFlag.AlignTop,
            "Arrastra para seleccionar la región del minimap  |  ESC para cancelar",
        )

    # ------------------------------------------------------------------ #
    # Mouse events                                                         #
    # ------------------------------------------------------------------ #

    def mousePressEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            self._start = event.position().toPoint()
            self._end = self._start
            self._selecting = True

    def mouseMoveEvent(self, event):
        if self._selecting:
            self._end = event.position().toPoint()
            self.update()

    def mouseReleaseEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton and self._selecting:
            self._end = event.position().toPoint()
            self._selecting = False
            rect = QRect(self._start, self._end).normalized()
            if rect.width() > 5 and rect.height() > 5:
                ox, oy = self._screen_offset.x(), self._screen_offset.y()
                self.region_selected.emit(
                    rect.x() + ox,
                    rect.y() + oy,
                    rect.width(),
                    rect.height(),
                )
            self.close()

    def keyPressEvent(self, event):
        if event.key() == Qt.Key.Key_Escape:
            self.close()

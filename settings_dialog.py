import os
import sys
import ctypes
from dataclasses import asdict

_HERE = os.path.dirname(os.path.abspath(__file__))

def _get_style():
    up = os.path.join(_HERE, 'arrow_up.svg').replace('\\', '/')
    dn = os.path.join(_HERE, 'arrow_down.svg').replace('\\', '/')
    return DARK_STYLE.replace('__UP__', up).replace('__DN__', dn)
from PyQt6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QFormLayout, QGroupBox,
    QLabel, QSpinBox, QDoubleSpinBox, QPushButton,
    QSlider, QLineEdit, QColorDialog, QDialogButtonBox,
)
from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtGui import QColor
from icon import make_qicon


DARK_STYLE = """
QWidget {
    background-color: #141414;
    color: #c0c0c0;
    font-family: 'Segoe UI';
    font-size: 9pt;
}
QDialog { background-color: #141414; }

QGroupBox {
    border: 1px solid #2a2a2a;
    border-radius: 0px;
    margin-top: 12px;
    padding: 10px 8px 8px 8px;
    color: #505050;
    font-size: 8pt;
    text-transform: uppercase;
    letter-spacing: 1px;
}
QGroupBox::title {
    subcontrol-origin: margin;
    left: 8px;
    padding: 0 4px;
}

QSpinBox, QDoubleSpinBox, QLineEdit, QComboBox {
    background-color: #1c1c1c;
    border: 1px solid #2e2e2e;
    border-radius: 0px;
    padding: 4px 6px;
    color: #c0c0c0;
    selection-background-color: #002840;
}
QSpinBox:focus, QDoubleSpinBox:focus,
QLineEdit:focus, QComboBox:focus {
    border-color: #00537d;
}

QAbstractSpinBox::up-button {
    subcontrol-origin: border;
    subcontrol-position: top right;
    width: 24px;
    border-left: 1px solid #2e2e2e;
    background-color: #1e1e1e;
}
QAbstractSpinBox::up-button:hover   { background-color: #2e2e2e; }
QAbstractSpinBox::up-button:pressed { background-color: #181818; }
QAbstractSpinBox::up-arrow {
    image: url(__UP__);
    width: 10px; height: 6px;
}
QAbstractSpinBox::down-button {
    subcontrol-origin: border;
    subcontrol-position: bottom right;
    width: 24px;
    border-left: 1px solid #2e2e2e;
    background-color: #1e1e1e;
}
QAbstractSpinBox::down-button:hover   { background-color: #2e2e2e; }
QAbstractSpinBox::down-button:pressed { background-color: #181818; }
QAbstractSpinBox::down-arrow {
    image: url(__DN__);
    width: 10px; height: 6px;
}

QComboBox::drop-down { border: none; width: 22px; }
QComboBox QAbstractItemView {
    background-color: #1c1c1c;
    selection-background-color: #002840;
    border: 1px solid #2e2e2e;
}

QPushButton {
    background-color: #1c1c1c;
    border: 1px solid #2e2e2e;
    border-radius: 0px;
    padding: 5px 14px;
    color: #c0c0c0;
}
QPushButton:hover   { background-color: #252525; border-color: #404040; }
QPushButton:pressed { background-color: #111; }
QPushButton[locked="true"] {
    border-color: #a05000;
    color: #e07020;
}
QPushButton[cover="true"] {
    border-color: #002840;
    color: #0077b0;
}

QSlider::groove:horizontal {
    height: 3px;
    background: #2a2a2a;
    border-radius: 0px;
}
QSlider::sub-page:horizontal {
    background: #00537d;
}
QSlider::handle:horizontal {
    background: #0077b0;
    width: 12px;
    height: 12px;
    margin: -5px 0;
    border-radius: 0px;
}

QLabel { background: transparent; color: #606060; }
QFormLayout QLabel { color: #606060; }
QDialogButtonBox QPushButton { min-width: 80px; }
"""


class SettingsDialog(QDialog):
    config_applied          = pyqtSignal()
    select_region_requested = pyqtSignal()

    def __init__(self, config, parent=None):
        super().__init__(parent)
        self.config = config
        self._border_color  = config.border_color
        self._cover_color   = config.source_cover_color
        self._cover_enabled = config.source_cover_enabled
        self._original      = asdict(config)   # snapshot for Cancel revert
        self._live          = True             # emit live updates

        self.setWindowTitle("Minimap — Settings")
        self.setWindowIcon(make_qicon())
        self.setMinimumWidth(440)
        self.setStyleSheet(_get_style())
        self.setWindowFlags(
            self.windowFlags() | Qt.WindowType.WindowStaysOnTopHint
        )
        self._build_ui()
        self._load()
        self._connect_live()

    def showEvent(self, event) -> None:
        super().showEvent(event)
        if sys.platform == "win32":
            try:
                hwnd = int(self.winId())
                # Dark title bar
                ctypes.windll.dwmapi.DwmSetWindowAttribute(
                    hwnd, 20,
                    ctypes.byref(ctypes.c_int(1)),
                    ctypes.sizeof(ctypes.c_int),
                )
                # Square corners (Windows 11)
                ctypes.windll.dwmapi.DwmSetWindowAttribute(
                    hwnd, 33,
                    ctypes.byref(ctypes.c_int(1)),
                    ctypes.sizeof(ctypes.c_int),
                )
            except Exception:
                pass

    # ------------------------------------------------------------------ #
    # UI construction                                                      #
    # ------------------------------------------------------------------ #

    def _build_ui(self):
        root = QVBoxLayout(self)
        root.setSpacing(8)
        root.setContentsMargins(14, 14, 14, 14)

        # ── Capture region ──────────────────────────────────────────────
        grp_cap = QGroupBox("Capture region")
        fl = QFormLayout(grp_cap)
        fl.setSpacing(5)

        self.x_spin = self._spin(0, 7680)
        self.y_spin = self._spin(0, 4320)
        self.w_spin = self._spin(10, 3840)
        self.h_spin = self._spin(10, 2160)
        fl.addRow("X:", self.x_spin)
        fl.addRow("Y:", self.y_spin)
        fl.addRow("Width:", self.w_spin)
        fl.addRow("Height:", self.h_spin)

        btn_select = QPushButton("Select with mouse…")
        btn_select.clicked.connect(self.select_region_requested.emit)
        fl.addRow(btn_select)
        root.addWidget(grp_cap)

        # ── Overlay position ─────────────────────────────────────────────
        grp_pos = QGroupBox("Overlay position")
        fl_pos = QFormLayout(grp_pos)
        fl_pos.setSpacing(5)

        self.ox_spin = self._spin(-7680, 7680)
        self.oy_spin = self._spin(-4320, 4320)
        fl_pos.addRow("Center X:", self.ox_spin)
        fl_pos.addRow("Center Y:", self.oy_spin)

        # Lock button
        self._lock_btn = QPushButton()
        self._lock_btn.setCheckable(False)
        self._lock_btn.clicked.connect(self._toggle_lock)
        fl_pos.addRow(self._lock_btn)
        root.addWidget(grp_pos)

        # ── Display ─────────────────────────────────────────────────────
        grp_disp = QGroupBox("Display")
        fl2 = QFormLayout(grp_disp)
        fl2.setSpacing(9)

        self.scale_spin = QDoubleSpinBox()
        self.scale_spin.setRange(0.25, 5.0)
        self.scale_spin.setSingleStep(0.25)
        self.scale_spin.setDecimals(2)
        fl2.addRow("Scale:", self.scale_spin)

        self.fps_spin = QSpinBox()
        self.fps_spin.setRange(1, 240)
        self.fps_spin.setSuffix(" FPS")
        fl2.addRow("FPS:", self.fps_spin)

        op_row = QHBoxLayout()
        self.opacity_slider = self._slider(10, 100)
        self.opacity_lbl = QLabel("100%")
        self.opacity_lbl.setFixedWidth(36)
        self.opacity_slider.valueChanged.connect(
            lambda v: self.opacity_lbl.setText(f"{v}%")
        )
        op_row.addWidget(self.opacity_slider)
        op_row.addWidget(self.opacity_lbl)
        fl2.addRow("Opacity:", op_row)

        # Border radius
        cr_row = QHBoxLayout()
        self.corner_slider = self._slider(0, 20)
        self.corner_lbl = QLabel("0%")
        self.corner_lbl.setFixedWidth(36)
        self.corner_slider.valueChanged.connect(
            lambda v: self.corner_lbl.setText(f"{v * 5}%")
        )
        cr_row.addWidget(self.corner_slider)
        cr_row.addWidget(self.corner_lbl)
        fl2.addRow("Border radius:", cr_row)

        # Border width
        self.border_w_spin = self._spin(0, 20)
        self.border_w_spin.setSuffix(" px")
        fl2.addRow("Border width:", self.border_w_spin)

        # Border color
        self._color_btn = QPushButton()
        self._color_btn.setMinimumHeight(26)
        self._color_btn.clicked.connect(self._pick_color)
        self._refresh_color_btn()
        fl2.addRow("Border color:", self._color_btn)

        # Cover on/off
        self._cover_toggle_btn = QPushButton()
        self._cover_toggle_btn.clicked.connect(self._toggle_cover)
        self._update_cover_btn()
        fl2.addRow("Cover:", self._cover_toggle_btn)

        # Cover color
        self._cover_color_btn = QPushButton()
        self._cover_color_btn.setMinimumHeight(26)
        self._cover_color_btn.clicked.connect(self._pick_cover_color)
        self._refresh_cover_color_btn()
        fl2.addRow("Cover color:", self._cover_color_btn)

        root.addWidget(grp_disp)

        # ── Hotkeys ─────────────────────────────────────────────────────
        grp_key = QGroupBox("Hotkeys  (applied on Save)")
        fl3 = QFormLayout(grp_key)
        fl3.setSpacing(5)

        tip = (
            "Format: ctrl+num 1  ·  f8  ·  ctrl+shift+m\n"
            "Numpad keys: num 0 … num 9\n"
            "Leave empty to disable."
        )
        self.hk_toggle   = self._hk_edit(tip)
        self.hk_settings = self._hk_edit(tip)
        self.hk_cover    = self._hk_edit(tip)
        self.hk_exit     = self._hk_edit(tip)

        fl3.addRow("Toggle on/off:", self.hk_toggle)
        fl3.addRow("Open settings:", self.hk_settings)
        fl3.addRow("Cover source:", self.hk_cover)
        fl3.addRow("Exit:", self.hk_exit)
        root.addWidget(grp_key)

        # ── Buttons ─────────────────────────────────────────────────────
        btns = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok
            | QDialogButtonBox.StandardButton.Cancel
        )
        btns.button(QDialogButtonBox.StandardButton.Ok).setText("Save")
        btns.button(QDialogButtonBox.StandardButton.Cancel).setText("Cancel")
        btns.accepted.connect(self._save)
        btns.rejected.connect(self._cancel)
        root.addWidget(btns)

    # ------------------------------------------------------------------ #
    # Helpers                                                              #
    # ------------------------------------------------------------------ #

    @staticmethod
    def _spin(lo: int, hi: int) -> QSpinBox:
        s = QSpinBox()
        s.setRange(lo, hi)
        return s

    @staticmethod
    def _slider(lo: int, hi: int) -> QSlider:
        s = QSlider(Qt.Orientation.Horizontal)
        s.setRange(lo, hi)
        return s

    @staticmethod
    def _hk_edit(tooltip: str) -> QLineEdit:
        e = QLineEdit()
        e.setToolTip(tooltip)
        e.setPlaceholderText("e.g. ctrl+num 1")
        return e

    def _pick_color(self):
        c = QColorDialog.getColor(QColor(self._border_color), self, "Border color")
        if c.isValid():
            self._border_color = c.name()
            self._refresh_color_btn()
            self._live_update()

    def _refresh_color_btn(self):
        self._color_btn.setStyleSheet(
            f"background-color:{self._border_color}; border:1px solid #444;"
        )

    def _pick_cover_color(self):
        c = QColorDialog.getColor(QColor(self._cover_color), self, "Cover color")
        if c.isValid():
            self._cover_color = c.name()
            self._refresh_cover_color_btn()
            self._live_update()

    def _refresh_cover_color_btn(self):
        self._cover_color_btn.setStyleSheet(
            f"background-color:{self._cover_color}; border:1px solid #444;"
        )

    def _toggle_cover(self):
        self._cover_enabled = not self._cover_enabled
        self._update_cover_btn()
        self._live_update()

    def _update_cover_btn(self):
        if self._cover_enabled:
            self._cover_toggle_btn.setText("ON")
            self._cover_toggle_btn.setProperty("cover", "true")
        else:
            self._cover_toggle_btn.setText("OFF")
            self._cover_toggle_btn.setProperty("cover", "false")
        self._cover_toggle_btn.style().unpolish(self._cover_toggle_btn)
        self._cover_toggle_btn.style().polish(self._cover_toggle_btn)

    def _toggle_lock(self):
        self.config.locked = not self.config.locked
        self._update_lock_btn()
        self.config_applied.emit()

    def _update_lock_btn(self):
        if self.config.locked:
            self._lock_btn.setText("Unlock movement")
            self._lock_btn.setProperty("locked", "true")
        else:
            self._lock_btn.setText("Lock movement")
            self._lock_btn.setProperty("locked", "false")
        # Force stylesheet refresh
        self._lock_btn.style().unpolish(self._lock_btn)
        self._lock_btn.style().polish(self._lock_btn)

    # ------------------------------------------------------------------ #
    # Live preview                                                         #
    # ------------------------------------------------------------------ #

    def _connect_live(self):
        for w in (self.x_spin, self.y_spin, self.w_spin, self.h_spin,
                  self.ox_spin, self.oy_spin, self.border_w_spin, self.fps_spin):
            w.valueChanged.connect(self._live_update)
        self.scale_spin.valueChanged.connect(self._live_update)
        self.opacity_slider.valueChanged.connect(self._live_update)
        self.corner_slider.valueChanged.connect(self._live_update)
        # Hotkeys and color are handled separately (on Save / on pick)

    def _live_update(self):
        if not self._live:
            return
        cfg = self.config
        cfg.capture_x      = self.x_spin.value()
        cfg.capture_y      = self.y_spin.value()
        cfg.capture_w      = self.w_spin.value()
        cfg.capture_h      = self.h_spin.value()
        cfg.overlay_cx     = self.ox_spin.value()
        cfg.overlay_cy     = self.oy_spin.value()
        cfg.overlay_scale  = self.scale_spin.value()
        cfg.fps            = self.fps_spin.value()
        cfg.overlay_opacity = self.opacity_slider.value() / 100.0
        cfg.border_width          = self.border_w_spin.value()
        cfg.border_color          = self._border_color
        cfg.corner_radius         = self.corner_slider.value() * 5
        cfg.source_cover_enabled  = self._cover_enabled
        cfg.source_cover_color    = self._cover_color
        self.config_applied.emit()

    # ------------------------------------------------------------------ #
    # Load / Save / Cancel                                                 #
    # ------------------------------------------------------------------ #

    def _load(self):
        cfg = self.config
        self._live = False   # block signals while loading
        self.x_spin.setValue(cfg.capture_x)
        self.y_spin.setValue(cfg.capture_y)
        self.w_spin.setValue(cfg.capture_w)
        self.h_spin.setValue(cfg.capture_h)
        self.ox_spin.setValue(cfg.overlay_cx)
        self.oy_spin.setValue(cfg.overlay_cy)
        self.scale_spin.setValue(cfg.overlay_scale)
        self.fps_spin.setValue(cfg.fps)
        self.opacity_slider.setValue(int(cfg.overlay_opacity * 100))
        self.border_w_spin.setValue(cfg.border_width)
        self.corner_slider.setValue(cfg.corner_radius // 5)
        self.corner_lbl.setText(f"{cfg.corner_radius}%")
        self._border_color  = cfg.border_color
        self._refresh_color_btn()
        self._cover_enabled = cfg.source_cover_enabled
        self._cover_color   = cfg.source_cover_color
        self._refresh_cover_color_btn()
        self._update_cover_btn()
        self.hk_toggle.setText(cfg.hotkey_toggle)
        self.hk_settings.setText(cfg.hotkey_settings)
        self.hk_cover.setText(cfg.hotkey_cover)
        self.hk_exit.setText(cfg.hotkey_exit)
        self._update_lock_btn()
        self._live = True

    def _save(self):
        # Hotkeys only applied on explicit Save
        cfg = self.config
        cfg.hotkey_toggle   = self.hk_toggle.text().strip()
        cfg.hotkey_settings = self.hk_settings.text().strip()
        cfg.hotkey_cover    = self.hk_cover.text().strip()
        cfg.hotkey_exit     = self.hk_exit.text().strip()
        self.config_applied.emit()
        self.accept()

    def _cancel(self):
        # Revert all live changes to the snapshot taken at open time
        for k, v in self._original.items():
            if hasattr(self.config, k):
                setattr(self.config, k, v)
        self.config_applied.emit()
        self.reject()

    # ------------------------------------------------------------------ #
    # Called from main when region selector finishes                      #
    # ------------------------------------------------------------------ #

    def update_position(self, cx: int, cy: int) -> None:
        """Called when the overlay is dragged — keeps spinboxes in sync."""
        self._live = False
        self.ox_spin.setValue(cx)
        self.oy_spin.setValue(cy)
        self._live = True

    def update_region(self, x: int, y: int, w: int, h: int) -> None:
        self._live = False
        self.x_spin.setValue(x)
        self.y_spin.setValue(y)
        self.w_spin.setValue(w)
        self.h_spin.setValue(h)
        self._live = True
        self._live_update()

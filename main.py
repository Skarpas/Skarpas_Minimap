"""
Minimap Overlay – entry point
Captures a screen region and shows it as a frameless always-on-top window.
System tray icon provides access to settings and toggle.
"""

import sys
import ctypes

from PyQt6.QtWidgets import QApplication
from PyQt6.QtCore import QObject, pyqtSignal

from config import load_config, save_config
from capture import CaptureThread
from overlay_window import OverlayWindow, SourceCoverWindow
from settings_dialog import SettingsDialog
from region_selector import RegionSelector
from tray_manager import TrayManager

import keyboard as kb


# ──────────────────────────────────────────────────────────────────────────────
# Qt signal bridge (lets non-Qt threads trigger Qt-thread operations safely)
# ──────────────────────────────────────────────────────────────────────────────

class _Bridge(QObject):
    show_settings  = pyqtSignal()
    toggle_overlay = pyqtSignal()
    toggle_cover   = pyqtSignal()
    quit_app       = pyqtSignal()


# ──────────────────────────────────────────────────────────────────────────────
# Application controller
# ──────────────────────────────────────────────────────────────────────────────

class MinimapApp:
    def __init__(self):
        self._app = QApplication(sys.argv)
        self._app.setQuitOnLastWindowClosed(False)

        self._config  = load_config()
        self._capture = CaptureThread(self._config)
        self._overlay = OverlayWindow(self._config, self._capture)
        self._cover   = SourceCoverWindow(self._config)
        self._bridge  = _Bridge()
        self._tray    = TrayManager(
            on_settings = self._bridge.show_settings.emit,
            on_toggle   = self._bridge.toggle_overlay.emit,
            on_exit     = self._bridge.quit_app.emit,
        )

        self._settings_open:  bool                   = False
        self._selector:       RegionSelector | None  = None
        self._active_dialog:  SettingsDialog | None  = None
        self._hotkey_handles: dict[str, object]      = {}
        self._settings_pos                           = None   # remembered position

        self._bridge.show_settings.connect(self._open_settings)
        self._bridge.toggle_overlay.connect(self._toggle)
        self._bridge.toggle_cover.connect(self._toggle_cover_source)
        self._bridge.quit_app.connect(self._quit)
        self._overlay.position_changed.connect(self._on_overlay_moved)

    def run(self) -> int:
        self._capture.start()

        if self._config.enabled:
            self._overlay.show()
            if self._config.source_cover_enabled:
                self._cover.apply_config()
                self._cover.show()

        self._tray.start()
        self._register_hotkeys()

        return self._app.exec()

    # ------------------------------------------------------------------ #
    # Overlay toggle                                                       #
    # ------------------------------------------------------------------ #

    def _toggle_cover_source(self) -> None:
        self._config.source_cover_enabled = not self._config.source_cover_enabled
        self._update_cover()

    def _toggle(self) -> None:
        self._config.enabled = not self._config.enabled
        if self._config.enabled:
            self._capture.set_enabled(True)
            self._overlay.show()
        else:
            self._overlay.hide()
            self._capture.set_enabled(False)
        self._update_cover()

        status = "ON" if self._config.enabled else "OFF"
        self._tray.update_tooltip(f"Minimap Overlay – {status}")

    # ------------------------------------------------------------------ #
    # Settings dialog                                                      #
    # ------------------------------------------------------------------ #

    def _open_settings(self) -> None:
        if self._settings_open:
            if self._active_dialog:
                self._active_dialog.raise_()
                self._active_dialog.activateWindow()
            return

        self._settings_open = True
        dlg = SettingsDialog(self._config)
        self._active_dialog = dlg

        dlg.select_region_requested.connect(lambda: self._start_region_select(dlg))
        dlg.config_applied.connect(self._apply_config)
        dlg.finished.connect(self._on_settings_closed)

        dlg.show()
        if self._settings_pos:
            dlg.move(self._settings_pos)   # restore last position

    def _on_settings_closed(self) -> None:
        if self._active_dialog:
            self._settings_pos = self._active_dialog.pos()   # remember for next open
        self._settings_open = False
        self._active_dialog = None
        save_config(self._config)

    def _on_overlay_moved(self, cx: int, cy: int) -> None:
        if self._active_dialog:
            self._active_dialog.update_position(cx, cy)

    def _apply_config(self) -> None:
        self._overlay.apply_config()
        self._capture.update_config(self._config)
        self._register_hotkeys()
        self._update_cover()

    def _update_cover(self) -> None:
        if self._config.source_cover_enabled and self._config.enabled:
            self._cover.apply_config()
            self._cover.show()
        else:
            self._cover.hide()

    # ------------------------------------------------------------------ #
    # Region selector                                                      #
    # ------------------------------------------------------------------ #

    def _start_region_select(self, dialog: SettingsDialog) -> None:
        saved_pos = dialog.pos()   # remember position before hiding
        dialog.hide()
        self._selector = RegionSelector(screen_index=0)
        self._selector.region_selected.connect(
            lambda x, y, w, h: self._on_region_done(dialog, x, y, w, h)
        )
        def _restore():
            if not dialog.isVisible():
                dialog.show()
                dialog.move(saved_pos)   # restore after show()
        self._selector.destroyed.connect(_restore)

    def _on_region_done(
        self, dialog: SettingsDialog, x: int, y: int, w: int, h: int
    ) -> None:
        dialog.update_region(x, y, w, h)
        dialog.show()
        dialog.raise_()

    # ------------------------------------------------------------------ #
    # Hotkeys                                                              #
    # ------------------------------------------------------------------ #

    def _register_hotkeys(self) -> None:
        for handle in self._hotkey_handles.values():
            try:
                kb.remove_hotkey(handle)
            except Exception:
                pass
        self._hotkey_handles.clear()

        actions = {
            "toggle":   (self._config.hotkey_toggle,   self._bridge.toggle_overlay.emit),
            "settings": (self._config.hotkey_settings,  self._bridge.show_settings.emit),
            "cover":    (self._config.hotkey_cover,     self._bridge.toggle_cover.emit),
            "exit":     (self._config.hotkey_exit,      self._bridge.quit_app.emit),
        }
        for name, (combo, callback) in actions.items():
            combo = combo.strip().lower()
            if not combo:
                continue
            try:
                self._hotkey_handles[name] = kb.add_hotkey(combo, callback)
            except Exception as exc:
                print(f"[Minimap] No se pudo registrar '{combo}': {exc}")

    # ------------------------------------------------------------------ #
    # Quit                                                                 #
    # ------------------------------------------------------------------ #

    def _quit(self) -> None:
        save_config(self._config)
        self._capture.stop()
        self._cover.hide()
        self._tray.stop()
        self._app.quit()


# ──────────────────────────────────────────────────────────────────────────────
# Entry point
# ──────────────────────────────────────────────────────────────────────────────

def _hide_console() -> None:
    try:
        hwnd = ctypes.windll.kernel32.GetConsoleWindow()
        if hwnd:
            ctypes.windll.user32.ShowWindow(hwnd, 0)
    except Exception:
        pass


if __name__ == "__main__":
    _hide_console()
    app = MinimapApp()
    sys.exit(app.run())

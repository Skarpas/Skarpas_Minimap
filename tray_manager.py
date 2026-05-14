import threading
import pystray
from icon import make_icon


class TrayManager:
    def __init__(self, on_settings, on_toggle, on_exit):
        self._on_settings = on_settings
        self._on_toggle   = on_toggle
        self._on_exit     = on_exit
        self._icon: pystray.Icon | None = None

    def start(self) -> None:
        menu = pystray.Menu(
            pystray.MenuItem("Configuración",        self._settings_cb),
            pystray.MenuItem("Activar / Desactivar", self._toggle_cb),
            pystray.Menu.SEPARATOR,
            pystray.MenuItem("Salir",                self._exit_cb),
        )
        self._icon = pystray.Icon(
            "MinimapOverlay",
            make_icon(),
            "Minimap Overlay",
            menu,
        )
        threading.Thread(target=self._icon.run, daemon=True).start()

    def stop(self) -> None:
        if self._icon:
            self._icon.stop()

    def update_tooltip(self, text: str) -> None:
        if self._icon:
            self._icon.title = text

    def _settings_cb(self, icon, item): self._on_settings()
    def _toggle_cb(self,   icon, item): self._on_toggle()
    def _exit_cb(self,     icon, item): self._on_exit(); icon.stop()

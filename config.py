import json
import os
import sys
from dataclasses import dataclass, asdict

# When running as a PyInstaller exe, __file__ points to a temp folder.
# Use the directory of the exe itself so config.json persists next to it.
if getattr(sys, "frozen", False):
    _BASE = os.path.dirname(sys.executable)
else:
    _BASE = os.path.dirname(os.path.abspath(__file__))

CONFIG_PATH = os.path.join(_BASE, "config.json")


@dataclass
class Config:
    # Capture region (pixels on source screen)
    capture_x: int = 2058
    capture_y: int = 0
    capture_w: int = 400
    capture_h: int = 400

    # Overlay window position (CENTER of the overlay window)
    overlay_cx: int = 1280
    overlay_cy: int = 1000

    # Display
    overlay_scale: float = 1.0
    fps: int = 60
    overlay_opacity: float = 1.0   # 0.1 – 1.0

    # Border
    border_color: str = "#00537d"
    border_width: int = 2

    # Hotkeys (keyboard-library format: "ctrl+num 1", "f8", "ctrl+shift+m" …)
    hotkey_toggle:   str = "ctrl+num 1"
    hotkey_settings: str = "ctrl+num 2"
    hotkey_exit:     str = "ctrl+num 9"
    hotkey_cover:    str = "ctrl+num 3"

    # Shape
    corner_radius: int = 0     # 0 = square, up to min(w,h)/2 = circle

    # Source cover (solid overlay drawn over the captured region)
    source_cover_enabled: bool = False
    source_cover_color: str = "#00537d"

    # Behaviour
    enabled: bool = True
    locked:  bool = True


def load_config() -> Config:
    if os.path.exists(CONFIG_PATH):
        try:
            with open(CONFIG_PATH, "r", encoding="utf-8") as f:
                data = json.load(f)
            cfg = Config()
            for k, v in data.items():
                if hasattr(cfg, k):
                    setattr(cfg, k, v)
            return cfg
        except Exception:
            pass
    return Config()


def save_config(config: Config) -> None:
    with open(CONFIG_PATH, "w", encoding="utf-8") as f:
        json.dump(asdict(config), f, indent=2)

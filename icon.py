"""Shared icon generator used by the tray and the settings window."""
from PIL import Image, ImageDraw, ImageFont


def make_icon() -> Image.Image:
    """
    'SM' initials on a dark square — matches the Settings dialog palette.
    Dark bg #141414, light gray text #c0c0c0. Rendered at 128x128 → 64x64.
    """
    S   = 128
    BG  = (20,  20,  20,  255)   # #141414
    FG  = (192, 192, 192, 255)   # #c0c0c0

    img  = Image.new("RGBA", (S, S), BG)
    draw = ImageDraw.Draw(img)

    # Try to load a clean system font; fall back to PIL default
    font = None
    for name in [
        "C:/Windows/Fonts/segoeui.ttf",
        "C:/Windows/Fonts/arial.ttf",
        "C:/Windows/Fonts/verdana.ttf",
    ]:
        try:
            font = ImageFont.truetype(name, size=80)
            break
        except Exception:
            pass
    if font is None:
        font = ImageFont.load_default()

    text = "SM"
    bbox = draw.textbbox((0, 0), text, font=font)
    tw   = bbox[2] - bbox[0]
    th   = bbox[3] - bbox[1]
    x    = (S - tw) // 2 - bbox[0]
    y    = (S - th) // 2 - bbox[1]
    draw.text((x, y), text, fill=FG, font=font)

    return img.resize((64, 64), Image.LANCZOS)


def make_qicon():
    """Return a QIcon built from make_icon() for use in Qt windows."""
    from PyQt6.QtGui import QIcon, QPixmap, QImage
    pil = make_icon().convert("RGBA")
    data = pil.tobytes("raw", "RGBA")
    qimg = QImage(data, pil.width, pil.height, QImage.Format.Format_RGBA8888)
    return QIcon(QPixmap.fromImage(qimg))

"""
Helper utilities for PHASe application
"""
import os
import sys
import math
from PyQt5.QtCore import QPointF
from PyQt5.QtGui import QIcon, QPixmap, QCursor, QPainter, QPen, QColor
from PyQt5.QtCore import Qt


def absolute_path(relative_path):
    """Get absolute path to resource, works for dev and for PyInstaller"""
    try:
        # PyInstaller creates a temp folder and stores path in _MEIPASS
        base_path = sys._MEIPASS
    except Exception:
        base_path = os.path.abspath(".")
    return os.path.join(base_path, relative_path)


def serialize_qt_object(obj):
    """Serialize Qt objects for saving"""
    if isinstance(obj, QPointF):
        return {'__type__': 'QPointF', 'x': obj.x(), 'y': obj.y()}
    return str(obj)


def deserialize_qt_object(obj):
    """Deserialize Qt objects from saved data"""
    if isinstance(obj, dict) and '__type__' in obj:
        if obj['__type__'] == 'QPointF':
            return QPointF(float(obj['x']), float(obj['y']))
    return obj


def parse_input_with_units(input_text):
    """Parse input text with units and convert to micrometers.
    Supported units: mm, µm/um/u, nm, pm.
    """
    if not input_text:
        return None

    input_text = input_text.strip().lower().replace(" ", "").replace("μ", "u")

    try:
        # Find where the number ends and the unit begins
        number_end = 0
        for i, char in enumerate(input_text):
            if not (char.isdigit() or char == '.'):
                number_end = i
                break

        if number_end == 0:
            number = float(input_text)
            unit = 'um'  # Default to micrometers if no unit is specified
        else:
            number = float(input_text[:number_end])
            unit = input_text[number_end:]

        # Convert to micrometers
        if unit in ['um', 'µm', 'u']:
            return number
        elif unit == 'mm':
            return number * 1000
        elif unit == 'nm':
            return number / 1000
        elif unit == 'pm':
            return number / 1_000_000
        else:
            raise ValueError(f"Invalid unit: {unit}")

    except ValueError as e:
        raise ValueError(f"Invalid input: {input_text}") from e


def calculate_height(x, y, capillary_height, ceiling_y, floor_y, angle_degrees, wall_thickness=0):
    """Calculate particle height based on position and capillary parameters"""
    if capillary_height is None or ceiling_y is None or floor_y is None:
        return 0

    slope = math.tan(math.radians(angle_degrees))

    ceiling_y_at_x = ceiling_y + x * slope
    floor_y_at_x = floor_y + x * slope

    total_pixels = abs(ceiling_y_at_x - floor_y_at_x)

    if wall_thickness > 0:
        wall_adjustment = (wall_thickness / capillary_height) * total_pixels
        ceiling_y_at_x += wall_adjustment
        floor_y_at_x -= wall_adjustment

    adjusted_total_pixels = abs(ceiling_y_at_x - floor_y_at_x)
    pixels_from_bottom = abs(y - floor_y_at_x)

    return (pixels_from_bottom / adjusted_total_pixels) * capillary_height if adjusted_total_pixels > 0 else 0


def create_custom_cursor(svg_path, color):
    """Create a custom cursor from SVG with color overlay"""
    # Create a base pixmap for the cursor
    base_pixmap = QPixmap(32, 32)
    base_pixmap.fill(Qt.transparent)

    # Draw the cross
    painter = QPainter(base_pixmap)
    painter.setPen(QPen(Qt.white, 2))
    painter.drawLine(16, 0, 16, 32)  # Vertical line
    painter.drawLine(0, 16, 32, 16)  # Horizontal line

    # Load and color the SVG icon
    icon = QIcon(absolute_path(svg_path))
    icon_pixmap = icon.pixmap(16, 16)  # Smaller size for the corner icon
    icon_painter = QPainter(icon_pixmap)
    icon_painter.setCompositionMode(QPainter.CompositionMode_SourceIn)
    icon_painter.fillRect(icon_pixmap.rect(), color)
    icon_painter.end()

    # Draw the icon in the top-right corner
    painter.drawPixmap(16, 0, icon_pixmap)
    painter.end()

    return QCursor(base_pixmap, 16, 16)  # Hotspot at the center of the cross


def get_app_data_dir(app_name, app_author):
    """Get platform-specific application data directory"""
    if sys.platform == 'win32':
        import winreg
        key = winreg.OpenKey(
            winreg.HKEY_CURRENT_USER,
            r"Software\Microsoft\Windows\CurrentVersion\Explorer\Shell Folders"
        )
        dir_, _ = winreg.QueryValueEx(key, "Local AppData")
        return os.path.join(dir_, app_author, app_name)
    elif sys.platform == 'darwin':
        return os.path.expanduser(f'~/Library/Application Support/{app_name}')
    else:
        return os.path.expanduser(f'~/.local/share/{app_name}')

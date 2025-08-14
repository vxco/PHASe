# Application metadata
CURRENT_VERSION = "4.0.1"
CURRENT_VERSION_NAME = "Bosphorus"

# Feature flags
FAST_BOOT = True
BETA_FEATURES_ENABLED = True
AUTO_UPDATE_ENABLED = False

# UI Configuration
DEFAULT_LABEL_SIZE = 100
MAX_RECENT_FILES = 5

# Update configuration
GITHUB_OWNER = "vxco"
GITHUB_REPO = "PHASe"

# File extensions
WORKSPACE_EXTENSION = "*.phw"
IMAGE_EXTENSIONS = "*.png *.jpg *.bmp"

# Default values
DEFAULT_ANGLE = 0.0
MIN_ANGLE = -90
MAX_ANGLE = 90
DEFAULT_BASE_WIDTH = 1000

# Colors (as tuples for easy conversion to QColor)
CEILING_COLOR = (255, 0, 0)  # Red
FLOOR_COLOR = (0, 255, 0)    # Green
PARTICLE_COLOR = (255, 0, 0) # Red
BACKGROUND_COLOR = (44, 62, 80)
PRIMARY_COLOR = (52, 152, 219)
SECONDARY_COLOR = (52, 73, 94)

# UI Styling
BUTTON_STYLE = """
    QPushButton {
        background-color: #34495e;
        color: white;
        border: 2px solid #2c3e50;
        border-radius: 10px;
        padding: 10px;
        text-align: center;
        font-size: 13px;
    }
    QPushButton:hover {
        background-color: #3498db;
        border-color: #2980b9;
    }
    QPushButton:pressed {
        background-color: #2980b9;
        border-color: #21618c;
    }
"""

MAIN_WINDOW_STYLE = """
    QMainWindow {
        background-color: #2c3e50;
    }
    QLabel {
        color: white;
        font-size: 14px;
    }
"""

INPUT_STYLE = """
    QLineEdit {
        background-color: #34495e;
        color: white;
        border: 1px solid #2c3e50;
        border-radius: 5px;
        padding: 5px;
        font-size: 14px;
    }
"""

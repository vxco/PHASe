"""
PHASe - Particle Height Analysis Software
Main application entry point using modular architecture
"""
import sys
import platform
from PyQt5.QtWidgets import QApplication
from PyQt5.QtCore import Qt

from utils.logging_utils import app_logger, exception_handler
from core.analyzer import CapillaryAnalyzer


def main():
    """Main application entry point"""
    try:
        app_logger.info("Starting PHASe...")

        # Set up exception handling
        sys.excepthook = lambda *args: exception_handler(app_logger, *args)

        # Create QApplication
        app = QApplication(sys.argv)

        # Platform-specific settings
        if platform.system() == 'Darwin':
            app.setAttribute(Qt.AA_DontUseNativeMenuBar, False)

        app_logger.info("Creating main window...")

        # Create and show main window
        window = CapillaryAnalyzer()
        window.show()

        app_logger.info("Entering main event loop...")
        sys.exit(app.exec_())

    except Exception as e:
        app_logger.exception("An unexpected error occurred during startup:")
        sys.exit(1)


if __name__ == "__main__":
    main()

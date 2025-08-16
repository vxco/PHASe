"""
PHASe - Particle Height Analysis Software
Main application entry point using modular architecture
"""
import sys
import platform
from PyQt5.QtWidgets import QApplication
from PyQt5.QtCore import Qt

from utils.logging_utils import app_logger, app_logger_instance, performance_logger, exception_handler
from core.analyzer import CapillaryAnalyzer


def main():
    """Main application entry point"""
    try:
        # Log application startup timing
        with performance_logger.log_timing("Application Startup"):

            # Set up exception handling
            sys.excepthook = lambda *args: exception_handler(app_logger, *args)

            # Enable detailed calculation logging for development/debugging
            # Set to False for production to reduce log size
            DETAILED_LOGGING = False  # Change to True to enable detailed calculation logs
            if DETAILED_LOGGING:
                app_logger_instance.set_detailed_calculation_logging(
                    enabled=True,
                    min_duration_ms=0.5  # Log operations taking >= 0.5ms
                )

            # Log Qt application creation
            with performance_logger.log_timing("QApplication Creation"):
                app = QApplication(sys.argv)

            # Platform-specific settings
            app_logger.info(f"Detected platform: {platform.system()}")
            if platform.system() == 'Darwin':
                app.setAttribute(Qt.AA_DontUseNativeMenuBar, False)
                app_logger.debug("Set macOS-specific Qt attributes")

            # Log main window creation timing
            with performance_logger.log_timing("Main Window Initialization"):
                window = CapillaryAnalyzer()
                window.show()

            app_logger_instance.log_event("APPLICATION", "PHASe main window displayed successfully")

        # Enter main event loop
        app_logger.info("Entering Qt main event loop...")
        exit_code = app.exec_()
        app_logger.info(f"Application exited with code: {exit_code}")

        # Ensure logs are saved before exit
        app_logger_instance.save_session_logs()
        sys.exit(exit_code)

    except Exception as e:
        app_logger_instance.log_error("STARTUP_ERROR", "Fatal error during application startup", exception=e)
        # Still save logs even on error
        app_logger_instance.save_session_logs()
        sys.exit(1)


if __name__ == "__main__":
    main()

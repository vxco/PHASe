"""
Logging utilities for PHASe application
"""
import logging
import os
import sys
import time
import functools
import atexit
from datetime import datetime
from contextlib import contextmanager
from logging.handlers import RotatingFileHandler
from collections import defaultdict, Counter


class CalculationLogManager:
    """Manages calculation logs with classification and summarization"""

    def __init__(self):
        self.detailed_logs = []
        self.summary_stats = defaultdict(list)
        self.operation_counts = Counter()
        self.total_durations = defaultdict(float)
        self.detailed_logging_enabled = False
        self.min_duration_threshold = 1.0  # Only log operations > 1ms in detailed mode

    def set_detailed_logging(self, enabled, min_duration_ms=1.0):
        """Enable/disable detailed logging with minimum duration threshold"""
        self.detailed_logging_enabled = enabled
        self.min_duration_threshold = min_duration_ms

    def add_calculation(self, calc_type, operation, duration_ms, result_count=None, **kwargs):
        """Add a calculation with smart classification"""
        timestamp = datetime.now().isoformat()

        # Classify the operation
        classification = self._classify_operation(calc_type, operation)

        # Always update summary stats
        self.summary_stats[classification].append(duration_ms)
        self.operation_counts[f"{calc_type}:{operation}"] += 1
        self.total_durations[classification] += duration_ms

        # Only store detailed logs if enabled and meets threshold
        if (self.detailed_logging_enabled and
            duration_ms >= self.min_duration_threshold):

            detailed_entry = {
                'timestamp': timestamp,
                'calc_type': calc_type,
                'operation': operation,
                'classification': classification,
                'duration_ms': duration_ms,
                'result_count': result_count,
                'metadata': {k: v for k, v in kwargs.items()}
            }
            self.detailed_logs.append(detailed_entry)

    def _classify_operation(self, calc_type, operation):
        """Classify operations into categories for better organization"""
        operation_lower = operation.lower()

        # UI Operations
        if calc_type == "UI" or any(term in operation_lower for term in
                                   ['label', 'widget', 'button', 'dialog', 'graphics']):
            if any(term in operation_lower for term in ['creation', 'init', 'setup']):
                return "UI_INITIALIZATION"
            elif any(term in operation_lower for term in ['render', 'draw', 'paint']):
                return "UI_RENDERING"
            elif any(term in operation_lower for term in ['drag', 'move', 'resize']):
                return "UI_INTERACTION"
            else:
                return "UI_OTHER"

        # Image Processing
        elif any(term in operation_lower for term in
                ['image', 'pixel', 'crop', 'resize', 'filter']):
            return "IMAGE_PROCESSING"

        # Calculations
        elif any(term in operation_lower for term in
                ['calculate', 'compute', 'analyze', 'measurement']):
            return "CALCULATIONS"

        # File Operations
        elif any(term in operation_lower for term in
                ['load', 'save', 'export', 'import', 'file']):
            return "FILE_OPERATIONS"

        # Performance/System
        elif any(term in operation_lower for term in
                ['startup', 'initialization', 'cleanup']):
            return "SYSTEM_PERFORMANCE"

        else:
            return "MISCELLANEOUS"

    def get_summary(self):
        """Generate summary statistics"""
        summary = {
            'session_overview': {
                'total_operations': sum(self.operation_counts.values()),
                'unique_operation_types': len(self.operation_counts),
                'detailed_logs_captured': len(self.detailed_logs),
                'detailed_logging_enabled': self.detailed_logging_enabled,
                'min_duration_threshold_ms': self.min_duration_threshold
            },
            'category_statistics': {},
            'top_operations': dict(self.operation_counts.most_common(10)),
            'performance_insights': {}
        }

        # Calculate category statistics
        for category, durations in self.summary_stats.items():
            if durations:
                summary['category_statistics'][category] = {
                    'total_time_ms': sum(durations),
                    'average_time_ms': sum(durations) / len(durations),
                    'min_time_ms': min(durations),
                    'max_time_ms': max(durations),
                    'operation_count': len(durations),
                    'percentage_of_total': (sum(durations) / sum(sum(d) for d in self.summary_stats.values())) * 100
                }

        # Performance insights
        total_time = sum(sum(d) for d in self.summary_stats.values())
        if total_time > 0:
            # Find performance bottlenecks
            slowest_categories = sorted(
                [(cat, sum(durations)) for cat, durations in self.summary_stats.items()],
                key=lambda x: x[1], reverse=True
            )[:3]

            summary['performance_insights'] = {
                'total_computation_time_ms': total_time,
                'slowest_categories': [
                    {'category': cat, 'total_time_ms': time_ms, 'percentage': (time_ms/total_time)*100}
                    for cat, time_ms in slowest_categories
                ],
                'recommendations': self._generate_recommendations(slowest_categories, total_time)
            }

        return summary

    def _generate_recommendations(self, slowest_categories, total_time):
        """Generate performance recommendations based on analysis"""
        recommendations = []

        for category, time_ms in slowest_categories[:2]:  # Top 2 slowest
            percentage = (time_ms / total_time) * 100

            if category == "UI_RENDERING" and percentage > 30:
                recommendations.append("Consider optimizing UI rendering - high rendering time detected")
            elif category == "IMAGE_PROCESSING" and percentage > 40:
                recommendations.append("Image processing operations are taking significant time - consider async processing")
            elif category == "UI_INITIALIZATION" and percentage > 20:
                recommendations.append("UI initialization is slow - consider lazy loading of components")
            elif category == "CALCULATIONS" and percentage > 50:
                recommendations.append("Mathematical calculations dominate execution time - consider optimization or caching")

        if not recommendations:
            recommendations.append("Performance appears well-balanced across categories")

        return recommendations


class PerformanceLogger:
    """Performance and timing logger"""

    def __init__(self, logger):
        self.logger = logger

    @contextmanager
    def log_timing(self, operation_name, level=logging.INFO):
        """Context manager for timing operations"""
        start_time = time.perf_counter()
        self.logger.log(level, f"Starting operation: {operation_name}")
        try:
            yield
            end_time = time.perf_counter()
            duration_ms = (end_time - start_time) * 1000
            self.logger.log(level, f"Completed operation: {operation_name} in {duration_ms:.2f}ms")
        except Exception as e:
            end_time = time.perf_counter()
            duration_ms = (end_time - start_time) * 1000
            self.logger.error(f"Failed operation: {operation_name} after {duration_ms:.2f}ms - Error: {str(e)}")
            raise

    def log_function_timing(self, func):
        """Decorator for timing function calls"""
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            start_time = time.perf_counter()
            self.logger.debug(f"Calling function: {func.__name__}")
            try:
                result = func(*args, **kwargs)
                end_time = time.perf_counter()
                duration_ms = (end_time - start_time) * 1000
                self.logger.debug(f"Function {func.__name__} completed in {duration_ms:.2f}ms")
                return result
            except Exception as e:
                end_time = time.perf_counter()
                duration_ms = (end_time - start_time) * 1000
                self.logger.error(f"Function {func.__name__} failed after {duration_ms:.2f}ms - Error: {str(e)}")
                raise
        return wrapper


class Logger:
    def __init__(self, app_name):
        self.app_name = app_name
        self.logger = logging.getLogger(app_name)
        self.logger.setLevel(logging.DEBUG)
        self.performance = PerformanceLogger(self.logger)

        # Initialize enhanced calculation log manager
        self.calc_log_manager = CalculationLogManager()
        self.session_timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")

        # Register exit handler to save logs
        atexit.register(self.save_session_logs)

        self.setup_logging()

    def get_log_path(self, filename):
        if getattr(sys, 'frozen', False):
            if sys.platform == 'Darwin':
                return os.path.join(os.path.expanduser('~/Library/Logs'), self.app_name, filename)
            else:
                return os.path.join(os.path.dirname(sys.executable), 'logs', filename)
        else:
            return os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'logs', filename)

    def get_session_log_path(self, filename):
        """Get path for session-specific logs in timestamped folder"""
        session_folder = f"session_{self.session_timestamp}"
        if getattr(sys, 'frozen', False):
            if sys.platform == 'Darwin':
                return os.path.join(os.path.expanduser('~/Library/Logs'), self.app_name, session_folder, filename)
            else:
                return os.path.join(os.path.dirname(sys.executable), 'logs', session_folder, filename)
        else:
            return os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'logs', session_folder, filename)

    def setup_logging(self):
        # Clear existing handlers
        self.logger.handlers.clear()

        log_file = self.get_log_path('phase.log')
        log_dir = os.path.dirname(log_file)
        os.makedirs(log_dir, exist_ok=True)

        # File handler with more detailed format
        file_handler = RotatingFileHandler(log_file, maxBytes=5 * 1024 * 1024, backupCount=10)
        console_handler = logging.StreamHandler()

        # Enhanced formatter with more details
        detailed_formatter = logging.Formatter(
            '%(asctime)s - %(name)s - %(levelname)s - [%(filename)s:%(lineno)d] | %(message)s'
        )
        file_handler.setFormatter(detailed_formatter)
        console_handler.setFormatter(detailed_formatter)

        # Set different levels for different handlers
        file_handler.setLevel(logging.DEBUG)
        console_handler.setLevel(logging.INFO)

        self.logger.addHandler(file_handler)
        self.logger.addHandler(console_handler)

        # Log system information on startup
        self.log_system_info()

    def log_system_info(self):
        """Log system and environment information"""
        import platform
        import PyQt5.QtCore

        self.logger.info("=" * 50)
        self.logger.info("PHASe Application Starting")
        self.logger.info("=" * 50)
        self.logger.info(f"Python version: {sys.version}")
        self.logger.info(f"Platform: {platform.system()} {platform.release()}")
        self.logger.info(f"Architecture: {platform.machine()}")
        self.logger.info(f"PyQt5 version: {PyQt5.QtCore.QT_VERSION_STR}")
        self.logger.info("=" * 50)

    def get_logger(self):
        return self.logger

    def log_event(self, event_type, message, **kwargs):
        """Log structured events with optional metadata"""
        metadata = " | ".join([f"{k}={v}" for k, v in kwargs.items()])
        full_message = f"[{event_type}] {message}"
        if metadata:
            full_message += f" | {metadata}"
        self.logger.info(full_message)

    def log_error(self, error_type, message, exception=None, **kwargs):
        """Log structured errors with optional metadata"""
        metadata = " | ".join([f"{k}={v}" for k, v in kwargs.items()])
        full_message = f"[{error_type}] {message}"
        if metadata:
            full_message += f" | {metadata}"

        if exception:
            self.logger.error(full_message, exc_info=exception)
        else:
            self.logger.error(full_message)

    def set_detailed_calculation_logging(self, enabled, min_duration_ms=1.0):
        """Enable/disable detailed calculation logging"""
        self.calc_log_manager.set_detailed_logging(enabled, min_duration_ms)
        self.logger.info(f"Detailed calculation logging {'enabled' if enabled else 'disabled'} "
                        f"(threshold: {min_duration_ms}ms)")

    def log_calculation(self, calc_type, operation, duration_ms, result_count=None, **kwargs):
        """Log calculation operations with smart classification and summarization"""
        # Add to calculation log manager
        self.calc_log_manager.add_calculation(calc_type, operation, duration_ms, result_count, **kwargs)

        # Log to regular logger based on importance/duration
        if duration_ms >= 10.0:  # Only log operations >= 10ms to regular log
            metadata_str = " | ".join([f"{k}={v}" for k, v in kwargs.items()])
            message = f"[CALC:{calc_type}] {operation} completed in {duration_ms:.2f}ms"
            if result_count is not None:
                message += f" | results={result_count}"
            if metadata_str:
                message += f" | {metadata_str}"
            self.logger.debug(message)

    def save_session_logs(self):
        """Save calculation logs and general logs to timestamped session folder"""
        try:
            # Create session folder
            session_folder_path = os.path.dirname(self.get_session_log_path("dummy"))
            os.makedirs(session_folder_path, exist_ok=True)

            # Generate summary
            summary = self.calc_log_manager.get_summary()

            # Save summary statistics (always saved)
            summary_path = self.get_session_log_path("calculation_summary.json")
            import json
            with open(summary_path, 'w') as f:
                json.dump({
                    'session_info': {
                        'session_id': self.session_timestamp,
                        'start_time': self.session_timestamp,
                        'end_time': datetime.now().strftime("%Y%m%d_%H%M%S"),
                    },
                    'summary': summary
                }, f, indent=2)

            print(f"Calculation summary saved to: {summary_path}")

            # Save detailed logs only if they exist and detailed logging was enabled
            if self.calc_log_manager.detailed_logs:
                detailed_log_path = self.get_session_log_path("calculation_detailed.json")
                with open(detailed_log_path, 'w') as f:
                    json.dump({
                        'session_info': {
                            'session_id': self.session_timestamp,
                            'detailed_logging_enabled': self.calc_log_manager.detailed_logging_enabled,
                            'min_duration_threshold_ms': self.calc_log_manager.min_duration_threshold,
                            'total_detailed_entries': len(self.calc_log_manager.detailed_logs)
                        },
                        'detailed_calculations': self.calc_log_manager.detailed_logs
                    }, f, indent=2)

                print(f"Detailed calculation logs saved to: {detailed_log_path}")

            # Copy current general log to session folder
            current_log_path = self.get_log_path('phase.log')
            session_general_log_path = self.get_session_log_path("general_log.log")

            if os.path.exists(current_log_path):
                import shutil
                shutil.copy2(current_log_path, session_general_log_path)
                print(f"General logs saved to: {session_general_log_path}")

            print(f"Session logs saved to folder: {session_folder_path}")

        except Exception as e:
            # Use basic print since logger might be shutting down
            print(f"Error saving session logs: {e}")

def exception_handler(logger, exc_type, exc_value, exc_traceback):
    """Global exception handler"""
    logger.error("Uncaught exception", exc_info=(exc_type, exc_value, exc_traceback))
    sys.exit(1)


# Initialize application logger
app_logger_instance = Logger("PHASe")
app_logger = app_logger_instance.get_logger()
performance_logger = app_logger_instance.performance

import logging
import os
import sys
from logging.handlers import RotatingFileHandler


class Logger:
    def __init__(self, app_name):
        self.app_name = app_name
        self.logger = logging.getLogger(app_name)
        self.logger.setLevel(logging.DEBUG)
        self.setup_logging()

    def get_log_path(self, filename):
        if getattr(sys, 'frozen', False):
            if sys.platform == 'darwin':
                return os.path.join(os.path.expanduser('~/Library/Logs'), self.app_name, filename)
            else:
                return os.path.join(os.path.dirname(sys.executable), 'logs', filename)
        else:
            return os.path.join(os.path.dirname(os.path.abspath(__file__)), 'logs', filename)

    def setup_logging(self):
        log_file = self.get_log_path('app.log')
        log_dir = os.path.dirname(log_file)
        os.makedirs(log_dir, exist_ok=True)

        file_handler = RotatingFileHandler(log_file, maxBytes=1024 * 1024, backupCount=5)
        console_handler = logging.StreamHandler()

        formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
        file_handler.setFormatter(formatter)
        console_handler.setFormatter(formatter)

        self.logger.addHandler(file_handler)
        self.logger.addHandler(console_handler)

    def get_logger(self):
        return self.logger


def exception_handler(logger, exc_type, exc_value, exc_traceback):
    logger.error("Uncaught exception", exc_info=(exc_type, exc_value, exc_traceback))
    sys.exit(1)


# Initialize logger
app_logger = Logger('PHASe').get_logger()
sys.excepthook = lambda *args: exception_handler(app_logger, *args)

app_logger.info("Starting PHASe")

try:
    import csv
    import json
    import math
    import traceback
    import platform
    import subprocess
    import tempfile
    from urllib.request import urlretrieve
    import requests
    from packaging import version

    from PyQt5.QtCore import (Qt, QPoint, QPointF, QRectF, QLineF, pyqtSignal,
                              QObject, QSize, QTimer, QBuffer, QPropertyAnimation,
                              QEasingCurve, QByteArray)

    from PyQt5.QtGui import (QPainter, QColor, QPen, QPixmap, QImage, QFont, QPalette, QIcon, QCursor)

    from PyQt5.QtWidgets import (QApplication, QMainWindow, QLabel, QPushButton, QInputDialog,
                                 QVBoxLayout, QHBoxLayout, QWidget, QGraphicsScene, QGraphicsView,
                                 QGraphicsTextItem, QGraphicsRectItem, QGraphicsLineItem,
                                 QGraphicsItemGroup, QGraphicsItem, QFrame, QGridLayout,
                                 QSizePolicy, QMenu, QAction, QGraphicsDropShadowEffect,
                                 QGraphicsEllipseItem, QCheckBox, QLineEdit, QFileDialog,
                                 QMessageBox, QGraphicsOpacityEffect)

    app_logger.info("All modules imported successfully")

except ImportError as e:
    app_logger.error(f"oopsie! Import error: {str(e)}")
    app_logger.error("contact support with the above error")
    sys.exit(1)

CURRENT_VERSION = "3.0.5"
CURRENT_VERSION_NAME = "Hierapolis"


def serialize_qt_object(obj):
    if isinstance(obj, QPointF):
        return {'__type__': 'QPointF', 'x': obj.x(), 'y': obj.y()}
    return str(obj)

def deserialize_qt_object(obj):
    if isinstance(obj, dict) and '__type__' in obj:
        if obj['__type__'] == 'QPointF':
            return QPointF(float(obj['x']), float(obj['y']))
    return obj


def absolute_path(relative_path):
    """ Get absolute path to resource, works for dev and for PyInstaller """
    try:
        # PyInstaller creates a temp folder and stores path in _MEIPASS
        base_path = sys._MEIPASS
    except Exception:
        base_path = os.path.abspath(".")

    return os.path.join(base_path, relative_path)


class ToastNotification(QWidget):
    def __init__(self, parent, title, message, buttons=None, timeout=5000):
        super().__init__(parent)
        self.parent = parent
        self.timeout = timeout

        # Update the timer setup
        self.timer = QTimer(self)
        self.timer.timeout.connect(self.fade_out)
        self.timer.setSingleShot(True)

        self.setWindowFlags(Qt.FramelessWindowHint | Qt.Tool | Qt.WindowStaysOnTopHint)
        self.setAttribute(Qt.WA_TranslucentBackground)

        layout = QVBoxLayout()
        self.setLayout(layout)

        # Title
        self.title_label = QLabel(title)
        self.title_label.setStyleSheet("color: white; font-size: 16px; font-weight: bold;")
        layout.addWidget(self.title_label)

        # Message
        self.message_label = QLabel(message)
        self.message_label.setStyleSheet("color: white; font-size: 14px;")
        self.message_label.setWordWrap(True)
        layout.addWidget(self.message_label)

        # Buttons
        self.buttons = {}
        if buttons:
            button_layout = QHBoxLayout()
            for button_text in buttons:
                button = QPushButton(button_text)
                button.setStyleSheet("""
                    QPushButton {
                        background-color: #34495e;
                        color: white;
                        border: none;
                        border-radius: 5px;
                        padding: 5px 15px;
                        margin: 5px;
                    }
                    QPushButton:hover {
                        background-color: #3498db;
                    }
                """)
                button_layout.addWidget(button)
                self.buttons[button_text] = button
            layout.addLayout(button_layout)

        # Set size and position
        self.setMinimumSize(400, 150)
        self.adjustSize()
        self.move(parent.width() - self.width() - 20, parent.height() - self.height() - 20)

        # Fade in animation
        self.opacity_effect = QGraphicsOpacityEffect(self)
        self.setGraphicsEffect(self.opacity_effect)
        self.fade_in_animation = QPropertyAnimation(self.opacity_effect, b"opacity")
        self.fade_in_animation.setDuration(500)
        self.fade_in_animation.setStartValue(0)
        self.fade_in_animation.setEndValue(1)
        self.fade_in_animation.setEasingCurve(QEasingCurve.InOutQuad)

        # Fade out animation
        self.fade_out_animation = QPropertyAnimation(self.opacity_effect, b"opacity")
        self.fade_out_animation.setDuration(500)
        self.fade_out_animation.setStartValue(1)
        self.fade_out_animation.setEndValue(0)
        self.fade_out_animation.setEasingCurve(QEasingCurve.InOutQuad)
        self.fade_out_animation.finished.connect(self.close)

        # Auto-close timer
        self.timer = QTimer(self)
        self.timer.timeout.connect(self.fade_out)
        self.timer.setSingleShot(True)

    def showEvent(self, event):
        super().showEvent(event)
        self.fade_in_animation.start()
        self.timer.start(self.timeout)

    def fade_out(self):
        self.fade_out_animation.start()

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)

        # Draw rounded rectangle
        painter.setBrush(QColor(44, 62, 80, 230))  # Semi-transparent dark blue
        painter.setPen(Qt.NoPen)
        painter.drawRoundedRect(self.rect(), 10, 10)

        super().paintEvent(event)


class TourGuide(QWidget):
    def __init__(self, parent):
        super().__init__(parent)
        self.setWindowFlags(Qt.FramelessWindowHint | Qt.Tool)
        self.setAttribute(Qt.WA_TranslucentBackground)
        self.setAttribute(Qt.WA_ShowWithoutActivating)

        self.layout = QVBoxLayout(self)
        self.message = QLabel()
        self.message.setWordWrap(True)
        self.message.setStyleSheet("""
            background-color: rgba(52, 73, 94, 220);
            color: white;
            border-radius: 10px;
            padding: 10px;
        """)
        self.layout.addWidget(self.message)

        self.next_button = QPushButton("Next")
        self.next_button.setStyleSheet("""
            background-color: #3498db;
            color: white;
            border: none;
            padding: 5px 10px;
            border-radius: 5px;
        """)
        self.layout.addWidget(self.next_button)

        self.setFixedWidth(350)  # Set a fixed width to make it narrower

        self.opacity_effect = QGraphicsOpacityEffect()
        self.setGraphicsEffect(self.opacity_effect)

        self.arrow = QLabel("▲")  # Unicode up arrow
        self.arrow.setStyleSheet("""
                    color: rgba(52, 73, 94, 220);
                    font-size: 16px;
                """)
        self.layout.insertWidget(0, self.arrow, 0, Qt.AlignCenter)

        self.opacity_animation = QPropertyAnimation(self.opacity_effect, b"opacity")
        self.opacity_animation.setDuration(300)
        self.opacity_animation.setStartValue(0)
        self.opacity_animation.setEndValue(1)
        self.opacity_animation.setEasingCurve(QEasingCurve.InOutQuad)

    def show_message(self, message, target_widget, custom_pos=None):
        self.message.setText(message)

        if custom_pos:
            pos = self.adjust_position(custom_pos)
            self.move(pos)
            self.arrow.show()
        elif target_widget:
            pos = self.adjust_position(self.get_target_position(target_widget))
            self.move(pos)
            self.arrow.hide()
        else:
            pos = self.adjust_position(self.parent().rect().center() - self.rect().center())
            self.move(pos)
            self.arrow.hide()

        self.show()
        self.opacity_animation.start()

    def get_target_position(self, target_widget):
        if target_widget:
            target_rect = target_widget.rect()
            target_pos = target_widget.mapToGlobal(target_rect.topRight())
            return self.parent().mapFromGlobal(target_pos + QPoint(10, 0))
        return self.parent().rect().center() - self.rect().center()

    def adjust_position(self, pos):
        parent_rect = self.parent().rect()
        guide_rect = self.rect()

        # Adjust x-coordinate
        if pos.x() + guide_rect.width() > parent_rect.width():
            pos.setX(parent_rect.width() - guide_rect.width())
        if pos.x() < 0:
            pos.setX(0)

        # Adjust y-coordinate
        if pos.y() + guide_rect.height() > parent_rect.height():
            pos.setY(parent_rect.height() - guide_rect.height())
        if pos.y() < 0:
            pos.setY(0)

        return pos

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)
        painter.setBrush(Qt.transparent)
        painter.setPen(QPen(QColor(52, 152, 219), 2))
        painter.drawRoundedRect(self.rect(), 10, 10)
        super().paintEvent(event)


class CustomGraphicsScene(QGraphicsScene):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.parent = parent

    def update_connection_lines(self):
        for particle in self.particles:
            if 'label_item' in particle and 'line_item' in particle:
                label = particle['label_item']
                line = particle['line_item']
                start = QPointF(particle['x'], particle['y'])
                end = label.sceneBoundingRect().center()
                line.setLine(QLineF(start, end))


class DraggableLabelSignals(QObject):
    deleteRequested = pyqtSignal(object)
    moved = pyqtSignal(object)



class ScrollWheel(QWidget):
    valueChanged = pyqtSignal(float)

    def __init__(self, parent=None, is_fine=False):
        super().__init__(parent)
        self.value = 0
        self.min_value = -90
        self.max_value = 90
        self.setFixedSize(40, 100)  # Even smaller fixed size
        self.last_y = None
        self.sensitivity = 0.01 if is_fine else 0.1
        self.is_fine = is_fine

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)

        # Draw background
        painter.fillRect(self.rect(), QColor(50, 50, 50))

        # Draw wheel
        wheel_rect = QRectF(2, 2, self.width() - 4, self.height() - 4)
        painter.setPen(QPen(QColor(200, 200, 200), 1))
        painter.setBrush(QColor(100, 100, 100))
        painter.drawRoundedRect(wheel_rect, 5, 5)

        # Draw label
        painter.setPen(QColor(255, 255, 255))
        painter.setFont(QFont("Arial", 8))
        label = "Fine" if self.is_fine else "Coarse"
        painter.drawText(wheel_rect, Qt.AlignHCenter | Qt.AlignTop, label)

        # Draw tick marks
        painter.setPen(QPen(QColor(200, 200, 200), 1))
        for i in range(5):
            y = int(10 + i * (self.height() - 20) / 4)
            painter.drawLine(5, y, 10, y)
            painter.drawLine(self.width() - 10, y, self.width() - 5, y)

    def mousePressEvent(self, event):
        self.last_y = event.pos().y()

    def setValue(self, new_value):
        new_value = max(self.min_value, min(self.max_value, new_value))
        if self.value != new_value:
            self.value = new_value
            self.update()
            self.valueChanged.emit(self.value)

    def getValue(self):
        return self.value

    def mouseMoveEvent(self, event):
        if self.last_y is not None:
            delta = self.last_y - event.pos().y()
            self.value += delta * self.sensitivity
            self.value = max(self.min_value, min(self.max_value, self.value))
            self.last_y = event.pos().y()
            self.update()
            self.valueChanged.emit(self.value)

    def mouseReleaseEvent(self, event):
        self.last_y = None

    def wheelEvent(self, event):
        delta = event.angleDelta().y() / 120
        self.value += delta * self.sensitivity
        self.value = max(self.min_value, min(self.max_value, self.value))
        self.update()
        self.valueChanged.emit(self.value)



class ModernButton(QPushButton):
    def __init__(self, icon_path, text, parent=None):
        super().__init__(parent)
        self.setText(text)
        self.setIcon(QIcon(absolute_path(icon_path)))
        self.setIconSize(QSize(32, 32))
        self.setCursor(Qt.PointingHandCursor)
        self.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        self.setStyleSheet("""
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
        """)

    def sizeHint(self):
        return QSize(120, 60)  # Set a default size for the buttons


class DraggableLabel(QGraphicsItemGroup):
    def __init__(self, x, y, name, height, analyzer):
        super().__init__()
        self.setFlag(QGraphicsItemGroup.ItemIsMovable)
        self.setFlag(QGraphicsItemGroup.ItemSendsGeometryChanges)
        self.x = x
        self.y = y
        self.name = name
        self.height = height
        self.analyzer = analyzer
        self.signals = DraggableLabelSignals()
        self.delete_button = None
        self.create_label()

    def create_label(self):
        font_size = 14
        label_text = self.get_label_text()
        label = QGraphicsTextItem(label_text)
        font = QFont("Arial", font_size)
        label.setFont(font)
        label.setDefaultTextColor(QColor(255, 255, 255))

        text_width = label.boundingRect().width()
        text_height = label.boundingRect().height()
        padding = 8
        delete_button_size = 20
        total_width = max(text_width + delete_button_size + padding * 2, 100)  # Minimum width of 100
        total_height = max(text_height, delete_button_size) + padding * 2

        background = QGraphicsRectItem(0, 0, total_width, total_height)
        background.setBrush(QColor(60, 60, 60, 220))
        background.setPen(QPen(QColor(100, 100, 100), 1))

        label.setPos(QPointF(padding, padding))

        delete_button = QGraphicsRectItem(total_width - delete_button_size - padding, padding, delete_button_size,
                                          delete_button_size)
        delete_button.setBrush(QColor(200, 60, 60))
        delete_button.setPen(QPen(QColor(220, 80, 80), 1))
        delete_button.setFlag(QGraphicsItem.ItemIsSelectable)

        delete_cross = QGraphicsTextItem('×')
        delete_cross.setFont(QFont("Arial", delete_button_size - 4, QFont.Bold))
        delete_cross.setDefaultTextColor(QColor(255, 255, 255))

        # Center the cross in the delete button
        cross_rect = delete_cross.boundingRect()
        cross_x = delete_button.rect().x() + (delete_button_size - cross_rect.width()) / 2
        cross_y = delete_button.rect().y() + (delete_button_size - cross_rect.height()) / 2
        delete_cross.setPos(cross_x, cross_y)

        self.addToGroup(background)
        self.addToGroup(label)
        self.addToGroup(delete_button)
        self.addToGroup(delete_cross)
        self.delete_button = delete_button

        self.setPos(self.x + 10, self.y - total_height - 10)

    def mousePressEvent(self, event):
        if event.button() == Qt.RightButton:
            self.show_context_menu(event.screenPos())
        elif self.delete_button.contains(event.pos()):
            self.signals.deleteRequested.emit(self)
        else:
            super().mousePressEvent(event)

    def show_context_menu(self, pos):
        menu = QMenu()
        rename_action = menu.addAction("Rename")
        delete_action = menu.addAction("Delete")

        # Add submenu for previously used names
        names_submenu = menu.addMenu("Select Name")
        for name in self.analyzer.used_names:
            names_submenu.addAction(name)

        action = menu.exec_(pos)
        if action == rename_action:
            self.rename()
        elif action == delete_action:
            self.signals.deleteRequested.emit(self)
        elif action and action.text() in self.analyzer.used_names:
            self.name = action.text()
            self.update_label_text()
            self.analyzer.update_particle_data(self, {'name': self.name})

    def rename(self):
        dialog = self.analyzer.create_styled_input_dialog("Rename Particle", "Enter new name:", self.name or "")
        if dialog.exec_() == QInputDialog.Accepted:
            new_name = dialog.textValue()
            self.name = new_name if new_name else ''
            if self.name:
                self.analyzer.add_used_name(self.name)
            self.update_label_text()
            self.analyzer.update_particle_data(self, {'name': self.name, 'x': self.x, 'y': self.y})

    def get_label_text(self):
        if self.name:
            return f"{self.name}: {self.height:.2f} µm"
        else:
            return f"{self.height:.2f} µm"

    def update_label_text(self):
        label_text = self.get_label_text()
        text_item = self.childItems()[1]
        text_item.setPlainText(label_text)

        # Recalculate size
        text_width = text_item.boundingRect().width()
        text_height = text_item.boundingRect().height()
        padding = 8
        delete_button_size = 20
        total_width = max(text_width + delete_button_size + padding * 2, 100)  # Minimum width of 100
        total_height = max(text_height, delete_button_size) + padding * 2

        # Update background rectangle
        background = self.childItems()[0]
        background.setRect(0, 0, total_width, total_height)

        # Update delete button position
        delete_button = self.childItems()[2]
        delete_button.setRect(total_width - delete_button_size - padding, padding, delete_button_size,
                              delete_button_size)

        # Update delete cross position
        delete_cross = self.childItems()[3]
        cross_rect = delete_cross.boundingRect()
        cross_x = delete_button.rect().x() + (delete_button_size - cross_rect.width()) / 2
        cross_y = delete_button.rect().y() + (delete_button_size - cross_rect.height()) / 2
        delete_cross.setPos(cross_x, cross_y)


        # #ifitworksdonttouchit


    def itemChange(self, change, value):
        if change == QGraphicsItemGroup.ItemPositionHasChanged:
            self.signals.moved.emit(self)
        return super().itemChange(change, value)


class CapillaryAnalyzer(QMainWindow):
    def __init__(self):
        super().__init__()
        self.logger = app_logger
        self.image_loaded = False
        self.setWindowTitle("PHASe - Particle Height Analysis Software")
        self.setGeometry(100, 100, 1400, 900)
        self.setStyleSheet("""
            QMainWindow {
                background-color: #2c3e50;
            }
            QLabel {
                color: white;
                font-size: 14px;
            }
        """)

        main_widget = QWidget()
        self.setCentralWidget(main_widget)
        main_layout = QHBoxLayout()
        main_widget.setLayout(main_layout)

        app_name = "PHASe"
        app_author = "VX Software"
        self.config_dir = self.get_app_data_dir(app_name, app_author)
        os.makedirs(self.config_dir, exist_ok=True)
        self.config_path = os.path.join(self.config_dir, 'phase_config.json')

        self.load_config()

        self.ceiling_cursor = self.create_custom_cursor("assets/set_ceiling_btn.svg", QColor(255, 0, 0))
        self.floor_cursor = self.create_custom_cursor("assets/set_floor_btn.svg", QColor(0, 255, 0))

        self.ceiling_ghost_line = None
        self.floor_ghost_line = None

        self.has_completed_tour = False

        self.tour_guide = TourGuide(self)
        self.tour_guide.next_button.clicked.connect(self.next_tour_step)
        self.tour_steps = []
        self.current_tour_step = 0

        self.message_box_style = """
                QMessageBox {
                    background-color: #2c3e50;
                    color: white;
                }
                QMessageBox QLabel {
                    color: white;
                }
                QMessageBox QPushButton {
                    background-color: #34495e;
                    color: white;
                    border: none;
                    border-radius: 5px;
                    padding: 5px;
                    min-width: 70px;
                }
                QMessageBox QPushButton:hover {
                    background-color: #3498db;
                }
                """

        # Control panel
        control_panel = QFrame()
        control_panel.setStyleSheet("""
                    QFrame {
                        background-color: #34495e;
                        border-radius: 15px;
                        margin: 10px;
                    }
                    QFrame#separator {
                        background-color: #2c3e50;
                        min-height: 2px;
                        max-height: 2px;
                    }
                """)
        control_layout = QVBoxLayout(control_panel)
        self.angle_control = None

        # Logo space
        logo_label = QLabel()
        logo_pixmap = QPixmap(absolute_path("assets/phase_logo_v3.svg"))
        logo_label.setPixmap(logo_pixmap.scaled(200, 100, Qt.KeepAspectRatio, Qt.SmoothTransformation))
        logo_label.setAlignment(Qt.AlignCenter)
        control_layout.addWidget(logo_label)

        # Load Image button (spans two button widths)
        self.load_button = ModernButton("assets/load_image_btn.svg", "Load Image")
        self.load_button.clicked.connect(self.load_image)
        control_layout.addWidget(self.load_button)

        # Ceiling and Floor buttons
        ceiling_floor_layout = QHBoxLayout()


        ceiling_floor_left = QVBoxLayout()
        self.set_ceiling_button = ModernButton("assets/set_ceiling_btn.svg", "Set Ceiling")
        self.set_ceiling_button.clicked.connect(self.set_ceiling_mode)
        ceiling_floor_left.addWidget(self.set_ceiling_button)

        self.set_floor_button = ModernButton("assets/set_floor_btn.svg", "Set Floor")
        self.set_floor_button.clicked.connect(self.set_floor_mode)
        ceiling_floor_left.addWidget(self.set_floor_button)

        ceiling_floor_layout.addLayout(ceiling_floor_left)

        control_layout.addLayout(ceiling_floor_layout)

        # Height and Wall Thickness Layout
        height_wall_layout = QGridLayout()

        self.create_menu_bar()


        # Height Input
        height_label = QLabel("Capillary Height:")
        height_label.setStyleSheet("color: white; font-size: 14px;")
        height_wall_layout.addWidget(height_label, 0, 0)

        self.height_input = QLineEdit()
        self.height_input.setPlaceholderText("mm, µm, pm")
        self.height_input.setStyleSheet("""
            QLineEdit {
                background-color: #34495e;
                color: white;
                border: 1px solid #2c3e50;
                border-radius: 5px;
                padding: 5px;
                font-size: 14px;
            }
        """)
        self.height_input.textChanged.connect(lambda: self.on_input_change(self.height_input))

        height_wall_layout.addWidget(self.height_input, 0, 1)

        # Wall Thickness Checkbox
        self.wall_thickness_checkbox = QCheckBox("Enable Wall Thickness")
        self.wall_thickness_checkbox.setStyleSheet("color: white;")
        self.wall_thickness_checkbox.stateChanged.connect(self.toggle_wall_thickness)
        height_wall_layout.addWidget(self.wall_thickness_checkbox, 1, 0, 1, 2)
        self.height_input.textChanged.connect(lambda: self.on_input_change(self.height_input))

        # Wall Thickness Input
        wall_thickness_label = QLabel("Wall Thickness:")
        wall_thickness_label.setStyleSheet("color: white; font-size: 14px;")
        height_wall_layout.addWidget(wall_thickness_label, 2, 0)

        self.wall_thickness_input = QLineEdit()
        self.wall_thickness_input.setPlaceholderText("Enter thickness (µm)")
        self.wall_thickness_input.setStyleSheet("""
            QLineEdit {
                background-color: #34495e;
                color: white;
                border: 1px solid #2c3e50;
                border-radius: 5px;
                padding: 5px;
                font-size: 14px;
            }
        """)
        self.wall_thickness_input.textChanged.connect(self.update_wall_thickness)
        self.wall_thickness_input.setEnabled(False)
        height_wall_layout.addWidget(self.wall_thickness_input, 2, 1)

        # Add height and wall thickness layout to the main control layout
        control_layout.addLayout(height_wall_layout)

        self.wall_thickness = 0

        # Angle control layout
        angle_control_layout = QHBoxLayout()
        angle_control_layout.setSpacing(5)

        angle_label = QLabel("Angle:")
        angle_label.setStyleSheet("color: white; font-size: 14px;")
        angle_control_layout.addWidget(angle_label)

        self.angle_value = 0

        # Coarse scroll wheel
        self.coarse_wheel = ScrollWheel(is_fine=False)
        self.coarse_wheel.valueChanged.connect(lambda v: self.update_angle(v, is_fine=False))
        angle_control_layout.addWidget(self.coarse_wheel)

        # Fine scroll wheel
        self.fine_wheel = ScrollWheel(is_fine=True)
        self.fine_wheel.valueChanged.connect(lambda v: self.update_angle(v, is_fine=True))
        angle_control_layout.addWidget(self.fine_wheel)

        # Angle input
        self.angle_input = QLineEdit()
        self.angle_input.setText("0.00")
        self.angle_input.setFixedWidth(60)
        self.angle_input.setPlaceholderText("Angle")
        self.angle_input.setStyleSheet("""
            QLineEdit {
                background-color: #34495e;
                color: white;
                border: 1px solid #2c3e50;
                border-radius: 5px;
                padding: 5px;
                font-size: 14px;
            }
        """)
        self.angle_input.returnPressed.connect(self.set_angle_from_input)
        angle_control_layout.addWidget(self.angle_input)

        # Add angle control layout to the main control layout
        control_layout.addLayout(angle_control_layout)

        # Export CSV button (spans two button widths)
        self.export_button = ModernButton("assets/export_as_csv_btn.svg", "Export CSV")
        self.export_button.clicked.connect(self.export_csv)
        control_layout.addWidget(self.export_button)

        # Reset and Clear buttons
        reset_clear_layout = QHBoxLayout()

        self.reset_angle_button = self.create_small_button("Reset Angle", absolute_path("assets/reset_icon.svg"))
        self.reset_angle_button.clicked.connect(self.reset_angle)
        reset_clear_layout.addWidget(self.reset_angle_button)

        self.clear_selections_button = self.create_small_button("Clear All", absolute_path("assets/clear_icon.svg"))
        self.clear_selections_button.clicked.connect(self.clear_selections)
        reset_clear_layout.addWidget(self.clear_selections_button)

        control_layout.addLayout(reset_clear_layout)

        control_layout.addStretch()

        # Image area
        self.graphics_view = QGraphicsView()
        self.graphics_view.setStyleSheet("""
            QGraphicsView {
                background-color: #2c3e50;
                border: none;
                border-radius: 15px;
            }
        """)
        self.scene = CustomGraphicsScene(self)
        self.graphics_view.setScene(self.scene)
        self.graphics_view.setRenderHint(QPainter.Antialiasing)
        self.graphics_view.setTransformationAnchor(QGraphicsView.AnchorUnderMouse)
        self.graphics_view.setResizeAnchor(QGraphicsView.AnchorUnderMouse)

        main_layout.addWidget(control_panel, 1)
        main_layout.addWidget(self.graphics_view, 3)

        self.original_image = None
        self.image_item = None
        self.capillary_height = None
        self.particles = []
        self.particle_items = []
        self.ceiling_y = None
        self.floor_y = None
        self.current_mode = None
        self.used_names = set()

        self.ceiling_line = None
        self.floor_line = None
        self.scale_factor = 1.0

        self.wall_thickness_input.setStyleSheet("""
                        QLineEdit {
                            background-color: #34495e;
                            color: white;
                            border: 1px solid #2c3e50;
                            border-radius: 5px;
                            padding: 5px;
                            font-size: 14px;
                        }
                        QLineEdit:disabled {
                            background-color: #2c3e50;
                            color: #999;
                        }
                    """)
        self.height_input.textChanged.connect(self.on_height_input_change)
        self.height_input.returnPressed.connect(self.process_height_input)
        self.toast_label = None
        self.height_input_valid = False

        QTimer.singleShot(1000, self.check_for_updates)

    def process_height_input(self):
        input_text = self.height_input.text().strip().lower()
        if not input_text:
            return

        try:
            input_text = input_text.replace(" ", "").replace("μ", "u")

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
                self.capillary_height = number
            elif unit == 'mm':
                self.capillary_height = number * 1000
            elif unit == 'pm':
                self.capillary_height = number / 1000
            else:
                raise ValueError("Invalid unit")

            self.height_input.setText(f"{self.capillary_height:.2f} µm")
            self.height_input_valid = True
            self.update_lines()
            self.show_info_message("Height Set", f"Capillary height set to {self.capillary_height:.2f} µm", legacy=True)

        except ValueError:
            self.show_warning_message("Invalid Input",
                                      "Please enter a valid number followed by a unit (um, mm, or pm).")

    def get_app_data_dir(self, app_name, app_author):
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

    def parse_input_with_units(self, input_text):
        input_text = input_text.strip().lower()
        if not input_text:
            return None

        try:
            # Find where the number ends and the unit begins
            for i, char in enumerate(input_text):
                if not (char.isdigit() or char == '.'):
                    number = float(input_text[:i])
                    unit = input_text[i:]
                    break
            else:
                number = float(input_text)
                unit = 'um'  # Default to micrometers if no unit is specified

            # Convert to micrometers
            if unit in ['um', 'μm']:
                return number
            elif unit == 'mm':
                return number * 1000
            elif unit == 'pm':
                return number / 1000
            else:
                self.show_toast("Invalid Unit. Please use um, mm, or pm.", message_type="error")
                return None
        except ValueError:
            self.show_toast("Invalid Input. Please enter a valid number followed by a unit (um, mm, or pm).",
                            message_type="error")
            return None

    def create_menu_bar(self):
        menu_bar = self.menuBar()

        # File menu
        file_menu = menu_bar.addMenu('File')

        save_workspace_action = QAction('Save Workspace', self)
        save_workspace_action.triggered.connect(self.save_workspace)
        file_menu.addAction(save_workspace_action)

        load_workspace_action = QAction('Load Workspace', self)
        load_workspace_action.triggered.connect(self.load_workspace)
        file_menu.addAction(load_workspace_action)

        file_menu.addSeparator()

        check_updates_action = QAction('Check for Updates', self)
        check_updates_action.triggered.connect(self.check_for_updates)
        file_menu.addAction(check_updates_action)

        exit_action = QAction('Exit', self)
        exit_action.triggered.connect(self.close)
        file_menu.addAction(exit_action)

        edit_menu = menu_bar.addMenu('Edit')

        clear_workspace_action = QAction('Clear Workspace', self)
        clear_workspace_action.triggered.connect(self.clear_workspace)
        edit_menu.addAction(clear_workspace_action)

        # Help menu
        help_menu = menu_bar.addMenu('Help')
        interactive_guide_action = QAction('Interactive Guide', self)
        interactive_guide_action.triggered.connect(self.start_guided_tour)
        help_menu.addAction(interactive_guide_action)
        help_menu.addSeparator()
        about_action = QAction('About', self)
        about_action.triggered.connect(self.show_about_dialog)
        help_menu.addAction(about_action)


        # Style the menu bar
        menu_style = """
            QMenuBar {
                background-color: #2c3e50;
                color: white;
                border: none;
            }
            QMenuBar::item {
                background-color: transparent;
                padding: 5px 10px;
            }
            QMenuBar::item:selected {
                background-color: #34495e;
            }
            QMenuBar::item:pressed {
                background-color: #3498db;
            }
            QMenu {
                background-color: #2c3e50;
                color: white;
                border: 1px solid #34495e;
            }
            QMenu::item {
                padding: 5px 30px 5px 20px;
            }
            QMenu::item:selected {
                background-color: #3498db;
            }
        """
        menu_bar.setStyleSheet(menu_style)

        self.setStyleSheet(self.styleSheet() + menu_style)

    def show_about_dialog(self):
        about_text = f"""
        <h2 style='color: white;'>PHASe - Particle Height Analysis Software</h2>
        <p style='color: white;'>Version: {CURRENT_VERSION} ({CURRENT_VERSION_NAME})</p>
        <p style='color: white;'>PHASe is an open source tool for measuring particle heights in imaged capillary systems.</p>
        <p style='color: white;'>Developed by: Alfa Ozaltin @ VX Software</p>
        <p style='color: white;'>Current Platform: {"MacOS (Darwin)" if platform.system() == "Darwin" else f"{platform.system()}"} {platform.release()}</p>
        """

        about_box = QMessageBox(self)
        about_box.setWindowTitle("About PHASe")
        about_box.setWindowFlags(Qt.Tool | Qt.WindowStaysOnTopHint)
        about_box.setText(about_text)
        about_box.setStandardButtons(QMessageBox.Ok)

        about_box.setStyleSheet("""
            QMessageBox {
                background-color: #2c3e50;
            }
            QMessageBox QLabel {
                color: white;
            }
            QMessageBox QPushButton {
                background-color: #34495e;
                color: white;
                border: none;
                border-radius: 5px;
                padding: 5px 15px;
                margin: 5px;
            }
            QMessageBox QPushButton:hover {
                background-color: #3498db;
            }
        """)
        icon = QPixmap(absolute_path("assets/phase_logo_v3.svg"))
        about_box.setIconPixmap(icon.scaled(128, 128, Qt.KeepAspectRatio, Qt.SmoothTransformation))

        about_box.exec_()

    def load_config(self):
        if os.path.exists(self.config_path):
            with open(self.config_path, 'r') as f:
                self.config = json.load(f)
        else:
            self.config = {'tour_completed': False}

    def save_config(self):
        with open(self.config_path, 'w') as f:
            json.dump(self.config, f)

    def start_guided_tour(self):
        self.tour_steps = [
            ("Welcome to PHASe!", "Let's go through the main features of the application.", None),
            ("Set Ceiling", "Click this button and then click on the image to set the ceiling of the capillary.",
             self.set_ceiling_button),
            ("Set Floor", "Click this button and then click on the image to set the Floor of the capillary.",
             self.set_floor_button),
            ("Set Capillary Height", "Enter the capillary height in this input field. You can use mm, µm, or pm units.",
             self.height_input),
            ("Adjust Angle", "Use these scroll wheels or enter a value directly to adjust the angle of the capillary.",
             self.angle_input),
            ("Add Particles", "Click on the image to add particles. You can drag the labels to reposition them.",
             self.graphics_view),
            ("Export Data", "When you're done, click this button to save your data as a CSV file.", self.export_button),
            ("Reset and Clear", "Use these buttons to reset the angle or clear all particle selections.",
             self.reset_angle_button),
            ("Save Workspace","Save your workspace for sharing it with other users or picking up from where you leave off!", "File/Save Workspace"),
            ("Load Workspace","Load saved .phw files to replace the current workspace with the saved one.", "File/Load Workspace"),
            ("That's it!", "You're all set! Remember, you can always access this guide again.", None),
            ("Interactive Guide",
             "You can find the Interactive Guide here in the Help menu whenever you need a refresher.",
             "Help/Interactive Guide")

        ]
        self.current_tour_step = 0
        self.next_tour_step()

    def clear_workspace(self):
        self.show_info_message(
            "Clear Workspace",
            "Are you sure you want to clear the entire workspace? This action cannot be undone.",
            buttons=["Yes", "No"],
            callback=self.perform_clear_workspace
        )

    def perform_clear_workspace(self, response):
        if response == "Yes":
            # Clear image
            self.original_image = None
            self.scene.clear()
            self.image_item = None

            # Reset variables
            self.capillary_height = None
            self.ceiling_y = None
            self.floor_y = None
            self.angle_value = 0
            self.wall_thickness = 0
            self.particles = []
            self.used_names.clear()

            # Reset UI elements
            self.height_input.clear()
            self.angle_input.setText("0.00")
            self.coarse_wheel.setValue(0)
            self.fine_wheel.setValue(0)
            self.wall_thickness_checkbox.setChecked(False)
            self.wall_thickness_input.clear()

            # Clear lines
            self.ceiling_line = None
            self.floor_line = None
            self.ceiling_ghost_line = None
            self.floor_ghost_line = None

            # Update scene
            self.scene.update()

            self.show_info_message("Workspace Cleared",
                                   "The workspace has been reset to its initial state.",
                                   buttons=["OK"],
                                   timeout=3000)  # Set to 2 seconds

    def next_tour_step(self):
        if self.current_tour_step < len(self.tour_steps):
            title, message, target = self.tour_steps[self.current_tour_step]
            if isinstance(target, str) and '/' in target:
                menu_name, item_name = target.split('/')
                self.show_menu_item(menu_name, item_name)
                self.tour_guide.show_message(f"<b>{title}</b><br><br>{message}", self.menuBar())
            else:
                self.tour_guide.show_message(f"<b>{title}</b><br><br>{message}", target)
                if target:
                    self.highlight_widget(target)
            self.current_tour_step += 1
        else:
            self.tour_guide.hide()
            self.config['tour_completed'] = True
            self.save_config()

    def show_menu_item(self, menu_name, item_name):
        menu = next((action.menu() for action in self.menuBar().actions() if action.text() == menu_name), None)
        if menu:
            # Find the menu action
            menu_action = next(action for action in self.menuBar().actions() if action.text() == menu_name)
            menu_rect = self.menuBar().actionGeometry(menu_action)
            global_pos = self.menuBar().mapToGlobal(menu_rect.topLeft())

            # Calculate position for the tour guide
            # Adjust these values to fine-tune the position
            x_offset = 20  # Positive value moves it to the right
            y_offset = menu_rect.height() + 5  # Position it just below the menu bar
            guide_pos = global_pos + QPoint(x_offset, y_offset)

            # Show the tour guide message
            title, message, _ = self.tour_steps[self.current_tour_step]
            self.tour_guide.show_message(f"<b>{title}</b><br><br>{message}", None,
                                         custom_pos=self.mapFromGlobal(guide_pos))

            # Open the menu after a short delay
            QTimer.singleShot(500, lambda: self.open_and_highlight_menu(menu, item_name))

        # Prevent the tour from advancing automatically
        self.tour_guide.next_button.clicked.disconnect()
        self.tour_guide.next_button.clicked.connect(self.on_menu_item_shown)


    def open_and_highlight_menu(self, menu, item_name):
        # Open the menu
        menu_pos = self.menuBar().mapToGlobal(self.menuBar().actionGeometry(menu.menuAction()).bottomLeft())
        menu.popup(menu_pos)

        # Find and highlight the specific item
        item = next((action for action in menu.actions() if action.text() == item_name), None)
        if item:
            # Create a semi-transparent overlay widget
            overlay = QWidget(menu)
            overlay.setStyleSheet("background-color: rgba(52, 152, 219, 100);")
            overlay.setGeometry(menu.actionGeometry(item))
            overlay.show()

            # Remove the overlay and close the menu after a delay
            QTimer.singleShot(5000, overlay.deleteLater)
            QTimer.singleShot(5000, menu.close)

    def on_menu_item_shown(self):
        # Re-connect the next button and move to the next step
        self.tour_guide.next_button.clicked.disconnect()
        self.tour_guide.next_button.clicked.connect(self.next_tour_step)
        self.next_tour_step()

    def highlight_widget(self, widget):
        effect = QGraphicsDropShadowEffect(self)
        effect.setColor(QColor(52, 152, 219))
        effect.setOffset(0, 0)
        effect.setBlurRadius(20)
        widget.setGraphicsEffect(effect)
        QTimer.singleShot(5000, lambda: widget.setGraphicsEffect(None))

    def save_workspace(self):
        file_name, _ = QFileDialog.getSaveFileName(self, "Save Workspace", "", "PHASe Workspace Files (*.phw)")
        if file_name:
            try:
                workspace_data = {
                    'capillary_height': self.capillary_height,
                    'ceiling_y': self.ceiling_y,
                    'floor_y': self.floor_y,
                    'angle_value': self.angle_value,
                    'wall_thickness': self.wall_thickness,
                    'particles': [
                        {k: serialize_qt_object(v) for k, v in p.items() if
                         k not in ['label_item', 'dot_item', 'line_item']}
                        for p in self.particles
                    ],
                    'used_names': list(self.used_names)
                }

                if self.original_image:
                    buffer = QBuffer()
                    buffer.open(QBuffer.ReadWrite)
                    self.original_image.save(buffer, "PNG")
                    workspace_data['image'] = buffer.data().toBase64().data().decode()

                with open(file_name, 'w') as f:
                    json.dump(workspace_data, f, default=serialize_qt_object)

                self.show_info_message("Workspace Saved", f"Workspace saved to {file_name}", legacy=True)

            except Exception as e:
                self.show_error_message("Save Error", f"Error saving workspace: {str(e)}")
                print(f"Full error: {traceback.format_exc()}")  # This will print the full error traceback


    def load_workspace(self):
        file_name, _ = QFileDialog.getOpenFileName(self, "Load Workspace", "", "PHASe Workspace Files (*.phw)")
        if file_name:
            try:
                with open(file_name, 'r') as f:
                    workspace_data = json.load(f, object_hook=self.deserialize_qt_object)

                self.capillary_height = workspace_data.get('capillary_height')
                self.ceiling_y = workspace_data.get('ceiling_y')
                self.floor_y = workspace_data.get('floor_y')
                self.angle_value = workspace_data.get('angle_value', 0)
                self.wall_thickness = workspace_data.get('wall_thickness', 0)
                self.used_names = set(workspace_data.get('used_names', []))

                if 'image' in workspace_data:
                    image_data = QByteArray.fromBase64(workspace_data['image'].encode())
                    self.original_image = QImage.fromData(image_data)
                    self.scene.clear()
                    pixmap = QPixmap.fromImage(self.original_image)
                    self.image_item = self.scene.addPixmap(pixmap)
                    self.scene.setSceneRect(self.image_item.boundingRect())
                    self.graphics_view.fitInView(self.scene.sceneRect(), Qt.KeepAspectRatio)

                    # Recalculate scale factor
                    base_width = 1000  # This should be the same value used in load_image
                    self.scale_factor = self.original_image.width() / base_width

                # Reconstruct particles
                self.particles = []
                for particle_data in workspace_data.get('particles', []):
                    particle = {
                        'x': float(particle_data['x']),
                        'y': float(particle_data['y']),
                        'name': particle_data['name'],
                        'height': float(particle_data['height']),
                        'label_pos': deserialize_qt_object(particle_data['label_pos'])
                    }
                    self.particles.append(particle)

                # Update UI elements
                self.update_ui_from_workspace()

                # Redraw particles
                self.draw_particles()

                self.show_info_message("Workspace Loaded", f"Workspace loaded from {file_name}", legacy=True)


            except Exception as e:

                self.show_error_message("Load Error", f"Error loading workspace: {str(e)}")

                print(f"Full error: {traceback.format_exc()}")  # This will print the full error traceback


    def update_ui_from_workspace(self):
        # Update height input
        if self.capillary_height:
            self.height_input.setText(f"{self.capillary_height:.2f}")

        # Update angle input and wheels
        self.angle_input.setText(f"{self.angle_value:.2f}")
        self.coarse_wheel.setValue(self.angle_value)
        self.fine_wheel.setValue(0)

        # Update wall thickness
        self.wall_thickness_checkbox.setChecked(self.wall_thickness > 0)
        if self.wall_thickness > 0:
            self.wall_thickness_input.setText(f"{self.wall_thickness:.2f}")

        # Redraw particles
        self.draw_particles()

        # Update lines
        self.update_lines()

        # Update scene
        self.scene.update()

    def show_toast(self, message, message_type, timeout=3000):
        if not hasattr(self, 'toast_label') or self.toast_label is None:
            self.toast_label = QLabel(self)
            self.toast_label.setAlignment(Qt.AlignCenter)
            self.toast_label.setWindowFlags(Qt.FramelessWindowHint | Qt.Tool | Qt.WindowStaysOnTopHint)

        self.toast_label.setText(message)

        if message_type == "error":
            background_color = "rgba(231, 76, 60, 220)"  # Semi-transparent red
        elif message_type == "warning":
            background_color = "rgba(243, 156, 18, 220)"  # Semi-transparent orange
        else:  # info
            background_color = "rgba(52, 73, 94, 220)"  # Semi-transparent dark blue

        self.toast_label.setStyleSheet(f"""
            QLabel {{
                color: white;
                padding: 10px;
                border-radius: 10px;
                font-size: 14px;
                background-color: {background_color};
            }}
        """)

        self.toast_label.adjustSize()

        # Position the toast at the bottom center of the window
        toast_x = self.x() + (self.width() - self.toast_label.width()) // 2
        toast_y = self.y() + self.height() - self.toast_label.height() - 20
        self.toast_label.move(toast_x, toast_y)

        self.toast_label.show()

        # Hide the toast after 3 seconds
        QTimer.singleShot(timeout, self.toast_label.hide)

    def create_custom_cursor(self, svg_path, color):
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


    def hide_toast(self):
        if hasattr(self, 'toast_label'):
            self.toast_label.hide()
        if hasattr(self, 'toast_background'):
            self.toast_background.hide()

    def on_height_input_change(self):
        self.height_input_valid = False
        input_text = self.height_input.text().strip().lower()

        if input_text:
            try:
                # Allow for partial input of numbers
                float(input_text.rstrip('um μm mm pm'))
                palette = self.height_input.palette()
                palette.setColor(QPalette.Text, QColor(255, 255, 255))  # White text for valid input
                self.height_input.setPalette(palette)
            except ValueError:
                palette = self.height_input.palette()
                palette.setColor(QPalette.Text, QColor(255, 0, 0))  # Red text for invalid input
                self.height_input.setPalette(palette)
        else:
            # Reset to default style if empty
            self.height_input.setPalette(self.style().standardPalette())

    def on_input_change(self, input_widget):
        input_text = input_widget.text().strip().lower()
        if not input_text:
            return

        try:
            # Allow for partial input of numbers
            float(input_text.rstrip('um μm mm pm'))
            palette = input_widget.palette()
            palette.setColor(QPalette.Text, QColor(255, 255, 255))  # White text for valid input
            input_widget.setPalette(palette)
        except ValueError:
            palette = input_widget.palette()
            palette.setColor(QPalette.Text, QColor(255, 0, 0))  # Red text for invalid input
            input_widget.setPalette(palette)


    def toggle_wall_thickness(self, state):
        if not self.check_image_loaded():
            return
        self.wall_thickness_input.setEnabled(state == Qt.Checked)
        if state != Qt.Checked:
            self.wall_thickness = 0
            self.wall_thickness_input.clear()
        self.update_lines()

    def reset_angle(self):
        self.angle_value = 0
        self.coarse_wheel.setValue(0)
        self.fine_wheel.setValue(0)
        self.angle_input.setText("0.00")
        self.update_lines()

    def clear_selections(self):
        self.ceiling_y = None
        self.floor_y = None
        for particle in self.particles:
            self.scene.removeItem(particle['label_item'])
            self.scene.removeItem(particle['dot_item'])
            self.scene.removeItem(particle['line_item'])
        self.particles.clear()
        self.scene.update()
        self.update_lines()

    def update_wall_thickness(self):
        if not self.check_image_loaded():
            return
        thickness = self.parse_input_with_units(self.wall_thickness_input.text())
        if thickness is not None:
            if thickness >= 0:
                self.wall_thickness = thickness
                self.update_lines()
                self.show_toast(f"Wall thickness set to {self.wall_thickness:.2f} µm", message_type="info")
            else:
                self.show_toast("Invalid Thickness. Please enter a non-negative number.", message_type="error")
        self.update_lines()

    def update_capillary_height(self):
        height_input = self.height_input.text().strip().lower()
        if not height_input:
            return

        try:
            # Find where the number ends and the unit begins
            for i, char in enumerate(height_input):
                if not (char.isdigit() or char == '.'):
                    number = float(height_input[:i])
                    unit = height_input[i:]
                    break
            else:
                number = float(height_input)
                unit = 'um'  # Default to micrometers if no unit is specified

            # Convert to micrometers
            if unit == 'um':
                self.capillary_height = number
            elif unit == 'mm':
                self.capillary_height = number * 1000
            elif unit == 'pm':
                self.capillary_height = number / 1000
            else:
                self.show_warning_message("Invalid Unit", "Please use um, mm, or pm.")
                return

            self.update_lines()
        except ValueError:
            # self.show_warning_message("Invalid Input", "Please enter a valid number followed by a unit (um, mm, or pm).")
            pass

    def update_angle(self, value, is_fine):
        if not self.check_image_loaded():
            return
        if is_fine:
            self.angle_value += value
        else:
            self.angle_value = value

        self.angle_value = max(-90, min(90, self.angle_value))

        # Disconnect signals temporarily
        self.coarse_wheel.valueChanged.disconnect()
        self.fine_wheel.valueChanged.disconnect()

        # Update values
        self.coarse_wheel.setValue(self.angle_value)
        self.fine_wheel.setValue(0)  # Reset fine wheel to center

        # Reconnect signals
        self.coarse_wheel.valueChanged.connect(lambda v: self.update_angle(v, is_fine=False))
        self.fine_wheel.valueChanged.connect(lambda v: self.update_angle(v, is_fine=True))

        self.angle_input.setText(f"{self.angle_value:.2f}")
        self.update_lines()

    def set_angle_from_input(self):
        if not self.check_image_loaded():
            return
        try:
            angle = float(self.angle_input.text())
            if -90 <= angle <= 90:
                self.angle_value = angle
                self.coarse_wheel.setValue(self.angle_value)
                self.fine_wheel.setValue(0)  # Reset fine wheel to center
                self.update_lines()
            else:
                self.show_toast("Invalid Angle: Please enter an angle between -90 and 90 degrees.", message_type="warning")
        except ValueError:
            self.show_toast("Invalid Input: Please enter a valid number for the angle.", message_type="error")

    def load_image(self):
        if not self.config.get('tour_completed', False):
            self.start_guided_tour()
        try:
            file_name, _ = QFileDialog.getOpenFileName(self, "Open Image", "", "Image Files (*.png *.jpg *.bmp)")
            if file_name:
                image = QImage(file_name)
                if image.isNull():
                    raise Exception("Failed to load image.")

                self.original_image = image.convertToFormat(QImage.Format_RGB32)
                self.scene.clear()
                pixmap = QPixmap.fromImage(self.original_image)
                self.image_item = self.scene.addPixmap(pixmap)
                self.scene.setSceneRect(self.image_item.boundingRect())
                self.graphics_view.fitInView(self.scene.sceneRect(), Qt.KeepAspectRatio)

                # Calculate scale factor based on image size
                base_width = 1000  # You can adjust this value
                self.scale_factor = self.original_image.width() / base_width

                self.particles = []
                self.ceiling_y = None
                self.floor_y = None

                print(f"Image loaded successfully: {file_name}")
                self.image_loaded = True
                print(f"Image size: {self.original_image.width()}x{self.original_image.height()}")
                print(f"Scale factor: {self.scale_factor}")

                # Automatically start ceiling selection
                self.set_ceiling_mode()

        except Exception as e:
            error_message = f"Error loading image: {str(e)}"
            print(error_message)
            QMessageBox.critical(self, "Error", error_message)


    def resizeEvent(self, event):
        super().resizeEvent(event)
        if self.image_item:
            self.graphics_view.fitInView(self.scene.sceneRect(), Qt.KeepAspectRatio)

    def set_ceiling_mode(self):
        if not self.check_image_loaded():
            return
        self.current_mode = "ceiling"
        self.graphics_view.viewport().setCursor(self.ceiling_cursor)
        self.graphics_view.viewport().update()  # Force an update
        QApplication.processEvents()  # Process any pending events
        self.show_info_message("Set Ceiling", "Click on the image to set the ceiling of the capillary.", legacy=True)

    def set_floor_mode(self):
        if not self.check_image_loaded():
            return
        self.current_mode = "floor"
        self.graphics_view.viewport().setCursor(self.floor_cursor)
        self.graphics_view.viewport().update()
        QApplication.processEvents()
        self.show_info_message("Set Floor", "Click on the image to set the floor of the capillary.", legacy=True)


    def point_to_menu_item(self, menu_name, item_name):
        menu = next((action.menu() for action in self.menuBar().actions() if action.text() == menu_name), None)
        if menu:
            item = next((action for action in menu.actions() if action.text() == item_name), None)
            if item:
                menu_pos = self.menuBar().mapToGlobal(self.menuBar().actionGeometry(menu.menuAction()).topLeft())
                item_pos = menu.actionGeometry(item).topLeft()
                global_pos = menu_pos + item_pos

                arrow = QLabel(self)
                arrow.setText("➡")  # Unicode right arrow
                arrow.setStyleSheet("""
                    QLabel {
                        color: #3498db;
                        font-size: 24px;
                        background-color: rgba(52, 152, 219, 50);
                        border-radius: 5px;
                        padding: 5px;
                    }
                """)
                arrow.adjustSize()

                arrow_pos = global_pos - QPoint(arrow.width() + 5, -5)
                arrow.move(self.mapFromGlobal(arrow_pos))
                arrow.show()

                QTimer.singleShot(5000, arrow.deleteLater)

    def mousePressEvent(self, event):
        if not self.image_loaded:
            self.show_toast("Please load an image first.", message_type="error", timeout=3000)
            return
        if self.original_image and self.graphics_view.underMouse():
            scene_pos = self.graphics_view.mapToScene(self.graphics_view.mapFromGlobal(event.globalPos()))

            if self.current_mode == "ceiling":
                self.ceiling_y = scene_pos.y()
                self.current_mode = None
                self.graphics_view.viewport().setCursor(Qt.BlankCursor)
                QApplication.processEvents()
                self.graphics_view.viewport().setCursor(Qt.ArrowCursor)
                self.graphics_view.viewport().update()
                QApplication.processEvents()
                self.update_lines()
                self.set_floor_mode()
            elif self.current_mode == "floor":
                self.floor_y = scene_pos.y()
                self.graphics_view.viewport().setCursor(Qt.BlankCursor)
                QApplication.processEvents()
                self.current_mode = None
                self.graphics_view.viewport().setCursor(Qt.ArrowCursor)
                self.graphics_view.viewport().update()
                QApplication.processEvents()
                self.update_lines()
                self.show_info_message("",
                                       "Ceiling and floor have been set.",
                                       legacy=True)
            else:  # particle adding
                x, y = scene_pos.x(), scene_pos.y()
                height = self.calculate_height(x, y)
                particle = {
                    'x': x,
                    'y': y,
                    'name': f'Particle {len(self.particles) + 1}',
                    'height': height,
                    'label_pos': QPointF(x + 10, y - 60)
                }
                self.particles.append(particle)
                self.draw_particles()
                self.show_info_message("Particle Added", f"Particle added at ({x:.2f}, {y:.2f})", legacy=True)

    def update_particle_name(self, label, new_name):
        for particle in self.particles:
            if particle.get('label_item') == label:
                particle['name'] = new_name
                break

    def update_lines(self):
        angle = self.angle_value
        if self.original_image and self.image_item:
            # Remove existing lines
            for item in [self.ceiling_line, self.floor_line, self.ceiling_ghost_line, self.floor_ghost_line]:
                if item and item in self.scene.items():
                    self.scene.removeItem(item)

            width = self.original_image.width()

            # Get the angle, defaulting to 0 if the input is empty
            try:
                angle = float(self.angle_input.text())
            except ValueError:
                angle = 0

            slope = math.tan(math.radians(angle))

            # Draw original lines
            if self.floor_y is not None:
                start_y = self.floor_y
                end_y = start_y + width * slope
                self.floor_line = self.scene.addLine(0, start_y, width, end_y, QPen(QColor(0, 255, 0), 2))

            if self.ceiling_y is not None:
                start_y = self.ceiling_y
                end_y = start_y + width * slope
                self.ceiling_line = self.scene.addLine(0, start_y, width, end_y, QPen(QColor(255, 0, 0), 2))

            # Draw ghost lines if wall thickness is applied
            if self.wall_thickness > 0 and self.capillary_height:
                total_pixels = abs(
                    self.ceiling_y - self.floor_y) if self.ceiling_y is not None and self.floor_y is not None else 0
                if total_pixels > 0:
                    wall_adjustment = (self.wall_thickness / self.capillary_height) * total_pixels

                    ghost_pen = QPen(QColor(255, 255, 255, 150), 1, Qt.DashLine)

                    if self.floor_y is not None:
                        start_y = self.floor_y - wall_adjustment  # Subtract for inward adjustment
                        end_y = start_y + width * slope
                        self.floor_ghost_line = self.scene.addLine(0, start_y, width, end_y, ghost_pen)

                    if self.ceiling_y is not None:
                        start_y = self.ceiling_y + wall_adjustment  # Add for inward adjustment
                        end_y = start_y + width * slope
                        self.ceiling_ghost_line = self.scene.addLine(0, start_y, width, end_y, ghost_pen)


    def set_height(self):
        if not self.check_image_loaded():
            return
        dialog = self.create_styled_input_dialog("Set Capillary Height", "(mm, um, pm):")
        if dialog.exec_() == QInputDialog.Accepted:
            height = dialog.textValue().replace(" ", "").lower()
            unit_start = 0
            for i, char in enumerate(height):
                if not (char.isdigit() or char == '.'):
                    unit_start = i
                    break

            if unit_start == 0:
                self.show_warning_message("Invalid Input", "Please enter a number followed by a unit (mm, um, or pm).")
                return

            try:
                value = float(height[:unit_start])
                unit = height[unit_start:]

                if unit == 'um':
                    self.capillary_height = value
                elif unit == 'mm':
                    self.capillary_height = value * 1000
                elif unit == 'pm':
                    self.capillary_height = value / 1000
                else:
                    self.show_warning_message("Invalid Unit", "Please use um, mm, or pm.")
                    return

                self.show_info_message("Height Set", f"Capillary height set to {self.capillary_height} µm")
                self.update_lines()  # Update lines after setting the height
            except ValueError:
                self.show_warning_message("Invalid Number", "Please enter a valid number followed by a unit.")

    def create_styled_input_dialog(self, title, label, text=""):
        dialog = QInputDialog(self)
        dialog.setWindowTitle(title)
        dialog.setLabelText(label)
        dialog.setTextValue(text)
        dialog.setStyleSheet("""
            QInputDialog {
                background-color: #2c3e50;
                color: white;
            }
            QInputDialog QLineEdit {
                background-color: #34495e;
                color: white;
                border: none;
                border-radius: 5px;
                padding: 5px;
            }
            QInputDialog QPushButton {
                background-color: #34495e;
                color: white;
                border: none;
                border-radius: 5px;
                padding: 5px;
                min-width: 70px;
            }
            QInputDialog QPushButton:hover {
                background-color: #3498db;
            }
        """)
        return dialog

    def create_small_button(self, text, icon_path=None):
        button = QPushButton(text)
        if icon_path:
            button.setIcon(QIcon(icon_path))
        button.setStyleSheet("""
            QPushButton {
                background-color: #34495e;
                color: white;
                border: 1px solid #2c3e50;
                border-radius: 5px;
                padding: 5px;
                font-size: 12px;
                max-width: 100px;
            }
            QPushButton:hover {
                background-color: #3498db;
            }
            QPushButton:pressed {
                background-color: #2980b9;
            }
        """)
        return button

    def calculate_height(self, x, y):
        if self.capillary_height is not None and self.ceiling_y is not None and self.floor_y is not None:
            try:
                angle = float(self.angle_input.text())
            except ValueError:
                angle = 0  # Default to 0 if the input is empty or invalid

            slope = math.tan(math.radians(angle))

            ceiling_y = self.ceiling_y + x * slope
            floor_y = self.floor_y + x * slope

            total_pixels = abs(ceiling_y - floor_y)

            if self.wall_thickness > 0:
                wall_adjustment = (self.wall_thickness / self.capillary_height) * total_pixels
                ceiling_y += wall_adjustment
                floor_y -= wall_adjustment

            adjusted_total_pixels = abs(ceiling_y - floor_y)
            pixels_from_bottom = abs(y - floor_y)
            return (pixels_from_bottom / adjusted_total_pixels) * self.capillary_height
        return 0


    def update_particles(self):
        if self.capillary_height is not None:
            updated_particles = []
            for x, y, name, _, label_pos in self.particles:
                height = self.calculate_height(y)
                updated_particles.append((x, y, name, height, label_pos))
            self.particles = updated_particles
            self.draw_particles()

    def draw_particles(self):
        if self.original_image and self.image_item:
            # Store existing label positions
            existing_positions = {particle['label_item']: particle['label_item'].pos() for particle in self.particles if
                                  'label_item' in particle}

            # Remove all existing particle items from the scene
            for particle in self.particles:
                if 'label_item' in particle:
                    self.scene.removeItem(particle['label_item'])
                if 'dot_item' in particle:
                    self.scene.removeItem(particle['dot_item'])
                if 'line_item' in particle:
                    self.scene.removeItem(particle['line_item'])

            for particle in self.particles:
                x, y = particle['x'], particle['y']

                # Recalculate height based on new angle
                particle['height'] = self.calculate_height(x, y)

                # Scale the particle dot size
                dot_size = 6 * self.scale_factor
                particle_dot = QGraphicsEllipseItem(x - dot_size / 2, y - dot_size / 2, dot_size, dot_size)
                particle_dot.setBrush(QColor(255, 0, 0))
                self.scene.addItem(particle_dot)

                label = DraggableLabel(x, y, particle['name'], particle['height'], self)

                # Restore the previous position if it exists, otherwise use the default
                if 'label_item' in particle and particle['label_item'] in existing_positions:
                    label.setPos(existing_positions[particle['label_item']])
                elif 'label_pos' in particle:
                    label.setPos(particle['label_pos'])
                else:
                    label.setPos(QPointF(x + 10, y - 60))

                label.signals.deleteRequested.connect(self.delete_particle)
                label.signals.moved.connect(self.update_connection_lines)
                self.scene.addItem(label)

                # Scale the line width
                line = QGraphicsLineItem()
                line.setPen(QPen(QColor(255, 255, 255), max(1, int(self.scale_factor)), Qt.DashLine))
                self.scene.addItem(line)

                particle['label_item'] = label
                particle['dot_item'] = particle_dot
                particle['line_item'] = line

            self.update_connection_lines()
            self.scene.update()


    def show_warning_message(self, title, message):
        self.show_toast(f"{title}: {message}", message_type="warning")

    def show_error_message(self, title, message):
        self.show_toast(f"{title}: {message}", message_type="error")

    def show_info_message(self, title, message, buttons=None, callback=None, timeout=5000, legacy=False):
        if legacy:
            if len(title) == 0:
                self.show_toast(message=message, message_type="info", timeout=timeout - 1000)
            else:
                self.show_toast(message=f"{title}: {message}", message_type="info", timeout=timeout - 1000)
        else:
            toast = ToastNotification(self, title, message, buttons, timeout=timeout)
            if buttons:
                for button_text, button in toast.buttons.items():
                    button.clicked.connect(
                        lambda checked, text=button_text: self.handle_toast_response(toast, text, callback))
            toast.show()

    def handle_toast_response(self, toast, response, callback):
        toast.fade_out()
        if callback:
            callback(response)

    def update_particle_data(self, label, new_data):
        for particle in self.particles:
            if 'label_item' in particle and particle['label_item'] == label:
                particle.update(new_data)
                if 'name' in new_data:
                    self.add_used_name(new_data['name'])
                break
            elif 'x' in particle and 'y' in particle:
                # If label_item is not present, compare positions
                if abs(particle['x'] - label.x) < 1 and abs(particle['y'] - label.y) < 1:
                    particle.update(new_data)
                    if 'name' in new_data:
                        self.add_used_name(new_data['name'])
                    break

        # Redraw particles to update visual representation
        self.draw_particles()


    def delete_particle(self, label):
        for i, particle in enumerate(self.particles):
            if particle['label_item'] == label:
                self.scene.removeItem(particle['label_item'])
                self.scene.removeItem(particle['dot_item'])
                self.scene.removeItem(particle['line_item'])
                del self.particles[i]
                break

        self.scene.update()

    def update_connection_lines(self):
        for particle in self.particles:
            if 'label_item' in particle and 'line_item' in particle:
                label = particle['label_item']
                line = particle['line_item']
                start = QPointF(particle['x'], particle['y'])
                end = label.sceneBoundingRect().center()
                line.setLine(QLineF(start, end))



    def add_used_name(self, name):
        self.used_names.add(name)

    def export_csv(self):
        if not self.check_image_loaded():
            self.show_toast("Nothing to export", message_type="warning", timeout=3000)
            return
        if not self.particles:
            self.show_warning_message("Export Error", "No particles to export.")
            return

        file_name, _ = QFileDialog.getSaveFileName(self, "Save CSV", "", "CSV Files (*.csv)")
        if file_name:
            try:
                with open(file_name, 'w', newline='') as csvfile:
                    writer = csv.writer(csvfile)
                    writer.writerow(['Name', 'X', 'Y', 'Height (µm)'])
                    for particle in self.particles:
                        writer.writerow([
                            particle['name'],
                            particle['x'],
                            particle['y'],
                            f"{particle['height']:.2f}"
                        ])
                self.show_info_message("Export Successful", f"Data exported to {file_name}")
            except Exception as e:
                self.show_error_message("Export Error", f"Error exporting data: {str(e)}")

    def check_for_updates(self):
        try:
            owner = "simitbey"
            repo = "PHASe"
            url = f"https://api.github.com/repos/{owner}/{repo}/releases/latest"

            response = requests.get(url)
            response.raise_for_status()

            latest_release = json.loads(response.text)
            latest_version = latest_release['tag_name'].lstrip('v')

            if version.parse(latest_version) > version.parse(CURRENT_VERSION):
                message = f"A new version ({latest_version}) is available!\n"
                message += f"You are currently using version {CURRENT_VERSION}.\n"
                message += "Do you want to download and install the update?"

                update_box = QMessageBox(self)
                update_box.setStyleSheet(self.message_box_style)
                update_box.setIcon(QMessageBox.Question)
                update_box.setWindowTitle("Update Available")
                update_box.setText(message)
                update_box.setStandardButtons(QMessageBox.Yes | QMessageBox.No)

                result = update_box.exec_()
                if result == QMessageBox.Yes:
                    self.download_and_install_update(latest_release)
            else:
                pass
        except Exception as e:
            self.show_error_message("Update Check Failed", f"Check your connection and retry.")
            print(f"error message shown from function check_for_updates with exception: {e}")

    def check_image_loaded(self):
        if not self.image_loaded:
            self.show_toast("Please load an image first", message_type="error", timeout=3000)
            return False
        return True


    def download_and_install_update(self, release):
        try:
            # Find the .app asset
            app_asset = next((asset for asset in release['assets'] if asset['name'].endswith('_osx64app.zip')), None)
            if not app_asset:
                raise Exception("No .app download found in the release")

            # Download the update
            with tempfile.NamedTemporaryFile(delete=False, suffix='.zip') as tmp_file:
                self.show_info_message("Downloading Update", "The update is being downloaded. Please wait...")
                urlretrieve(app_asset['browser_download_url'], tmp_file.name)

            update_dir = tempfile.mkdtemp()
            subprocess.run(['unzip', '-q', tmp_file.name, '-d', update_dir])

            app_path = next((os.path.join(root, name)
                             for root, dirs, files in os.walk(update_dir)
                             for name in dirs if name.endswith('.app')), None)
            if not app_path:
                raise Exception("Could not find .app in the downloaded update")

            current_app_path = os.path.abspath(sys.executable)
            current_app_dir = os.path.dirname(os.path.dirname(current_app_path))
            new_app_path = os.path.join(os.path.dirname(current_app_dir), os.path.basename(app_path))

            updater_script = f"""
            #!/bin/bash
            sleep 2
            rm -rf "{current_app_dir}"
            mv "{app_path}" "{new_app_path}"
            open "{new_app_path}"
            """

            with tempfile.NamedTemporaryFile('w', delete=False, suffix='.sh') as script_file:
                script_file.write(updater_script)
                updater_path = script_file.name
            os.chmod(updater_path, 0o755)

            self.show_info_message("Update Ready",
                                   "The update has been downloaded and is ready to install. The application will now close and update.")
            subprocess.Popen(['/bin/bash', updater_path])
            QApplication.quit()

        except Exception as e:
            self.show_error_message("Update Failed", f"Failed to download and prepare the update.")
            print(f"error message shown from function download_and_install_update with exception: {e}")


def exception_hook(exctype, value, tb):
    print(''.join(traceback.format_exception(exctype, value, tb)))
    sys.exit(1)


if __name__ == "__main__":
    try:
        app_logger.info("Application starting...")
        app = QApplication(sys.argv)

        if platform.system() == 'Darwin':
            app.setAttribute(Qt.AA_DontUseNativeMenuBar, False)

        app_logger.info("Creating main window...")
        window = CapillaryAnalyzer()
        app_logger.info("Showing main window...")
        window.show()
        app_logger.info("Entering main event loop...")
        sys.exit(app.exec_())
    except Exception as e:
        app_logger.exception("An unexpected error occurred:")
        sys.exit(1)
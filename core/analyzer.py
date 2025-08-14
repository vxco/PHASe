"""
Main application controller for PHASe
"""
import base64
import csv
import math
import os
import json
import pickle
import platform
import subprocess
import sys
import traceback
from packaging import version

import requests
from PyQt5.QtCore import Qt, QTimer, QBuffer, QByteArray, QPointF, QLineF, QPoint
from PyQt5.QtGui import QPixmap, QIcon, QColor, QPen, QPainter, QImage, QCursor, QPalette
from PyQt5.QtWidgets import (QMainWindow, QLabel, QPushButton, QVBoxLayout,
                             QHBoxLayout, QWidget, QFrame, QGridLayout, QLineEdit,
                             QButtonGroup, QRadioButton, QCheckBox, QGraphicsView, QAction, QDialog, QComboBox,
                             QMessageBox, QGroupBox, QSlider, QGraphicsDropShadowEffect, QFileDialog, QApplication,
                             QInputDialog, QGraphicsEllipseItem, QGraphicsLineItem)

from config.constants import *
from core.models import WorkspaceManager
from ui.widgets import ModernButton, CoolModeSwitch, ScrollWheel
from ui.dialogs import AboutDialog, TourGuide, ToastNotification
from ui.graphics import CustomGraphicsView, CustomGraphicsScene, DraggableLabel
from utils.helpers import absolute_path, get_app_data_dir, create_custom_cursor
from utils.logging_utils import app_logger

cursorCustom = False


class CapillaryAnalyzer(QMainWindow):
    def __init__(self):
        self.cursorCustom = cursorCustom
        super().__init__()
        self.current_set_mode = None
        self.initial_setup_complete = False
        self.logger = app_logger
        self.image_loaded = False
        self.setWindowTitle("PHASe")
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

        self.current_label_size = 100  # Default label size (100%)

        app_name = "PHASe"
        app_author = "Alfa Ozaltin @ VX Software"
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

        control_panel.setFixedWidth(300)

        self.angle_control = None

        # Logo space
        logo_label = QLabel()
        logo_pixmap = QPixmap(absolute_path("assets/phase_logo_v3.svg"))
        logo_label.setPixmap(logo_pixmap.scaled(120, 60, Qt.KeepAspectRatio, Qt.SmoothTransformation))
        logo_label.setAlignment(Qt.AlignCenter)
        control_layout.addWidget(logo_label)

        self.workspace_name_input = QLineEdit("Untitled Workspace")
        self.workspace_name_input.setReadOnly(True)
        self.workspace_name_input.setStyleSheet("""
                    QLineEdit {
                        background-color: transparent;
                        border: none;
                        color: white;
                        font-size: 18px;
                        font-weight: bold;
                    }
                    QLineEdit:focus {
                        background-color: #34495e;
                        border: 1px solid #3498db;
                    }
                """)
        self.workspace_name_input.mousePressEvent = self.edit_workspace_name

        # Add the workspace name input to the layout
        control_layout.insertWidget(1, self.workspace_name_input)

        self.workspace_name_input.editingFinished.connect(self.finish_editing_workspace_name)

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

        ceiling_floor_right = QVBoxLayout()
        ceiling_increment_layout = QHBoxLayout()
        self.ceiling_up_button = self.create_small_button("▲")
        self.ceiling_up_button.clicked.connect(lambda: self.increment_ceiling(-1))
        self.ceiling_down_button = self.create_small_button("▼")
        self.ceiling_down_button.clicked.connect(lambda: self.increment_ceiling(1))
        ceiling_increment_layout.addWidget(self.ceiling_up_button)
        ceiling_increment_layout.addWidget(self.ceiling_down_button)
        ceiling_floor_right.addLayout(ceiling_increment_layout)

        floor_increment_layout = QHBoxLayout()
        self.floor_up_button = self.create_small_button("▲")
        self.floor_up_button.clicked.connect(lambda: self.increment_floor(-1))
        self.floor_down_button = self.create_small_button("▼")
        self.floor_down_button.clicked.connect(lambda: self.increment_floor(1))
        floor_increment_layout.addWidget(self.floor_up_button)
        floor_increment_layout.addWidget(self.floor_down_button)
        ceiling_floor_right.addLayout(floor_increment_layout)

        ceiling_floor_layout.addLayout(ceiling_floor_right)

        control_layout.addLayout(ceiling_floor_layout)

        # Height and Wall Thickness Layout
        height_wall_layout = QGridLayout()

        self.unsaved_changes = False
        self.current_workspace_file = None
        self.recent_files = []
        self.max_recent_files = 5

        self.load_recent_files()
        self.create_menu_bar()

        # Height input mode selection
        self.height_mode_group = QButtonGroup(self)
        self.magnet_distance_radio = QRadioButton("Magnet Distance")
        self.capillary_height_radio = QRadioButton("Capillary Height")
        self.height_mode_group.addButton(self.magnet_distance_radio)
        self.height_mode_group.addButton(self.capillary_height_radio)
        self.capillary_height_radio.setChecked(True)  # Default to capillary height

        # Connect radio buttons to update function
        self.magnet_distance_radio.toggled.connect(self.update_height_mode)
        self.capillary_height_radio.toggled.connect(self.update_height_mode)

        # Add radio buttons to layout
        height_mode_layout = QHBoxLayout()
        height_mode_layout.addWidget(self.magnet_distance_radio)
        height_mode_layout.addWidget(self.capillary_height_radio)
        control_layout.addLayout(height_mode_layout)

        # Height Input
        height_label = QLabel("Height Input:")
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
        self.wall_thickness_input.setPlaceholderText("µm")
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

        # Create mode switch
        self.mode_switch = CoolModeSwitch()
        self.mode_switch.toggled.connect(self.toggle_mode)

        # Add mode switch to control panel
        control_layout.addWidget(self.mode_switch, alignment=Qt.AlignCenter)

        self.current_mode = "particle"  # Default mode

        control_layout.addStretch()

        self.graphics_view = CustomGraphicsView()

        # Image area
        self.graphics_view.setStyleSheet("""
            QGraphicsView {
                background-color: #2c3e50;
                border: none;
                border-radius: 15px;
            }
        """)
        self.scene = CustomGraphicsScene(self)


        self.graphics_view.setInteractive(True)
        self.graphics_view.setMouseTracking(True)

        self.graphics_view.setScene(self.scene)
        self.graphics_view.setRenderHint(QPainter.Antialiasing)
        self.graphics_view.setTransformationAnchor(QGraphicsView.AnchorUnderMouse)
        self.graphics_view.setResizeAnchor(QGraphicsView.AnchorUnderMouse)

        right_layout = QVBoxLayout()
        right_layout.addWidget(self.graphics_view)

        slider_layout = QHBoxLayout()
        slider_layout.addStretch(1)
        self.label_size_slider = self.create_label_size_slider()
        slider_layout.addWidget(QLabel("Label Size:"))
        slider_layout.addWidget(self.label_size_slider)

        right_layout.addLayout(slider_layout)

        main_layout.addWidget(control_panel)
        main_layout.addWidget(self.graphics_view, 1)

        self.setup_file_associations()

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

        self.zoom_factor = 1.0
        self.zoom_indicator = QLabel(self)
        self.zoom_indicator.setStyleSheet("""
                    QLabel {
                        background-color: rgba(52, 73, 94, 180);
                        color: white;
                        border-radius: 10px;
                        padding: 5px;
                    }
                """)
        self.zoom_indicator.hide()

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

        QTimer.singleShot(1000, self.check_for_updates) if AUTO_UPDATE_ENABLED else None

    def toggle_mode(self, is_particle_mode):
        if is_particle_mode:
            self.current_mode = "particle"
            self.graphics_view.setDragMode(QGraphicsView.NoDrag)
            self.graphics_view.setCursor(Qt.ArrowCursor)
            self.graphics_view.setPanningEnabled(False)  # Disable panning
            print("cursor set to arrow in toggle mode under capillary analyzer")
            self.show_toast("Switched to Particle Mode", message_type="info")
        else:
            self.current_mode = "pan"
            self.graphics_view.setDragMode(QGraphicsView.ScrollHandDrag)
            self.graphics_view.setCursor(Qt.OpenHandCursor)
            self.graphics_view.setPanningEnabled(True)  # Enable panning
            self.show_toast("Switched to Pan Mode", message_type="info")

    def update_height_mode(self):
        if self.magnet_distance_radio.isChecked():
            self.height_input.setPlaceholderText("Magnet Distance (mm, µm, pm)")
        else:
            self.height_input.setPlaceholderText("Capillary Height (mm, µm, pm)")
        self.process_height_input()

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
                value = number
            elif unit == 'mm':
                value = number * 1000
            elif unit == 'pm':
                value = number / 1000
            else:
                raise ValueError("Invalid unit")

            if self.magnet_distance_radio.isChecked():
                # Subtract wall thickness if it's enabled
                if self.wall_thickness_checkbox.isChecked():
                    self.capillary_height = value - (2 * self.wall_thickness)
                else:
                    self.capillary_height = value
            else:
                self.capillary_height = value

            self.height_input.setText(f"{self.capillary_height:.2f} µm")
            self.height_input_valid = True
            self.update_lines()
            self.update_particle_heights()

            if self.magnet_distance_radio.isChecked():
                if self.wall_thickness_checkbox.isChecked():
                    self.show_warning_message("Wall Thickness Subtracted", f"Capillary height set to {self.capillary_height:.2f} µm")
                else:
                    self.show_info_message("Height Set", f"Capillary height set to {self.capillary_height:.2f} µm",
                                           legacy=True)
            else:
                self.show_info_message("Height Set", f"Capillary height set to {self.capillary_height:.2f} µm",
                                       legacy=True)



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

        if BETA_FEATURES_ENABLED:
            save_workspace_action = QAction('Save Workspace', self)
            save_workspace_action.setShortcut('Ctrl+S')
            save_workspace_action.triggered.connect(self.save_workspace)
            file_menu.addAction(save_workspace_action)

            save_workspace_as_action = QAction('Save Workspace As...', self)
            save_workspace_as_action.setShortcut('Ctrl+Shift+S')
            save_workspace_as_action.triggered.connect(self.save_workspace_as)
            file_menu.addAction(save_workspace_as_action)

            load_workspace_action = QAction('Load Workspace', self)
            load_workspace_action.triggered.connect(self.load_workspace)
            file_menu.addAction(load_workspace_action)

            file_menu.addSeparator()

            self.recent_files_menu = file_menu.addMenu('Recent Files')
            self.update_recent_files_menu()

            file_menu.addSeparator()

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

        # Add Height Reference action
        height_reference_action = QAction('Height Reference', self)
        height_reference_action.triggered.connect(self.show_height_reference)
        help_menu.addAction(height_reference_action)

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

    def show_height_reference(self):
        try:
            url = "https://raw.githubusercontent.com/vxco/PHASe/refs/heads/master/height_reference.json"
            response = requests.get(url)
            response.raise_for_status()
            reference_data = json.loads(response.text)

            dialog = QDialog(self)
            dialog.setWindowTitle("Height Reference")
            dialog.setFixedSize(350, 300)
            dialog.setWindowFlags(dialog.windowFlags() | Qt.WindowStaysOnTopHint)
            layout = QVBoxLayout(dialog)

            # Device type selection
            device_label = QLabel("Device Type:")
            layout.addWidget(device_label)
            device_type_combo = QComboBox()
            device_type_combo.addItems(reference_data.keys())
            layout.addWidget(device_type_combo)

            # Version selection
            version_label = QLabel("Version:")
            layout.addWidget(version_label)
            version_combo = QComboBox()
            layout.addWidget(version_combo)

            # Reference information display
            info_group = QGroupBox("Reference Information")
            info_layout = QGridLayout()
            wall_thickness_label = QLabel("Wall Thickness:")
            wall_thickness_value = QLabel()
            magnet_distance_label = QLabel("Magnet Distance:")
            magnet_distance_value = QLabel()
            inner_width_label = QLabel("Inner Width:")
            inner_width_value = QLabel()

            info_layout.addWidget(wall_thickness_label, 0, 0)
            info_layout.addWidget(wall_thickness_value, 0, 1)
            info_layout.addWidget(magnet_distance_label, 1, 0)
            info_layout.addWidget(magnet_distance_value, 1, 1)
            info_layout.addWidget(inner_width_label, 2, 0)
            info_layout.addWidget(inner_width_value, 2, 1)

            info_group.setLayout(info_layout)
            layout.addWidget(info_group)

            def update_versions():
                device = device_type_combo.currentText()
                version_combo.clear()
                version_combo.addItems(reference_data[device].keys())
                update_info()

            def update_info():
                device = device_type_combo.currentText()
                version = version_combo.currentText()
                if device in reference_data and version in reference_data[device]:
                    data = reference_data[device][version]
                    wall_thickness_value.setText(f"{data.get('wall_thickness', 'N/A')} µm")
                    magnet_distance_value.setText(f"{data.get('magnet_distance', 'N/A')} mm")
                    inner_width_value.setText(f"{data.get('inner_width', 'N/A')} µm")
                else:
                    wall_thickness_value.setText("N/A")
                    magnet_distance_value.setText("N/A")
                    inner_width_value.setText("N/A")

            device_type_combo.currentTextChanged.connect(update_versions)
            version_combo.currentTextChanged.connect(update_info)

            update_versions()

            dialog.setStyleSheet("""
                QDialog {
                    background-color: #2c3e50;
                    color: white;
                }
                QGroupBox {
                    border: 2px solid #3498db;
                    border-radius: 5px;
                    margin-top: 10px;
                    font-weight: bold;
                }
                QGroupBox::title {
                    subcontrol-origin: margin;
                    left: 10px;
                    padding: 0 3px 0 3px;
                }
                QComboBox {
                    background-color: #34495e;
                    color: white;
                    border: 1px solid #3498db;
                    border-radius: 3px;
                    padding: 5px;
                    min-width: 6em;
                }
                QComboBox::drop-down {
                    subcontrol-origin: padding;
                    subcontrol-position: top right;
                    width: 15px;
                    border-left-width: 1px;
                    border-left-color: #3498db;
                    border-left-style: solid;
                    border-top-right-radius: 3px;
                    border-bottom-right-radius: 3px;
                }
                QLabel {
                    color: white;
                    font-size: 12px;
                }
                QLabel[objectName^="value"] {
                    font-weight: bold;
                    color: #3498db;
                }
            """)

            # Set object names for styling
            wall_thickness_value.setObjectName("value_wall_thickness")
            magnet_distance_value.setObjectName("value_magnet_distance")
            inner_width_value.setObjectName("value_inner_width")

            dialog.show()

        except Exception as e:
            self.show_error_message("Error", f"Failed to load height reference data: {str(e)}")

    def update_recent_files_menu(self):
        self.recent_files_menu.clear()
        for file in self.recent_files:
            action = QAction(file, self)
            action.triggered.connect(lambda checked, f=file: self.load_workspace(f))
            self.recent_files_menu.addAction(action)

    def load_recent_files(self):
        try:
            with open(os.path.join(self.config_dir, 'recent_files.txt'), 'r') as f:
                self.recent_files = [line.strip() for line in f.readlines()]
        except FileNotFoundError:
            self.recent_files = []

    def save_recent_files(self):
        with open(os.path.join(self.config_dir, 'recent_files.txt'), 'w') as f:
            for file in self.recent_files:
                f.write(f"{file}\n")

    def add_recent_file(self, file_path):
        if file_path in self.recent_files:
            self.recent_files.remove(file_path)
        self.recent_files.insert(0, file_path)
        self.recent_files = self.recent_files[:self.max_recent_files]
        self.save_recent_files()
        self.update_recent_files_menu()

    def set_unsaved_changes(self, value=True):
        self.unsaved_changes = value
        self.update_window_title()

    def show_about_dialog(self):
        dialog = AboutDialog(self)
        dialog.resize(self.size())
        dialog.show()

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
            ("Load Image", "Click this button to load an image of the capillary.", self.load_button),
            ("Workspace Name", "You can click here to edit the workspace name. press enter to apply.",
             self.workspace_name_input),
            ("Set Ceiling", "Click this button and then click on the image to set the ceiling of the capillary.",
             self.set_ceiling_button),
            ("Set Floor", "Click this button and then click on the image to set the Floor of the capillary.",
             self.set_floor_button),
            ("Set Height", "Enter the capillary height in this input field. You can use mm, µm, or pm units.",
             self.height_input),
            ("Select Height Input Type","Select magnet height or capillary height to allow correct wall thickness calculations", self.capillary_height_radio),
            ("Adjust Angle", "Use these scroll wheels or enter a value directly to adjust the angle of the capillary.",
             self.angle_input),
            ("Add Particles", "Click on the image to add particles. You can drag the labels to reposition them.",
             self.graphics_view),
            ("Export Data", "When you're done, click this button to save your data as a CSV file.", self.export_button),
            ("Reset and Clear", "Use these buttons to reset the angle or clear all particle selections.",
             self.clear_selections_button),
            (
            "Modes", "Select between Handle and Analyze modes to either use clicking for panning or setting particles.",
            self.mode_switch),
            ("Minimap", "You can see the minimap to see your viewpoint, and drag the viewpoint to change it.",
             self.graphics_view.minimap),
            ("Height Reference", "Height reference for common device dimensions.",
             "Help/Height Reference"),
            ("Save Workspace",
             "Save your workspace for sharing it with other users or picking up from where you leave off!",
             "File/Save Workspace") if BETA_FEATURES_ENABLED else None,
            ("Load Workspace", "Load saved .phw files to replace the current workspace with the saved one.",
             "File/Load Workspace") if BETA_FEATURES_ENABLED else None,
            ("That's it!", "You're all set! Remember, you can always access this guide again in the help Menu",
             "Help/Interactive Guide"),

        ]
        self.current_tour_step = 0
        self.next_tour_step()

    def closeEvent(self, event):
        if self.unsaved_changes:
            reply = QMessageBox.question(self, f'Unsaved Changes to ',
                                         "You have unsaved changes. Do you want to save before closing? All Unsaved changes will be destroyed!",
                                         QMessageBox.Save | QMessageBox.Discard | QMessageBox.Cancel,
                                         QMessageBox.Save)
            if reply == QMessageBox.Save:
                self.save_workspace()
                self.show_info_message("", "Saved Workspace. Closing!", legacy=True)
                event.accept()
            elif reply == QMessageBox.Discard:
                event.accept()
            else:
                event.ignore()
        else:
            event.accept()

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
                                   timeout=3000)

    def next_tour_step(self):
        while self.current_tour_step < len(self.tour_steps):
            step = self.tour_steps[self.current_tour_step]

            if step is None:
                self.current_tour_step += 1
                continue

            title, message, target = step

            if isinstance(target, str) and '/' in target:
                menu_name, item_name = target.split('/')
                self.show_menu_item(menu_name, item_name, title, message)
            else:
                self.tour_guide.show_message(f"<b>{title}</b><br><br>{message}", target)
                if target:
                    self.highlight_widget(target)

            self.current_tour_step += 1
            return

        self.tour_guide.hide()
        self.config['tour_completed'] = True
        self.save_config()

    def show_menu_item(self, menu_name, item_name, title, message):
        menu = next((action.menu() for action in self.menuBar().actions() if action.text() == menu_name), None)
        if menu:
            # Find the menu action
            menu_action = next(action for action in self.menuBar().actions() if action.text() == menu_name)
            menu_rect = self.menuBar().actionGeometry(menu_action)
            global_pos = self.menuBar().mapToGlobal(menu_rect.topLeft())

            x_offset = 20  # Positive to right
            y_offset = menu_rect.height() + 5
            guide_pos = global_pos + QPoint(x_offset, y_offset)

            self.tour_guide.show_message(f"<b>{title}</b><br><br>{message}", None,
                                         custom_pos=self.mapFromGlobal(guide_pos))

            QTimer.singleShot(500, lambda: self.open_and_highlight_menu(menu, item_name))

        # Prevent the tour from continuing automatically
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

    def create_label_size_slider(self):
        slider = QSlider(Qt.Horizontal)
        slider.setMinimum(10)
        slider.setMaximum(600)
        slider.setValue(100)
        slider.setTickPosition(QSlider.TicksBelow)
        slider.setTickInterval(25)
        slider.setStyleSheet("""
            QSlider::groove:horizontal {
                border: 1px solid #999999;
                height: 8px;
                background: qlineargradient(x1:0, y1:0, x2:0, y2:1, stop:0 #B1B1B1, stop:1 #c4c4c4);
                margin: 2px 0;
            }
            QSlider::handle:horizontal {
                background: qlineargradient(x1:0, y1:0, x2:1, y2:1, stop:0 #b4b4b4, stop:1 #8f8f8f);
                border: 1px solid #5c5c5c;
                width: 18px;
                margin: -2px 0;
                border-radius: 3px;
            }
        """)
        slider.valueChanged.connect(self.update_label_size)
        return slider

    def update_label_size(self, value):
        self.current_label_size = value
        scale = value / 100.0
        for particle in self.particles:
            if 'label_item' in particle:
                particle['label_item'].setScale(scale)
        self.update_connection_lines()
        self.scene.update()
        self.set_unsaved_changes()

    def edit_workspace_name(self, event):
        self.workspace_name_input.setReadOnly(False)
        self.workspace_name_input.setFocus()
        self.workspace_name_input.selectAll()
        self.set_unsaved_changes()

    def save_workspace(self):
        if self.current_workspace_file:
            self.perform_save(self.current_workspace_file)
        else:
            self.save_workspace_as()

    def save_workspace_as(self):
        file_name, _ = QFileDialog.getSaveFileName(self, "Save Workspace As", "", "PHASe Workspace Files (*.phw)")
        if file_name:
            self.perform_save(file_name)
            self.current_workspace_file = file_name
            self.add_recent_file(file_name)

    def perform_save(self, file_name):
        try:
            workspace_data = {
                'name': self.workspace_name_input.text(),
                'capillary_height': self.capillary_height,
                'ceiling_y': self.ceiling_y,
                'floor_y': self.floor_y,
                'angle_value': self.angle_value,
                'wall_thickness': self.wall_thickness,
                'particles': [
                    {
                        'x': p['x'],
                        'y': p['y'],
                        'name': p['name'],
                        'height': p['height'],
                        'label_pos': p['label_item'].pos() if 'label_item' in p else None
                    }
                    for p in self.particles
                ],
                'used_names': list(self.used_names)
            }

            if self.original_image:
                buffer = QBuffer()
                buffer.open(QBuffer.ReadWrite)
                self.original_image.save(buffer, "PNG")
                workspace_data['image'] = base64.b64encode(buffer.data()).decode()

            with open(file_name, 'wb') as f:
                pickle.dump(workspace_data, f, protocol=pickle.HIGHEST_PROTOCOL)

            self.show_info_message("Workspace Saved", f"Workspace saved to {file_name}", legacy=True)
            self.unsaved_changes = False
            self.update_window_title()

        except Exception as e:
            self.show_error_message("Save Error", f"Error saving workspace: {str(e)}")
            print(f"Full error: {traceback.format_exc()}")

    def finish_editing_workspace_name(self):
        self.workspace_name_input.setReadOnly(True)
        self.update_window_title()

    def load_workspace(self, file_name=None):
        if self.unsaved_changes:
            self.show_info_message(
                "Unsaved Changes",
                "You have unsaved changes. Would you like to save before loading a new workspace?",
                buttons=["Save", "Don't Save", "Cancel"],
                callback=lambda response: self.handle_unsaved_changes_before_load(response, file_name)
            )
        else:
            self.proceed_with_load(file_name)

    def handle_unsaved_changes_before_load(self, response, file_name):
        if response == "Save":
            self.save_workspace()
            self.proceed_with_load(file_name)
        elif response == "Don't Save":
            self.proceed_with_load(file_name)
        # If "Cancel", do nothing

    def proceed_with_load(self, file_name):
        if not file_name:
            file_name, _ = QFileDialog.getOpenFileName(self, "Load Workspace", "", "PHASe Workspace Files (*.phw)")
        if file_name:
            try:
                with open(file_name, 'rb') as f:
                    workspace_data = pickle.load(f)

                self.workspace_name_input.setText(workspace_data.get('name', 'Untitled Workspace'))
                self.update_window_title()
                self.capillary_height = workspace_data.get('capillary_height')
                self.ceiling_y = workspace_data.get('ceiling_y')
                self.floor_y = workspace_data.get('floor_y')
                self.angle_value = workspace_data.get('angle_value', 0)
                self.wall_thickness = workspace_data.get('wall_thickness', 0)
                self.used_names = set(workspace_data.get('used_names', []))

                if 'image' in workspace_data:
                    image_data = base64.b64decode(workspace_data['image'])
                    self.original_image = QImage.fromData(QByteArray(image_data))
                    self.scene.clear()
                    pixmap = QPixmap.fromImage(self.original_image)
                    self.image_item = self.scene.addPixmap(pixmap)
                    self.scene.setSceneRect(self.image_item.boundingRect())
                    self.graphics_view.fitInView(self.scene.sceneRect(), Qt.KeepAspectRatio)

                    # Recalculate scale factor
                    base_width = 1000  # This should be the same value used in load_image
                    self.scale_factor = self.original_image.width() / base_width

                # Reconstruct particles
                self.particles = workspace_data.get('particles', [])

                # Update UI elements
                self.update_ui_from_workspace()

                # Redraw particles
                self.draw_particles()

                self.current_workspace_file = file_name
                self.add_recent_file(file_name)
                self.unsaved_changes = False
                self.update_window_title()
                self.show_info_message("Workspace Loaded", f"Workspace loaded from {file_name}", legacy=True)
                self.image_loaded = True

            except Exception as e:
                self.show_error_message("Load Error", f"Error loading workspace: {str(e)}")
                print(f"Full error: {traceback.format_exc()}")


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

    def set_wall_thickness(self):
        if not self.check_image_loaded():
            return
        dialog = self.create_styled_input_dialog("Set Wall Thickness", "(mm, um, pm):")
        if dialog.exec_() == QInputDialog.Accepted:
            thickness = dialog.textValue().replace(" ", "").lower()
            unit_start = 0
            for i, char in enumerate(thickness):
                if not (char.isdigit() or char == '.'):
                    unit_start = i
                    break

            if unit_start == 0:
                self.show_warning_message("Invalid Input", "Please enter a number followed by a unit (mm, um, or pm).")
                return

            try:
                value = float(thickness[:unit_start])
                unit = thickness[unit_start:]

                if unit == 'um':
                    self.wall_thickness = value
                elif unit == 'mm':
                    self.wall_thickness = value * 1000
                elif unit == 'pm':
                    self.wall_thickness = value / 1000
                else:
                    self.show_warning_message("Invalid Unit", "Please use um, mm, or pm.")
                    return

                self.wall_thickness_input.setText(f"{self.wall_thickness:.2f}")
                self.show_info_message("Wall Thickness Set", f"Wall thickness set to {self.wall_thickness} µm")
                self.update_lines()  # Update lines after setting the wall thickness
            except ValueError:
                self.show_warning_message("Invalid Number", "Please enter a valid number followed by a unit.")

    def setup_file_associations(self):
        if sys.platform == 'darwin':  # macOS
            self.setup_macos_file_association()
        elif sys.platform == 'win32':  # Windows
            self.setup_windows_file_association()

    def setup_macos_file_association(self):
        icns_path = absolute_path("assets/phw_icon.icns")

        # Path to your application
        app_path = sys.executable

        # Use UTI for file type
        uti = "com.vxsoftware.phase.phw"

        # Create a plist file for the UTI
        plist_content = f"""
        <?xml version="1.0" encoding="UTF-8"?>
        <!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
        <plist version="1.0">
        <dict>
            <key>CFBundleDocumentTypes</key>
            <array>
                <dict>
                    <key>CFBundleTypeExtensions</key>
                    <array>
                        <string>phw</string>
                    </array>
                    <key>CFBundleTypeIconFile</key>
                    <string>{icns_path}</string>
                    <key>CFBundleTypeName</key>
                    <string>PHASe Workspace</string>
                    <key>CFBundleTypeRole</key>
                    <string>Editor</string>
                    <key>LSHandlerRank</key>
                    <string>Owner</string>
                </dict>
            </array>
            <key>UTExportedTypeDeclarations</key>
            <array>
                <dict>
                    <key>UTTypeConformsTo</key>
                    <array>
                        <string>public.data</string>
                    </array>
                    <key>UTTypeDescription</key>
                    <string>PHASe Workspace</string>
                    <key>UTTypeIconFile</key>
                    <string>{icns_path}</string>
                    <key>UTTypeIdentifier</key>
                    <string>{uti}</string>
                    <key>UTTypeTagSpecification</key>
                    <dict>
                        <key>public.filename-extension</key>
                        <array>
                            <string>phw</string>
                        </array>
                    </dict>
                </dict>
            </array>
        </dict>
        </plist>
        """

        plist_path = os.path.join(os.path.dirname(app_path), "Info.plist")
        with open(plist_path, "w") as f:
            f.write(plist_content)

        # Update the system's Launch Services database
        subprocess.run(
            ["/System/Library/Frameworks/CoreServices.framework/Frameworks/LaunchServices.framework/Support/lsregister",
             "-f", app_path])

    def setup_windows_file_association(self):
        print("placeholder")

    def reset_angle(self):
        self.angle_value = 0
        self.coarse_wheel.setValue(0)
        self.fine_wheel.setValue(0)
        self.angle_input.setText("0.00")
        self.update_lines()
        self.set_unsaved_changes()

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
        self.set_unsaved_changes()

    def update_window_title(self):
        title = f"PHASe - {self.workspace_name_input.text()}"
        if self.unsaved_changes:
            title += " *"
        self.setWindowTitle(title)
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
        self.update_particle_heights()

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
        self.update_particle_heights()

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
        self.update_particle_heights()
        self.draw_particles()
        self.set_unsaved_changes()

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
                self.update_particle_heights()
            else:
                self.show_toast("Invalid Angle: Please enter an angle between -90 and 90 degrees.",
                                message_type="warning")
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

                # Set the image for the minimap
                self.graphics_view.set_image(pixmap)

                # Calculate scale factor based on image size
                base_width = 1000  # You can adjust this value
                self.scale_factor = self.original_image.width() / base_width

                self.particles = []
                self.ceiling_y = None
                self.floor_y = None
                self.initial_setup_complete = False

                print(f"Image loaded successfully: {file_name}")
                self.image_loaded = True
                print(f"Image size: {self.original_image.width()}x{self.original_image.height()}")
                print(f"Scale factor: {self.scale_factor}")

                self.graphics_view.update_minimap()

                self.set_ceiling_mode()

        except Exception as e:
            error_message = f"Error loading image: {str(e)}"
            print(error_message)
            QMessageBox.critical(self, "Error", error_message)

    def resizeEvent(self, event):
        super().resizeEvent(event)
        if self.image_item:
            self.graphics_view.fitInView(self.scene.sceneRect(), Qt.KeepAspectRatio)
        self.graphics_view.position_widgets()
        self.graphics_view.update_minimap()

    def update_zoom_indicator_position(self):
        self.zoom_indicator.move(self.graphics_view.width() - self.zoom_indicator.width() - 10,
                                 self.graphics_view.height() - self.zoom_indicator.height() - 10)

    def wheelEvent(self, event):
        if self.image_item:
            # Zoom factor
            zoom_in_factor = 1.03
            zoom_out_factor = 1 / zoom_in_factor

            # Set anchor point
            self.graphics_view.setTransformationAnchor(QGraphicsView.AnchorUnderMouse)

            # Save the scene pos
            old_pos = self.graphics_view.mapToScene(event.pos())

            # Zoom
            if event.angleDelta().y() > 0:
                zoom_factor = zoom_in_factor
                self.zoom_factor *= zoom_factor
            else:
                zoom_factor = zoom_out_factor
                self.zoom_factor /= zoom_in_factor

            self.graphics_view.scale(zoom_factor, zoom_factor)

            # Get the new position
            new_pos = self.graphics_view.mapToScene(event.pos())

            # Move scene to old position
            delta = new_pos - old_pos
            self.graphics_view.translate(delta.x(), delta.y())

            # Update zoom indicator
            self.update_zoom_indicator()
            self.update_particle_heights()


    def update_zoom_indicator(self):
        zoom_percentage = int(self.zoom_factor * 100)
        self.zoom_indicator.setText(f"Zoom: {zoom_percentage}%")
        self.zoom_indicator.adjustSize()
        self.update_zoom_indicator_position()
        self.zoom_indicator.show()
        QTimer.singleShot(2000, self.zoom_indicator.hide)


    def set_ceiling_mode(self):
        if not self.check_image_loaded():
            return
        self.current_mode = "set_ceiling"
        self.current_set_mode = "ceiling"
        self.graphics_view.setDragMode(QGraphicsView.NoDrag)
        self.graphics_view.setCursor(self.ceiling_cursor)

        self.graphics_view.viewport().update()
        QApplication.processEvents()
        self.show_info_message("Set Ceiling", "Click on the image to set the ceiling of the capillary.", legacy=True)
        self.cursorCustom = True
        print("cursor set custom?")
        self.set_unsaved_changes()

    def set_floor_mode(self):
        if not self.check_image_loaded():
            return
        self.current_mode = "set_floor"
        self.current_set_mode = "floor"
        self.graphics_view.setDragMode(QGraphicsView.NoDrag)
        self.graphics_view.setCursor(self.floor_cursor)

        self.graphics_view.viewport().update()
        QApplication.processEvents()
        self.show_info_message("Set Floor", "Click on the image to set the floor of the capillary.", legacy=True)
        cursorCustom = True
        print("cursor set custom?")
        self.set_unsaved_changes()



    def switch_ceiling_floor_mode(self):
        if self.current_set_mode == "ceiling":
            self.set_floor_mode()
        else:
            self.set_ceiling_mode()

    def increment_ceiling(self, direction):
        if self.ceiling_y is not None:
            self.ceiling_y += direction
            self.update_lines()
            self.update_particle_heights()
            self.set_unsaved_changes()

    def increment_floor(self, direction):
        if self.floor_y is not None:
            self.floor_y += direction
            self.update_lines()
            self.update_particle_heights()
            self.set_unsaved_changes()


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

            if event.button() == Qt.LeftButton:
                if self.current_mode == "set_ceiling":
                    self.ceiling_y = scene_pos.y()
                    self.update_lines()
                    if not self.initial_setup_complete and self.floor_y is None:
                        self.set_floor_mode()  # Auto-switch to floor mode only during initial setup
                        self.show_info_message("Ceiling Set", "Now click to set the floor.", legacy=True)
                    else:
                        self.show_info_message("Ceiling Set", "Ceiling has been set.", legacy=True),
                        cursorCustom = False
                        print("cursorcustom set to false on 2605")
                        self.reset_cursor_and_mode()
                elif self.current_mode == "set_floor":
                    self.floor_y = scene_pos.y()
                    self.update_lines()
                    self.show_info_message("Floor Set", "Floor has been set.", legacy=True)
                    cursorCustom = False
                    print("cursorcustom set to false on 2612")
                    self.reset_cursor_and_mode()
                    self.initial_setup_complete = True  # Mark initial setup as complete
                elif self.current_mode == "particle":
                    x, y = scene_pos.x(), scene_pos.y()
                    height = self.calculate_height(x, y)
                    particle = {
                        'x': x,
                        'y': y,
                        'name': f'P{len(self.particles) + 1}',
                        'height': height,
                        'label_pos': QPointF(x + 10, y - 60)
                    }
                    self.particles.append(particle)
                    self.draw_particles()

    def reset_cursor_and_mode(self):
        self.current_mode = "particle"
        self.current_set_mode = None
        self.graphics_view.setCursor(Qt.ArrowCursor)
        print("cursor set to arrow !!!!! in reset_cursor_and_mode")
        self.update_particle_heights()

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
            self.set_unsaved_changes()

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
                label.setScale(self.current_label_size / 100.0)

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
                line.setPen(QPen(QColor(255, 255, 255), max(2, int(self.scale_factor)), Qt.DashLine))
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
                self.show_toast(message=message, message_type="info", timeout=timeout)
            else:
                self.show_toast(message=f"{title}: {message}", message_type="info", timeout=timeout)
        else:
            toast = ToastNotification(self, title, message, buttons)
            if buttons:
                for button_text, button in toast.buttons.items():
                    button.clicked.connect(lambda checked, text=button_text: toast.button_clicked(text))
            toast.show()

            if buttons:
                response = toast.get_response()
                if callback:
                    callback(response)
            else:
                QTimer.singleShot(timeout, toast.fade_out)

    def handle_toast_response(self, response, callback):
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

    def update_particle_heights(self):
        if self.capillary_height is None or self.ceiling_y is None or self.floor_y is None:
            return

        capillary_pixels = abs(self.floor_y - self.ceiling_y)
        for particle in self.particles:
            particle_y = particle['y']
            relative_height = (self.floor_y - particle_y) / capillary_pixels
            particle['height'] = relative_height * self.capillary_height

            if 'label_item' in particle:
                particle['label_item'].update_height(particle['height'])

        self.set_unsaved_changes()

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
                    writer.writerow(['Name', 'Height (µm)', 'Notes'])
                    for particle in self.particles:
                        writer.writerow([
                            particle['name'],
                            f"{particle['height']:.2f}",
                            particle.get('notes', '') if BETA_FEATURES_ENABLED else ''
                        ])
                self.show_info_message("Export Successful", f"Data exported to {file_name}", buttons=['OK'])
            except Exception as e:
                self.show_error_message("Export Error", f"Error exporting data: {str(e)}")

    def check_for_updates(self):
        try:
            owner = "vxco"
            repo = "PHASe"
            url = f"https://api.github.com/repos/{owner}/{repo}/releases/latest"

            response = requests.get(url)
            response.raise_for_status()

            latest_release = json.loads(response.text)
            latest_version = latest_release['tag_name'].lstrip('v')

            if version.parse(latest_version) > version.parse(CURRENT_VERSION):
                if platform.system() == 'Darwin':
                    asset_suffix = '_osx64app.zip'
                elif platform.system() == 'Windows':
                    asset_suffix = '_win64.zip'
                else:
                    self.show_toast(f"The current platform, {platform.system()}, is not natively maintained",
                                    message_type="warning")
                    return

                suitable_asset = any(asset['name'].endswith(asset_suffix) for asset in latest_release['assets'])
                if not suitable_asset:
                    self.show_toast("No suitable update available for your platform", message_type="warning")
                    return
                message = f"A new version ({latest_version}) is available. You are currently using version {CURRENT_VERSION}. Do you want to download and install the update?"
                self.show_info_message("Update Available", message, buttons=['Yes', 'No'],
                                       callback=lambda response: self.handle_update_response(response, latest_release))

            elif version.parse(latest_version) < version.parse(CURRENT_VERSION):
                if platform.system() == 'Darwin':
                    asset_suffix = '_osx64app.zip'
                elif platform.system() == 'Windows':
                    asset_suffix = '_win64.zip'
                else:
                    self.show_toast(f"The current platform, {platform.system()}, is not natively maintained",
                                    message_type="warning")
                    return

                suitable_asset = any(asset['name'].endswith(asset_suffix) for asset in latest_release['assets'])
                if not suitable_asset:
                    self.show_toast("update modal triggered, but no asset was found.", message_type="warning")
                    return

                message = f"A new version ({latest_version}) is available. You are currently using version {CURRENT_VERSION}. Do you want to download and install the update?"
                self.show_info_message("Beta Update Modal", message, buttons=['Yes', 'No'],
                                       callback=lambda response: self.handle_update_response(response, latest_release))

            else:
                self.show_toast(message="You are using the latest version", message_type="info")

        except Exception as e:
            self.show_error_message("Update Check Failed", f"Check your connection and retry.")
            print(f"error message shown from function check_for_updates with exception: {e}")

    def check_image_loaded(self):
        if not self.image_loaded:
            self.show_toast("Please load an image first", message_type="error", timeout=3000)
            return False
        return True

    def handle_update_response(self, response, latest_release):
        if response == 'Yes':
            self.download_and_install_update(latest_release)
        else:
            self.show_toast("Update cancelled", message_type="info")

    def download_and_install_update(self, release):
        try:
            # Determine the correct asset based on the platform
            if platform.system() == 'Darwin':
                asset_suffix = '_osx64app.zip'
            elif platform.system() == 'Windows':
                asset_suffix = '_win64.zip'
            else:
                raise Exception("Unsupported platform for auto-update")

            # Find the correct asset
            update_asset = next((asset for asset in release['assets'] if asset['name'].endswith(asset_suffix)), None)
            if not update_asset:
                raise Exception(f"No suitable download found for {platform.system()} in the release")

            # Get the download URL
            download_url = update_asset['browser_download_url']

            # Get the path to the updater script and the current executable
            if getattr(sys, 'frozen', False):
                # Running as bundled app
                if platform.system() == 'Darwin':
                    current_app_path = os.path.join(sys._MEIPASS, 'MacOS', 'PHASe')
                else:
                    current_app_path = sys.executable
                updater_path = os.path.join(sys._MEIPASS, 'updater.py')
            else:
                # Running as script
                current_app_path = sys.executable
                updater_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'updater.py')

            # Run the updater
            updater_command = [current_app_path, updater_path, download_url, current_app_path]
            subprocess.Popen(updater_command)

            self.show_info_message("Update Started",
                                   "The updater has been launched in a separate window. This application will now close. Please follow the instructions in the updater window.")
            QApplication.quit()

        except Exception as e:
            self.show_error_message("Update Failed", f"Update Failed: {str(e)}")
            print(f"Error in download_and_install_update: {e}")


import sys
import csv
from PyQt5.QtWidgets import (QApplication, QMainWindow, QLabel, QPushButton, QFileDialog,
                             QInputDialog, QVBoxLayout, QHBoxLayout, QWidget, QSlider,
                             QGraphicsScene, QGraphicsView, QGraphicsEllipseItem,
                             QGraphicsTextItem, QGraphicsRectItem, QGraphicsLineItem,
                             QGraphicsItemGroup, QGraphicsItem, QStyleFactory, QFrame, QGridLayout,
                             QSizePolicy, QMessageBox, QMenu, QAction, QListWidget, QStackedWidget)
from PyQt5.QtGui import QPixmap, QImage, QColor, QFont, QPen, QCursor, QTransform, QPainter, QLinearGradient, QPalette, QIcon, QDesktopServices
from PyQt5.QtCore import Qt, QRectF, QPointF, QLineF, pyqtSignal, QObject, QSize, QUrl, QTimer
import traceback
import requests
import json
from packaging import version
import os
import tempfile
import subprocess
from urllib.request import urlretrieve

CURRENT_VERSION = "3.0.0"



class CustomGraphicsScene(QGraphicsScene):
    """
    Extends QGraphicsScene and includes a method to update connection lines.
    """
    def __init__(self, parent=None):
        super().__init__(parent)
        self.parent = parent

    def update_connection_line(self, label):
        """
        Updates the connection line between the particle label and the particle dot.

        Args:
            label (DraggableLabel): The label object to update the connection line for.
        """
        line = label.data(0)
        if line:
            start = QPointF(label.x, label.y)
            end = label.sceneBoundingRect().center()
            line.setLine(QLineF(start, end))

class DraggableLabelSignals(QObject):
    """
    Defines custom signals for DraggableLabel. A stupid workaround for PyInstaller.
    """
    deleteRequested = pyqtSignal(object)


class ModernButton(QPushButton):
    """
    A custom QPushButton with a modern look. Extends QPushButton
    """

    def __init__(self, icon_path, text, parent=None):
        super().__init__(parent)
        self.setText(text)
        self.setIcon(QIcon(icon_path))
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
        """
        Sets a default size for the buttons.

        Returns:
            QSize: The default size for the button.
        """
        return QSize(120, 60)


class DraggableLabel(QGraphicsItemGroup):
    """
    A draggable label for particles. Extends QGraphicsItemGroup
    """
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
        """
        Creates the visual components of the draggable label.
        """
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
        """
        Handles mouse press events on the label.

        Args:
            event (QGraphicsSceneMouseEvent): The mouse pressing event.
        """
        if event.button() == Qt.RightButton:
            self.show_context_menu(event.screenPos())
        elif self.delete_button.contains(event.pos()):
            self.signals.deleteRequested.emit(self)
        else:
            super().mousePressEvent(event)

    def show_context_menu(self, pos):
        """
        Shows a context menu for the label.

        Args:
            pos (QPoint): The position where to show the menu.
        """
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
        """
        Opens a dialog to rename the particle.
        """
        dialog = self.analyzer.create_styled_input_dialog("Rename Particle", "Enter new name:", self.name or "")
        if dialog.exec_() == QInputDialog.Accepted:
            new_name = dialog.textValue()
            self.name = new_name if new_name else ''
            if self.name:
                self.analyzer.add_used_name(self.name)
            self.update_label_text()
            self.analyzer.update_particle_data(self, {'name': self.name})

    def get_label_text(self):
        """
        Gets the text to display on the label.

        Returns:
            str: The label text.
        """

        if self.name:
            return f"{self.name}: {self.height:.2f} µm"
        else:
            return f"{self.height:.2f} µm"

    def update_label_text(self):
        """
        Updates the text displayed on the label.
        """

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

        # This method is so janky I can't even look at it
        # But, it works. So, I'm not going to touch it.
        # #ifitworksdonttouchit


    def itemChange(self, change, value):
        """
        Handles changes to the item's state.

        Args:
            change (GraphicsItemChange): The type of change.
            value: The new value.

        Returns:
            The result of the superclass' itemChange method.
        """

        if change == QGraphicsItemGroup.ItemPositionHasChanged and self.scene():
            self.scene().update_connection_line(self)
        return super().itemChange(change, value)


class CapillaryAnalyzer(QMainWindow):
    """
    The main application window.
    """

    def __init__(self):
        super().__init__()
        self.setWindowTitle("PHASe - Particle Height Analysis Software")
        self.setGeometry(100, 100, 1200, 800)
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

        # Create graphics view
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

        # Sidebar
        sidebar = QFrame()
        sidebar.setStyleSheet("""
            QFrame {
                background-color: #34495e;
                border-radius: 15px;
                margin: 10px;
            }
            QPushButton {
                background-color: #2c3e50;
                color: white;
                border: none;
                border-radius: 5px;
                padding: 10px;
                margin: 5px;
                font-size: 14px;
            }
            QPushButton:hover {
                background-color: #3498db;
            }
        """)
        sidebar_layout = QVBoxLayout(sidebar)

        # Logo space
        logo_label = QLabel()
        logo_pixmap = QPixmap(resource_path("assets/phase_logo_v3.svg"))
        logo_label.setPixmap(logo_pixmap.scaled(200, 100, Qt.KeepAspectRatio, Qt.SmoothTransformation))
        logo_label.setAlignment(Qt.AlignCenter)
        sidebar_layout.addWidget(logo_label)

        # Navigation buttons
        self.setup_button = QPushButton("Setup")
        self.setup_button.clicked.connect(lambda: self.stacked_widget.setCurrentIndex(0))
        sidebar_layout.addWidget(self.setup_button)

        self.analysis_button = QPushButton("Analysis")
        self.analysis_button.clicked.connect(lambda: self.stacked_widget.setCurrentIndex(1))
        sidebar_layout.addWidget(self.analysis_button)

        sidebar_layout.addStretch()

        # Stacked widget to hold different pages
        self.stacked_widget = QStackedWidget()

        # Setup page
        setup_page = QWidget()
        setup_layout = QHBoxLayout(setup_page)

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

        # Load Image button
        self.load_button = ModernButton(resource_path("assets/load_image_btn.svg"), "Load Image")
        self.load_button.clicked.connect(self.load_image)
        control_layout.addWidget(self.load_button)

        # Ceiling and Floor buttons
        ceiling_floor_layout = QHBoxLayout()

        ceiling_floor_left = QVBoxLayout()
        self.set_ceiling_button = ModernButton(resource_path("assets/set_ceiling_btn.svg"), "Set Ceiling")
        self.set_ceiling_button.clicked.connect(self.set_ceiling_mode)
        ceiling_floor_left.addWidget(self.set_ceiling_button)

        self.set_floor_button = ModernButton(resource_path("assets/set_floor_btn.svg"), "Set Floor")
        self.set_floor_button.clicked.connect(self.set_floor_mode)
        ceiling_floor_left.addWidget(self.set_floor_button)

        ceiling_floor_layout.addLayout(ceiling_floor_left)

        # Set Height button
        self.set_height_button = ModernButton(resource_path("assets/set_height_btn.svg"), "Set Height")
        self.set_height_button.clicked.connect(self.set_height)
        self.set_height_button.setFixedHeight(
            self.set_ceiling_button.sizeHint().height() * 2 + 7)
        ceiling_floor_layout.addWidget(self.set_height_button)

        control_layout.addLayout(ceiling_floor_layout)

        # Export CSV button
        self.export_button = ModernButton(resource_path("assets/export_as_csv_btn.svg"), "Export CSV")
        self.export_button.clicked.connect(self.export_csv)
        control_layout.addWidget(self.export_button)

        control_layout.addStretch()

        setup_layout.addWidget(control_panel, 1)
        setup_layout.addWidget(self.graphics_view, 3)

        # Analysis page
        analysis_page = QWidget()
        analysis_layout = QVBoxLayout(analysis_page)

        # Particle list
        self.particle_list = QListWidget()
        self.particle_list.setStyleSheet("""
            QListWidget {
                background-color: #34495e;
                color: white;
                border-radius: 5px;
            }
            QListWidget::item {
                padding: 5px;
            }
            QListWidget::item:selected {
                background-color: #3498db;
            }
        """)
        analysis_layout.addWidget(QLabel("Selected Particles:"))
        analysis_layout.addWidget(self.particle_list)

        # Analysis buttons
        analyze_color_button = QPushButton("Analyze Color")
        analyze_color_button.clicked.connect(self.analyze_color)
        analysis_layout.addWidget(analyze_color_button)

        calculate_average_button = QPushButton("Calculate Average Height")
        calculate_average_button.clicked.connect(self.calculate_average_height)
        analysis_layout.addWidget(calculate_average_button)

        # Add pages to stacked widget
        self.stacked_widget.addWidget(setup_page)
        self.stacked_widget.addWidget(analysis_page)

        # Main layout
        main_layout.addWidget(sidebar, 1)
        main_layout.addWidget(self.stacked_widget, 4)

        self.original_image = None
        self.image_item = None
        self.capillary_height = None
        self.particles = []
        self.particle_items = []
        self.ceiling_y = None
        self.floor_y = None
        self.current_mode = None
        self.used_names = set()
        self.image_item = None
        self.ceiling_line = None
        self.floor_line = None
        self.scale_factor = 1.0

        QTimer.singleShot(1000, self.check_for_updates)

    def load_image(self):
        """
                Opens a file dialog to load an image and displays it in the scene.
        """
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
                print(f"Image size: {self.original_image.width()}x{self.original_image.height()}")
                print(f"Scale factor: {self.scale_factor}")
        except Exception as e:
            error_message = f"Error loading image: {str(e)}"
            print(error_message)
            QMessageBox.critical(self, "Error", error_message)

    def resizeEvent(self, event):
        """
        Handles the resize event of the main window.

        Args:
            event (QResizeEvent): The resize event.
        """
        super().resizeEvent(event)
        if self.image_item:
            self.graphics_view.fitInView(self.scene.sceneRect(), Qt.KeepAspectRatio)

    def set_ceiling_mode(self):
        """
        Sets the current mode to 'ceiling' for setting the ceiling line.
        """
        self.current_mode = "ceiling"
        self.graphics_view.viewport().setCursor(Qt.CrossCursor)

    def set_floor_mode(self):
        """
        Sets the current mode to 'floor' for setting the floor line.
        """
        self.current_mode = "floor"
        self.graphics_view.viewport().setCursor(Qt.CrossCursor)

    def mousePressEvent(self, event):
        """
        Handles mouse press events in the main window.

        Args:
            event (QMouseEvent): The mouse pressing event.
        """
        if self.original_image and self.graphics_view.underMouse():
            scene_pos = self.graphics_view.mapToScene(self.graphics_view.mapFromGlobal(event.globalPos()))

            if self.current_mode == "ceiling":
                self.ceiling_y = scene_pos.y()
                self.current_mode = None
                self.graphics_view.viewport().setCursor(Qt.ArrowCursor)
                self.update_lines()
            elif self.current_mode == "floor":
                self.floor_y = scene_pos.y()
                self.current_mode = None
                self.graphics_view.viewport().setCursor(Qt.ArrowCursor)
                self.update_lines()
            elif not isinstance(self.scene.itemAt(scene_pos, self.graphics_view.transform()),
                                (QGraphicsRectItem, QGraphicsTextItem)):
                x, y = scene_pos.x(), scene_pos.y()
                height = self.calculate_height(y)
                label_pos = QPointF(x + 10, y - 60)
                new_particle = {
                    'x': x,
                    'y': y,
                    'name': '',
                    'height': height,
                    'label_pos': label_pos
                }
                self.particles.append(new_particle)
                self.draw_particles()

    def update_particle_name(self, label, new_name):
        """
        Updates the name of a particle.

        Args:
            label (DraggableLabel): The label of the particle to update.
            new_name (str): The new name for the particle.
        """

        for particle in self.particles:
            if particle.get('label_item') == label:
                particle['name'] = new_name
                break

    def update_lines(self):
        """
        Updates the ceiling and floor lines in the scene.
        """
        if self.original_image and self.image_item:
            # Remove existing ceiling and floor lines if they exist
            if hasattr(self, 'ceiling_line') and self.ceiling_line:
                self.scene.removeItem(self.ceiling_line)
            if hasattr(self, 'floor_line') and self.floor_line:
                self.scene.removeItem(self.floor_line)

            width = self.original_image.width()

            if self.floor_y is not None:
                self.floor_line = self.scene.addLine(0, self.floor_y, width, self.floor_y, QPen(QColor(0, 255, 0), 2))
            if self.ceiling_y is not None:
                self.ceiling_line = self.scene.addLine(0, self.ceiling_y, width, self.ceiling_y,
                                                       QPen(QColor(255, 0, 0), 2))

            self.draw_particles()

    def set_height(self):
        """
        Opens a dialog to set the capillary height and updates particle heights.
        """
        dialog = self.create_styled_input_dialog("Set Capillary Height", "Enter height (e.g. 0.1mm, 100um, 100000pm):")
        if dialog.exec_() == QInputDialog.Accepted:
            height = dialog.textValue().replace(" ", "").lower()
            unit_start = 0
            for i, char in enumerate(height):
                if not (char.isdigit() or char == '.'):
                    unit_start = i
                    break

            if unit_start == 0:
                self.show_warning_message("Invalid Input", "Please enter a number followed by a unit (um, mm, or pm).")
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
                self.update_particles()
            except ValueError:
                self.show_warning_message("Invalid Number", "Please enter a valid number followed by a unit.")

    def create_styled_input_dialog(self, title, label, text=""):
        """
        Creates a styled input dialog.

        Args:
            title (str): The title of the dialog.
            label (str): The label text for the input field.
            text (str): The initial text in the input field.

        Returns:
            QInputDialog: The created input dialog.
        """
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


    def calculate_height(self, y):
        """
        Calculates the height of a particle based on its y-position.

        Args:
            y (float): The y-position of the particle.

        Returns:
            float: The calculated height of the particle.
        """

        if self.capillary_height is not None and self.ceiling_y is not None and self.floor_y is not None:
            total_pixels = abs(self.ceiling_y - self.floor_y)
            pixels_from_bottom = abs(y - self.floor_y)
            return (pixels_from_bottom / total_pixels) * self.capillary_height
        return 0

    def update_particles(self):
        """
        Updates the heights of all particles based on the current capillary height.
        """
        if self.capillary_height is not None:
            updated_particles = []
            for x, y, name, _, label_pos in self.particles:
                height = self.calculate_height(y)
                updated_particles.append((x, y, name, height, label_pos))
            self.particles = updated_particles
            self.draw_particles()

    def draw_particles(self):
        """
        Draws all particles in the scene.
        """
        if self.original_image and self.image_item:
            for particle in self.particles:
                if 'label_item' not in particle:
                    x, y = particle['x'], particle['y']

                    # Scale the particle dot size
                    dot_size = 6 * self.scale_factor
                    particle_dot = QGraphicsEllipseItem(x - dot_size / 2, y - dot_size / 2, dot_size, dot_size)
                    particle_dot.setBrush(QColor(255, 0, 0))
                    self.scene.addItem(particle_dot)

                    label = DraggableLabel(x, y, particle['name'], particle['height'], self)
                    label.setPos(particle['label_pos'])
                    label.signals.deleteRequested.connect(self.delete_particle)
                    self.scene.addItem(label)

                    # Scale the line width
                    line = QGraphicsLineItem()
                    line.setPen(QPen(QColor(255, 255, 255), max(1, int(self.scale_factor)), Qt.DashLine))
                    self.scene.addItem(line)
                    label.setData(0, line)

                    particle['label_item'] = label
                    particle['dot_item'] = particle_dot
                    particle['line_item'] = line

                self.scene.update_connection_line(particle['label_item'])
                self.update_particle_list()

    def show_error_message(self, title, message):
        """
        Shows an error message box.

        Args:
            title (str): The title of the message box.
            message (str): The error message to display.
        """
        error_box = QMessageBox(self)
        error_box.setStyleSheet(self.message_box_style)
        error_box.setIcon(QMessageBox.Critical)
        error_box.setWindowTitle(title)
        error_box.setText(message)
        error_box.exec_()

    def update_particle_list(self):
        self.particle_list.clear()
        for particle in self.particles:
            item_text = f"{particle['name']} - Height: {particle['height']:.2f} µm"
            self.particle_list.addItem(item_text)

    def analyze_color(self):
        # TODO: better color analysis PLEASE DONT FORGET THİS (note to self)
        selected_items = self.particle_list.selectedItems()
        if not selected_items:
            self.show_warning_message("No Selection", "Please select particles to analyze.")
            return

        for item in selected_items:
            particle_index = self.particle_list.row(item)
            particle = self.particles[particle_index]
            x, y = particle['x'], particle['y']

            color = self.get_average_color(x, y, radius=5)
            color_name = self.get_color_name(color)

            particle['name'] = color_name
            particle['label_item'].name = color_name
            particle['label_item'].update_label_text()

        self.update_particle_list()
        self.scene.update()

    def get_average_color(self, x, y, radius):
        if not self.original_image:
            return QColor(0, 0, 0)

        x, y = int(x), int(y)
        total_r, total_g, total_b = 0, 0, 0
        count = 0

        for dx in range(-radius, radius + 1):
            for dy in range(-radius, radius + 1):
                if dx * dx + dy * dy <= radius * radius:
                    px, py = x + dx, y + dy
                    if 0 <= px < self.original_image.width() and 0 <= py < self.original_image.height():
                        color = QColor(self.original_image.pixel(px, py))
                        total_r += color.red()
                        total_g += color.green()
                        total_b += color.blue()
                        count += 1

        if count == 0:
            return QColor(0, 0, 0)

        return QColor(total_r // count, total_g // count, total_b // count)

    def get_color_name(self, color):
        # Simple color naming (you can expand this)
        if color.red() > 200 and color.green() < 100 and color.blue() < 100:
            return "Red Particle"
        elif color.green() > 200 and color.red() < 100 and color.blue() < 100:
            return "Green Particle"
        elif color.blue() > 200 and color.red() < 100 and color.green() < 100:
            return "Blue Particle"
        else:
            return "Unknown Color"

    def calculate_average_height(self):
        selected_items = self.particle_list.selectedItems()
        if not selected_items:
            self.show_warning_message("No Selection", "Please select particles to calculate average height.")
            return

        total_height = 0
        count = 0
        for item in selected_items:
            particle_index = self.particle_list.row(item)
            particle = self.particles[particle_index]
            total_height += particle['height']
            count += 1

        if count > 0:
            average_height = total_height / count
            self.show_info_message("Average Height", f"The average height of selected particles is {average_height:.2f} µm")
        else:
            self.show_warning_message("Calculation Error", "No valid heights found for selected particles.")


    def show_info_message(self, title, message):
        """
        Shows an information message box.

        Args:
            title (str): The title of the message box.
            message (str): The information message to display.
        """
        info_box = QMessageBox(self)
        info_box.setStyleSheet(self.message_box_style)
        info_box.setIcon(QMessageBox.Information)
        info_box.setWindowTitle(title)
        info_box.setText(message)
        info_box.exec_()


    def show_warning_message(self, title, message):
        """
        Shows a warning message box.

        Args:
            title (str): The title of the message box.
            message (str): The warning message to display.
        """
        warning_box = QMessageBox(self)
        warning_box.setStyleSheet(self.message_box_style)
        warning_box.setIcon(QMessageBox.Warning)
        warning_box.setWindowTitle(title)
        warning_box.setText(message)
        warning_box.exec_()

    def update_particle_data(self, label, new_data):
        """
        Updates the data of a particle.

        Args:
            label (DraggableLabel): The label of the particle to update.
            new_data (dict): The new data for the particle.
        """
        for particle in self.particles:
            if particle['label_item'] == label:
                particle.update(new_data)
                if 'name' in new_data:
                    self.add_used_name(new_data['name'])
                break


    def delete_particle(self, label):
        """
        Deletes a particle from the scene and the particles list.

        Args:
            label (DraggableLabel): The label of the particle to delete.
        """
        for i, particle in enumerate(self.particles):
            if particle['label_item'] == label:
                self.scene.removeItem(particle['label_item'])
                self.scene.removeItem(particle['dot_item'])
                self.scene.removeItem(particle['line_item'])
                del self.particles[i]
                break

        self.scene.update()


    def add_used_name(self, name):
        """
        Adds a name to the set of used particle names.

        Args:
            name (str): The name to add.
        """

        self.used_names.add(name)

    def export_csv(self):
        """
        Exports particle data to a CSV file.
        """
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
        """
        Checks for available updates and prompts the user to update if a new version is available.
        """
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
            self.show_error_message("Update Check Failed", f"Failed to check for updates: {str(e)}")

    def download_and_install_update(self, release):
        """
        Downloads and installs the latest update.

        Args:
            release (dict): Information about the latest release.
        """
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
            self.show_error_message("Update Failed", f"Failed to download and prepare the update: {str(e)}")


def exception_hook(exctype, value, tb):
    """
    Global exception hook to handle uncaught exceptions.

    Args:
        exctype: The type of the exception.
        value: The exception instance.
        tb: The traceback object.
    """

    print(''.join(traceback.format_exception(exctype, value, tb)))
    sys.exit(1)


def resource_path(relative_path):
    """
    Get the absolute path to a resource, works for development and PyInstaller.

    Args:
        relative_path (str): The relative path to the resource. (How it appears in the CWD and the spec file)

    Returns:
        str: The absolute path to the resource.
    """
    try:
        # PyInstaller creates a temp folder and stores path in _MEIPASS
        base_path = sys._MEIPASS
    except Exception:
        base_path = os.path.abspath(".")

    return os.path.join(base_path, relative_path)


if __name__ == "__main__":
    sys.excepthook = exception_hook
    try:
        app = QApplication(sys.argv)
        window = CapillaryAnalyzer()
        window.show()
        sys.exit(app.exec_())
    except Exception as e:
        print(f"An unexpected error occurred: {e}")
        print("Traceback:")
        traceback.print_exc()
        sys.exit(1)


import sys
import csv
from PyQt5.QtWidgets import (QApplication, QMainWindow, QLabel, QPushButton, QFileDialog,
                             QInputDialog, QVBoxLayout, QHBoxLayout, QWidget, QSlider,
                             QGraphicsScene, QGraphicsView, QGraphicsEllipseItem,
                             QGraphicsTextItem, QGraphicsRectItem, QGraphicsLineItem,
                             QGraphicsItemGroup, QGraphicsItem, QStyleFactory, QFrame, QGridLayout,
                             QSizePolicy, QMessageBox, QMenu, QAction)
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

CURRENT_VERSION = "2.1.5"



class CustomGraphicsScene(QGraphicsScene):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.parent = parent

    def update_connection_line(self, label):
        line = label.data(0)
        if line:
            start = QPointF(label.x, label.y)
            end = label.sceneBoundingRect().center()
            line.setLine(QLineF(start, end))

class DraggableLabelSignals(QObject):
    deleteRequested = pyqtSignal(object)


class ModernButton(QPushButton):
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
        total_width = text_width + delete_button_size + padding * 2
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

        cross_rect = delete_cross.boundingRect()
        cross_x = delete_button.rect().center().x() - cross_rect.width() / 2
        cross_y = delete_button.rect().center().y() - cross_rect.height() / 2
        delete_cross.setPos(delete_button.pos() + QPointF(cross_x, cross_y))

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

    def rename(self):
        dialog = self.analyzer.create_styled_input_dialog("Rename Particle", "Enter new name:", self.name or "")
        if dialog.exec_() == QInputDialog.Accepted:
            new_name = dialog.textValue()
            self.name = new_name if new_name else ''
            if self.name:
                self.analyzer.add_used_name(self.name)
            self.update_label_text()
            self.analyzer.update_particle_data(self, {'name': self.name})

    def get_label_text(self):
        if self.name:
            return f"{self.name}: {self.height:.2f} µm"
        else:
            return f"{self.height:.2f} µm"


    def update_label_text(self):
        label_text = self.get_label_text()
        self.childItems()[1].setPlainText(label_text)

    def itemChange(self, change, value):
        if change == QGraphicsItemGroup.ItemPositionHasChanged and self.scene():
            self.scene().update_connection_line(self)
        return super().itemChange(change, value)


class CapillaryAnalyzer(QMainWindow):
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

        # Logo space
        logo_label = QLabel()
        logo_pixmap = QPixmap("assets/phase_logo_v3.svg")
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


        # Set Height button (spans two button heights)
        self.set_height_button = ModernButton("assets/set_height_btn.svg", "Set Height")
        self.set_height_button.clicked.connect(self.set_height)
        self.set_height_button.setFixedHeight(
            self.set_ceiling_button.sizeHint().height() * 2 + 7)  # Match height of two buttons + spacing
        ceiling_floor_layout.addWidget(self.set_height_button)

        control_layout.addLayout(ceiling_floor_layout)


        # Export CSV button (spans two button widths)
        self.export_button = ModernButton("assets/export_as_csv_btn.svg", "Export CSV")
        self.export_button.clicked.connect(self.export_csv)
        control_layout.addWidget(self.export_button)

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

        QTimer.singleShot(1000, self.check_for_updates)

    def load_image(self):
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
        super().resizeEvent(event)
        if self.image_item:
            self.graphics_view.fitInView(self.scene.sceneRect(), Qt.KeepAspectRatio)

    def set_ceiling_mode(self):
        self.current_mode = "ceiling"
        self.graphics_view.viewport().setCursor(Qt.CrossCursor)

    def set_floor_mode(self):
        self.current_mode = "floor"
        self.graphics_view.viewport().setCursor(Qt.CrossCursor)

    def mousePressEvent(self, event):
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
        for particle in self.particles:
            if particle.get('label_item') == label:
                particle['name'] = new_name
                break

    def update_lines(self):
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
        if self.capillary_height is not None and self.ceiling_y is not None and self.floor_y is not None:
            total_pixels = abs(self.ceiling_y - self.floor_y)
            pixels_from_bottom = abs(y - self.floor_y)
            return (pixels_from_bottom / total_pixels) * self.capillary_height
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

    def show_error_message(self, title, message):
        error_box = QMessageBox(self)
        error_box.setStyleSheet(self.message_box_style)
        error_box.setIcon(QMessageBox.Critical)
        error_box.setWindowTitle(title)
        error_box.setText(message)
        error_box.exec_()


    def show_info_message(self, title, message):
        info_box = QMessageBox(self)
        info_box.setStyleSheet(self.message_box_style)
        info_box.setIcon(QMessageBox.Information)
        info_box.setWindowTitle(title)
        info_box.setText(message)
        info_box.exec_()


    def show_warning_message(self, title, message):
        warning_box = QMessageBox(self)
        warning_box.setStyleSheet(self.message_box_style)
        warning_box.setIcon(QMessageBox.Warning)
        warning_box.setWindowTitle(title)
        warning_box.setText(message)
        warning_box.exec_()

    def update_particle_data(self, label, new_data):
        for particle in self.particles:
            if particle['label_item'] == label:
                particle.update(new_data)
                break

    def delete_particle(self, label):
        for i, particle in enumerate(self.particles):
            if particle['label_item'] == label:
                self.scene.removeItem(particle['label_item'])
                self.scene.removeItem(particle['dot_item'])
                self.scene.removeItem(particle['line_item'])
                del self.particles[i]
                break

        self.scene.update()


    def add_used_name(self, name):
        self.used_names.add(name)

    def export_csv(self):
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
                            particle['name'] if particle['name'] else '',
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
            self.show_error_message("Update Check Failed", f"Failed to check for updates: {str(e)}")

    def download_and_install_update(self, release):
        try:
            # Find the .app asset
            app_asset = next((asset for asset in release['assets'] if asset['name'].endswith('.osx64app.zip')), None)
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

            current_app_path = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
            updater_script = f"""
            #!/bin/bash
            sleep 2
            rm -rf "{current_app_path}"
            mv "{app_path}" "{os.path.dirname(current_app_path)}"
            open "{os.path.dirname(current_app_path)}/{os.path.basename(app_path)}"
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
    print(''.join(traceback.format_exception(exctype, value, tb)))
    sys.exit(1)





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

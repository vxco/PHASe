import sys
from PyQt5.QtWidgets import (QApplication, QMainWindow, QLabel, QPushButton, QFileDialog,
                             QInputDialog, QVBoxLayout, QHBoxLayout, QWidget, QSlider,
                             QGraphicsScene, QGraphicsView, QGraphicsEllipseItem,
                             QGraphicsTextItem, QGraphicsRectItem, QGraphicsLineItem,
                             QGraphicsItemGroup, QGraphicsItem)
from PyQt5.QtGui import QPixmap, QImage, QColor, QFont, QPen, QCursor, QTransform
from PyQt5.QtCore import Qt, QRectF, QPointF, QLineF, pyqtSignal, QObject


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


class DraggableLabel(QGraphicsItemGroup):
    def __init__(self, x, y, name, height, analyzer, parent=None):
        super().__init__(parent)
        self.setFlag(QGraphicsItemGroup.ItemIsMovable)
        self.setFlag(QGraphicsItemGroup.ItemSendsGeometryChanges)
        self.x = x
        self.y = y
        self.name = name
        self.height = height
        self.analyzer = analyzer  # Store reference to CapillaryAnalyzer
        self.signals = DraggableLabelSignals()
        self.delete_button = None
        self.create_label()

    def create_label(self):
        font_size = 16
        label_text = f"{self.name}: {self.height:.2f} µm"
        label = QGraphicsTextItem(label_text)
        font = QFont("Arial", font_size)
        label.setFont(font)
        label.setDefaultTextColor(QColor(255, 255, 255))

        text_width = label.boundingRect().width()
        text_height = label.boundingRect().height()
        padding = 10
        delete_button_size = 24
        total_width = text_width + delete_button_size + padding * 2
        total_height = max(text_height, delete_button_size) + padding * 2

        background = QGraphicsRectItem(0, 0, total_width, total_height)
        background.setBrush(QColor(0, 0, 0, 180))

        label.setPos(QPointF(padding, padding))

        delete_button = QGraphicsRectItem(total_width - delete_button_size - padding, padding, delete_button_size,
                                          delete_button_size)
        delete_button.setBrush(QColor(255, 0, 0))
        delete_button.setFlag(QGraphicsItem.ItemIsSelectable)
        delete_button.setCursor(Qt.PointingHandCursor)

        delete_cross = QGraphicsTextItem('×')
        delete_cross.setFont(QFont("Arial", delete_button_size, QFont.Bold))
        delete_cross.setDefaultTextColor(QColor(255, 255, 255))

        # Center the cross in the delete button
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
        if self.delete_button and self.delete_button.contains(event.pos()):
            self.signals.deleteRequested.emit(self)
            event.accept()
        else:
            super().mousePressEvent(event)

    def itemChange(self, change, value):
        if change == QGraphicsItemGroup.ItemPositionHasChanged and self.scene():
            self.scene().update_connection_line(self)
            # Update the label position in the particles list
            for i, (px, py, name, height, _) in enumerate(self.analyzer.particles):
                if abs(self.x - px) < 10 and abs(self.y - py) < 10:
                    self.analyzer.particles[i] = (px, py, name, height, self.pos())
                    break
        return super().itemChange(change, value)
class CapillaryAnalyzer(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("PHASe - Particle Height Analysis Software")
        self.setGeometry(100, 100, 1000, 600)

        main_widget = QWidget()
        self.setCentralWidget(main_widget)
        main_layout = QHBoxLayout()
        main_widget.setLayout(main_layout)

        # Image area
        self.graphics_view = QGraphicsView()
        self.graphics_view.setFixedSize(800, 500)
        self.scene = CustomGraphicsScene(self)
        self.graphics_view.setScene(self.scene)

        # Controls area
        controls_layout = QVBoxLayout()

        self.load_button = QPushButton("Load Image")
        self.load_button.clicked.connect(self.load_image)

        self.ceiling_slider = QSlider(Qt.Vertical)
        self.ceiling_slider.setRange(0, 500)
        self.ceiling_slider.setValue(0)  # Inverted
        self.ceiling_slider.valueChanged.connect(self.update_lines)

        self.floor_slider = QSlider(Qt.Vertical)
        self.floor_slider.setRange(0, 500)
        self.floor_slider.setValue(500)  # Inverted
        self.floor_slider.valueChanged.connect(self.update_lines)

        self.set_height_button = QPushButton("Set Height")
        self.set_height_button.clicked.connect(self.set_height)

        controls_layout.addWidget(self.load_button)
        controls_layout.addWidget(QLabel("Ceiling"))
        controls_layout.addWidget(self.ceiling_slider)
        controls_layout.addWidget(QLabel("Floor"))
        controls_layout.addWidget(self.floor_slider)
        controls_layout.addWidget(self.set_height_button)

        main_layout.addWidget(self.graphics_view)
        main_layout.addLayout(controls_layout)

        self.original_image = None
        self.image_item = None  # Initialize image_item attribute
        self.capillary_height = None
        self.particles = []

        self.floor_slider.valueChanged.connect(self.update_particles)
        self.ceiling_slider.valueChanged.connect(self.update_particles)

    def load_image(self):
        file_name, _ = QFileDialog.getOpenFileName(self, "Open Image", "", "Image Files (*.png *.jpg *.bmp)")
        if file_name:
            self.original_image = QImage(file_name)
            if self.image_item:
                self.scene.removeItem(self.image_item)
            self.image_item = self.scene.addPixmap(QPixmap.fromImage(self.original_image))
            self.scene.setSceneRect(self.image_item.boundingRect())
            self.graphics_view.fitInView(self.scene.sceneRect(), Qt.KeepAspectRatio)
            self.update_lines()

    def update_lines(self):
        if self.original_image:
            self.scene.clear()
            self.scene.addPixmap(QPixmap.fromImage(self.original_image))

            height = self.original_image.height()
            width = self.original_image.width()

            floor_y = int(self.floor_slider.value() * height / 500)
            ceiling_y = int(self.ceiling_slider.value() * height / 500)

            floor_line = self.scene.addLine(0, floor_y, width, floor_y, QPen(QColor(0, 255, 0), 2))
            ceiling_line = self.scene.addLine(0, ceiling_y, width, ceiling_y, QPen(QColor(255, 0, 0), 2))

            self.draw_particles()

    def set_height(self):
        height, ok = QInputDialog.getText(self, "Set Capillary Height", "Enter height (e.g. 0.1mm, 100um, 100000pm):")
        if ok:
            height = height.replace(" ", "").lower()
            unit_start = 0
            for i, char in enumerate(height):
                if not (char.isdigit() or char == '.'):
                    unit_start = i
                    break

            if unit_start == 0:
                print("Invalid input. Please enter a number followed by a unit (um, mm, or pm).")
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
                    print("Invalid unit. Please use um, mm, or pm.")
                    return

                print(f"Capillary height set to {self.capillary_height} um")
                self.update_particles()
            except ValueError:
                print("Invalid number format. Please enter a valid number followed by a unit.")

    def update_connection_line(self, label):
        line = self.scene.items()[-1]  # Assuming the line is the last item added
        start = QPointF(label.x, label.y)
        end = label.sceneBoundingRect().center()
        line.setLine(QLineF(start, end))

    def mousePressEvent(self, event):
        if self.original_image and self.graphics_view.underMouse():
            scene_pos = self.graphics_view.mapToScene(self.graphics_view.mapFromGlobal(event.globalPos()))
            item = self.scene.itemAt(scene_pos, self.graphics_view.transform())

            if isinstance(item, QGraphicsEllipseItem):
                # Clicked on particle dot
                return

            if not isinstance(item, (QGraphicsRectItem, QGraphicsTextItem)):
                # Clicked elsewhere, add new particle
                x, y = scene_pos.x(), scene_pos.y()
                name, ok = QInputDialog.getText(self, "Particle Name", "Enter particle name:")
                if ok:
                    height = self.calculate_height(y)
                    label_pos = QPointF(x + 10, y - 60)  # Initial label position
                    self.particles.append((x, y, name, height, label_pos))
                    self.draw_particles()

    def calculate_height(self, y):
        if self.capillary_height is not None:
            height = self.original_image.height()
            floor_y = height - int(self.floor_slider.value() * height / 500)  # Inverted
            ceiling_y = height - int(self.ceiling_slider.value() * height / 500)  # Inverted
            total_pixels = abs(ceiling_y - floor_y)
            pixels_from_bottom = abs(y - floor_y)
            return (pixels_from_bottom / total_pixels) * self.capillary_height
        return 0
    def update_particles(self):
        updated_particles = []
        for x, y, name, _, label_pos in self.particles:
            height = self.calculate_height(y)
            updated_particles.append((x, y, name, height, label_pos))
        self.particles = updated_particles
        self.draw_particles()

    def draw_particles(self):
        self.scene.clear()
        self.scene.addPixmap(QPixmap.fromImage(self.original_image))

        height = self.original_image.height()
        width = self.original_image.width()

        floor_y = height - int(self.floor_slider.value() * height / 500)  # Inverted
        ceiling_y = height - int(self.ceiling_slider.value() * height / 500)  # Inverted

        self.scene.addLine(0, floor_y, width, floor_y, QPen(QColor(0, 255, 0), 2))
        self.scene.addLine(0, ceiling_y, width, ceiling_y, QPen(QColor(255, 0, 0), 2))

        for x, y, name, particle_height, label_pos in self.particles:
            particle = QGraphicsEllipseItem(x - 3, y - 3, 6, 6)
            particle.setBrush(QColor(255, 0, 0))
            self.scene.addItem(particle)

            label = DraggableLabel(x, y, name, particle_height, self)  # Pass 'self' as analyzer
            label.signals.deleteRequested.connect(self.delete_particle)
            label.setPos(label_pos)
            self.scene.addItem(label)

            line = QGraphicsLineItem()
            line.setPen(QPen(QColor(0, 0, 0), 1, Qt.DashLine))
            self.scene.addItem(line)
            label.setData(0, line)
            self.scene.update_connection_line(label)
    def delete_particle(self, label):
        for i, (px, py, _, _, _) in enumerate(self.particles):
            if abs(label.x - px) < 10 and abs(label.y - py) < 10:
                del self.particles[i]
                self.draw_particles()
                break

if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = CapillaryAnalyzer()
    window.show()
    sys.exit(app.exec_())

"""
Custom widgets for PHASe application
"""
from PyQt5.QtCore import (Qt, QSize, QPropertyAnimation, QEasingCurve, pyqtProperty, pyqtSignal, QRectF)
from PyQt5.QtGui import QPainter, QColor, QPen, QPixmap, QIcon, QFont
from PyQt5.QtWidgets import (QPushButton, QSlider, QWidget, QSizePolicy, QStyleOptionSlider, QStyle)
from PyQt5.QtSvg import QSvgRenderer
from utils.helpers import absolute_path
from config.constants import BUTTON_STYLE


class ModernButton(QPushButton):
    """Styled button with icon and modern appearance"""

    def __init__(self, icon_path, text, parent=None):
        super().__init__(parent)
        self.setText(text)
        self.setIcon(QIcon(absolute_path(icon_path)))
        self.setIconSize(QSize(32, 32))
        self.setCursor(Qt.PointingHandCursor)
        self.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        self.setStyleSheet(BUTTON_STYLE)

    def sizeHint(self):
        return QSize(120, 60)


class CoolModeSwitch(QWidget):
    """Animated toggle switch between pan and particle modes"""

    toggled = pyqtSignal(bool)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setFixedSize(100, 40)
        self._is_particle_mode = True
        self._handle_position = 60.0
        self._icon_to_draw = 'particle'

        # Load icons
        self.pan_icon = QPixmap(absolute_path("assets/pan_icon.svg")).scaled(
            30, 30, Qt.KeepAspectRatio, Qt.SmoothTransformation)
        self.particle_icon = QPixmap(absolute_path("assets/particle_icon.svg")).scaled(
            30, 30, Qt.KeepAspectRatio, Qt.SmoothTransformation)

        self.animation = QPropertyAnimation(self, b"handle_position", self)
        self.animation.setEasingCurve(QEasingCurve.InOutExpo)
        self.animation.setDuration(300)
        self.animation.finished.connect(self.animation_finished)

    @pyqtProperty(float)
    def handle_position(self):
        return self._handle_position

    @handle_position.setter
    def handle_position(self, pos):
        self._handle_position = pos
        self.update()

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)

        # Draw background
        painter.setPen(Qt.NoPen)
        painter.setBrush(QColor(52, 73, 94))
        painter.drawRoundedRect(0, 0, self.width(), self.height(), 20, 20)

        # Draw icons
        painter.drawPixmap(10, 5, self.pan_icon)
        painter.drawPixmap(60, 5, self.particle_icon)

        # Draw sliding handle
        painter.setBrush(QColor(41, 128, 185))
        handle_rect = QRectF(self._handle_position, 0, 40, 40)
        painter.drawRoundedRect(handle_rect, 20, 20)

        # Draw icon on handle
        handle_icon_x = int(self._handle_position) + 5
        if self._icon_to_draw == 'particle':
            painter.drawPixmap(handle_icon_x, 5, self.particle_icon)
        else:
            painter.drawPixmap(handle_icon_x, 5, self.pan_icon)

    def mousePressEvent(self, event):
        if event.button() == Qt.LeftButton:
            self.toggle()
            event.accept()

    def toggle(self):
        self._is_particle_mode = not self._is_particle_mode
        target_pos = 60 if self._is_particle_mode else 0
        self.animation.setStartValue(self._handle_position)
        self.animation.setEndValue(target_pos)
        self.animation.start()

    def animation_finished(self):
        self._icon_to_draw = 'particle' if self._is_particle_mode else 'pan'
        self.update()
        self.toggled.emit(self._is_particle_mode)


class ZoomSlider(QSlider):
    """Vertical zoom slider with percentage display"""

    def __init__(self, parent=None):
        super().__init__(Qt.Vertical, parent)
        self.setRange(10, 400)  # 10% to 400% zoom
        self.setValue(100)  # Start at 100% zoom
        self.setTickPosition(QSlider.TicksRight)
        self.setTickInterval(50)
        self.setStyleSheet("""
            QSlider::groove:vertical {
                background: #34495e;
                width: 10px;
                border-radius: 5px;
            }
            QSlider::handle:vertical {
                background: #3498db;
                height: 20px;
                width: 20px;
                margin: 0 -5px;
                border-radius: 10px;
            }
            QSlider::add-page:vertical {
                background: #2c3e50;
            }
            QSlider::sub-page:vertical {
                background: #3498db;
            }
        """)

    def paintEvent(self, event):
        super().paintEvent(event)
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)

        opt = QStyleOptionSlider()
        self.initStyleOption(opt)

        # Draw zoom percentage text
        font = painter.font()
        font.setPointSize(8)
        painter.setFont(font)
        painter.setPen(Qt.white)
        zoom = self.value()
        rect = self.style().subControlRect(QStyle.CC_Slider, opt, QStyle.SC_SliderHandle, self)
        painter.drawText(rect, Qt.AlignCenter, f"{zoom}%")


class ScrollWheel(QWidget):
    """Custom scroll wheel widget for precise angle control"""

    valueChanged = pyqtSignal(float)

    def __init__(self, parent=None, is_fine=False):
        super().__init__(parent)
        self.value = 0
        self.min_value = -90
        self.max_value = 90
        self.setFixedSize(40, 100)
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

"""
Dialog components for PHASe application
"""
import platform
import random
import math
from PyQt5.QtCore import (Qt, QPoint, QPointF, QTimer, QPropertyAnimation,
                          QEasingCurve, QParallelAnimationGroup, QEventLoop)
from PyQt5.QtGui import (QPainter, QColor, QPen, QPixmap, QFont,
                         QFontDatabase, QRadialGradient, QTransform)
from PyQt5.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QLabel,
                             QPushButton, QGraphicsOpacityEffect, QGraphicsDropShadowEffect)
from PyQt5.QtSvg import QSvgRenderer
from utils.helpers import absolute_path
from config.constants import CURRENT_VERSION, CURRENT_VERSION_NAME


class AboutDialog(QWidget):
    """About dialog with animated elements"""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowFlags(Qt.FramelessWindowHint | Qt.Dialog)
        self.setAttribute(Qt.WA_TranslucentBackground)

        self.content = QWidget(self)
        self.content.setStyleSheet("background-color: rgba(20, 20, 30, 240); border-radius: 20px;")
        self.content.setFixedSize(500, 600)

        layout = QVBoxLayout(self.content)
        layout.setContentsMargins(40, 40, 40, 40)

        # Load custom font
        QFontDatabase.addApplicationFont(absolute_path("assets/Roboto-Light.ttf"))

        # Logo
        logo_label = QLabel()
        logo_pixmap = QPixmap(absolute_path("assets/phase_logo_v3.svg"))
        logo_label.setPixmap(logo_pixmap.scaled(200, 200, Qt.KeepAspectRatio, Qt.SmoothTransformation))
        logo_label.setAlignment(Qt.AlignCenter)
        layout.addWidget(logo_label)

        # About text
        about_text = f"""
        <h2 style='color: #e0e0e0; text-align: center; font-family: "Roboto Light", sans-serif;'>PHASe</h2>
        <h3 style='color: #3498db; text-align: center; font-family: "Roboto Light", sans-serif;'>Particle Height Analysis Software</h3>
        <p style='color: #b0b0b0; text-align: center; font-family: "Roboto Light", sans-serif;'>Version: {CURRENT_VERSION} ({CURRENT_VERSION_NAME})</p>
        <p style='color: #b0b0b0; text-align: center; font-family: "Roboto Light", sans-serif;'>PHASe is an open source tool for measuring particle heights in imaged capillary systems.</p>
        <p style='color: #b0b0b0; text-align: center; font-family: "Roboto Light", sans-serif;'>Developed by: Alfa Ozaltin @ VX Software</p>
        <p style='color: #808080; text-align: center; font-family: "Roboto Light", sans-serif;'>Current Platform: {"MacOS (Darwin)" if platform.system() == "Darwin" else f"{platform.system()}"} {platform.release()}</p>
        """
        self.about_label = QLabel(about_text)
        self.about_label.setWordWrap(True)
        self.about_label.setStyleSheet("font-size: 16px;")
        layout.addWidget(self.about_label)

        # VX Logo
        vx_logo = QLabel()
        vx_logo_pixmap = QPixmap(absolute_path("assets/vx_logo.svg"))
        vx_logo.setPixmap(vx_logo_pixmap.scaled(140, 56, Qt.KeepAspectRatio, Qt.SmoothTransformation))
        vx_logo.setAlignment(Qt.AlignCenter)
        layout.addWidget(vx_logo)

        layout.addStretch(1)

        self.content_layout = QVBoxLayout(self)
        self.content_layout.addWidget(self.content, alignment=Qt.AlignCenter)

        # Add subtle glow effect
        glow = QGraphicsDropShadowEffect()
        glow.setColor(QColor(52, 152, 219, 75))
        glow.setBlurRadius(40)
        glow.setOffset(0)
        self.content.setGraphicsEffect(glow)

        self.animation = QParallelAnimationGroup()
        self.fade_in_animation = QPropertyAnimation(self, b"windowOpacity")
        self.fade_in_animation.setStartValue(0.0)
        self.fade_in_animation.setEndValue(1.0)
        self.fade_in_animation.setDuration(600)
        self.animation.addAnimation(self.fade_in_animation)

        self.content_animation = QPropertyAnimation(self.content, b"geometry")
        self.content_animation.setDuration(600)
        self.content_animation.setEasingCurve(QEasingCurve.OutQuint)
        self.animation.addAnimation(self.content_animation)

        self.frog_timer = QTimer(self)
        self.frog_timer.timeout.connect(self.levitate_frog)
        self.frog_timer.start(12000)

        # Load SVG frog
        self.frog_svg = QSvgRenderer(absolute_path("assets/tf.svg"))
        self.frog_pixmap = QPixmap(30, 30)
        self.frog_pixmap.fill(Qt.transparent)
        painter = QPainter(self.frog_pixmap)
        self.frog_svg.render(painter)
        painter.end()

        self.frog_label = QLabel(self)
        self.frog_label.setFixedSize(30, 30)
        self.frog_label.hide()

        # Frog rotation animation
        self.rotation_anim = QPropertyAnimation(self, b"frogRotation")
        self.rotation_anim.setDuration(2000)  # 2 seconds for a full rotation
        self.rotation_anim.setStartValue(0)
        self.rotation_anim.setEndValue(360)
        self.rotation_anim.setLoopCount(-1)  # Infinite loop
        self.rotation_anim.valueChanged.connect(self.rotateFrog)

    def levitate_frog(self):
        """Animate a flying frog across the dialog"""
        if random.random() < 1.0:
            start_x = -30
            end_x = self.width() + 30
            y = random.randint(50, self.height() - 50)

            self.frog_label.move(start_x, y)
            self.frog_label.show()

            self.frog_anim = QPropertyAnimation(self.frog_label, b"pos")
            self.frog_anim.setDuration(5000)
            self.frog_anim.setStartValue(QPoint(start_x, y))
            self.frog_anim.setEndValue(QPoint(end_x, y))
            self.frog_anim.setEasingCurve(QEasingCurve.InOutSine)
            self.frog_anim.finished.connect(self.frog_label.hide)
            self.frog_anim.finished.connect(self.rotation_anim.stop)
            self.frog_anim.start()

            self.rotation_anim.start()

    def rotateFrog(self, angle):
        """Rotate and scale the frog for 3D effect"""
        transform = QTransform()
        transform.rotate(angle)
        scale = 0.5 + abs(math.sin(math.radians(angle))) * 0.5
        transform.scale(scale, 1.0)

        rotated_pixmap = self.frog_pixmap.transformed(transform, Qt.SmoothTransformation)

        # Center the rotated pixmap
        centered_pixmap = QPixmap(30, 30)
        centered_pixmap.fill(Qt.transparent)
        painter = QPainter(centered_pixmap)
        painter.drawPixmap(QPointF((30 - rotated_pixmap.width()) / 2, 
                                   (30 - rotated_pixmap.height()) / 2),
                           rotated_pixmap)
        painter.end()

        self.frog_label.setPixmap(centered_pixmap)

    def showEvent(self, event):
        """Handle show event with animations"""
        super().showEvent(event)
        start_rect = self.content.geometry()
        start_rect.moveCenter(self.rect().center() + QPoint(0, 50))
        end_rect = self.content.geometry()
        end_rect.moveCenter(self.rect().center())

        self.content_animation.setStartValue(start_rect)
        self.content_animation.setEndValue(end_rect)
        self.animation.start()

    def paintEvent(self, event):
        """Paint the dialog background"""
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)

        # Draw background gradient
        gradient = QRadialGradient(self.rect().center(), max(self.width(), self.height()) / 2)
        gradient.setColorAt(0, QColor(25, 25, 35))
        gradient.setColorAt(1, QColor(15, 15, 25))
        painter.fillRect(self.rect(), gradient)

    def mousePressEvent(self, event):
        """Close dialog when clicking outside content area"""
        if event.button() == Qt.LeftButton:
            if not self.content.geometry().contains(event.pos()):
                self.close()


class TourGuide(QWidget):
    """Interactive tour guide widget"""

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

        self.setFixedWidth(420)

        self.opacity_effect = QGraphicsOpacityEffect()
        self.setGraphicsEffect(self.opacity_effect)

        self.arrow = QLabel("▲")  # Unicode up arrow
        self.arrow.setStyleSheet("""
            color: rgba(52, 73, 94, 220);
            font-size: 16px;
        """)
        self.layout.insertWidget(0, self.arrow, 0, Qt.AlignCenter)

        self.opacity_animation = QPropertyAnimation(self.opacity_effect, b"opacity")
        self.opacity_animation.setDuration(150)
        self.opacity_animation.setStartValue(0)
        self.opacity_animation.setEndValue(1)
        self.opacity_animation.setEasingCurve(QEasingCurve.InOutQuad)

    def show_message(self, message, target_widget, custom_pos=None):
        """Show a message with optional target widget highlighting"""
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
        """Get the position relative to target widget"""
        if target_widget:
            target_rect = target_widget.rect()
            target_pos = target_widget.mapToGlobal(target_rect.topRight())
            return self.parent().mapFromGlobal(target_pos + QPoint(10, 0))
        return self.parent().rect().center() - self.rect().center()

    def adjust_position(self, pos):
        """Adjust position to keep dialog within parent bounds"""
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
        """Paint the tour guide border"""
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)
        painter.setBrush(Qt.transparent)
        painter.setPen(QPen(QColor(52, 152, 219), 2))
        painter.drawRoundedRect(self.rect(), 10, 10)
        super().paintEvent(event)


class ToastNotification(QWidget):
    """Toast notification widget for user feedback"""

    def __init__(self, parent, title, message, buttons=None, timeout=5000):
        super().__init__(parent)
        self.parent = parent
        self.timeout = timeout

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
                button.clicked.connect(lambda checked, text=button_text: self.button_clicked(text))
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

        self.response = None
        self.event_loop = None

    def showEvent(self, event):
        """Handle show event with fade in animation"""
        super().showEvent(event)
        self.fade_in_animation.start()
        self.timer.start(self.timeout)

    def fade_out(self):
        """Start fade out animation"""
        self.fade_out_animation.start()

    def paintEvent(self, event):
        """Paint the toast background"""
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)

        # Draw rounded rectangle
        painter.setBrush(QColor(44, 62, 80, 230))
        painter.setPen(Qt.NoPen)
        painter.drawRoundedRect(self.rect(), 10, 10)

        super().paintEvent(event)

    def get_response(self):
        """Get user response from button click"""
        self.event_loop = QEventLoop()
        self.event_loop.exec_()
        return self.response

    def button_clicked(self, text):
        """Handle button click"""
        self.response = text
        if self.event_loop:
            self.event_loop.quit()
        self.fade_out()

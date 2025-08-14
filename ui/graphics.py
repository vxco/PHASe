"""
Graphics components for PHASe application
"""
from PyQt5.QtCore import (Qt, QPointF, QRectF, QLineF, pyqtSignal,
                          QObject, QTimer)
from PyQt5.QtGui import QPainter, QColor, QPen, QFont
from PyQt5.QtWidgets import (QGraphicsView, QGraphicsScene, QGraphicsItemGroup,
                             QGraphicsTextItem, QGraphicsRectItem, QGraphicsItem,
                             QMenu, QInputDialog, QWidget)
from core.models import Particle


class DraggableLabelSignals(QObject):
    """Signals for draggable label interactions"""
    deleteRequested = pyqtSignal(object)
    moved = pyqtSignal(object)


class DraggableLabel(QGraphicsItemGroup):
    """Draggable label for particle annotations"""

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
        self.notes = ""
        self.create_label()

    def create_label(self):
        """Create the visual label components"""
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
        total_width = max(text_width + delete_button_size + padding * 2, 100)
        total_height = max(text_height, delete_button_size) + padding * 2

        # Background
        background = QGraphicsRectItem(0, 0, total_width, total_height)
        background.setBrush(QColor(60, 60, 60, 220))
        background.setPen(QPen(QColor(100, 100, 100), 1))

        # Position label text
        label.setPos(QPointF(padding, padding))

        # Delete button
        delete_button = QGraphicsRectItem(
            total_width - delete_button_size - padding, padding,
            delete_button_size, delete_button_size
        )
        delete_button.setBrush(QColor(200, 60, 60))
        delete_button.setPen(QPen(QColor(220, 80, 80), 1))
        delete_button.setFlag(QGraphicsItem.ItemIsSelectable)

        # Delete cross
        delete_cross = QGraphicsTextItem('×')
        delete_cross.setFont(QFont("Arial", delete_button_size - 4, QFont.Bold))
        delete_cross.setDefaultTextColor(QColor(255, 255, 255))

        cross_rect = delete_cross.boundingRect()
        cross_x = delete_button.rect().x() + (delete_button_size - cross_rect.width()) / 2
        cross_y = delete_button.rect().y() + (delete_button_size - cross_rect.height()) / 2
        delete_cross.setPos(cross_x, cross_y)

        # Add all components to group
        self.addToGroup(background)
        self.addToGroup(label)
        self.addToGroup(delete_button)
        self.addToGroup(delete_cross)
        self.delete_button = delete_button

        # Apply scale and position
        scale_factor = 1 / self.analyzer.scale_factor
        self.setScale(scale_factor)
        self.setPos(self.x + 10 / scale_factor, self.y - total_height * scale_factor - 10 / scale_factor)

    def get_label_text(self):
        """Get formatted label text"""
        if self.name:
            return f"{self.name}: {self.height:.2f} µm"
        else:
            return f"{self.height:.2f} µm"

    def update_height(self, new_height):
        """Update the displayed height"""
        self.height = new_height
        self.update_label_text()
        self.analyzer.set_unsaved_changes()

    def update_label_text(self):
        """Update the label text and resize components"""
        label_text = self.get_label_text()
        text_item = self.childItems()[1]
        text_item.setPlainText(label_text)

        # Recalculate size
        text_width = text_item.boundingRect().width()
        text_height = text_item.boundingRect().height()
        padding = 8
        delete_button_size = 20
        total_width = max(text_width + delete_button_size + padding * 2, 100)
        total_height = max(text_height, delete_button_size) + padding * 2

        # Update background rectangle
        background = self.childItems()[0]
        background.setRect(0, 0, total_width, total_height)

        # Update delete button position
        delete_button = self.childItems()[2]
        delete_button.setRect(total_width - delete_button_size - padding, padding, 
                             delete_button_size, delete_button_size)

        # Update delete cross position
        delete_cross = self.childItems()[3]
        cross_rect = delete_cross.boundingRect()
        cross_x = delete_button.rect().x() + (delete_button_size - cross_rect.width()) / 2
        cross_y = delete_button.rect().y() + (delete_button_size - cross_rect.height()) / 2
        delete_cross.setPos(cross_x, cross_y)
        self.analyzer.set_unsaved_changes()

    def mousePressEvent(self, event):
        """Handle mouse press events"""
        if event.button() == Qt.RightButton:
            self.show_context_menu(event.screenPos())
        elif self.delete_button and self.delete_button.contains(event.pos()):
            self.signals.deleteRequested.emit(self)
        else:
            super().mousePressEvent(event)

    def show_context_menu(self, pos):
        """Show context menu for particle operations"""
        menu = QMenu()
        rename_action = menu.addAction("Rename")
        delete_action = menu.addAction("Delete")
        
        action = menu.exec_(pos)
        if action == rename_action:
            self.rename()
        elif action == delete_action:
            self.signals.deleteRequested.emit(self)

    def rename(self):
        """Handle particle renaming"""
        text, ok = QInputDialog.getText(None, "Rename Particle", "Enter new name:", text=self.name or "")
        if ok:
            self.name = text if text else ''
            self.update_label_text()
            # Note: The analyzer should handle updating the workspace data

    def itemChange(self, change, value):
        """Handle item position changes"""
        if change == QGraphicsItemGroup.ItemPositionHasChanged:
            self.signals.moved.emit(self)
        return super().itemChange(change, value)


class Minimap(QWidget):
    """Minimap widget for navigation"""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setFixedSize(200, 100)
        self.view_rect = QRectF()
        self.full_rect = QRectF()
        self.pixmap = None
        self.dragging = False
        self.drag_start = QPointF()
        self.view_rect_start = QRectF()
        self.hide()

    def set_pixmap(self, pixmap):
        """Set the minimap background image"""
        self.pixmap = pixmap.scaled(self.size(), Qt.KeepAspectRatio, Qt.SmoothTransformation)
        self.update()

    def update_rects(self, view_rect, full_rect):
        """Update view and full rectangles"""
        if full_rect.isNull() or full_rect.isEmpty():
            self.view_rect = QRectF()
            self.full_rect = QRectF()
        else:
            self.view_rect = self.map_rect_to_minimap(view_rect, full_rect)
            self.full_rect = full_rect
        self.update()

    def map_rect_to_minimap(self, rect, full_rect):
        """Map a rectangle to minimap coordinates"""
        if full_rect.width() == 0 or full_rect.height() == 0:
            return QRectF()
        x_ratio = self.width() / full_rect.width()
        y_ratio = self.height() / full_rect.height()
        return QRectF(
            (rect.x() - full_rect.x()) * x_ratio,
            (rect.y() - full_rect.y()) * y_ratio,
            rect.width() * x_ratio,
            rect.height() * y_ratio
        )

    def mousePressEvent(self, event):
        """Handle mouse press for navigation"""
        if event.button() == Qt.LeftButton:
            if self.view_rect.contains(event.pos()):
                self.dragging = True
                self.drag_start = event.pos()
                self.view_rect_start = self.view_rect
            else:
                self.move_view(event.pos())

    def mouseMoveEvent(self, event):
        """Handle mouse drag for navigation"""
        if self.dragging:
            delta = event.pos() - self.drag_start
            new_view_rect = self.view_rect_start.translated(delta)

            # Constrain within minimap bounds
            if new_view_rect.left() < 0:
                new_view_rect.moveLeft(0)
            if new_view_rect.right() > self.width():
                new_view_rect.moveRight(self.width())
            if new_view_rect.top() < 0:
                new_view_rect.moveTop(0)
            if new_view_rect.bottom() > self.height():
                new_view_rect.moveBottom(self.height())

            self.move_view(new_view_rect.center())

    def mouseReleaseEvent(self, event):
        """Handle mouse release"""
        if event.button() == Qt.LeftButton:
            self.dragging = False

    def move_view(self, pos):
        """Move the main view to the specified position"""
        if self.full_rect.isNull():
            return
        x_ratio = self.full_rect.width() / self.width()
        y_ratio = self.full_rect.height() / self.height()
        new_center = QPointF(pos.x() * x_ratio + self.full_rect.x(),
                             pos.y() * y_ratio + self.full_rect.y())
        self.parent().center_on(new_center)

    def paintEvent(self, event):
        """Paint the minimap"""
        if self.pixmap is None:
            return

        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)

        # Draw background image
        painter.drawPixmap(self.rect(), self.pixmap)

        # Draw semi-transparent overlay
        painter.fillRect(self.rect(), QColor(52, 73, 94, 100))

        # Draw full image area outline
        painter.setPen(QPen(Qt.white, 1))
        painter.drawRect(self.rect().adjusted(1, 1, -1, -1))

        # Draw view area
        if not self.full_rect.isNull():
            painter.fillRect(self.view_rect, QColor(52, 152, 219, 120))
            painter.setPen(QPen(Qt.white, 2))
            painter.drawRect(self.view_rect)


class CustomGraphicsView(QGraphicsView):
    """Custom graphics view with zoom, pan, and minimap functionality"""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setRenderHints(QPainter.Antialiasing | QPainter.SmoothPixmapTransform)
        self.setTransformationAnchor(QGraphicsView.AnchorUnderMouse)
        self.setResizeAnchor(QGraphicsView.AnchorUnderMouse)
        self.setVerticalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self.setDragMode(QGraphicsView.NoDrag)
        self.setViewportUpdateMode(QGraphicsView.FullViewportUpdate)

        # Initialize minimap placeholder
        self.minimap = None
        self.panning_enabled = True
        self.last_pan_pos = None

    def setPanningEnabled(self, enabled):
        """Enable or disable panning"""
        self.panning_enabled = enabled

    def resizeEvent(self, event):
        """Handle resize events"""
        super().resizeEvent(event)
        self.position_widgets()

    def position_widgets(self):
        """Position child widgets like minimap and zoom controls"""
        # Placeholder for widget positioning
        pass

    def update_minimap(self):
        """Update minimap display"""
        # Placeholder for minimap update
        pass

    def set_image(self, pixmap):
        """Set the background image"""
        # Placeholder for image setting
        pass

    def center_on(self, pos):
        """Center view on specified position"""
        self.centerOn(pos)
        self.update_minimap()

    def mousePressEvent(self, event):
        """Handle mouse press for panning"""
        if event.button() == Qt.LeftButton and self.panning_enabled:
            self.setCursor(Qt.ClosedHandCursor)
            self.last_pan_pos = event.pos()
        super().mousePressEvent(event)

    def mouseMoveEvent(self, event):
        """Handle mouse move for panning"""
        if event.buttons() == Qt.LeftButton and self.last_pan_pos and self.panning_enabled:
            delta = event.pos() - self.last_pan_pos
            self.horizontalScrollBar().setValue(self.horizontalScrollBar().value() - delta.x())
            self.verticalScrollBar().setValue(self.verticalScrollBar().value() - delta.y())
            self.last_pan_pos = event.pos()
            self.update_minimap()
        super().mouseMoveEvent(event)

    def mouseReleaseEvent(self, event):
        """Handle mouse release"""
        if event.button() == Qt.LeftButton:
            self.setCursor(Qt.ArrowCursor)
            self.last_pan_pos = None
        super().mouseReleaseEvent(event)


class CustomGraphicsScene(QGraphicsScene):
    """Custom graphics scene for PHASe"""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.parent = parent

    def update_connection_lines(self):
        """Update connection lines between particles and labels"""
        if hasattr(self.parent, 'particles'):
            for particle in self.parent.particles:
                if 'label_item' in particle and 'line_item' in particle:
                    label = particle['label_item']
                    line = particle['line_item']
                    start = QPointF(particle['x'], particle['y'])
                    end = label.sceneBoundingRect().center()
                    line.setLine(QLineF(start, end))
                    if hasattr(self.parent, 'set_unsaved_changes'):
                        self.parent.set_unsaved_changes()

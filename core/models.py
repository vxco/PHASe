"""
Data models for PHASe application particles and workspace
"""
import pickle
import base64
from PyQt5.QtCore import QPointF, QObject, pyqtSignal, QByteArray, QBuffer
from PyQt5.QtGui import QImage
from utils.helpers import calculate_height


class Particle:
    """Represents a single particle with position, name, height, and metadata"""

    def __init__(self, x, y, name="", height=0, notes=""):
        self.x = x
        self.y = y
        self.name = name
        self.height = height
        self.notes = notes
        self.label_pos = QPointF(x + 10, y - 60)

    def update_height(self, capillary_height, ceiling_y, floor_y, angle_degrees, wall_thickness=0):
        """Recalculate height based on capillary parameters"""
        self.height = calculate_height(
            self.x, self.y, capillary_height, ceiling_y, floor_y, angle_degrees, wall_thickness
        )

    def to_dict(self):
        """Convert particle to dictionary for serialization"""
        return {
            'x': self.x,
            'y': self.y,
            'name': self.name,
            'height': self.height,
            'notes': self.notes,
            'label_pos': (self.label_pos.x(), self.label_pos.y())
        }

    @classmethod
    def from_dict(cls, data):
        """Create particle from dictionary"""
        particle = cls(
            data['x'], data['y'],
            data.get('name', ''),
            data.get('height', 0),
            data.get('notes', '')
        )
        if 'label_pos' in data:
            particle.label_pos = QPointF(data['label_pos'][0], data['label_pos'][1])
        return particle


class WorkspaceManager(QObject):
    """Manages workspace data including particles, settings, and image"""

    workspace_changed = pyqtSignal()

    def __init__(self):
        super().__init__()
        self.reset()

    def reset(self):
        """Reset workspace to initial state"""
        self.name = "Untitled Workspace"
        self.particles = []
        self.capillary_height = None
        self.ceiling_y = None
        self.floor_y = None
        self.angle_value = 0.0
        self.wall_thickness = 0.0
        self.used_names = set()
        self.original_image = None
        self.unsaved_changes = False
        self.current_file = None

    def add_particle(self, particle):
        """Add a particle to the workspace"""
        self.particles.append(particle)
        if particle.name:
            self.used_names.add(particle.name)
        self.unsaved_changes = True
        self.workspace_changed.emit()

    def remove_particle(self, particle):
        """Remove a particle from the workspace"""
        if particle in self.particles:
            self.particles.remove(particle)
            self.unsaved_changes = True
            self.workspace_changed.emit()

    def update_all_particle_heights(self):
        """Recalculate heights for all particles"""
        for particle in self.particles:
            particle.update_height(
                self.capillary_height, self.ceiling_y, self.floor_y,
                self.angle_value, self.wall_thickness
            )
        self.unsaved_changes = True
        self.workspace_changed.emit()

    def set_image(self, image):
        """Set the workspace image"""
        self.original_image = image
        self.unsaved_changes = True
        self.workspace_changed.emit()

    def set_capillary_parameters(self, capillary_height=None, ceiling_y=None, floor_y=None,
                                angle_value=None, wall_thickness=None):
        """Update capillary parameters"""
        if capillary_height is not None:
            self.capillary_height = capillary_height
        if ceiling_y is not None:
            self.ceiling_y = ceiling_y
        if floor_y is not None:
            self.floor_y = floor_y
        if angle_value is not None:
            self.angle_value = angle_value
        if wall_thickness is not None:
            self.wall_thickness = wall_thickness

        self.update_all_particle_heights()
        self.unsaved_changes = True
        self.workspace_changed.emit()

    def save_workspace(self, file_path):
        """Save workspace to file"""
        try:
            workspace_data = {
                'name': self.name,
                'capillary_height': self.capillary_height,
                'ceiling_y': self.ceiling_y,
                'floor_y': self.floor_y,
                'angle_value': self.angle_value,
                'wall_thickness': self.wall_thickness,
                'particles': [particle.to_dict() for particle in self.particles],
                'used_names': list(self.used_names)
            }

            if self.original_image:
                buffer = QBuffer()
                buffer.open(QBuffer.ReadWrite)
                self.original_image.save(buffer, "PNG")
                workspace_data['image'] = base64.b64encode(buffer.data()).decode()

            with open(file_path, 'wb') as f:
                pickle.dump(workspace_data, f, protocol=pickle.HIGHEST_PROTOCOL)

            self.current_file = file_path
            self.unsaved_changes = False
            return True

        except Exception as e:
            raise Exception(f"Error saving workspace: {str(e)}")

    def load_workspace(self, file_path):
        """Load workspace from file"""
        try:
            with open(file_path, 'rb') as f:
                workspace_data = pickle.load(f)

            self.name = workspace_data.get('name', 'Untitled Workspace')
            self.capillary_height = workspace_data.get('capillary_height')
            self.ceiling_y = workspace_data.get('ceiling_y')
            self.floor_y = workspace_data.get('floor_y')
            self.angle_value = workspace_data.get('angle_value', 0)
            self.wall_thickness = workspace_data.get('wall_thickness', 0)
            self.used_names = set(workspace_data.get('used_names', []))

            # Load particles
            self.particles = []
            for particle_data in workspace_data.get('particles', []):
                particle = Particle.from_dict(particle_data)
                self.particles.append(particle)

            # Load image
            if 'image' in workspace_data:
                image_data = base64.b64decode(workspace_data['image'])
                self.original_image = QImage.fromData(QByteArray(image_data))

            self.current_file = file_path
            self.unsaved_changes = False
            self.workspace_changed.emit()
            return True

        except Exception as e:
            raise Exception(f"Error loading workspace: {str(e)}")

    def export_csv(self, file_path):
        """Export particles to CSV file"""
        import csv
        try:
            with open(file_path, 'w', newline='') as csvfile:
                writer = csv.writer(csvfile)
                writer.writerow(['Name', 'Height (µm)', 'Notes'])
                for particle in self.particles:
                    writer.writerow([
                        particle.name,
                        f"{particle.height:.2f}",
                        particle.notes
                    ])
            return True
        except Exception as e:
            raise Exception(f"Error exporting CSV: {str(e)}")

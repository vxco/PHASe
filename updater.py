import os
import sys
import shutil
import subprocess
import tempfile
import zipfile
import platform
from urllib.request import urlretrieve

from PyQt5.QtWidgets import QApplication, QWidget, QVBoxLayout, QProgressBar, QLabel, QPushButton
from PyQt5.QtCore import Qt, QThread, pyqtSignal

class UpdaterThread(QThread):
    update_progress = pyqtSignal(int, str)
    update_finished = pyqtSignal(bool, str)

    def __init__(self, download_url, current_app_path):
        super().__init__()
        self.download_url = download_url
        self.current_app_path = current_app_path

    def run(self):
        try:
            # Download the update
            self.update_progress.emit(10, "Downloading update...")
            with tempfile.NamedTemporaryFile(delete=False, suffix='.zip') as tmp_file:
                urlretrieve(self.download_url, tmp_file.name)

            self.update_progress.emit(30, "Extracting update...")
            # Create a temporary directory for extraction
            with tempfile.TemporaryDirectory() as extract_dir:
                # Extract the downloaded zip
                with zipfile.ZipFile(tmp_file.name, 'r') as zip_ref:
                    zip_ref.extractall(extract_dir)

                self.update_progress.emit(50, "Installing update...")
                if platform.system() == 'Darwin':
                    self._update_macos(extract_dir)
                elif platform.system() == 'Windows':
                    self._update_windows(extract_dir)
                else:
                    raise Exception("Unsupported operating system")

            self.update_progress.emit(100, "Update completed successfully!")
            self.update_finished.emit(True, "Update completed successfully! Please restart the application.")

        except Exception as e:
            self.update_finished.emit(False, f"Error during update: {str(e)}")

        finally:
            # Clean up
            if 'tmp_file' in locals():
                os.unlink(tmp_file.name)

    def _update_macos(self, extract_dir):
        app_path = next((os.path.join(root, name)
                         for root, dirs, files in os.walk(extract_dir)
                         for name in dirs if name.endswith('.app')), None)
        if not app_path:
            raise Exception("Could not find .app in the downloaded update")

        current_app_dir = os.path.dirname(os.path.dirname(self.current_app_path))
        parent_dir = os.path.dirname(current_app_dir)
        app_name = os.path.basename(current_app_dir)
        new_app_path = os.path.join(parent_dir, f"{app_name}_new.app")

        if os.path.exists(current_app_dir):
            shutil.rmtree(current_app_dir)
        shutil.move(app_path, new_app_path)
        os.rename(new_app_path, current_app_dir)

        self.update_progress.emit(80, "Setting permissions...")
        subprocess.run(['xattr', '-rc', current_app_dir])
        subprocess.run(['chmod', '-R', '755', current_app_dir])

    def _update_windows(self, extract_dir):
        exe_path = next((os.path.join(root, name)
                         for root, dirs, files in os.walk(extract_dir)
                         for name in files if name.endswith('.exe')), None)
        if not exe_path:
            raise Exception("Could not find .exe in the downloaded update")

        current_dir = os.path.dirname(self.current_app_path)
        new_exe_path = os.path.join(current_dir, 'PHASe_new.exe')

        shutil.move(exe_path, new_exe_path)
        os.remove(self.current_app_path)
        os.rename(new_exe_path, self.current_app_path)

class UpdaterUI(QWidget):
    def __init__(self, download_url, current_app_path):
        super().__init__()
        self.download_url = download_url
        self.current_app_path = current_app_path
        self.init_ui()

    def init_ui(self):
        self.setWindowTitle('PHASe Updater')
        self.setGeometry(300, 300, 400, 150)
        self.setStyleSheet("""
            QWidget {
                background-color: #2c3e50;
                color: white;
            }
            QProgressBar {
                border: 2px solid #3498db;
                border-radius: 5px;
                text-align: center;
            }
            QProgressBar::chunk {
                background-color: #3498db;
            }
            QPushButton {
                background-color: #3498db;
                border: none;
                color: white;
                padding: 5px 15px;
                margin-top: 10px;
                border-radius: 5px;
            }
            QPushButton:hover {
                background-color: #2980b9;
            }
        """)

        layout = QVBoxLayout()

        self.status_label = QLabel('Preparing to update...')
        layout.addWidget(self.status_label)

        self.progress_bar = QProgressBar()
        layout.addWidget(self.progress_bar)

        self.close_button = QPushButton('Close')
        self.close_button.clicked.connect(self.close)
        self.close_button.hide()
        layout.addWidget(self.close_button)

        self.setLayout(layout)

        self.updater_thread = UpdaterThread(self.download_url, self.current_app_path)
        self.updater_thread.update_progress.connect(self.update_progress)
        self.updater_thread.update_finished.connect(self.update_finished)
        self.updater_thread.start()

    def update_progress(self, value, message):
        self.progress_bar.setValue(value)
        self.status_label.setText(message)

    def update_finished(self, success, message):
        self.status_label.setText(message)
        if success:
            self.progress_bar.setValue(100)
        else:
            self.progress_bar.setStyleSheet("""
                QProgressBar {
                    border: 2px solid #e74c3c;
                }
                QProgressBar::chunk {
                    background-color: #e74c3c;
                }
            """)
        self.close_button.show()

def run_updater(download_url, current_app_path):
    app = QApplication(sys.argv)
    updater = UpdaterUI(download_url, current_app_path)
    updater.show()
    sys.exit(app.exec_())

if __name__ == "__main__":
    if len(sys.argv) != 3:
        print("Usage: python updater.py <download_url> <current_app_path>")
        sys.exit(1)

    download_url = sys.argv[1]
    current_app_path = sys.argv[2]
    run_updater(download_url, current_app_path)

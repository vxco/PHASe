import sys
import os
import requests
import tempfile
import zipfile
import shutil
import subprocess
from PyQt5.QtWidgets import QApplication, QWidget, QVBoxLayout, QProgressBar, QLabel, QPushButton
from PyQt5.QtCore import Qt, QThread, pyqtSignal


class UpdaterThread(QThread):
    update_progress = pyqtSignal(int, str)
    update_finished = pyqtSignal(bool, str)

    def __init__(self, download_url, app_path):
        super().__init__()
        self.download_url = download_url
        self.app_path = app_path

    def run(self):
        try:
            # Download the update
            self.update_progress.emit(10, "Downloading update...")
            with tempfile.NamedTemporaryFile(delete=False, suffix='.zip') as tmp_file:
                response = requests.get(self.download_url, stream=True)
                total_size = int(response.headers.get('content-length', 0))
                block_size = 1024
                downloaded = 0
                for data in response.iter_content(block_size):
                    downloaded += len(data)
                    tmp_file.write(data)
                    if total_size:
                        percent = int((downloaded / total_size) * 20)
                        self.update_progress.emit(10 + percent, f"Downloading... {percent * 5}%")

            self.update_progress.emit(30, "Extracting update...")
            with tempfile.TemporaryDirectory() as extract_dir:
                with zipfile.ZipFile(tmp_file.name, 'r') as zip_ref:
                    zip_ref.extractall(extract_dir)

                self.update_progress.emit(50, "Installing update...")
                app_name = os.path.basename(self.app_path)
                new_app_path = os.path.join(extract_dir, app_name)

                if not os.path.exists(new_app_path):
                    raise Exception(f"Updated application not found in downloaded package: {new_app_path}")

                if os.path.exists(self.app_path):
                    shutil.rmtree(self.app_path)
                shutil.move(new_app_path, self.app_path)

            self.update_progress.emit(90, "Finalizing...")
            subprocess.run(['xattr', '-rc', self.app_path])
            subprocess.run(['chmod', '-R', '755', self.app_path])

            self.update_progress.emit(100, "Update completed successfully!")
            self.update_finished.emit(True, "Update completed successfully! Please restart the application.")

        except Exception as e:
            self.update_finished.emit(False, f"Error during update: {str(e)}")

        finally:
            if 'tmp_file' in locals():
                os.unlink(tmp_file.name)


class UpdaterUI(QWidget):
    def __init__(self, download_url, app_path):
        super().__init__()
        self.download_url = download_url
        self.app_path = app_path
        self.init_ui()

    def init_ui(self):
        self.setWindowTitle('PHASe Updater')
        self.setGeometry(300, 300, 400, 150)
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

        self.updater_thread = UpdaterThread(self.download_url, self.app_path)
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
            self.progress_bar.setStyleSheet("QProgressBar::chunk { background-color: red; }")
        self.close_button.show()


def main():
    if len(sys.argv) != 3:
        print("Usage: standalone_updater.py <download_url> <app_path>")
        sys.exit(1)

    app = QApplication(sys.argv)
    updater = UpdaterUI(sys.argv[1], sys.argv[2])
    updater.show()
    sys.exit(app.exec_())


if __name__ == "__main__":
    main()

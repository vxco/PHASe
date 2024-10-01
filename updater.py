"""Python pyinstaller bundled app updater by simitbey"""

import os
import sys
import shutil
import subprocess
import tempfile
import zipfile
import platform
from urllib.request import urlretrieve

def update_app(download_url, current_app_path):
    try:
        # Download the update
        with tempfile.NamedTemporaryFile(delete=False, suffix='.zip') as tmp_file:
            print("Downloading update...")
            urlretrieve(download_url, tmp_file.name)

        # Create a temporary directory for extraction
        with tempfile.TemporaryDirectory() as extract_dir:
            # Extract the downloaded zip
            print("Extracting update...")
            with zipfile.ZipFile(tmp_file.name, 'r') as zip_ref:
                zip_ref.extractall(extract_dir)

            if platform.system() == 'Darwin':
                # macOS update process
                app_path = next((os.path.join(root, name)
                                 for root, dirs, files in os.walk(extract_dir)
                                 for name in dirs if name.endswith('.app')), None)
                if not app_path:
                    raise Exception("Could not find .app in the downloaded update")

                current_app_dir = os.path.dirname(os.path.dirname(current_app_path))
                parent_dir = os.path.dirname(current_app_dir)
                app_name = os.path.basename(current_app_dir)
                new_app_path = os.path.join(parent_dir, f"{app_name}_new.app")

                print("Installing update...")
                if os.path.exists(current_app_dir):
                    shutil.rmtree(current_app_dir)
                shutil.move(app_path, new_app_path)
                os.rename(new_app_path, current_app_dir)

                print("Setting permissions...")
                subprocess.run(['xattr', '-rc', current_app_dir])
                subprocess.run(['chmod', '-R', '755', current_app_dir])

                print(f"Update completed successfully! Please restart {app_name}.")

            elif platform.system() == 'Windows':
                # Windows update process
                exe_path = next((os.path.join(root, name)
                                 for root, dirs, files in os.walk(extract_dir)
                                 for name in files if name.endswith('.exe')), None)
                if not exe_path:
                    raise Exception("Could not find .exe in the downloaded update")

                current_dir = os.path.dirname(current_app_path)
                new_exe_path = os.path.join(current_dir, 'PHASe_new.exe')

                print("Installing update...")
                shutil.move(exe_path, new_exe_path)
                os.remove(current_app_path)
                os.rename(new_exe_path, current_app_path)

                print("Update completed successfully! Please restart the application.")

            else:
                raise Exception("Unsupported operating system")

    except Exception as e:
        print(f"Error during update: {str(e)}")

    finally:
        # Clean up
        if 'tmp_file' in locals():
            os.unlink(tmp_file.name)

if __name__ == "__main__":
    if len(sys.argv) != 3:
        print("Usage: python updater.py <download_url> <current_app_path>")
        sys.exit(1)

    download_url = sys.argv[1]
    current_app_path = sys.argv[2]
    update_app(download_url, current_app_path)

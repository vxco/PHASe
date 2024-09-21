from setuptools import setup

APP = ['main.py']
DATA_FILES = []
OPTIONS = {'includes': ['sys', 'PyQt5.QtWidgets',
                        'PyQt5.QtGui', 'PyQt5.QtCore',]}

setup(
    app=APP,
    data_files=DATA_FILES,
    options={'py2app': OPTIONS},
    setup_requires=['py2app'],
)
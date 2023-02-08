import ctypes
import json
import logging
import os
import signal
import sys
import time
from importlib import reload

import psutil
from PyQt5 import uic, QtGui, QtCore
from PyQt5.QtWidgets import QApplication, QMainWindow, QMessageBox

import AudioHandler
import LectureBuilder
import WebinarHandler

WEBINAR_HACKER_VERSION = '1.0.0'

LOGGING_LEVEL = logging.INFO

SETTINGS_FILE = 'settings.json'


def logging_setup():
    """
    Sets up logging format and level
    :return:
    """
    logging.shutdown()
    reload(logging)
    logging.basicConfig(encoding='utf-8', format='%(asctime)s %(levelname)-8s %(message)s',
                        level=LOGGING_LEVEL,
                        datefmt='%Y-%m-%d %H:%M:%S')
    logging.info('logging setup is complete')


def load_json(file_name: str):
    """
    Loads json from file_name
    :return: json if loaded or None if not
    """
    try:
        logging.info('Loading ' + file_name + '...')
        file = open(file_name, encoding='utf-8')
        json_content = json.load(file)
        file.close()
        if json_content is not None and len(str(json_content)) > 0:
            logging.info('Loaded json: ' + str(json_content))
        else:
            json_content = None
            logging.error('Error loading json data from file ' + file_name)
    except Exception as e:
        json_content = None
        logging.error(e, exc_info=True)

    return json_content


def save_json(file_name: str, content):
    """
    Saves
    :param file_name: filename to save
    :param content: JSON dictionary
    :return:
    """
    logging.info('Saving to ' + file_name + '...')
    file = open(file_name, 'w')
    json.dump(content, file, indent=4)
    file.close()


def exit_(signum, frame):
    """
    Closes app
    :param signum:
    :param frame:
    :return:
    """
    logging.warning('Killing all threads...')
    current_system_pid = os.getpid()
    psutil.Process(current_system_pid).terminate()
    exit(0)


class Window(QMainWindow):
    stop_browser_and_recording = QtCore.pyqtSignal()  # QtCore.Signal()
    elements_set_enabled_signal = QtCore.pyqtSignal(bool)  # QtCore.Signal(bool)
    progress_bar_audio_signal = QtCore.pyqtSignal(int)  # QtCore.Signal(int)

    def __init__(self, settings_):
        super(Window, self).__init__()

        self.settings = settings_

        # Load GUI from file
        uic.loadUi('gui.ui', self)

        # Connect signals
        self.stop_browser_and_recording.connect(self.stop_browser)
        self.elements_set_enabled_signal.connect(self.elements_set_enabled)
        self.progress_bar_audio_signal.connect(self.progressBar_audio.setValue)

        # Initialize classes
        self.audio_handler = AudioHandler.AudioHandler(self.settings, self.progress_bar_audio_signal)
        self.webinar_handler = WebinarHandler.WebinarHandler(self.audio_handler, self.stop_browser_and_recording,
                                                             self.preview_label)
        self.lecture_builder = LectureBuilder.LectureBuilder(self.settings, self.elements_set_enabled_signal)

        # Set window title
        self.setWindowTitle('Webinar hacker ' + WEBINAR_HACKER_VERSION)

        # Set icon
        self.setWindowIcon(QtGui.QIcon('icon.png'))

        # Show GUI
        self.show()

        # Connect buttons
        self.btn_browser_open.clicked.connect(self.start_browser)
        self.btn_browser_stop.clicked.connect(self.stop_browser)
        self.btn_refresh.clicked.connect(self.lectures_refresh)
        self.btn_build.clicked.connect(self.lecture_build)

        # Set gui elements from settings
        self.line_edit_link.setText(str(self.settings['gui_link']))
        self.line_edit_name.setText(str(self.settings['gui_name']))
        self.line_edit_hello_message.setText(str(self.settings['gui_hello_message']))
        self.check_box_hello_message.setChecked(self.settings['gui_hello_message_enabled'])
        self.check_box_recording.setChecked(self.settings['gui_recording_enabled'])
        self.line_edit_proxy.setText(str(self.settings['gui_proxy']))
        self.slider_audio_threshold.setValue(int(self.settings['gui_audio_threshold_dbfs']))
        self.label_audio_threshold.setText(str(int(self.settings['gui_audio_threshold_dbfs'])) + ' dBFS')

        # Connect settings updater
        self.line_edit_link.textChanged.connect(self.update_settings)
        self.line_edit_name.textChanged.connect(self.update_settings)
        self.line_edit_hello_message.textChanged.connect(self.update_settings)
        self.check_box_hello_message.clicked.connect(self.update_settings)
        self.check_box_recording.clicked.connect(self.update_settings)
        self.line_edit_proxy.textChanged.connect(self.update_settings)
        self.slider_audio_threshold.valueChanged.connect(self.update_settings)

        # Refresh list of lectures
        self.lectures_refresh()

    def update_settings(self):
        """
        Saves gui fields to settings file
        :return:
        """
        # Read data from elements
        self.settings['gui_link'] = str(str(self.line_edit_link.text()))
        self.settings['gui_name'] = str(str(self.line_edit_name.text()))
        self.settings['gui_hello_message'] = str(str(self.line_edit_hello_message.text()))
        self.settings['gui_hello_message_enabled'] = self.check_box_hello_message.isChecked()
        self.settings['gui_recording_enabled'] = self.check_box_recording.isChecked()
        self.settings['gui_proxy'] = str(str(self.line_edit_proxy.text()))
        self.settings['gui_audio_threshold_dbfs'] = int(self.slider_audio_threshold.value())
        self.label_audio_threshold.setText(str(int(self.slider_audio_threshold.value())) + ' dBFS')

        # Save to file
        save_json(SETTINGS_FILE, self.settings)

    def lectures_refresh(self):
        """
        Searches for lectures
        :return:
        """
        logging.info('Refreshing list of lectures...')
        lectures = []
        self.combo_box_recordings.clear()
        recordings_dir = str(self.settings['recordings_directory_name']) + '/'
        if os.path.exists(recordings_dir):
            # List all dirs in recordings directory
            for recording_dir in os.listdir(recordings_dir):
                recording_dir_ = recording_dir
                recording_dir = os.path.join(recordings_dir, recording_dir)
                if os.path.isdir(recording_dir):
                    # List all dirs inside DD_MM_YYYY__HH_MM_SS folder
                    for audio_or_screenshot_dir in os.listdir(recording_dir):
                        audio_or_screenshot_dir = os.path.join(recording_dir, audio_or_screenshot_dir)
                        if os.path.isdir(audio_or_screenshot_dir):
                            for file_ in os.listdir(audio_or_screenshot_dir):
                                if str(file_).lower().endswith(AudioHandler.WAVE_FILE_EXTENSION):
                                    lectures.append(str(recording_dir_))
                                    self.combo_box_recordings.addItem(str(recording_dir_))
                                    break

        logging.info('Available lectures: ' + str(lectures))

    def lecture_build(self):
        """
        Starts building lecture
        :return:
        """
        selected_lecture = str(self.combo_box_recordings.currentText())
        logging.info('Selected lecture: ' + selected_lecture)
        if len(selected_lecture) > 0:
            # Disable all gui elements
            self.elements_set_enabled(False, False)

            # Start building lecture
            self.lecture_builder.start_building_lecture(str(self.settings['recordings_directory_name'])
                                                        + '/' + selected_lecture, selected_lecture)

    def start_browser(self):
        """
        Opens browser and starts recording
        :return:
        """
        link = str(self.settings['gui_link']).strip()
        user_name = str(self.settings['gui_name']).strip()
        hello_message = str(self.settings['gui_hello_message']) \
            .strip() if self.settings['gui_hello_message_enabled'] else ''
        proxy = str(self.settings['gui_proxy']).strip()

        # Check link and username
        if len(link) > 0:
            if len(user_name) > 0:
                # Open audio stream
                if self.settings['gui_recording_enabled']:
                    self.audio_handler.open_stream()

                # Disable form elements and start
                self.elements_set_enabled(False, True)
                self.webinar_handler.start_browser(link, proxy)
                self.webinar_handler.start_handler(user_name, hello_message,
                                                   float(self.settings['webinar_loop_interval_seconds']),
                                                   self.settings['gui_recording_enabled'],
                                                   int(self.settings['screenshot_diff_threshold_percents']),
                                                   int(self.settings['opencv_threshold']))
            else:
                QMessageBox.warning(self, 'No user name', 'Please type user name to connect with!')
        else:
            QMessageBox.warning(self, 'No link', 'Please type link to connect to!')

    def stop_browser(self):
        """
        Stops recording and closes browser
        :return:
        """
        # Stop recording
        self.audio_handler.recording_stop()

        # Close audio stream
        self.audio_handler.close_stream()

        # Close browser
        if self.webinar_handler.browser is not None:
            self.webinar_handler.stop_handler()
            self.webinar_handler.stop_browser()

        # Refresh lectures
        self.lectures_refresh()

        # Enable GUI elements
        self.elements_set_enabled(True, True)

    def elements_set_enabled(self, enabled: bool, browser=False):
        """
        Enables or disables gui elements
        :param enabled:
        :param browser: from browser or lecture builder
        :return:
        """
        logging.info('Enable gui elements? ' + str(enabled))
        self.line_edit_link.setEnabled(enabled)
        self.line_edit_name.setEnabled(enabled)
        self.line_edit_hello_message.setEnabled(enabled)
        self.check_box_hello_message.setEnabled(enabled)
        self.check_box_recording.setEnabled(enabled)
        self.line_edit_proxy.setEnabled(enabled)
        self.btn_browser_open.setEnabled(enabled)
        self.btn_browser_stop.setEnabled(not enabled if browser else False)
        self.combo_box_recordings.setEnabled(enabled)
        self.btn_refresh.setEnabled(enabled)
        self.btn_build.setEnabled(enabled)
        self.label_audio_threshold.setEnabled(True if browser else enabled)

        # Enable progress bar in lecture building mode
        if browser or enabled:
            self.progressBar.setMinimum(0)
            self.progressBar.setMaximum(100)
        else:
            self.progressBar.setMinimum(0)
            self.progressBar.setMaximum(0)

    def closeEvent(self, event):
        """
        Kills all threads
        :param event:
        :return:
        """
        # Stop recording
        self.audio_handler.recording_stop()

        # Close browser
        if self.webinar_handler.browser is not None:
            self.webinar_handler.stop_handler()
            self.webinar_handler.stop_browser()

        # Kill all threads
        exit_(None, None)

        # Accept event
        event.accept()


if __name__ == '__main__':
    # Initialize logging
    logging_setup()

    # Connect interrupt signal
    signal.signal(signal.SIGINT, exit_)

    # Load settings
    settings = load_json(SETTINGS_FILE)
    if settings is not None:
        # Replace icon in taskbar
        if os.name == 'nt':
            webinar_hacker_app_ip = 'f3rni.webinarhacker.webinarhacker.' + WEBINAR_HACKER_VERSION
            ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID(webinar_hacker_app_ip)

        # Start app
        app = QApplication.instance() or QApplication(sys.argv)
        app.setStyle('fusion')
        win = Window(settings)
        app.exec_()

    # Error loading settings file
    else:
        logging.error('Error loading ' + SETTINGS_FILE)
        exit_(None, None)

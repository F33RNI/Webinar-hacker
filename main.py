"""
 Copyright (C) 2022 Fern Lane, Webinar-hacker
 Licensed under the GNU Affero General Public License, Version 3.0 (the "License");
 you may not use this file except in compliance with the License.
 You may obtain a copy of the License at
       https://www.gnu.org/licenses/agpl-3.0.en.html
 Unless required by applicable law or agreed to in writing, software
 distributed under the License is distributed on an "AS IS" BASIS,
 WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
 See the License for the specific language governing permissions and
 limitations under the License.
 IN NO EVENT SHALL THE AUTHOR BE LIABLE FOR ANY CLAIM, DAMAGES OR
 OTHER LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE,
 ARISING FROM, OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR
 OTHER DEALINGS IN THE SOFTWARE.
"""

import ctypes
import json
import logging
import os
import signal
import sys

import psutil
from PyQt5 import uic, QtGui, QtCore
from PyQt5.QtWidgets import QApplication, QMainWindow, QMessageBox, QVBoxLayout, QLineEdit, QPushButton, QWidget, \
    QHBoxLayout

import AudioHandler
import LectureBuilder
import WebinarHandler

WEBINAR_HACKER_VERSION = 'beta_1.4.0'

LOGGING_LEVEL = logging.INFO

SETTINGS_FILE = 'settings.json'

STYLESHEET_FILE = 'stylesheet/Toolery.qss'


def logging_setup():
    """
    Sets up logging format and level
    :return:
    """
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
    progress_bar_set_value_signal = QtCore.pyqtSignal(int)  # QtCore.Signal(int)
    progress_bar_set_maximum_signal = QtCore.pyqtSignal(int)  # QtCore.Signal(int)
    lecture_building_done_signal = QtCore.pyqtSignal(str)  # QtCore.Signal(str)
    label_rec_set_stylesheet_signal = QtCore.pyqtSignal(str)  # QtCore.Signal(str)

    def __init__(self, settings_):
        super(Window, self).__init__()

        self.settings = settings_

        # Load GUI from file
        uic.loadUi('gui.ui', self)

        with open(STYLESHEET_FILE, 'r') as stylesheet_file:
            self.setStyleSheet(stylesheet_file.read())

        # Connect signals
        self.stop_browser_and_recording.connect(lambda: self.stop_browser(False))
        self.elements_set_enabled_signal.connect(self.elements_set_enabled)
        self.progress_bar_audio_signal.connect(self.progressBar_audio.setValue)
        self.progress_bar_set_value_signal.connect(self.progressBar.setValue)
        self.progress_bar_set_maximum_signal.connect(self.progressBar.setMaximum)
        self.lecture_building_done_signal.connect(self.lecture_building_done)
        self.label_rec_set_stylesheet_signal.connect(self.label_rec.setStyleSheet)

        # Initialize classes
        self.audio_handler = AudioHandler.AudioHandler(self.settings, self.progress_bar_audio_signal,
                                                       self.label_rec_set_stylesheet_signal)
        self.webinar_handler = WebinarHandler.WebinarHandler(self.audio_handler, self.stop_browser_and_recording,
                                                             self.preview_label)
        self.lecture_builder = LectureBuilder.LectureBuilder(self.settings, self.elements_set_enabled_signal,
                                                             self.progress_bar_set_value_signal,
                                                             self.progress_bar_set_maximum_signal,
                                                             self.lecture_building_done_signal)

        # Set window title
        self.setWindowTitle('Webinar hacker ' + WEBINAR_HACKER_VERSION)

        # Set icon
        self.setWindowIcon(QtGui.QIcon('icon.png'))

        # Show GUI
        self.show()

        # Additional links
        self.additional_links = []
        self.additional_links_widgets = []

        # Multiple links indexes
        self.current_link_index = 0

        # Connect buttons
        self.btn_link_add.clicked.connect(lambda: self.link_add(''))
        self.btn_browser_open.clicked.connect(lambda: self.start_browser(True))
        self.btn_browser_stop.clicked.connect(lambda: self.stop_browser(True))
        self.btn_refresh.clicked.connect(self.lectures_refresh)
        self.btn_build.clicked.connect(self.lecture_build)

        # Set gui elements from settings
        gui_links = self.settings['gui_links']
        if len(gui_links) > 0:
            self.line_edit_link.setText(str(gui_links[0]))
            if len(gui_links) > 1:
                for gui_link_n in range(1, len(gui_links)):
                    self.link_add(gui_links[gui_link_n])
        self.line_edit_name.setText(str(self.settings['gui_name']))
        self.line_edit_hello_message.setText(str(self.settings['gui_hello_message']))
        self.check_box_hello_message.setChecked(self.settings['gui_hello_message_enabled'])
        self.check_box_recording.setChecked(self.settings['gui_recording_enabled'])
        self.line_edit_proxy.setText(str(self.settings['gui_proxy']))
        self.slider_audio_threshold.setValue(int(self.settings['gui_audio_threshold_dbfs']))
        self.label_audio_threshold.setText(str(int(self.settings['gui_audio_threshold_dbfs'])) + ' dBFS')
        self.spell_correction.setChecked(self.settings['gui_spell_correction_enabled'])
        self.punctuation_correction.setChecked(self.settings['gui_punctuation_correction_enabled'])

        # Connect settings updater
        self.line_edit_link.textChanged.connect(self.update_settings)
        self.line_edit_name.textChanged.connect(self.update_settings)
        self.line_edit_hello_message.textChanged.connect(self.update_settings)
        self.check_box_hello_message.clicked.connect(self.update_settings)
        self.check_box_recording.clicked.connect(self.update_settings)
        self.line_edit_proxy.textChanged.connect(self.update_settings)
        self.slider_audio_threshold.valueChanged.connect(self.update_settings)
        self.spell_correction.clicked.connect(self.update_settings)
        self.punctuation_correction.clicked.connect(self.update_settings)

        # Refresh list of lectures
        self.lectures_refresh()

    def update_settings(self):
        """
        Saves gui fields to settings file
        :return:
        """
        # Read data from elements
        self.links_to_settings()
        self.settings['gui_name'] = str(str(self.line_edit_name.text()))
        self.settings['gui_hello_message'] = str(str(self.line_edit_hello_message.text()))
        self.settings['gui_hello_message_enabled'] = self.check_box_hello_message.isChecked()
        self.settings['gui_recording_enabled'] = self.check_box_recording.isChecked()
        self.settings['gui_proxy'] = str(str(self.line_edit_proxy.text()))
        self.settings['gui_audio_threshold_dbfs'] = int(self.slider_audio_threshold.value())
        self.label_audio_threshold.setText(str(int(self.slider_audio_threshold.value())) + ' dBFS')
        self.settings['gui_spell_correction_enabled'] = self.spell_correction.isChecked()
        self.settings['gui_punctuation_correction_enabled'] = self.punctuation_correction.isChecked()

        # Save to file
        save_json(SETTINGS_FILE, self.settings)

    def links_to_settings(self):
        """
        Updates gui_links
        :return:
        """
        gui_links = []
        # Append main link
        if len(str(self.line_edit_link.text()).strip()) > 0:
            gui_links.append(str(self.line_edit_link.text()).strip())

        # Append additional links
        for additional_link in self.additional_links:
            if additional_link is not None and len(str(additional_link).strip()) > 0:
                gui_links.append(str(additional_link).strip())

        # Write to settings
        self.settings['gui_links'] = gui_links

    def link_add(self, link=''):
        """
        Adds new link field
        :return:
        """
        logging.info('Adding new link ' + link)
        # Create elements
        widget = QWidget()
        layout = QHBoxLayout()
        button = QPushButton('-')
        line_edit = QLineEdit()
        index_ = len(self.additional_links_widgets)

        # Delete field on button click
        button.clicked.connect(lambda: self.link_remove(index_))

        # Set initial link
        if len(link.strip()) > 0:
            line_edit.setText(link)

        # Connect edit event
        line_edit.textChanged.connect(lambda: self.link_edit(index_, line_edit.text()))

        # Add elements to new layout
        layout.addWidget(line_edit)
        layout.addWidget(button)
        layout.setContentsMargins(0, 0, 0, 0)
        widget.setLayout(layout)

        # Add to lists
        self.additional_links_widgets.append(widget)
        self.additional_links.append(link)

        # Add to layout
        self.layout_links.addWidget(widget)

    def link_edit(self, link_index: int, link: str):
        """
        Edits additional link
        :param link_index:
        :param link:
        :return:
        """
        self.additional_links[link_index] = link
        self.update_settings()

    def link_remove(self, link_index: int):
        """
        Removes link field
        :param link_index:
        :return:
        """
        logging.info('Removing link with index: ' + str(link_index + 1))
        if 0 <= link_index < len(self.additional_links_widgets):
            widget = self.additional_links_widgets[link_index]
            if widget is not None:
                # Remove from layout
                self.layout_links.removeWidget(widget)
                widget.deleteLater()

                # Remove from list
                self.additional_links_widgets[link_index] = None
                self.additional_links[link_index] = ''

                # Write to settings
                self.update_settings()

    def lecture_building_done(self, lecture_name: str):
        """
        Shows info about saved lecture
        :return:
        """
        lectures_directory = str(self.settings['lectures_directory_name'])
        lecture_file = lecture_name + '.docx'
        QMessageBox.information(self, 'Done!', 'The lecture was successfully built!\nFile: ' +
                                os.path.join(lectures_directory, lecture_file))

    def lectures_refresh(self):
        """
        Searches for lectures
        :return:
        """
        logging.info('Refreshing list of lectures...')
        lectures = []
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
                                    break

        # Sort lectures
        lectures.sort(reverse=True)

        # Add to combobox and log list of lectures
        logging.info('Available lectures: ' + str(lectures))
        self.combo_box_recordings.clear()
        self.combo_box_recordings.addItems(lectures)

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

    def start_browser(self, from_button: bool):
        """
        Asks for confirmation and opens browser and starts recording
        :param from_button: True if button clicked false if automation
        :return:
        """
        # Reset current link index if action is from button
        if from_button:
            self.current_link_index = 0
        logging.info('Starting from link with index: ' + str(self.current_link_index))

        # Check link index
        if self.current_link_index >= len(self.settings['gui_links']):
            logging.info('No more links')
            QMessageBox.information(self, 'No links!', 'No more available links provided')
            self.elements_set_enabled(True, True)
            return

        # Get link
        link = str(self.settings['gui_links'][self.current_link_index]).strip()
        while len(link) <= 0 and self.current_link_index < len(self.settings['gui_links']):
            self.current_link_index += 1
            link = str(self.settings['gui_links'][self.current_link_index]).strip()

        # Can not get new link
        if len(link) <= 0:
            QMessageBox.warning(self, 'No links!', 'No more available links provided')
            self.elements_set_enabled(True, True)
            return

        user_name = str(self.settings['gui_name']).strip()
        hello_message = str(self.settings['gui_hello_message']) \
            .strip() if self.settings['gui_hello_message_enabled'] else ''
        proxy = str(self.settings['gui_proxy']).strip()

        # Check link and username
        if len(user_name) > 0:
            start_allowed = False
            # No confirmation needed in auto mode
            if not from_button:
                start_allowed = True
            # Ask for confirmation
            else:
                is_recording_enabled = self.settings['gui_recording_enabled']
                recording_state_str = 'ENABLED' if is_recording_enabled else 'DISABLED'
                warning_msg = 'Event recording ' + recording_state_str + '!\nDo you want to continue?'
                reply = QMessageBox.warning(self, 'Recording ' + recording_state_str, warning_msg, QMessageBox.Yes,
                                            QMessageBox.No)
                if reply == QMessageBox.Yes:
                    start_allowed = True

            if start_allowed:
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

    def stop_browser(self, from_button: bool):
        """
        Stops recording and closes browser
        :return:
        :param from_button: True if button clicked false if automation
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

        # Next link
        if not from_button and self.current_link_index <= len(self.settings['gui_links']):
            self.current_link_index += 1
            self.start_browser(False)

        # No more links
        else:
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
        self.slider_audio_threshold.setEnabled(True if browser else enabled)
        self.spell_correction.setEnabled(enabled)
        self.punctuation_correction.setEnabled(enabled)
        self.btn_link_add.setEnabled(enabled)
        for additional_links_widget in self.additional_links_widgets:
            if additional_links_widget is not None:
                additional_links_widget.setEnabled(enabled)

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

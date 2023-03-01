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

import base64
import logging
import threading
import time

import cv2
import numpy as np
from PyQt5 import QtCore
from PyQt5.QtGui import QPixmap, QImage
from qt_thread_updater import get_updater
from selenium import webdriver
from selenium.webdriver import Keys
from selenium.webdriver.common.by import By
from webdriver_manager.chrome import ChromeDriverManager

HANDLER_STAGE_LOGIN = 0
HANDLER_STAGE_SEND_HELLO_MESSAGE = 1
HANDLER_STAGE_IDLE = 2

SCREENSHOT_EXTENSION = '.png'

DISCONNECTED_MSG_LOWER = 'disconnected: not connected to devtools'
DISCONNECTED_EXCEPTION_LOWER = 'already closed'

SAVING_TEXT_COLOR = (85, 85, 217)


def resize_keep_ratio(source_image, target_width, target_height, interpolation=cv2.INTER_AREA):
    """
    Resize image and keeps aspect ratio (background fills with black)
    """
    border_v = 0
    border_h = 0
    if (target_height / target_width) >= (source_image.shape[0] / source_image.shape[1]):
        border_v = int((((target_height / target_width) * source_image.shape[1]) - source_image.shape[0]) / 2)
    else:
        border_h = int((((target_width / target_height) * source_image.shape[0]) - source_image.shape[1]) / 2)
    output_image = cv2.copyMakeBorder(source_image, border_v, border_v, border_h, border_h, cv2.BORDER_CONSTANT, 0)
    return cv2.resize(output_image, (target_width, target_height), interpolation)


class WebinarHandler:
    def __init__(self, audio_handler, settings, stop_browser_and_recording: QtCore.pyqtSignal, preview_label,
                 label_current_link_time_signal: QtCore.pyqtSignal):
        """
        Initializes WebinarHandler class
        """
        self.audio_handler = audio_handler
        self.settings = settings
        self.stop_browser_and_recording = stop_browser_and_recording
        self.preview_label = preview_label
        self.label_current_link_time_signal = label_current_link_time_signal

        self.browser = None  # webdriver.Chrome()
        self.handler_loop_running = False

        self.user_name = ''
        self.opencv_image_prev = None

    def start_browser(self, link: str):
        """
        Starts browser
        :param link: URL
        :return:
        """
        if self.browser is None:
            logging.info('Starting browser... Please wait')
            chrome_options = webdriver.ChromeOptions()
            proxy = str(self.settings['gui_proxy']).strip()
            if len(proxy) > 0:
                chrome_options.add_argument('--proxy-server=%s' % proxy)
            chrome_options.add_argument("--disable-infobars")
            chrome_options.add_argument("--disable-extensions")
            chrome_options.add_argument('--ignore-ssl-errors=yes')
            chrome_options.add_argument('--ignore-certificate-errors')
            # Pass the argument 1 to allow and 2 to block
            chrome_options.add_experimental_option("prefs", {
                "profile.default_content_setting_values.media_stream_mic": 2,
                "profile.default_content_setting_values.media_stream_camera": 2,
                "profile.default_content_setting_values.geolocation": 2,
                "profile.default_content_setting_values.notifications": 2
            })

            # Start browser
            self.browser = webdriver.Chrome(ChromeDriverManager().install(), chrome_options=chrome_options)
            self.browser.get(link)

    def stop_browser(self):
        """
        Closes browser
        :return:
        """
        try:
            if self.browser is not None:
                logging.info('Closing browser... Please wait')
                self.browser.quit()
                self.browser = None
        except Exception as e:
            logging.warning(e)

    def start_handler(self, user_name: str):
        """
        Starts webinar handler
        :param user_name: Connect with this name (not empty)
        :return:
        """
        # Set username, hello message and loop interval
        self.user_name = user_name

        # Clear previous image
        self.opencv_image_prev = None

        # Start webinar handler
        self.handler_loop_running = True
        thread = threading.Thread(target=self.handler_loop)
        thread.start()
        logging.info('Webinar handler thread: ' + thread.name)

        # Restart current time label
        self.label_current_link_time_signal.emit('Current link time: 00:00:00')

    def stop_handler(self):
        """
        Stops webinar handler
        :return:
        """
        self.handler_loop_running = False

        # Restart current time label
        self.label_current_link_time_signal.emit('Current link time: 00:00:00')

    def handler_loop(self):
        """
        Handles logging, popup blocking, attention checking etc...
        :return:
        """
        # Set initial stage and time
        handler_stage = HANDLER_STAGE_LOGIN
        time_started = int(time.time() * 1000)
        while self.handler_loop_running and len(self.user_name) > 0:
            try:
                # Calculate current time
                time_passed = int(time.time() * 1000) - time_started

                # Print current time
                time_passed_seconds = int((time_passed / 1000) % 60)
                time_passed_minutes = int((time_passed / (1000 * 60)) % 60)
                time_passed_hours = int(time_passed / (1000 * 60 * 60))
                self.label_current_link_time_signal.emit('Current link time: ' + '{:02d}'.format(time_passed_hours)
                                                         + ':' + '{:02d}'.format(time_passed_minutes)
                                                         + ':' + '{:02d}'.format(time_passed_seconds))

                # Check if browser is closed
                browser_closed = False
                try:
                    _ = self.browser.window_handles
                except Exception as e:
                    logging.warning(e)
                    browser_closed = True
                    logging.warning('Browser was closed')

                # Check if timed out
                timed_out = False
                if time_passed > int(self.settings['gui_max_event_time_milliseconds']) > 0:
                    logging.info('Timeout!')
                    timed_out = True

                # Finished, timed out or closed
                if browser_closed or timed_out or \
                        'AfterMeetingScreenContent' in self.browser.page_source or \
                        'event_stopped' in self.browser.page_source:
                    logging.warning('Event finished, timed out or browser closed! Closing browser...')
                    if self.browser is not None:
                        self.stop_browser_and_recording.emit()
                    break

                # Close camera / mic form
                prepare_containers = self.browser.find_elements(By.ID, 'prepare-vcs')
                for prepare_container in prepare_containers:
                    prepare_accept_buttons = prepare_container.find_elements(By.CLASS_NAME, 'btn')
                    for prepare_accept_button in prepare_accept_buttons:
                        prepare_accept_button.click()

                # Close popup
                popover_containers = self.browser.find_elements(By.CLASS_NAME, 'popover')
                for popover_container in popover_containers:
                    popover_container_buttons = popover_container.find_elements(By.CLASS_NAME, 'btn-link')
                    for popover_container_button in popover_container_buttons:
                        popover_container_button.click()

                # Login stage
                if handler_stage == HANDLER_STAGE_LOGIN:
                    # If page has stream container
                    stream_container = self.browser.find_elements(By.CLASS_NAME, 'stream-main')
                    if len(stream_container) > 0:
                        logging.info('Logged in successfully!')
                        # Switch to next stage
                        handler_stage = HANDLER_STAGE_SEND_HELLO_MESSAGE

                    # "Please wait, the event will start soon" message
                    before_event_pages = self.browser.find_elements(By.CLASS_NAME,
                                                                    'BeforeEventPage-module__main___xpKQX')
                    if len(before_event_pages) <= 0:
                        # Connect button on form window
                        form_buttons = self.browser.find_elements(By.CLASS_NAME, 'modal-footer')

                        # Connect button before form window
                        page_buttons = self.browser.find_elements(By.CLASS_NAME, 'event-btns')

                        # Form exists
                        if len(form_buttons) > 0:
                            # Set connect name and press connect button
                            name_forms = self.browser.find_elements(By.CLASS_NAME, 'input-field')
                            if len(name_forms) > 0:
                                name_fields = name_forms[0].find_elements(By.TAG_NAME, 'input')
                                if len(name_fields) > 0:
                                    logging.info('Typing ' + self.user_name + ' into name field...')
                                    # Click into field
                                    name_fields[0].click()

                                    # Erase previous text
                                    for _ in range(len(self.user_name)):
                                        name_fields[0].send_keys(Keys.BACKSPACE)

                                    # Type username and press Enter
                                    name_fields[0].send_keys(self.user_name, Keys.ENTER)

                                    # Switch to next stage
                                    handler_stage = HANDLER_STAGE_SEND_HELLO_MESSAGE

                        # No form -> click on connect button to show form
                        elif len(page_buttons) > 0:
                            page_connect_buttons = page_buttons[0].find_elements(By.CLASS_NAME, 'btn')
                            if len(page_connect_buttons) > 0:
                                logging.info('No form found. Clicking the Connect button...')
                                page_connect_buttons[0].click()

                    # Page has one
                    else:
                        logging.info('Waiting for event starting up...')

                # Send hellow message stage
                elif handler_stage == HANDLER_STAGE_SEND_HELLO_MESSAGE:
                    hello_message = str(self.settings['gui_hello_message']).strip() \
                        if self.settings['gui_hello_message_enabled'] else ''
                    recording_enabled = self.settings['gui_recording_enabled']
                    if len(hello_message) > 0:
                        # Chat class
                        chat_inputs = self.browser.find_elements(By.CLASS_NAME, 'editable-input')
                        for chat_input in chat_inputs:
                            # Find chat input field
                            chat_input_divs = chat_input.find_elements(By.TAG_NAME, 'div')
                            chat_input_div = None
                            for chat_input_div_test in chat_input_divs:
                                if chat_input_div_test.get_attribute('data-placeholder') is not None:
                                    chat_input_div = chat_input_div_test
                                    break

                            # Send hello message
                            if chat_input_div is not None:
                                logging.info('Sending ' + hello_message + ' to the chat...')

                                # Click into message field
                                chat_input_div.click()

                                # Send hellow message
                                chat_input_div.send_keys(hello_message, Keys.ENTER)

                                # Switch to IDLE
                                handler_stage = HANDLER_STAGE_IDLE

                                # Start recording
                                if recording_enabled:
                                    self.audio_handler.recording_start()

                    # No hello message -> switch to IDLE stage and start recording
                    else:
                        handler_stage = HANDLER_STAGE_IDLE

                        # Start recording
                        if recording_enabled:
                            self.audio_handler.recording_start()

                # IDLE stage -> handle attention checks
                elif handler_stage == HANDLER_STAGE_IDLE:
                    # Try to click into message field to simulate activity
                    try:
                        chat_inputs = self.browser.find_elements(By.CLASS_NAME, 'editable-input')
                        for chat_input in chat_inputs:
                            # Find chat input field
                            chat_input_divs = chat_input.find_elements(By.TAG_NAME, 'div')
                            chat_input_div = None
                            for chat_input_div_test in chat_input_divs:
                                if chat_input_div_test.get_attribute('data-placeholder') is not None:
                                    chat_input_div = chat_input_div_test
                                    break

                            # Click into message field
                            if chat_input_div is not None:
                                chat_input_div.click()
                    except:
                        pass

                    # Find attention checkers overlays
                    attention_overlays = self.browser.find_elements(By.CLASS_NAME, 'layer_over')
                    for attention_overlay in attention_overlays:
                        # Click on attention control button
                        attention_control_buttons = attention_overlay.find_elements(By.CLASS_NAME, 'btn')
                        for attention_control_button in attention_control_buttons:
                            logging.info('Clicking on attention overlay...')
                            attention_control_button.click()

                        # Click on close button
                        attention_close_buttons = attention_overlay.find_elements(By.CLASS_NAME, 'btn-link')
                        for attention_close_button in attention_close_buttons:
                            logging.info('Closing attention overlay...')
                            attention_close_button.click()

                    # If screen sharing enabled
                    stream_screensharings = self.browser.find_elements(By.CLASS_NAME, 'stream-screensharing')
                    if len(stream_screensharings) > 0:
                        stream_screensharing_videos = stream_screensharings[0].find_elements(By.TAG_NAME, 'video')
                        if len(stream_screensharing_videos) > 0:
                            # Take screenshot and convert to opencv image
                            base64_screenshot = stream_screensharing_videos[0].screenshot_as_base64
                            image_bytes = base64.b64decode(base64_screenshot)
                            image_array = np.frombuffer(image_bytes, dtype=np.uint8)
                            opencv_image = cv2.imdecode(image_array, flags=cv2.IMREAD_COLOR).astype('uint8')

                            # First start -> initialize self.opencv_image_prev
                            if self.opencv_image_prev is None:
                                self.opencv_image_prev = np.zeros(opencv_image.shape, dtype=opencv_image.dtype)

                            # Resize prev image
                            self.opencv_image_prev = cv2.resize(self.opencv_image_prev,
                                                                (opencv_image.shape[1], opencv_image.shape[0]))

                            # Find difference
                            diff = cv2.absdiff(opencv_image, self.opencv_image_prev).astype('uint8')

                            # Convert to grayscale
                            diff = cv2.cvtColor(diff, cv2.COLOR_BGR2GRAY)

                            # Store current image for next cycle
                            self.opencv_image_prev = opencv_image

                            # Apply threshold
                            _, thresh = cv2.threshold(diff, int(self.settings['opencv_threshold']),
                                                      255, cv2.THRESH_BINARY)

                            # Calculate difference in percents
                            diff_percents = (cv2.countNonZero(thresh) /
                                             (opencv_image.shape[1] * opencv_image.shape[0])) * 100
                            logging.info('Difference: ' + str(int(diff_percents)) + '%')

                            # Save screenshot
                            if diff_percents >= int(self.settings['screenshot_diff_threshold_percents']):
                                screenshot_name = str(int(time.time() * 1000) - self.audio_handler
                                                      .recording_started_time) + SCREENSHOT_EXTENSION
                                logging.info('Saving current screenshot as ' + screenshot_name + '...')
                                cv2.imwrite(self.audio_handler.screenshots_dir + screenshot_name, opencv_image)

                            # Resize preview
                            preview_resized = resize_keep_ratio(opencv_image, self.preview_label.size().width(),
                                                                self.preview_label.size().height())

                            # Put Saving... text on top of the image
                            if diff_percents >= int(self.settings['screenshot_diff_threshold_percents']):
                                cv2.putText(preview_resized, 'Saving...', (10, preview_resized.shape[0] // 2),
                                            cv2.FONT_HERSHEY_SIMPLEX, 2, SAVING_TEXT_COLOR, 2, cv2.LINE_AA)

                            # Convert to pixmap
                            pixmap = QPixmap.fromImage(
                                QImage(preview_resized.data, preview_resized.shape[1], preview_resized.shape[0],
                                       3 * preview_resized.shape[1], QImage.Format_BGR888))

                            # Push to preview
                            get_updater().call_latest(self.preview_label.setPixmap, pixmap)

            # Error
            except Exception as e:
                logging.warning(e)

            # Wait for next loop cycle
            time.sleep(float(self.settings['loop_interval_seconds']))

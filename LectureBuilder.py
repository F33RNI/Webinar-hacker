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

import logging
import os
import threading

from docx import Document
from docx.shared import Inches, Pt, RGBColor
from huggingsound import SpeechRecognitionModel

from WebinarHandler import SCREENSHOT_EXTENSION


class LectureBuilder:
    def __init__(self, settings, elements_set_enabled_signal):
        self.settings = settings
        self.elements_set_enabled_signal = elements_set_enabled_signal

        self.audio_files = []
        self.screenshots = []
        self.lecture_name = ''
        self.model = None

    def start_building_lecture(self, lecture_directory: str, lecture_name: str):
        """
        Starts building lecture
        :param lecture_name: example DD_MM_YYYY__HH_MM_SS
        :param lecture_directory: example recordings/DD_MM_YYYY__HH_MM_SS
        :return:
        """
        logging.info('Building lecture ' + lecture_name)
        self.lecture_name = lecture_name
        self.audio_files = []
        self.screenshots = []

        # Find audio files
        for audio_or_screenshot_dir in os.listdir(lecture_directory):
            audio_or_screenshot_dir = os.path.join(lecture_directory, audio_or_screenshot_dir)
            if os.path.isdir(audio_or_screenshot_dir) \
                    and str(self.settings['audio_directory_name']) in audio_or_screenshot_dir:
                for file_ in os.listdir(audio_or_screenshot_dir):
                    file_ = os.path.join(audio_or_screenshot_dir, file_)
                    if not os.path.isdir(file_) and '.wav' in str(file_):
                        time_diff = ''.join(os.path.basename(file_).strip().split('.')[: -1])
                        time_diff_int = -1
                        try:
                            time_diff_int = int(time_diff)
                        except:
                            pass
                        if time_diff_int >= 0:
                            logging.info('Found audio file: ' + str(file_) + ' with time: ' + str(time_diff_int))
                            self.audio_files.append([time_diff_int, str(file_)])

        # Find screenshots
        screenshots_dir = lecture_directory + '/' + str(self.settings['screenshots_directory_name']) + '/'
        if os.path.exists(screenshots_dir):
            for file in os.listdir(screenshots_dir):
                dir_or_file = os.path.join(screenshots_dir, file)
                if not os.path.isdir(dir_or_file) and SCREENSHOT_EXTENSION in str(dir_or_file):
                    time_diff = ''.join(os.path.basename(dir_or_file).strip().split('.')[: -1])
                    time_diff_int = -1
                    try:
                        time_diff_int = int(time_diff)
                    except:
                        pass
                    if time_diff_int >= 0:
                        logging.info('Found screenshot: ' + str(dir_or_file) + ' with time: ' + str(time_diff_int))
                        self.screenshots.append([time_diff_int, str(dir_or_file)])

        # Sort audio files and screenshots
        if len(self.audio_files) > 0:
            self.audio_files.sort(key=lambda x: x[0])
        if len(self.screenshots) > 0:
            self.screenshots.sort(key=lambda x: x[0], reverse=True)

        # Check for audio file
        if len(self.audio_files) > 0:
            # Start thread
            thread = threading.Thread(target=self.lecture_builder_thread)
            thread.start()
            logging.info('Lecture builder thread: ' + thread.name)

        # No audio file
        else:
            logging.warning('No audio file!')
            # Enable gui elements
            self.elements_set_enabled_signal.emit(True)

    def lecture_builder_thread(self):
        """
        Transcribes audio and build lecture
        :return:
        """
        # Load model
        if self.model is None:
            self.model = SpeechRecognitionModel(self.settings['speech_recognition_model'])

        # Transcribe audio
        logging.info('Starting transcription... Please wait')
        audio_files_to_transcribe = []
        for audio_file_ in self.audio_files:
            audio_files_to_transcribe.append(audio_file_[1])
        transcriptions = self.model.transcribe(audio_files_to_transcribe)

        # Check transcription
        if len(transcriptions) > 0:
            try:
                paragraphs = []
                paragraphs_time_stamps = []
                paragraphs_probabilities = []

                for i in range(len(transcriptions)):
                    transcription = transcriptions[i]['transcription']
                    start_timestamps = transcriptions[i]['start_timestamps']
                    end_timestamps = transcriptions[i]['end_timestamps']
                    probabilities = transcriptions[i]['probabilities']
                    timestamp_offset = self.audio_files[i][0]

                    # Check length
                    if len(transcription) == len(start_timestamps) == len(end_timestamps) == len(probabilities):
                        words = []
                        word_time_stamps = []
                        word_probabilities = []

                        # Split into words, end timestamps and probabilities
                        word = ''
                        word_probability = 0
                        for char_n in range(len(transcription)):
                            char_ = transcription[char_n]
                            # Space found -> make word
                            if char_ == ' ' and len(word) > 0:
                                words.append(word)
                                word_time_stamps.append(end_timestamps[char_n] + timestamp_offset)
                                word_probabilities.append(int((word_probability / len(word)) * 100))
                                word = ''
                                word_probability = 0

                            # Build word
                            else:
                                word += char_
                                word_probability += probabilities[char_n]

                        # Add last word
                        if len(word) > 0:
                            words.append(word)
                            word_time_stamps.append(end_timestamps[-1] + timestamp_offset)
                            word_probabilities.append(int((word_probability / len(word)) * 100))

                        # Append to paragraphs
                        paragraphs.append(words)
                        paragraphs_time_stamps.append(word_time_stamps)
                        paragraphs_probabilities.append(word_probabilities)
                    else:
                        logging.warning('Transcription n' + str(i + 1) + ' result length are not equal!')

                # Log number of words
                words_n = 0
                for words_ in paragraphs:
                    for _ in words_:
                        words_n += 1
                logging.info('Transcription result words: ' + str(words_n))

                # Create docx document
                logging.info('Writing to docx document...')
                document = Document()
                document.add_heading(self.lecture_name, 0)

                # First screenshot
                current_screenshot = None
                if len(self.screenshots) > 0:
                    current_screenshot = self.screenshots.pop()

                # List all paragraphs
                for paragraph_n in range(len(paragraphs)):
                    logging.info('Writing ' + str(paragraph_n + 1) + ' paragraph')

                    # Create initial paragraph
                    paragraph = document.add_paragraph('')

                    # Unpack data
                    words = paragraphs[paragraph_n]
                    word_time_stamps = paragraphs_time_stamps[paragraph_n]
                    word_probabilities = paragraphs_probabilities[paragraph_n]

                    # Add all words and screenshots
                    for word_n in range(len(words)):
                        word_ = words[word_n]
                        current_timestamp = word_time_stamps[word_n]
                        probability = word_probabilities[word_n]

                        # Append word
                        run_ = paragraph.add_run(word_ + ' ')

                        # Set font size
                        run_.font.size = Pt(int(self.settings['lecture_font_size_pt']))

                        # Show low probability words
                        if probability <= int(self.settings['word_low_probability_threshold_percents']):
                            text_colors = self.settings['lecture_low_probability_text_color']
                            run_.font.color.rgb = RGBColor(int(text_colors[0]),
                                                           int(text_colors[1]),
                                                           int(text_colors[2]))
                        else:
                            text_colors = self.settings['lecture_default_text_color']
                            run_.font.color.rgb = RGBColor(int(text_colors[0]),
                                                           int(text_colors[1]),
                                                           int(text_colors[2]))

                        # Check screenshot
                        if current_screenshot is not None and current_timestamp >= current_screenshot[0]:
                            # New paragraph
                            paragraph = document.add_paragraph('')

                            # Append screenshot
                            document.add_picture(str(current_screenshot[1]).replace('\\', '/'), width=Inches(
                                float(self.settings['lecture_picture_width_inches'])))

                            # Get next screenshot
                            if len(self.screenshots) > 0:
                                current_screenshot = self.screenshots.pop()
                            else:
                                current_screenshot = None

                # Create lectures directory
                lectures_dir = str(self.settings['lectures_directory_name']) + '/'
                if not os.path.exists(lectures_dir):
                    os.makedirs(lectures_dir)

                # Save lecture
                lecture_file = lectures_dir + self.lecture_name + '.docx'
                logging.info('Saving lecture as: ' + lecture_file)
                document.save(lecture_file)

            # Error building lecture
            except Exception as e:
                logging.error(e, exc_info=True)

            # Enable gui elements
            self.elements_set_enabled_signal.emit(True)

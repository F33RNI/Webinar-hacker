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

import numpy as np
from docx import Document
from docx.shared import Inches, RGBColor

from WebinarHandler import SCREENSHOT_EXTENSION

WAVE_FILE_SIZE_MIN_BYTES = 100


class LectureBuilder:
    def __init__(self, settings, elements_set_enabled_signal, progress_bar_set_value_signal,
                 progress_bar_set_maximum_signal, lecture_building_done_signal):
        self.settings = settings
        self.elements_set_enabled_signal = elements_set_enabled_signal
        self.progress_bar_set_value_signal = progress_bar_set_value_signal
        self.progress_bar_set_maximum_signal = progress_bar_set_maximum_signal
        self.lecture_building_done_signal = lecture_building_done_signal

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

                            # Check file size
                            if os.path.getsize(str(file_)) < WAVE_FILE_SIZE_MIN_BYTES:
                                logging.warning('Size of file ' + str(file_) + ' too small! Ignoring it')
                            else:
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
        try:
            # Load package
            logging.info('Importing SpeechRecognitionModel and torch...')
            from huggingsound import SpeechRecognitionModel
            import torch

            # Load model
            if self.model is None:
                device = 'cuda' if torch.cuda.is_available() else 'cpu'
                logging.info('Using device: ' + device)
                self.model = SpeechRecognitionModel(self.settings['speech_recognition_model'], device=device)

            # Transcribe audio
            logging.info('Starting transcription... Please wait')
            transcriptions = []
            self.progress_bar_set_maximum_signal.emit(len(self.audio_files))
            for audio_file_n in range(len(self.audio_files)):
                # Set progress
                self.progress_bar_set_value_signal.emit(audio_file_n + 1)

                # Transcribe
                audio_file_ = self.audio_files[audio_file_n]
                transcriptions.append(self.model.transcribe([audio_file_[1]]))

            # Check transcription
            if len(transcriptions) > 0:
                # Build words with timestamps
                words = []
                word_time_stamps = []
                for i in range(len(transcriptions)):
                    # Extract data
                    transcription = transcriptions[i][0]['transcription']
                    end_timestamps = transcriptions[i][0]['end_timestamps']
                    timestamp_offset = self.audio_files[i][0]

                    # Check length
                    if transcription is not None and end_timestamps is not None and \
                            len(transcription) == len(end_timestamps):
                        # Split into words, end timestamps and probabilities
                        word = ''
                        for char_n in range(len(transcription)):
                            char_ = transcription[char_n]
                            # Space found -> make word
                            if char_ == ' ' and len(word) > 0:
                                if len(word.strip()) > 0:
                                    words.append(word)
                                    word_time_stamps.append(end_timestamps[char_n] + timestamp_offset)
                                    word = ''

                            # Build word
                            else:
                                word += char_

                        # Add last word
                        if len(word) > 0:
                            if len(word.strip()) > 0:
                                words.append(word)
                                word_time_stamps.append(end_timestamps[-1] + timestamp_offset)
                    else:
                        logging.warning('Error transcribing ' + str(self.audio_files[i][1]))

                # Build paragraphs
                paragraphs = []
                paragraphs_time_stamps = []
                timestamp_last = word_time_stamps[0]
                paragraph_ = []
                for word_n in range(len(words)):
                    # Get word timestamp
                    timestamp_ = word_time_stamps[word_n]

                    # If word is too far from previous word
                    if timestamp_ - timestamp_last >= int(self.settings['paragraph_audio_distance_min_milliseconds']):
                        # Append to paragraphs
                        paragraphs.append(paragraph_)
                        paragraphs_time_stamps.append(timestamp_last)

                        # Reset paragraph_
                        paragraph_ = []

                    # Append current word to paragraph
                    paragraph_.append(words[word_n])

                    # Store timestamp_ for next cycle
                    timestamp_last = timestamp_

                # Append last paragraph
                if len(paragraph_) > 0:
                    paragraphs.append(paragraph_)
                    paragraphs_time_stamps.append(timestamp_last)

                # Remove empty paragraphs
                paragraphs = [x for x in paragraphs if x]

                # Log result
                logging.info('Transcription result words: ' + str(len(words)) + ', paragraphs: ' + str(len(paragraphs)))

                # Apply spell correction
                if self.settings['gui_spell_correction_enabled']:
                    paragraphs = self.fix_spelling(paragraphs)

                # Apply punctuation
                if self.settings['gui_punctuation_correction_enabled']:
                    paragraphs = self.punctuate(paragraphs)

                # Build docx
                self.write_to_docx(paragraphs, paragraphs_time_stamps)

                # Done
                self.lecture_building_done_signal.emit(self.lecture_name)

        # Error building lecture
        except Exception as e:
            logging.error(e, exc_info=True)

        # Reset progress
        self.progress_bar_set_maximum_signal.emit(100)
        self.progress_bar_set_value_signal.emit(0)

        # Enable gui elements
        self.elements_set_enabled_signal.emit(True)

    def fix_spelling(self, paragraphs: list):
        """
        Fixes spelling of each paragraph
        :param paragraphs:
        :return:
        """
        logging.info('Fixing spelling ...')
        # Make a copy
        paragraphs_copy = paragraphs.copy()
        paragraphs = []

        try:
            # Import packages
            import enchant

            # Load dictionary
            dictionary = enchant.Dict(self.settings['spell_correction_dictionary'])

            # Reset progress
            self.progress_bar_set_maximum_signal.emit(len(paragraphs_copy))
            self.progress_bar_set_value_signal.emit(0)

            # List all paragraphs
            for paragraph_n in range(len(paragraphs_copy)):
                # Set progress
                self.progress_bar_set_value_signal.emit(paragraph_n + 1)

                # Make sure every word is one word
                words_raw = (' '.join(paragraphs_copy[paragraph_n])).split(' ')

                words_corrected = []
                for word in words_raw:
                    # Check word length
                    if word is not None and len(word.strip()) > 0:
                        try:
                            # Check and correct word
                            if not dictionary.check(word.strip()):
                                replacements = dictionary.suggest(word.strip())
                                if replacements is not None and len(replacements) > 0:
                                    word = replacements[0]

                            # Append corrected word
                            words_corrected.append(word.strip())
                        except Exception as e:
                            logging.warning(e)

                # Append paragraph
                if len(words_corrected) > 0:
                    paragraphs.append(words_corrected)

            # Return sentences with fixed spelling
            return paragraphs

        # Error fixing spelling
        except Exception as e:
            # Log error
            logging.error(e, exc_info=True)

            # Return unchanged list
            return paragraphs_copy

    def punctuate(self, paragraphs: list):
        """
        Creates punctuation in given paragraphs
        :param paragraphs:
        :return:
        """
        logging.info('Adding punctuation...')
        # Make a copy
        paragraphs_copy = paragraphs.copy()
        paragraphs = []

        try:
            # Import packages
            logging.info('Importing packages...')
            import nltk.data
            import ru_punct.main
            import ru_punct.data
            import ru_punct.models
            import ru_punct.playing_with_model

            # Download punkt
            nltk.download('punkt')

            # Load vocabulary
            vocab_len = len(ru_punct.data.read_vocabulary(ru_punct.data.WORD_VOCAB_FILE))
            x_len = vocab_len if vocab_len < ru_punct.data.MAX_WORD_VOCABULARY_SIZE else \
                ru_punct.data.MAX_WORD_VOCABULARY_SIZE + ru_punct.data.MIN_WORD_COUNT_IN_VOCAB

            x = np.ones((x_len, ru_punct.main.MINIBATCH_SIZE)).astype(int)

            logging.info('Loading model parameters...')
            net, _ = ru_punct.models.load(self.settings['punctuation_correction_model'], x)

            logging.info('Building model...')
            word_vocabulary = net.x_vocabulary
            punctuation_vocabulary = net.y_vocabulary

            reverse_punctuation_vocabulary = {v: k for k, v in punctuation_vocabulary.items()}
            for key, value in reverse_punctuation_vocabulary.items():
                if value == '.PERIOD':
                    reverse_punctuation_vocabulary[key] = '.'
                if value == ',COMMA':
                    reverse_punctuation_vocabulary[key] = ','
                if value == '?QUESTIONMARK':
                    reverse_punctuation_vocabulary[key] = '?'

            # Reset progress
            self.progress_bar_set_maximum_signal.emit(len(paragraphs_copy))
            self.progress_bar_set_value_signal.emit(0)

            # List all paragraphs
            for paragraph_n in range(len(paragraphs_copy)):
                # Set progress
                self.progress_bar_set_value_signal.emit(paragraph_n + 1)

                words_ = paragraphs_copy[paragraph_n]
                text_with_punct = ru_punct.playing_with_model.restore(words_ + [ru_punct.data.END], word_vocabulary,
                                                                      reverse_punctuation_vocabulary, net)

                punkt_tokenizer = nltk.data.load(self.settings['punctuation_correction_tokenizer'])
                sentences = punkt_tokenizer.tokenize(text_with_punct)
                sentences = [sent.capitalize() for sent in sentences]

                # Append to paragraphs
                paragraphs.append(sentences)

            # Return sentences with punctuation
            return paragraphs

        # Error correcting punctuation
        except Exception as e:
            # Log error
            logging.error(e, exc_info=True)

            # Return unchanged list
            return paragraphs_copy

    def write_to_docx(self, paragraphs: list, paragraphs_time_stamps: list):
        """
        Finally writes paragraphs and screenshots to docx document
        :param paragraphs:
        :param paragraphs_time_stamps:
        :return:
        """
        # Create docx document
        logging.info('Writing to docx document...')
        document = Document()
        document.add_heading(self.lecture_name, 0)

        # First screenshot
        current_screenshot = None
        if len(self.screenshots) > 0:
            current_screenshot = self.screenshots.pop()

        # Reset progress
        self.progress_bar_set_maximum_signal.emit(len(paragraphs))
        self.progress_bar_set_value_signal.emit(0)

        # List all paragraphs
        for paragraph_n in range(len(paragraphs)):
            # Set progress
            self.progress_bar_set_value_signal.emit(paragraph_n + 1)

            # Unpack data
            paragraph_ = ' '.join(paragraphs[paragraph_n])
            paragraph_time_stamp = paragraphs_time_stamps[paragraph_n]

            # Add screenshots
            while current_screenshot is not None and paragraph_time_stamp >= current_screenshot[0]:
                # New paragraph
                document.add_paragraph('')

                # Append screenshot
                document.add_picture(str(current_screenshot[1]).replace('\\', '/'), width=Inches(
                    float(self.settings['lecture_picture_width_inches'])))

                # Get next screenshot
                if len(self.screenshots) > 0:
                    current_screenshot = self.screenshots.pop()
                else:
                    current_screenshot = None

            # Add paragraph
            document_run = document.add_paragraph().add_run(paragraph_)

            # Add color
            text_colors = self.settings['lecture_text_color']
            document_run.font.color.rgb = RGBColor(int(text_colors[0]),
                                                   int(text_colors[1]),
                                                   int(text_colors[2]))

        # Add all remaining screenshots
        while len(self.screenshots) > 0:
            # Pop screenshot
            current_screenshot = self.screenshots.pop()

            # New paragraph
            document.add_paragraph('')

            # Append screenshot
            document.add_picture(str(current_screenshot[1]).replace('\\', '/'), width=Inches(
                float(self.settings['lecture_picture_width_inches'])))

        # Create lectures directory
        lectures_dir = str(self.settings['lectures_directory_name']) + '/'
        if not os.path.exists(lectures_dir):
            os.makedirs(lectures_dir)

        # Save lecture
        lecture_file = lectures_dir + self.lecture_name + '.docx'
        logging.info('Saving lecture as: ' + lecture_file)
        document.save(lecture_file)

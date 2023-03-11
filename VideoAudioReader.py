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
import math
import os.path
import threading

import av
import cv2
import numpy as np
from PyQt5.QtGui import QPixmap, QImage
from qt_thread_updater import get_updater

from AudioHandler import WAVE_FILE_EXTENSION
from BrowserHandler import SAVING_TEXT_COLOR, resize_keep_ratio, SCREENSHOT_EXTENSION


class VideoAudioReader:
    def __init__(self, settings,
                 audio_handler,
                 preview_label,
                 label_current_video_audio_time_signal,
                 progress_bar_video_audio_signal,
                 video_audio_decoding_ended_signal):
        self.settings = settings
        self.audio_handler = audio_handler
        self.preview_label = preview_label
        self.label_current_video_audio_time_signal = label_current_video_audio_time_signal
        self.progress_bar_video_audio_signal = progress_bar_video_audio_signal
        self.video_audio_decoding_ended_signal = video_audio_decoding_ended_signal

        self.thread_running = False
        self.thread = None
        self.video_audio_file = ''
        self.opencv_image_prev = None

    def start_processing_file(self, file: str):
        """
        Initializes file decoding
        :param file: media file
        :return:
        """
        if file is not None and len(file) > 0 and os.path.exists(file):
            self.video_audio_file = file

            # Start thread
            self.thread_running = True
            self.thread = threading.Thread(target=self.processing_thread)
            self.thread.start()
            logging.info('Video / audio decoding thread: ' + self.thread.name)

    def abort_processing_file(self):
        """
        Aborts processing file
        :return:
        """
        self.thread_running = False
        if self.thread is not None:
            try:
                self.thread.join()
                self.thread = None
            except Exception as e:
                logging.warning('Error joining processing thread ' + str(e))

    def processing_thread(self):
        """
        Decodes video/audio file into wav files and screenshots
        :return:
        """
        try:
            # Open file and decode each frame
            container = av.open(self.video_audio_file, 'r')

            # Count frames
            total_frames = 0
            try:
                if container.streams.video is not None:
                    total_frames += container.streams.video[0].frames
            except:
                pass
            try:
                if container.streams.audio is not None:
                    total_frames += container.streams.audio[0].frames
            except:
                pass
            logging.info('Total: ' + str(total_frames) + ' frames')

            # Counters
            frame_counter = 0
            audio_frames_processed = 0
            video_frames_processed = 0

            # Resampler
            resampler = None

            frame_millis_last = 0
            for packet in container.demux():
                for frame in packet.decode():
                    # Abort
                    if not self.thread_running:
                        logging.warning('Aborting...')
                        break

                    # Calculate progress
                    frame_counter += 1
                    if total_frames > 0:
                        progress = int((frame_counter / total_frames) * 100.)
                        self.progress_bar_video_audio_signal.emit(progress)

                    # Infinite progress-bar
                    # TODO: Make it nice
                    else:
                        self.progress_bar_video_audio_signal.emit(min(int(math.log10(frame_counter)) * 10, 99))

                    # Calculate frame timestamp
                    frame_millis = int(frame.time * 1000)

                    # Print current time
                    frame_time_seconds = int((frame_millis / 1000) % 60)
                    frame_time_minutes = int((frame_millis / (1000 * 60)) % 60)
                    frame_time_hours = int(frame_millis / (1000 * 60 * 60))
                    self.label_current_video_audio_time_signal.emit('File time: ' + '{:02d}'.format(frame_time_hours)
                                                                    + ':' + '{:02d}'.format(frame_time_minutes) + ':'
                                                                    + '{:02d}'.format(frame_time_seconds))

                    # Skip correpted frames
                    if frame.is_corrupt:
                        continue

                    # Audio frame
                    if type(frame) == av.audio.frame.AudioFrame:
                        # Initialize resampler
                        if resampler is None:
                            resampler = av.audio.resampler.AudioResampler(format='fltp',
                                                                          layout='stereo',
                                                                          rate=frame.sample_rate)

                        # Convert to float
                        data_mono = np.array(resampler.resample(frame)[0].to_ndarray()[0], dtype=np.float32)

                        # Set samplerate
                        self.audio_handler.sampling_rate = frame.sample_rate

                        # Process samples
                        self.audio_handler.process_mono_data(data_mono, str(frame_millis) + WAVE_FILE_EXTENSION)
                        audio_frames_processed += 1

                    # Video frame
                    elif type(frame) == av.video.frame.VideoFrame:
                        if frame_millis - frame_millis_last \
                                >= int(float(self.settings['loop_interval_seconds']) * 1000.):
                            frame_millis_last = frame_millis
                            # Convert to opencv image
                            opencv_image = cv2.cvtColor(frame.to_rgb().to_ndarray(), cv2.COLOR_RGB2BGR)

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
                                screenshot_name = str(frame_millis) + SCREENSHOT_EXTENSION
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
                            video_frames_processed += 1

                # Abort
                if not self.thread_running:
                    logging.warning('Aborting...')
                    break

        # Error
        except Exception as e:
            logging.error('Error processing file ' + str(self.video_audio_file) + '! ' + str(e))

        # Reset progress and time
        self.label_current_video_audio_time_signal.emit('File time: 00:00:00')
        self.progress_bar_video_audio_signal.emit(0)

        # Clear preview image
        get_updater().call_latest(self.preview_label.clear)
        get_updater().call_latest(self.preview_label.setText, 'No image')

        # Stop recording
        self.audio_handler.recording_stop()

        # Done
        if audio_frames_processed + video_frames_processed > 0:
            self.video_audio_decoding_ended_signal.emit(self.video_audio_file)
        else:
            self.video_audio_decoding_ended_signal.emit(None)

        # Thread finished
        logging.info('Processing thread finished')
        self.thread_running = False
        self.thread = None

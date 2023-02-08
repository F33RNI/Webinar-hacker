import logging
import os
import time
import wave
from datetime import datetime

import numpy as np
import pyaudiowpatch as pyaudio

PCM_MAX = 32767


def s_mag_to_dbfs(data_s_mag):
    """
    Converts signal magnitude to dbfs
    :param data_s_mag:
    :return:
    """
    # Prevent zero values
    min_value = np.finfo(np.float).eps
    if data_s_mag < min_value:
        data_s_mag = min_value

    # Convert to dBFS
    return 20 * np.log10(data_s_mag)


def dbfs_to_s_mag(data_dbfs):
    """
    Converts dbfs to signal magnitude
    :param data_dbfs:
    :return:
    """

    # Convert to magnitude
    return np.power(10., np.divide(data_dbfs, 20.))


class AudioHandler:
    def __init__(self, settings, progress_bar_audio_signal):
        self.settings = settings
        self.progress_bar_audio_signal = progress_bar_audio_signal

        self.py_audio = None
        self.recording_stream = None
        self.is_recording = False
        self.wave_file = None

        self.screenshots_dir = ''
        self.audio_dir = ''
        self.recording_started_time = 0
        self.chunks_recorded_counter = 0

        self.recording_channels = 0
        self.sampling_rate = 0
        self.recording_threshold = 0

    def open_stream(self):
        # Initialize PyAudio
        if self.py_audio is None:
            self.py_audio = pyaudio.PyAudio()

        # Get default WASAPI info
        wasapi_info = self.py_audio.get_host_api_info_by_type(pyaudio.paWASAPI)

        # Get default WASAPI speakers
        default_speakers = self.py_audio.get_device_info_by_index(wasapi_info['defaultOutputDevice'])
        if not default_speakers['isLoopbackDevice']:
            for loopback in self.py_audio.get_loopback_device_info_generator():
                if default_speakers['name'] in loopback['name']:
                    default_speakers = loopback
                    break

        # Open recording stream
        logging.info('Opening audio loopback...')
        logging.info(str(default_speakers))
        self.recording_channels = default_speakers['maxInputChannels']
        self.sampling_rate = int(default_speakers['defaultSampleRate'])
        self.recording_stream = self.py_audio.open(input_device_index=default_speakers['index'],
                                                   format=pyaudio.paFloat32,
                                                   channels=self.recording_channels,
                                                   frames_per_buffer=int(self.settings['audio_chunk_size']),
                                                   rate=self.sampling_rate,
                                                   input=True,
                                                   stream_callback=self.callback)

    def close_stream(self):
        """
        Closes recording stream
        :return:
        """
        self.recording_stop()
        if self.recording_stream is not None:
            try:
                self.recording_stream.stop_stream()
                self.recording_stream.close()
            except Exception as e:
                logging.warning(e)

    def recording_start(self):
        """
        Generates self.screenshots_dir and sets self.recording_started_time and sets recording flag
        :return:
        """
        # Generate filenames
        timestamp_str = datetime.now().strftime(self.settings['timestamp_format'])
        logging.info('Recording into: ' + timestamp_str)

        # Create recording directory
        if not os.path.exists(str(self.settings['recordings_directory_name']) + '/' + timestamp_str + '/'):
            os.makedirs(str(self.settings['recordings_directory_name']) + '/' + timestamp_str + '/')

        # Create screenshots directory
        self.screenshots_dir = str(self.settings['recordings_directory_name']) + '/' + timestamp_str + '/' \
                               + str(self.settings['screenshots_directory_name']) + '/'
        if not os.path.exists(self.screenshots_dir):
            os.makedirs(self.screenshots_dir)

        # Create audio directory
        self.audio_dir = str(self.settings['recordings_directory_name']) + '/' + timestamp_str + '/' \
                         + str(self.settings['audio_directory_name']) + '/'
        if not os.path.exists(self.audio_dir):
            os.makedirs(self.audio_dir)

        # Set recording flag
        self.is_recording = True

        # Save start time
        self.recording_started_time = int(time.time() * 1000)

        # Reset audio volume progress bar
        self.progress_bar_audio_signal.emit(-60)

        # Reset counter
        self.chunks_recorded_counter = int(self.settings['audio_recording_chunks_min']) + 1

    def recording_stop(self):
        """
        Stops recording
        :return:
        """
        if self.is_recording:
            logging.info('Stopping recording...')
            # Clear recording flag
            self.is_recording = False

            # Close WAV file
            if self.wave_file is not None:
                self.wave_file.close()
                self.wave_file = None

            # Reset audio volume progress bar
            self.progress_bar_audio_signal.emit(-60)

    def callback(self, in_data, frame_count, time_info, status):
        # Just skip all if not recording
        if self.is_recording:
            # Decode data
            audio_data = np.fromstring(in_data, dtype=np.float32)

            # Split into channels and make mono
            audio_data = audio_data.reshape((len(audio_data) // self.recording_channels, self.recording_channels))
            data_per_channels = np.split(audio_data, self.recording_channels, axis=1)
            input_data_mono = data_per_channels[0].flatten()
            for channel_n in range(1, self.recording_channels):
                input_data_mono = np.add(input_data_mono, data_per_channels[channel_n].flatten())
            input_data_mono = np.divide(input_data_mono, self.recording_channels)

            # Calculate audio volume in dBFS
            dbfs_value = s_mag_to_dbfs((abs(np.min(input_data_mono)) + abs(np.max(input_data_mono))) / 2.)

            # Emit to progress bar
            dbfs_value_progress_bar = int(dbfs_value)
            if dbfs_value_progress_bar < -60:
                dbfs_value_progress_bar = -60
            elif dbfs_value_progress_bar > 0:
                dbfs_value_progress_bar = 0
            self.progress_bar_audio_signal.emit(dbfs_value_progress_bar)

            # Volume > threshold -> reset counter
            if dbfs_value >= self.settings['gui_audio_threshold_dbfs']:
                self.chunks_recorded_counter = 0

            # Recording
            if self.chunks_recorded_counter < int(self.settings['audio_recording_chunks_min']):
                if self.wave_file is None:
                    # Start WAV file
                    wave_name = str(int(time.time() * 1000) - self.recording_started_time) + '.wav'
                    wave_file_path = self.audio_dir + wave_name
                    logging.info('Starting audio recording with name: ' + wave_name)
                    self.wave_file = wave.open(wave_file_path, 'wb')
                    self.wave_file.setnchannels(1)  # Mono
                    self.wave_file.setsampwidth(self.py_audio.get_sample_size(pyaudio.paInt16))  # PCM16
                    self.wave_file.setframerate(int(self.sampling_rate))

                # Convert to PCM 16
                data_pcm = (input_data_mono * PCM_MAX).astype(np.int16)

                # Write to file
                if self.wave_file is not None:
                    self.wave_file.writeframesraw(data_pcm.tobytes())

                # Increment counter
                self.chunks_recorded_counter += 1

            # Stop recording
            else:
                if self.wave_file is not None:
                    logging.info('Stopping recording')
                    self.wave_file.close()
                    self.wave_file = None

        # Continue capturing audio
        return in_data, pyaudio.paContinue

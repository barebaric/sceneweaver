import sounddevice as sd
import numpy as np
from scipy.io.wavfile import write
from pathlib import Path
import sys
import time
import noisereduce as nr


class AudioRecorder:
    def __init__(self, output_path: Path, sample_rate: int = 44100):
        self.output_path = output_path
        self.sample_rate = sample_rate
        self.recording_chunks = []
        self.is_recording = False

    def _audio_callback(self, indata, frames, time, status):
        """This is called (from a separate thread) for each audio block."""
        if status:
            print(status, file=sys.stderr)
        if self.is_recording:
            self.recording_chunks.append(indata.copy())

    def record(self) -> bool:
        """
        Manages the audio recording session.
        Returns True if recording was successful and saved, False otherwise.
        """
        print("\n--- Audio Recording ---")
        print(f"Output file: {self.output_path}")

        try:
            with sd.InputStream(
                samplerate=self.sample_rate,
                channels=1,
                dtype="int16",
                callback=self._audio_callback,
            ):
                input("Press ENTER to start recording...")

                # Start recording logic
                self.is_recording = True
                print("Get ready...", end="", flush=True)
                time.sleep(0.1)  # Delay to avoid capturing key press sound
                self.recording_chunks = []  # Clear chunks from during delay
                print("\r🔴 Recording... Press ENTER to stop.     ")

                input()  # Wait here until the user presses Enter again

                # Stop recording logic
                self.is_recording = False
                print("✅ Recording finished.")

        except KeyboardInterrupt:
            print("\nRecording stopped by user.")
            return False
        except Exception as e:
            print(f"\nAn error occurred: {e}", file=sys.stderr)
            print(
                "Please ensure you have a working microphone and have granted "
                "permissions.",
                file=sys.stderr,
            )
            return False

        if not self.recording_chunks:
            print("No audio was recorded. Aborting.")
            return False

        full_recording = np.concatenate(self.recording_chunks, axis=0)

        # Trim the last 0.1 seconds to remove the stop key press sound
        samples_to_trim = int(0.1 * self.sample_rate)
        if len(full_recording) > samples_to_trim:
            trimmed_recording = full_recording[:-samples_to_trim]
        else:
            trimmed_recording = np.array([])  # Effectively empty

        if trimmed_recording.size == 0:
            print("Recording was too short after trimming. Aborting.")
            return False

        # Denoise the audio before saving
        print("Denoising recorded audio...")
        # Convert from int16 to float32 for processing
        audio_data_float = trimmed_recording.astype(np.float32) / 32767.0

        # The noisereduce library expects a 1D array for mono audio.
        # Our recording is shape (n_samples, 1), so we reshape it.
        audio_data_1d = audio_data_float.reshape(-1)

        # Perform noise reduction on the 1D array
        reduced_noise = nr.reduce_noise(
            y=audio_data_1d, sr=self.sample_rate, prop_decrease=0.95
        )

        # Convert back to int16 for saving
        denoised_recording_int16 = (reduced_noise * 32767).astype(np.int16)

        print(f"Saving audio to {self.output_path}...")
        write(self.output_path, self.sample_rate, denoised_recording_int16)
        print("Done.")
        return True

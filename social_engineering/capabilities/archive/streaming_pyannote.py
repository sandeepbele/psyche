from pyannote.core import notebook, Segment, SlidingWindow
from pyannote.core import SlidingWindowFeature as SWF

from pyannote.audio.core.io import Audio, AudioFile
from pyannote.audio import Pipeline

import torch
import numpy as np
from pyannote.audio import Model
from vosk import Model as VoskModel, KaldiRecognizer
from faster_whisper import WhisperModel
import scipy.io.wavfile
import io, json

class RollingAudioBuffer(Audio):
    """Rolling audio buffer
    
    Parameters
    ----------
    sample_rate : int
        Sample rate
    duration : float, optional
        Duration of rolling buffer. Defaults to 5s.
    step : float, optional
        Delay between two updates of the rolling buffer. Defaults to 1s.


    Usage
    -----
    >>> buffer = RollingAudioBuffer()("audio.wav")
    >>> current_buffer = next(buffer)
    """
    def __init__(self, sample_rate=16000, duration=5.0, step=1.):
        super().__init__(sample_rate=sample_rate, mono=True)
        self.duration = duration
        self.step = step
        
    def __call__(self, file: AudioFile):
        
        # duration of the whole audio file
        duration = self.get_duration(file)
        
        # slide a 5s window from the beginning to the end of the file
        window = SlidingWindow(start=0., duration=self.duration, step=self.step, end=duration)
        for chunk in window:
            # for each position of the window, yield the corresponding audio buffer
            # as a SlidingWindowFeature instance
            if chunk.end > duration:
                chunk = Segment(start=chunk.start, end=duration)

            waveform, sample_rate = self.crop(file, chunk, duration=self.duration,mode="pad")
            resolution = SlidingWindow(start=chunk.start, 
                                       duration=1./self.sample_rate, 
                                       step=1./sample_rate)
            yield SWF(waveform.T, resolution), sample_rate


import numpy as np

def waveform_to_bytes(waveform):
    # Normalize and convert waveform to 16-bit PCM
    # Pyannote usually returns floats in the range [-1, 1]
    waveform_int16 = np.int16(waveform * np.iinfo(np.int16).max)

    # Convert the numpy array to bytes
    waveform_bytes = waveform_int16.tobytes()

    # Convert to bytearray for compatibility with KaldiRecognizer
    return waveform_bytes

# Assuming you have your waveform and sample_rate from pyannote
# waveform, sample_rate = pyannote.Audio.crop(file, chunk, duration=self.duration)

# Convert waveform to bytearray

# Now, you can use waveform_bytearray with KaldiRecognizer
# e.g., kaldi_recognizer.AcceptWaveform(waveform_bytearray)


class VoskTranscriber:
    def __init__(self) -> None:
        self.model = VoskModel(model_name="vosk-model-small-en-us-0.15")
        self.rec = KaldiRecognizer(self.model, 16000)

    def __call__(self, current_buffer: SWF, sample_rate) -> str:
        # we start by applying the model on the current buffer
        waveform = current_buffer.data.T       
        waveform_bytes = waveform_to_bytes(waveform)
        self.rec.AcceptWaveform(waveform_bytes)
        result = self.rec.Result()
        return result

class WhisperTranscriber:
    def __init__(self) -> None:
        self.model = WhisperModel("base.en",
                            device="cpu",
                            compute_type="int8",
                            num_workers=10,
                            cpu_threads=4,
                            download_root="./models",
                            )
        
    def __call__(self, current_buffer: SWF, sample_rate) -> str:
        # we start by applying the model on the current buffer
        waveform_tensor = current_buffer.data.T
        #print("Waveform data type:", type(waveform_tensor))
        #print("Waveform shape:", waveform_tensor.shape)
        #print("Min and Max values:", waveform_tensor.min(), waveform_tensor.max())
        # Convert the tensor to a numpy array
        # Make sure to move the tensor to CPU and detach it from the gradient graph if it's on GPU
        waveform_np = waveform_tensor.cpu().detach().numpy()

        # If your waveform is multi-channel, ensure it's in the right shape (num_channels, num_samples)
        # If it's single-channel, reshape or squeeze it as needed
        waveform_np = waveform_np.squeeze()

        # Ensure waveform values are within [-1.0, 1.0] range
        waveform_np = np.clip(waveform_np, -1.0, 1.0)

        # Scaling to 16-bit PCM and conversion to int16
        waveform_int16 = np.int16(waveform_np * np.iinfo(np.int16).max)

        # Writing to buffer
        buffer = io.BytesIO()
        scipy.io.wavfile.write(buffer, sample_rate, waveform_int16)
        buffer.seek(0)  # Reset buffer position      
        
        try:
            segments, _ = self.model.transcribe(buffer,
                                language='en-US',
                                beam_size=5,
                                vad_filter=True,
                                word_timestamps=True)
        except Exception as e:
            print("Error in transcribing:",e)

        for s in segments:
            print(s.text)
            print(json.dumps(s.words))
        segments = [s.text for s in segments]
        transcription = " ".join(segments)
        transcription = transcription.strip()
        return transcription

class SpeakerAwareTranscriber:
    
    def __init__(self, speaker_model: Model, transcriber) -> None:
        self.speaker_model = speaker_model
        self.transcriber = transcriber
    
    def __call__(self, current_buffer: SWF, sample_rate) -> str:
           # we start by applying the model on the current buffer
        waveform_tensor = current_buffer.data.T
        #print("Waveform data type:", type(waveform_tensor))
        #print("Waveform shape:", waveform_tensor.shape)
        #print("Min and Max values:", waveform_tensor.min(), waveform_tensor.max())
        # Convert the tensor to a numpy array
        # Make sure to move the tensor to CPU and detach it from the gradient graph if it's on GPU
        waveform_np = waveform_tensor.cpu().detach().numpy()

        # If your waveform is multi-channel, ensure it's in the right shape (num_channels, num_samples)
        # If it's single-channel, reshape or squeeze it as needed
        waveform_np = waveform_np.squeeze()

        # Ensure waveform values are within [-1.0, 1.0] range
        waveform_np = np.clip(waveform_np, -1.0, 1.0)

        # Scaling to 16-bit PCM and conversion to int16
        waveform_int16 = np.int16(waveform_np * np.iinfo(np.int16).max)

        # Writing to buffer
        buffer = io.BytesIO()
        scipy.io.wavfile.write(buffer, sample_rate, waveform_int16)
        buffer.seek(0)  # Reset buffer position 

        # Load the diarization pipeline
        diarization_pipeline = Pipeline.from_pretrained("pyannote/speaker-diarization", use_auth_token="REDACTED_HUGGINGFACE_TOKEN")

        # Apply the pipeline to your audio file
        diarization = diarization_pipeline(buffer)
        for segment in diarization.get_timeline():
            print(segment)
        
        return ""

class RollingTrascriber:
        
        def __init__(self, sample_rate=16000, duration=5.0, step=1., transcriber=VoskTranscriber()):
            self.buffer = RollingAudioBuffer(sample_rate=sample_rate, duration=duration, step=step)
            self.transcriber = transcriber

        def __call__(self, file: AudioFile):
            for current_buffer, sample_rate in self.buffer(file):
                yield self.transcriber(current_buffer, sample_rate)


if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description='Voice Activity Detection')
    parser.add_argument('audio', type=str, help='Path to audio file')
    args = parser.parse_args()
    
    transcriber = RollingTrascriber(duration=600,transcriber=SpeakerAwareTranscriber(None,None))
    for part in transcriber(args.audio):
        print("--",part)
        

    print("Done. Press Ctrl+C to exit.")


"""getAudio -> chunk 
-> waveform 
-> diarization
-> transcribe
-> sentiment
-> LLM"""


### REDACTED_HUGGINGFACE_TOKEN ##
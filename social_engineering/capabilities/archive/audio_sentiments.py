import pyaudio
import numpy as np
from faster_whisper import WhisperModel
#from  faster_whisper.vad import VoiceActivityDetector
#from whisper.vad import VoiceActivityDetector




NUM_WORKERS = 10
MODEL_TYPE = "base.en" #"small.en" "base.en"
LANGUAGE_CODE = "en"
CPU_THREADS = 4
VAD_FILTER = True

whisper = WhisperModel(MODEL_TYPE,
                           device="cpu",
                           compute_type="int8",
                           num_workers=NUM_WORKERS,
                           cpu_threads=4,
                           download_root="./models",
                           )
print("Loaded model")

#vad = VoiceActivityDetector(sample_rate=RATE, window_duration=0.03, window_shift=0.01)

CHUNK = 16000    # 1 second of audio
FORMAT = pyaudio.paFloat32
CHANNELS = 1
RATE = 16000
STEP_IN_SEC = 5

p = pyaudio.PyAudio()

stream = p.open(format=FORMAT,
                channels=CHANNELS,
                rate=RATE,
                input=True,
                frames_per_buffer=CHUNK)

print("-" * 80)
print("Microphone initialized, recording started...")
print("-" * 80)
print("TRANSCRIPTION")
print("-" * 80)

while True:
    #audio_data = b""
    #for _ in range(STEP_IN_SEC):
    chunk = stream.read(CHUNK, exception_on_overflow=False)
    #audio_data += chunk
    audio_np = np.frombuffer(chunk, dtype=np.float32)
    
    segments, _ = whisper.transcribe(audio_np,
                            language='en-US',
                            beam_size=5,
                            vad_filter=False)
    segments = [s.text for s in segments]
    transcription = " ".join(segments)
    transcription = transcription.strip()
    print(segments)

from faster_whisper import WhisperModel
import time

NUM_WORKERS = 10
MODEL_TYPE = "small.en" #"base.en"
LANGUAGE_CODE = "en"
CPU_THREADS = 4
VAD_FILTER = True

model = WhisperModel(MODEL_TYPE,
                                    device="auto",
                                    compute_type="int8",
                                    num_workers=NUM_WORKERS,
                                    cpu_threads=4,
                                    download_root="./models",
                                    )
print("Loaded model")

start_time = time.time()
audio_file = "/Users/sandeep/Documents/SB_Sources/anm_dintel/phishnet/sales_call.wav"

segments,_ = model.transcribe(audio_file,vad_filter=True)

for segment in segments:
    print("[%.2fs -> %.2fs] %s" % (segment.start, segment.end, segment.text))

print("Time taken in %.2fs: " % (time.time() - start_time))

import whisper
from pyannote.audio import Pipeline

# Load the pre-trained diarization pipeline from pyannote
diarization_pipeline = Pipeline.from_pretrained("pyannote/speaker-diarization")

# Load your model
model = whisper.load_model("base")

# Transcribe the audio file
result = model.transcribe("/path/to/your/audio/file.mp3")

# Print the transcription
print(result["text"])

# Perform diarization
diarization = diarization_pipeline("/path/to/your/audio/file.mp3")

# The `diarization` object contains the timeline and speaker information
# You would need to write additional code to align this with the transcription
for turn, _, speaker in diarization.itertracks(yield_label=True):
    print(f"Speaker {speaker}, starts at {turn.start:.1f}s, ends at {turn.end:.1f}s.")

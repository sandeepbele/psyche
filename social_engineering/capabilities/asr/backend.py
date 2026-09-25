import whisper_timestamped
from whispercpp import Whisper as whispercpp
import whisper as openai_whisper
import logging 

from capabilities.helpers.utils import suppress_stdout

class WhisperModel:

    def load_model(self, model_name, **kwargs):
        raise NotImplementedError
    
    def transcribe_raw(self, wav_tensor, **kwargs):
        raise NotImplementedError
    
    
class WhisperTimestamped(WhisperModel):
    def __init__(self):
        self.model = None

    def load_model(self,model="small", **kwargs):
        device = kwargs.get("device", "cpu")
        self.model = whisper_timestamped.load_model(model, device=device)

    def transcribe_raw(self, wav_tensor, **kwargs) -> dict:
            logger = logging.getLogger("whisper_timestamped")

            """Transcribe audio using Whisper"""
            # Pad/trim audio to fit 30 seconds as required by Whisper
            audio = whisper_timestamped.pad_or_trim(wav_tensor)
            #prompt = "Anomalytica"
            # Transcribe the given audio while suppressing logs
            #with suppress_stdout():
            logger.debug(f"starting actual transcription")
            transcription = whisper_timestamped.transcribe(
                self.model,
                audio,
                #condition_on_previous_text=True,
                #vad="auditok",
                vad="silero:3.1",
                #trust_whisper_timestamps=True,
                #detect_disfluencies=True,
                # We use past transcriptions to condition the model
                #initial_prompt=prompt,
                verbose=True,  # to avoid progress bar,
                remove_empty_words=False,
            )

            return transcription
    
class WhisperCpp(WhisperModel):
    """ issues installing whispercpp """
    def __init__(self):
        self.model = None

    def load_model(self,model="tiny.en", **kwargs):
        self.model = whispercpp.from_pretrained(model)

    def transcribe_raw(self, wav_tensor, **kwargs):
        return self.model.transcribe(wav_tensor)

class OpenAIWhisper(WhisperModel):
    def __init__(self):
        self.model = None
    
    def load_model(self, model_name, **kwargs):
        self.model = openai_whisper.load_model(model_name)
    
    def transcribe_raw(self, wav_tensor, **kwargs):
        audio = openai_whisper.pad_or_trim(wav_tensor)
        return self.model.transcribe(wav_tensor, **kwargs)
    

class WhisperFactory:
   
    @staticmethod
    def get_whisper(backend) -> WhisperModel:
        if backend == "whisper_timestamped":
            return WhisperTimestamped()
        elif backend == "whisper_cpp":
            return WhisperCpp()
        elif backend == "openai_whisper":
            return OpenAIWhisper()
        else:
            raise NotImplementedError
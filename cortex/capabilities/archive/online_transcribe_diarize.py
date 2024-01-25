import logging
import os
import sys
import traceback
from contextlib import contextmanager

import diart.operators as dops
import numpy as np
import rich
import rx.operators as ops
import whisper_timestamped as whisper
from diart import SpeakerDiarization, SpeakerDiarizationConfig
from diart.blocks import SpeakerSegmentation
from diart.sources import MicrophoneAudioSource, FileAudioSource
from pyannote.core import Annotation, SlidingWindowFeature, SlidingWindow, Segment
import huggingface_hub
import pickle
from voice.archive.speaker_helper import get_embeddings_from_waveform, perform_matching
from pyannote.audio import Audio
import torch
from vosk import Model as VoskModel, KaldiRecognizer
import json 
import requests

def speaker_db():
    return {
        "Sarah": pickle.load(open("/Users/sandeep/Documents/SB_Sources/anm_dintel/phishnet/sales_rep_embd.pkl", "rb")),
        "Customer_A": pickle.load(open("/Users/sandeep/Documents/SB_Sources/anm_dintel/phishnet/cust_embd.pkl", "rb")),
    }

def concat(chunks, collar=0.05):
    """
    Concatenate predictions and audio
    given a list of `(diarization, waveform)` pairs
    and merge contiguous single-speaker regions
    with pauses shorter than `collar` seconds.
    """
    first_annotation = chunks[0][0]
    first_waveform = chunks[0][1]
    annotation = Annotation(uri=first_annotation.uri)
    data = []
    for ann, wav in chunks:
        annotation.update(ann)
        data.append(wav.data)
    annotation = annotation.support(collar)
    window = SlidingWindow(
        first_waveform.sliding_window.duration,
        first_waveform.sliding_window.step,
        first_waveform.sliding_window.start,
    )
    data = np.concatenate(data, axis=0)
    return annotation, SlidingWindowFeature(data, window)


def colorize_transcription(transcription):
    """
    Unify a speaker-aware transcription represented as
    a list of `(speaker: int, text: str)` pairs
    into a single text colored by speakers.
    """
    colors = 2 * [
        "bright_red", "bright_blue", "bright_green", "orange3", "deep_pink1",
        "yellow2", "magenta", "cyan", "bright_magenta", "dodger_blue2"
    ]
    result = []
    for speaker, text in transcription:
        if speaker == -1:
            # No speakerfound for this text, use default terminal color
            result.append(text)
        else:
            result.append(f"[{colors[speaker]}]{text}")
    return "\n".join(result)



def waveform_to_bytes(waveform):
    # Normalize and convert waveform to 16-bit PCM
    # Pyannote usually returns floats in the range [-1, 1]
    waveform_int16 = np.int16(waveform * np.iinfo(np.int16).max)

    # Convert the numpy array to bytes
    waveform_bytes = waveform_int16.tobytes()

    # Convert to bytearray for compatibility with KaldiRecognizer
    return waveform_bytes



class SpeakerAwareTrascriber:
    
    def verify_speaker(self, waveform_segment, known_speakers):
        # Implement the speaker verification logic
        # Convert waveform_segment to the required format if necessary
        # Compare it with the embeddings of known speakers
        # Return the label of the matched speaker or None if no match is found
        audio = Audio(sample_rate=16000, mono="downmix")
    
        embeddings = get_embeddings_from_waveform(waveform_segment)
        for label, known_embedding in known_speakers.items():
            if perform_matching(known_embedding, embeddings):
                return label
        return None

    def identify_speakers_4(self, transcriptions, diarization, time_shift, waveform_feature:SlidingWindowFeature):     
        speaker_captions = []
        transcription = self.transcribe(waveform_feature)
        for segment in transcription['segments']:

            # Extract start and end times of the segment
            #start, end = segment.start, segment.end
           
            # Extract the corresponding waveform segment
            frame_start = waveform_feature.sliding_window.closest_frame(time_shift+segment['start'])
            frame_end = waveform_feature.sliding_window.closest_frame(time_shift+segment['end'])
            
            print(frame_start,frame_end)
            #waveform_segment = waveform_feature.data[frame_start:frame_end, :]
            waveform_segment = waveform_feature.data[frame_start:frame_end, :]
            
            # Convert waveform_segment to a PyTorch tensor
            waveform_segment_tensor = torch.from_numpy(waveform_segment)
            # Ensure the tensor is in the shape (1, num_samples)
            if waveform_segment_tensor.ndim == 2 and waveform_segment_tensor.shape[1] == 1:
                waveform_segment_tensor = waveform_segment_tensor.transpose(0, 1)

            # Perform speaker verification on the segment
            verified_speaker_label = self.verify_speaker(waveform_segment_tensor, speaker_db())

            if verified_speaker_label is None:
                verified_speaker_label = self.verify_speaker(waveform_segment_tensor, self.speaker_embeddings)
                if verified_speaker_label is None:
                    self.new_speaker_label += 1
                    verified_speaker_label = str(self.new_speaker_label)
                    self.speaker_embeddings[verified_speaker_label] = get_embeddings_from_waveform(waveform_segment_tensor)
                else:
                    self.speaker_embeddings[verified_speaker_label] = np.vstack((self.speaker_embeddings[verified_speaker_label], get_embeddings_from_waveform(waveform_segment_tensor)))
            
            speaker_captions.append((verified_speaker_label, segment['text'])) 
            
        merged_captions = []
        current_key = None
        current_value = ""

        for speaker, text in speaker_captions:
            if speaker == current_key:
                current_value += text
            else:
                if current_key is not None:
                    merged_captions.append((current_key, current_value))
                current_key = speaker
                current_value = text

        if current_key is not None:
            merged_captions.append((current_key, current_value))

        #print(merged_captions)
        return merged_captions



    def identify_speakers_3(self, transcriptions, diarization, time_shift, waveform_feature:SlidingWindowFeature):
        speaker_captions = []
        transcription = self.transcribe(waveform_feature)
        for diarization_segment in diarization.get_timeline():
            diarization_start = diarization_segment.start
            diarization_end = diarization_segment.end
            # time_shift aligns timestamps wrt to the start of the original audio
            # segment timestamps are relative to the start of the audio chunk
            # diarization_start and diarization_end are relative to the start of original audio

            words_in_segment = [  word for segment in transcription['segments'] 
                                    for word in segment['words'] 
                                        if diarization_start <= time_shift + word['start'] <= diarization_end ]
            print(f"Diarization Segment: {diarization_segment}")
            print(f"Words in Segment: {' '.join([word['text'] for word in words_in_segment])}")
            if len(words_in_segment) == 0:
                continue

            # Extract start and end times of the segment
            #start, end = segment.start, segment.end
           
            # Extract the corresponding waveform segment
            frame_start = waveform_feature.sliding_window.closest_frame(diarization_start)
            frame_end = waveform_feature.sliding_window.closest_frame(diarization_end)
            
            print(frame_start,frame_end)
            #waveform_segment = waveform_feature.data[frame_start:frame_end, :]
            waveform_segment = waveform_feature.data[frame_start:frame_end, :]
            
            # Convert waveform_segment to a PyTorch tensor
            waveform_segment_tensor = torch.from_numpy(waveform_segment)
            # Ensure the tensor is in the shape (1, num_samples)
            if waveform_segment_tensor.ndim == 2 and waveform_segment_tensor.shape[1] == 1:
                waveform_segment_tensor = waveform_segment_tensor.transpose(0, 1)

            # Perform speaker verification on the segment
            verified_speaker_label = self.verify_speaker(waveform_segment_tensor, speaker_db())

            if verified_speaker_label is None:
                verified_speaker_label = -1 # Fallback to generic label
            
            # Combine transcription text with verified speaker label
            if verified_speaker_label != -1:
                speaker_captions.append((verified_speaker_label, words_in_segment)) 
            
        merged_captions = []
        current_key = None
        current_value = ""

        for speaker, text in speaker_captions:
            if speaker == current_key:
                current_value += text
            else:
                if current_key is not None:
                    merged_captions.append((current_key, current_value))
                current_key = speaker
                current_value = text

        if current_key is not None:
            merged_captions.append((current_key, current_value))

        #print(merged_captions)
        return merged_captions
   
    
    
    def identify_speakers_2(self, transcriptions, diarization, time_shift, waveform_feature:SlidingWindowFeature):
        speaker_captions = []
        speaker_map = {}
        # Iterate over diarization segments
        for segment in diarization.get_timeline():
            
            if segment.duration <=0 or segment.start == segment.end:
                continue

            # Extract start and end times of the segment
            #start, end = segment.start, segment.end
            start = segment.start
            end = segment.end
        
            # Extract the corresponding waveform segment
            frame_start = waveform_feature.sliding_window.closest_frame(start)
            frame_end = waveform_feature.sliding_window.closest_frame(end)
            
            print(frame_start,frame_end)
            #waveform_segment = waveform_feature.data[frame_start:frame_end, :]
            waveform_segment = waveform_feature.data[frame_start:frame_end, :]
            segment_waveSWF = waveform_feature.crop(focus=segment, return_data=False)     

            ## TODO: run transcription on whole segment and then merge diarization/speakers based on timelines
            ## transcription on whole will bring better results

            # Transcribe the segment (using Whisper or Vosk)
            transcription = self.transcribe(segment_waveSWF)
            if transcription['text'] == "":
                continue
            # Convert waveform_segment to a PyTorch tensor
            waveform_segment_tensor = torch.from_numpy(waveform_segment)
            # Ensure the tensor is in the shape (1, num_samples)
            if waveform_segment_tensor.ndim == 2 and waveform_segment_tensor.shape[1] == 1:
                waveform_segment_tensor = waveform_segment_tensor.transpose(0, 1)

            # Perform speaker verification on the segment
            verified_speaker_label = self.verify_speaker(waveform_segment_tensor, speaker_db())

            if verified_speaker_label is None:
                verified_speaker_label = -1 # Fallback to generic label
            
            # Combine transcription text with verified speaker label
            if verified_speaker_label != -1:
                speaker_captions.append((verified_speaker_label, transcription['text'])) 
            
            
        merged_captions = []
        current_key = None
        current_value = ""

        for speaker, text in speaker_captions:
            if speaker == current_key:
                current_value += text
            else:
                if current_key is not None:
                    merged_captions.append((current_key, current_value))
                current_key = speaker
                current_value = text

        if current_key is not None:
            merged_captions.append((current_key, current_value))

        print(merged_captions)

        audio_samples = waveform_feature.data.reshape(-1)

        # Set the sample rate (e.g., 44100 for 44.1 kHz)
        sample_rate = 16000

        # Play the audio
        #import sounddevice as sd
        #sd.default.device = 2
        #sd.play(audio_samples, sample_rate)
        #sd.wait()

        return merged_captions


    def identify_speakers(self, transcription, diarization, time_shift, waveform):
        """Iterate over transcription segments to assign speakers"""
        speaker_captions = []
        for segment in transcription["segments"]:

            # Crop diarization to the segment timestamps
            start = time_shift + segment["words"][0]["start"]
            end = time_shift + segment["words"][-1]["end"]
            dia = diarization.crop(Segment(start, end))

            # Extract the corresponding waveform segment
            # Assuming `waveform` is a SlidingWindowFeature
            #the frame indices corresponding to the start and end times
            frame_start = waveform.sliding_window.closest_frame(start)
            frame_end = waveform.sliding_window.closest_frame(end)

            # Extract the waveform segment from the SlidingWindowFeature
            waveform_segment = waveform.data[frame_start:frame_end,:]
            
            if waveform_segment.ndim == 1:
                waveform_segment = waveform_segment[None, :]  # Add a channel dimension

            # Convert waveform_segment to a PyTorch tensor
            waveform_segment_tensor = torch.from_numpy(waveform_segment)
            # Ensure the tensor is in the shape (1, num_samples)
            if waveform_segment_tensor.ndim == 2 and waveform_segment_tensor.shape[1] == 1:
                waveform_segment_tensor = waveform_segment_tensor.transpose(0, 1)

            # If the audio is stereo (or has more than one channel), convert it to mono
            #if waveform_segment_tensor.shape[0] > 1:
            #    waveform_segment_tensor = torch.mean(waveform_segment_tensor, dim=0)

            #waveform_segment_tensor = waveform_segment_tensor.unsqueeze(0)  # Add channel dimension if needed

            # Assign a speaker to the segment based on diarization
            speakers = dia.labels()
            num_speakers = len(speakers)
            if num_speakers == 0:
                # No speakers were detected
                caption = (-1, segment["text"])
            elif num_speakers == 1:
                # Only one speaker is active in this segment
                spk_id = int(speakers[0].split("speaker")[1])
                #wave_tensor = torch.from_numpy(waveform_segment)
                #wave_tensor_mono = torch.mean(wave_tensor, dim=0)
                #wave_tensor_mono = wave_tensor_mono.unsqueeze(1) 
                verified_speaker_label = self.verify_speaker(waveform_segment_tensor, speaker_db())
                if verified_speaker_label:
                    caption = (verified_speaker_label, segment["text"])
                else:
                    caption = (spk_id, segment["text"])  # Fallback to generic label
 
                #caption = (spk_id, segment["text"])
            else:
                # Multiple speakers, select the one that speaks the most
                max_speaker = int(np.argmax([
                    dia.label_duration(spk) for spk in speakers
                ]))
                caption = (max_speaker, segment["text"])
            speaker_captions.append(caption)

        return speaker_captions

    def __call__(self, diarization:Annotation, waveform:SlidingWindowFeature):
        method_1 = True
        speaker_transcriptions = []
        if method_1:

            transcription = {}
            # Update transcription buffer

            # The audio may not be the beginning of the conversation
            time_shift = waveform.sliding_window.start
            # Step 2: Assign speakers
            speaker_transcriptions = self.identify_speakers_4(transcription, diarization, time_shift, waveform)
        else:
            # Step 1: Transcribe
            transcription = self.transcribe(waveform)
            #transcription = {}
            # Update transcription buffer
            #self._buffer += transcription["text"]
            # The audio may not be the beginning of the conversation
            time_shift = waveform.sliding_window.start
            # Step 2: Assign speakers
            speaker_transcriptions = self.identify_speakers(transcription, diarization, time_shift, waveform)
    
        return speaker_transcriptions


class VoskTranscriber(SpeakerAwareTrascriber):
    def __init__(self) -> None:
        self.model = VoskModel(model_name="vosk-model-en-us-0.22")
        self.rec = KaldiRecognizer(self.model, 16000)

    #def __call__(self, current_buffer: SlidingWindowFeature, sample_rate) -> str:
    def transcribe(self, waveform):
        # we start by applying the model on the current buffer
        waveform_tensor = waveform.data.T       
        waveform_bytes = waveform_to_bytes(waveform_tensor)
        self.rec.AcceptWaveform(waveform_bytes)
        result = json.loads(self.rec.Result())
        return result



class WhisperTranscriber(SpeakerAwareTrascriber):
    def __init__(self, model="small", device=None):
        self.model = whisper.load_model(model, device=device)
        self._buffer = ""
        self.speaker_embeddings = {}
        self.new_speaker_label = 0

    def transcribe(self, waveform):
        """Transcribe audio using Whisper"""
        # Pad/trim audio to fit 30 seconds as required by Whisper
        audio = waveform.data.astype("float32").reshape(-1)
        audio = whisper.pad_or_trim(audio)
        #prompt = "Anomalytica"
        # Transcribe the given audio while suppressing logs
        with suppress_stdout():
            transcription = whisper.transcribe(
                self.model,
                audio,
                #condition_on_previous_text=True,
                #vad=True,
                # We use past transcriptions to condition the model
                #initial_prompt=prompt,
                verbose=True  # to avoid progress bar,
            )

        return transcription

    

def ask_llm(prompt,**kwargs):
    """curl http://localhost:11434/api/generate -d '{
    "model": "bakllava",
    "prompt":"What is in this picture?",
    "images": ["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"]
    }'
    """
    url = "http://localhost:11434/api/generate"
    system_propmpt = """This is telephonic conversation between support-agent and customer. The agent is Sarah representing  company called "Anomalytica". 
    Analyse the conversation and identify if there is any social engineering attempt going on. Respond with json in following format:
     {
        "social_engineering": boolean,
        "social_engineering_type": str,
        "social_engineering_subtype": str,
        "reasoning": str,
        "confidence": float,
        "conversation_sentiments: str,
        "agent_emotions": str,
        "customer_emotions": str,
        "summary_transcript": str" // in 80 words or less
     }. Conversation is as follows in the format [speaker]: text >>> """
    captions = [ f"[{speaker}]:{text}\n" for speaker,text in prompt]
    transcript = "".join(captions)
    prompt = f"{system_propmpt} {transcript}"
    payload = {
        "model": "mistral",
        "prompt":prompt,
        "stream": False,
        **kwargs
    }
    headers = {
        'Content-Type': 'application/json'
    }
    print("######payload", payload)
    response = requests.request("POST", url, headers=headers, data=json.dumps(payload))
    return response.text





huggingface_hub.login(token="REDACTED_HUGGINGFACE_TOKEN")

# Suppress whisper-timestamped warnings for a clean output
logging.getLogger("whisper_timestamped").setLevel(logging.ERROR)

# all values in seconds 
diarization_chunk_duration = 30
diarization_chunk_step = 30
transcription_chunk_duration = 10

# If you have a GPU, you can also set device=torch.device("cuda")
config = SpeakerDiarizationConfig(
    duration=diarization_chunk_duration,
    step=diarization_chunk_step,
    latency="min",
    tau_active=0.5,
    rho_update=0.1,
    delta_new=0.57
)
dia = SpeakerDiarization(config)
segmentation = SpeakerSegmentation.from_pretrained("pyannote/segmentation")

#source = MicrophoneAudioSource(config.sample_rate)
source = FileAudioSource("/Users/sandeep/Documents/SB_Sources/anm_dintel/phishnet/sales_call.wav", config.sample_rate)

# If you have a GPU, you can also set device="cuda"
asr = WhisperTranscriber(model="small", device="cpu")
#asr = VoskTranscriber()

# Split the stream into 2s chunks for transcription
#transcription_duration = transcription_chunk_durations
# Apply models in batches for better efficiency
batch_size = int(transcription_chunk_duration // config.step)

"""
Details about pipeline: uses reactivex library: https://rxpy.readthedocs.io/en/latest/get_started.html

def rearrange_audio_stream(duration: float, step: float, sample_rate: int) -> Observable:  
    Rearranges the audio stream into sliding windows of specified duration and step.
    :param duration: Duration of each window in seconds.
    :param step: Step between windows in seconds.
    :param sample_rate: Sample rate of the audio in Hz.
    :return: reactivex.Observable instance ... Stream of audio chunks.

def buffer_with_count(count: int) -> List:
    Buffers the audio chunks until a batch of specified size is full.
    :param count: Number of audio chunks in each batch.
    :return: List of audio chunks.

def map(dia: Callable) -> Tuple:
    Applies the `dia` function to each audio chunk to obtain diarization prediction.
    :param dia: Function to apply to each audio chunk.
    :return: Sequence[tuple[Annotation, SlidingWindowFeature]]

def map(concat: Callable) -> Tuple:
    Concatenates 500ms predictions/chunks to form a single 2s chunk.
    :param concat: Function to apply to each pair.
    :return: tuple[Annotation, SlidingWindowFeature]`.

def filter(predicate: Callable) -> Tuple:
    Filters out chunks that do not contain speech.
    :param predicate: Function to apply to each pair.
    :return: Pair `(diarization, audio chunk)`.

starmap -> unpacks the tuple and passes the elements as arguments to the function
starmap(asr) -> tuple[Annotation, SlidingWindowFeature] -> asr(Annotation, SlidingWindowFeature)

asr returns list of tuples (speaker, text)
"""

# Chain of operations to apply on the stream of microphone audio
source.stream.pipe(
    # Format audio stream to sliding windows of 5s with a step of 500ms
    
    # dops is custom reactivex operator module defined in diart/ops.py
    dops.rearrange_audio_stream(
        config.duration, config.step, config.sample_rate
    ),
    # Wait until a batch is full
    # The output is a list of audio chunks
    #ops.buffer_with_count(count=batch_size),
    # Obtain diarization prediction
    # The output is a list of pairs `(diarization, audio chunk)`
    #ops.map(dia),
    #ops.map(lambda wav: (segmentation(wav),wav)),
    # Concatenate 500ms predictions/chunks to form a single 2s chunk
    #ops.map(concat),
    # Ignore this chunk if it does not contain speech
    #ops.filter(lambda ann_wav: ann_wav[0].get_timeline().duration() > 0),
    # Obtain speaker-aware transcriptions
    # The output is a list of pairs `(speaker: int, caption: str)`
    ops.map(lambda wav: (None, wav)),
    ops.starmap(asr),
    
    # Color transcriptions according to the speaker
    # The output is plain text with color references for rich
    #ops.map(colorize_transcription),
    ops.map(ask_llm),
    ops.map(lambda x: rich.print(x)),
).subscribe(
    on_next=rich.print,  # print colored text
    on_error=lambda _: traceback.print_exc()  # print stacktrace if error
)

print("Listening...")
source.read()

"""
This is agent-customer conversation in typical contact center scenario.
The agent is Sarah.
Analyse the conversation and identify if there is any social engineering attempt going on. 
>>>
[
    ('Customer_A', ' Hello.'),
    (-1, ' Hello.'),
    ('Sarah', ' Yes. Yes. Sorry.'),
    (-1, ' Mark.'),
    ('Sarah', ' Gluvani?'),
    (-1, ' you'),
    (
        'Sarah',
        " Yeah, hi, sir. I know you're not expecting my call. My name is Sarah. I'm calling from Anomalyeticistur. I sent you a text message. a week ago, were you 
able to get it, sir? I'm not sure."
    )
]
[
    (-1, ' you'),
    ('Customer_A', ' What is audit?'),
    ('Sarah', ' Oh, I see. Okay. First of all, Also, be sent to you a'),
    (-1, ' Thank you. Bye. you'),
    ('Sarah', ' an email about our... company. and also our CEO Sandeep.'),
    (-1, ' you'),
    ('Sarah', " sent you a link and request to connect. So I'm just following up on that, sir, if you. already")
]
[
    (
        'Sarah',
        ' received those messages. but if not, sir. The reason why we are reaching out to you is Sandeep came across your league in profile. and he wants to 
personally get in touch with you, sir. Just to give you an idea about our company, sir, we are a... Thank you.'
    ),
    ('Customer_A', ' you'),
    ('Sarah', ' uh... anomaly did actually')
]
"""
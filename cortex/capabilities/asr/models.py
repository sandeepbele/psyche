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
#from speaker_helper import get_embeddings_from_waveform, perform_matching, get_embeddings_from_waveform_2
from pyannote.audio import Audio
import torch
from vosk import Model as VoskModel, KaldiRecognizer
import json 
import requests
from capabilities.helpers.utils import suppress_stdout
from capabilities.spk.embeddings import speaker_db, get_embeddings_from_waveform_2, get_embeddings_from_waveform, perform_matching
from typing import List, Optional
from timeit import default_timer as timer
import time

from capabilities.asr.backend import WhisperFactory
from capabilities.asr.datamodels import SpeakerSegment, TSegment

def waveform_to_bytes(waveform):
    # Normalize and convert waveform to 16-bit PCM
    # Pyannote usually returns floats in the range [-1, 1]
    waveform_int16 = np.int16(waveform * np.iinfo(np.int16).max)

    # Convert the numpy array to bytes
    waveform_bytes = waveform_int16.tobytes()

    # Convert to bytearray for compatibility with KaldiRecognizer
    return waveform_bytes


# create a django orm model for SpeakerSegment
#class SpeakerSegment(models.Model):
#    start = models.FloatField()
#    end = models.FloatField()
#    speaker = models.CharField(max_length=100)
#    text = models.TextField()
#    transcription = models.ForeignKey(Transcription, on_delete=models.CASCADE)
    

class SpeakerAwareTrascriber:
    
    def verify_speaker(self, waveform_segment, known_speakers):
        # Implement the speaker verification logic
        # Convert waveform_segment to the required format if necessary
        # Compare it with the embeddings of known speakers
        # Return the label of the matched speaker or None if no match is found
        audio = Audio(sample_rate=16000, mono="downmix")
    
        embeddings = get_embeddings_from_waveform_2(waveform_segment)
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
            
            SpeakerSegment(start=time_shift+segment['start'], end=time_shift+segment['end'], speaker=verified_speaker_label, text=segment['text'])
            
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
    

class WhisperTranscriber2():

        def __init__(self, backend, model, device=None, known_speaker_db=None):
            
            self.model = WhisperFactory.get_whisper(backend) #whisper.load_model(model, device=device)
            self.model.load_model(model, device=device)

            self._buffer = ""
            self.speaker_embeddings = {}
            self.new_speaker_label = 0
            self.known_speaker_db = known_speaker_db
            self.segments:List[TSegment] = []
        
        def audio_duration_sec(self):
            return sum([segment.duration() for segment in self.segments])
        
        def evaluation_time_ms(self):
            return sum([segment.ttd_model_ms for segment in self.segments])
        
        def median_evaluation_time_ms(self):
            return np.median([segment.ttd_model_ms for segment in self.segments])
        
        def transcription_length(self):
            return sum( [len(spk_seg.text) for segment in self.segments for spk_seg in segment.speaker_segments ])

        def _verify_speaker(self, waveform_segment, known_speakers):
            embeddings = get_embeddings_from_waveform(waveform_segment)
            for label, known_embedding in known_speakers.items():
                if perform_matching(known_embedding, embeddings):
                    return label
            return None
        
        def diarize_segment(self, segment, waveform, time_shift=0) -> SpeakerSegment:
            # Extract start and end times of the segment
            #start, end = segment.start, segment.end
        
            # Extract the corresponding waveform segment
            frame_start = waveform.sliding_window.closest_frame(time_shift+segment['start'])
            frame_end = waveform.sliding_window.closest_frame(time_shift+segment['end'])
            
            #print(frame_start,frame_end)
            #waveform_segment = waveform_feature.data[frame_start:frame_end, :]
            waveform_segment = waveform.data[frame_start:frame_end, :]
            
            # Convert waveform_segment to a PyTorch tensor
            waveform_segment_tensor = torch.from_numpy(waveform_segment)
            # Ensure the tensor is in the shape (1, num_samples)
            if waveform_segment_tensor.ndim == 2 and waveform_segment_tensor.shape[1] == 1:
                waveform_segment_tensor = waveform_segment_tensor.transpose(0, 1)

            verified_speaker_label = None
            # Perform known speaker verification on the segment if applicable
            if self.known_speaker_db is not None:
                verified_speaker_label = self._verify_speaker(waveform_segment_tensor, self.known_speaker_db)

            # Assign unique speaker label
            if verified_speaker_label is None:
                verified_speaker_label = self._verify_speaker(waveform_segment_tensor, self.speaker_embeddings)
                if verified_speaker_label is None:
                    self.new_speaker_label += 1
                    verified_speaker_label = str(self.new_speaker_label)
                    self.speaker_embeddings[verified_speaker_label] = get_embeddings_from_waveform(waveform_segment_tensor)
                else:
                    self.speaker_embeddings[verified_speaker_label] = np.vstack((self.speaker_embeddings[verified_speaker_label], get_embeddings_from_waveform(waveform_segment_tensor)))

            return SpeakerSegment(start=time_shift+segment['start'], 
                            end=time_shift+segment['end'], 
                            speaker=verified_speaker_label, 
                            text=segment['text'])

        
        def diarize_segment_2(self, segment, audio_tensor, sample_rate, time_shift=0) -> SpeakerSegment:
      
            # Calculate the start and end indices for the segment
            #sample_rate = audio_tensor.shape[0] / waveform_duration
            frame_start = int((time_shift + segment['start']) * sample_rate)
            frame_end = int((time_shift + segment['end']) * sample_rate)

            # Extract the corresponding waveform segment
            waveform_segment = audio_tensor[frame_start:frame_end]
            waveform_segment_tensor = torch.from_numpy(waveform_segment)
            waveform_segment_tensor = waveform_segment_tensor.unsqueeze(0)  # Add channel dimension if needed
            
            # Ensure the tensor is in the shape (1, num_samples)
            if waveform_segment_tensor.ndim == 2 and waveform_segment_tensor.shape[1] == 1:
                waveform_segment_tensor = waveform_segment_tensor.transpose(0, 1)
            
            verified_speaker_label = None
            try: 
                # Perform known speaker verification on the segment if applicable
                if self.known_speaker_db is not None:
                    verified_speaker_label = self._verify_speaker(waveform_segment_tensor, self.known_speaker_db)

                # Assign unique speaker label
                if verified_speaker_label is None:
                    verified_speaker_label = self._verify_speaker(waveform_segment_tensor, self.speaker_embeddings)
                    if verified_speaker_label is None:
                        self.new_speaker_label += 1
                        verified_speaker_label = str(self.new_speaker_label)
                        self.speaker_embeddings[verified_speaker_label] = get_embeddings_from_waveform(waveform_segment_tensor)
                    else:
                        self.speaker_embeddings[verified_speaker_label] = np.vstack((self.speaker_embeddings[verified_speaker_label], get_embeddings_from_waveform(waveform_segment_tensor)))
            except Exception as e:
                print(e)
                print("Error in diarize_segment_2")
                traceback.print_exc()

            return SpeakerSegment(start=time_shift+segment['start'], 
                            end=time_shift+segment['end'], 
                            speaker=verified_speaker_label, 
                            text=segment['text'])
        
        def transcribe(self, waveform:SlidingWindowFeature) -> TSegment:

            tsegment = TSegment()
            
            start_time = time.time()
            
            audio_tensor = waveform.data.astype("float32").reshape(-1)
            transcription = self.model.transcribe_raw(audio_tensor)
            tsegment.ttd_model_ms = (time.time() - start_time) * 1000
                
            time_shift = waveform.sliding_window.start
            
            for segment in transcription['segments']:
                spk_segment = self.diarize_segment(segment, waveform, time_shift)
                tsegment.speaker_segments.append( spk_segment )
                

            # Merge consecutive speaker segments
            tsegment.compact()
            
            tsegment.ttd_rt_ms = (time.time() - start_time) * 1000
            
            self.segments.append(tsegment)
            rich.print("\n",str(tsegment))
            rich.print(f"\nASR completed in: {tsegment.ttd_rt_ms/1000} sec, model evaluation time: {tsegment.ttd_model_ms/1000} sec")
            rich.print("-------------------")
            
            return tsegment
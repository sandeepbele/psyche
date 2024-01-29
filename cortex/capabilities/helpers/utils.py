
import os
import sys
from contextlib import contextmanager

@contextmanager
def suppress_stdout():
    # Auxiliary function to suppress Whisper logs (it is quite verbose)
    # All credit goes to: https://thesmithfam.org/blog/2012/10/25/temporarily-suppress-console-output-in-python/
    with open(os.devnull, "w") as devnull:
        old_stdout = sys.stdout
        sys.stdout = devnull
        try:
            yield
        finally:
            sys.stdout = old_stdout


import io
import torchaudio
import torch
from scipy.io import wavfile

def convert_audio(audio_file_data):
    # Create a BytesIO object from the audio file data
    audio_file = io.BytesIO(audio_file_data)

    # Load the audio file with torchaudio
    waveform, sample_rate = torchaudio.load(audio_file)

    # If the audio is not mono, convert it to mono
    if waveform.size(0) > 1:
        downmix_mono = torchaudio.transforms.DownmixMono()
        waveform = downmix_mono(waveform)

    # If the sample rate is not 16K, resample it to 16K
    if sample_rate != 16000:
        resampler = torchaudio.transforms.Resample(orig_freq=sample_rate, new_freq=16000)
        waveform = resampler(waveform)
        sample_rate = 16000

    return waveform, sample_rate


def split_audio(audio_entity, duration, padding=False, return_type='tensor'):
    # Get the audio file data
    audio_file_data = audio_entity.data

    # Convert the audio to mono and resample it to 16K
    waveform, sample_rate = convert_audio(audio_file_data)

    # Calculate the number of chunks
    num_chunks = waveform.size(1) // (sample_rate * duration)

    # Split the waveform into chunks
    chunks = waveform.split(sample_rate * duration, dim=1)

    # If padding is True and the last chunk is smaller than duration, pad it
    if padding and chunks[-1].size(1) < sample_rate * duration:
        pad_size = sample_rate * duration - chunks[-1].size(1)
        chunks[-1] = torch.nn.functional.pad(chunks[-1], (0, pad_size))

    # If the return type is 'wav', convert the chunks to WAV files
    if return_type == 'wav':
        wav_chunks = []
        for chunk in chunks:
            # Convert the chunk to a numpy array
            chunk_np = chunk.numpy()

            # Create a BytesIO object to hold the WAV file data
            wav_file = io.BytesIO()

            # Write the chunk as a WAV file to the BytesIO object
            wavfile.write(wav_file, sample_rate, chunk_np)

            # Add the BytesIO object to the list of WAV chunks
            wav_chunks.append(wav_file)

        return wav_chunks

    # If the return type is 'SlidingWindow', convert the chunks to SlidingWindow instances
    elif return_type == 'SlidingWindow':
        # You would need to define what a SlidingWindow is and how to convert a chunk to a SlidingWindow
        pass

    # Otherwise, return the chunks as tensors
    else:
        return chunks
    

from celery.result import AsyncResult

def check_task_and_children(task_id):
    # Get the AsyncResult for the task
    task = AsyncResult(task_id)

    # Check the status of the task
    if task.status not in ['SUCCESS', 'FAILURE']:
        return False

    # Check the status of each child task
    for child_task in task.children:
        # Recursively check the status of the child task and its children
        if not check_task_and_children(child_task.id):
            return False

    # If the task and all child tasks are either SUCCESS or FAILURE, return True
    return True
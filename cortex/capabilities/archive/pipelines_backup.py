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
#source = FileAudioSource("/Users/sandeep/Documents/SB_Sources/anm_dintel/phishnet/sales_call.wav", config.sample_rate)
#source = FileAudioSource("/Users/sandeep/Documents/SB_Sources/anm_dintel/phishnet/scam_call_1.wav", config.sample_rate)
source = FileAudioSource("/Users/sandeep/Documents/SB_Sources/anm_dintel/phishnet/social_eng_1.wav", config.sample_rate)


# If you have a GPU, you can also set device="cuda"
#asr = WhisperTranscriber(model="small", device="cpu")
asr = WhisperTranscriber2(model="small", device="cpu")
#asr = VoskTranscriber()

# Split the stream into 2s chunks for transcription
#transcription_duration = transcription_chunk_durations
# Apply models in batches for better efficiency
batch_size = int(transcription_chunk_duration // config.step)

situation_prompt = """This is telephonic conversation between 'alledged' support-agent and customer. Customer recieved a random call. He then called back to enquire about the call."""

#situation_prompt = """This is telephonic conversation between support-agent and customer. The agent is Sarah representing company called "Anomalytica"."""

system_prompt = """You are given just part of the conversation at a time. Analyse it along with prior context and deduce if there is any social engineering or scam attempt going on. 
Do not haste in your judgement.Presence of a link or a phone number does not necessarily mean that it is a social engineering attempt.Understand the context and then decide.

Respond in following format i.e. key >>> value:

social_engineering >>> boolean
scam >>> boolean
reasoning >>> str
conversation_sentiments >>> str
agent_emotions >>> str
customer_emotions >>> str
summary_transcript >>> str // in 80 words or less
"""


prompt = """\
### Instructions:
You are cybersecurity expert specialized in detecting social engineering, human manipulation, scam and fraud attempts. \
You are given just part of the conversation at a time. Analyse it along with prior context and deduce if there is any \
social engineering, manipulation or scam attempt going on. \ 
Adher to output format. \
### Context: This is telephonic conversation between 'alledged' support-agent and customer. Customer recieved a random call. He then called back to enquire about the call.\
    Following is the summary of the conversation that happened so far between the customer and the agent: \
    [SUMMARY]:{CONVERSATION_SUMMARY} \
### Input: {CONVERSATION_SEGMENT}
### Output: Reponse should be in following format i.e. key >>> value where each key and value in on new line. 
Make sure values do not have new lines or if they have they are escaped properly. Key and value should be seperated by >>>. \ 
social_engineering >>> boolean
scam >>> boolean
reasoning >>> str
conversation_sentiments >>> str
agent_emotions >>> list: aggresive, professional, rude, polite, friendly, neutral, manipulative, deceptive
customer_emotions >>> list: aggresive, professional, rude, polite, friendly, neutral, manipulative, deceptive, agitated, angry
summary_transcript >>> str // in 80 words or less

"""


mistral = Ollma(model="mistral", system_prompt=f"{prompt}", stream=False)

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
    #ops.map(lambda wav: (None, wav)),
    #ops.starmap(asr),
    ops.map(lambda wav: asr.transcribe(wav)),
    # Color transcriptions according to the speaker
    # The output is plain text with color references for rich
    #ops.map(colorize_transcription),
    ops.map(mistral.ask_llm),
    ops.map(lambda x: pprint(x)),
).subscribe(
    on_next=rich.print,  # print colored text
    on_error=lambda _: traceback.print_exc()  # print stacktrace if error
)

print("Listening...")
source.read()


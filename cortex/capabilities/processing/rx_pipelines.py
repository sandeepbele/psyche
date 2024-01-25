import traceback
import diart.operators as dops
import rx.operators as ops
import huggingface_hub
import time

from capabilities.asr.models import WhisperTranscriber2
from capabilities.llm.ollama import ConversationMemory, InstructionPromptFactory, OllamaThread, Ollma
from capabilities.processing.base import AbstractPipeline


class ASRWithLLMOnRx(AbstractPipeline):
    
    def __init__(self, source, kwargs):
        self.source = source
        self.kwargs = kwargs
        self.setup()
    
    def setup(self):
        huggingface_hub.login(token=self.kwargs['hf_token'])

    def execute(self):

        asr = WhisperTranscriber2(  backend=self.kwargs['whisper_backend'],
                                    model=self.kwargs['whisper_model'], 
                                    device=self.kwargs['whisper_device'])

        llm_evaluator = OllamaThread(model = self.kwargs['ollama_model'],
                 api_url = self.kwargs['ollama_url'],
                 prompt_format = self.kwargs['ollama_prompt_format'],
                 memory=ConversationMemory(),
                 continue_on_error=self.kwargs['ollama_continue_on_error'])

        self.source.stream.pipe(
            dops.rearrange_audio_stream(
                self.kwargs["audio_source_chunk_size_in_sec"], 
                self.kwargs["audio_source_chunk_step_in_sec"], 
                self.kwargs["audio_source_sample_rate"]
            ),
            ops.map(lambda wav: asr.transcribe(wav)),
            ops.map(lambda tsegment: str(tsegment)),
            ops.map(llm_evaluator.run),
            #ops.map(lambda x: pprint(x.parsed_response)),
        ).subscribe(
            #on_next=rich.print,  # print colored text
            on_error=lambda _: traceback.print_exc() , # print stacktrace if error
            on_completed=lambda: print(f"Completed: total evaluation time in sec:llm:{llm_evaluator.run_duration()},asr:{asr.evaluation_time_ms()/1000},total:{(llm_evaluator.run_duration() + (asr.evaluation_time_ms()/1000))}")
        )
        print("Listening...")
        start = time.time()
        self.source.read()
        print (f"Audio duration in sec:{asr.audio_duration_sec()}")
        print (f"Total run time in sec:{(time.time() - start)}")
    
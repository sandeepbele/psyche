from pyannote.core import SlidingWindowFeature, SlidingWindow
import diart.operators as dops
import traceback
import rx.operators as ops
import time
from celery import Celery, group, chain
from capabilities.processing.base import TrackablePipeline, AbstractPipeline
from capabilities.processing.tasks import asr_raw_task, asr_segment_task, asr_whole_task, process_llm, transcribe


class ASRWithLLMOnCelery(TrackablePipeline):

    PIPELINE_TYPE = "asr_llm_celery"

    def __init__(self, source, kwargs):
        super().__init__(self.PIPELINE_TYPE)
        self.source = source
        self.kwargs = kwargs
        self.segment_start_time = 0
        self.status = 0
        self.setup()

    def setup(self):
        pass

    def _execute(self):
        if self.status == 1:
            print("Pipeline already executed")
            return

        # convert wav tensor to SlidingWindowFeature
        # source does not have sliding window feature
        # we need to create one
        """def process_wav(wav):
            print("...start")
            sw = SlidingWindow( start=self.segment_start_time, 
                        duration=self.kwargs['audio_source_chunk_size_in_sec'], 
                        step=1/self.kwargs['audio_source_sample_rate'] )

            slw = SlidingWindowFeature(data = wav, sliding_window=sw)"""


        def asr_pipeline_as_multiple_tasks(wav):
            start_time = time.time()
            audio_tensor = wav.astype("float32").reshape(-1)
            asr_kwargs = {key: self.kwargs[key] for key in self.kwargs.keys() if not key.startswith('ollama')}
            audio_task = asr_raw_task.delay(asr_kwargs, audio_tensor)
            tsegment = audio_task.get()
            #print(str(tsegment))
            print(f"###### time in sec for raw transcription:{time.time() - start_time}")      
            
            segment_tasks = group([asr_segment_task.s(asr_kwargs, segment,audio_tensor, self.kwargs['audio_source_sample_rate'], self.segment_start_time ) for segment in tsegment['segments']])()
            segments = segment_tasks.get()
            for segment in segments:
                print(segment)
                
            self.segment_start_time += self.kwargs['audio_source_chunk_size_in_sec']
            print(f"###### time in sec for segment:{time.time() - start_time}")

        def asr_pipeline_single_task(wav):
            #nonlocal segment_start_time
            start_time = time.time()
            audio_tensor = wav.astype("float32").reshape(-1)
            asr_kwargs = {key: self.kwargs[key] for key in self.kwargs.keys() if not key.startswith('ollama')}
            audio_task = asr_whole_task.delay(asr_kwargs, audio_tensor, self.kwargs['audio_source_sample_rate'], self.segment_start_time)
            tsegment = audio_task.get()
            print(str(tsegment))
            self.segment_start_time += self.kwargs['audio_source_chunk_size_in_sec']
            print(f"###### time in sec for segment:{time.time() - start_time}")


        def asr_llm_pipeline(wav):
            #nonlocal segment_start_time
            context = {"pipeline_run_id": self.pipeline_run_id}
            
            start_time = time.time()
            audio_tensor = wav.astype("float32").reshape(-1)
            asr_kwargs = {key: self.kwargs[key] for key in self.kwargs.keys() if not key.startswith('ollama')}
            audio_task = asr_whole_task.delay(asr_kwargs, audio_tensor, self.kwargs['audio_source_sample_rate'], self.segment_start_time)
            tsegment = audio_task.get()
            print(str(tsegment))
            self.segment_start_time += self.kwargs['audio_source_chunk_size_in_sec']
            print(f"###### time in sec for segment:{time.time() - start_time}")

            result = process_llm.delay(str(tsegment), self.kwargs)
            ollama_run = result.get()
            print(ollama_run.parsed_response)
            print(f"###### time taken for ollama run:{time.time() - start_time}")


        asr_kwargs = {key: self.kwargs[key] for key in self.kwargs.keys() if not key.startswith('ollama')}
        context = {"pipeline_run_id": self.pipeline_run_id}
        try:
            self.source.stream.pipe(
                dops.rearrange_audio_stream(
                self.kwargs["audio_source_chunk_size_in_sec"], 
                self.kwargs["audio_source_chunk_step_in_sec"], 
                self.kwargs["audio_source_sample_rate"]
                ),
                #ops.map(lambda sliding_window: asr_llm_pipeline(sliding_window.data)),
                ops.map(lambda sliding_window: transcribe.s(sliding_window, kwargs=asr_kwargs, context=context) | process_llm.s(kwargs=self.kwargs, context=context)),  
                ops.map(lambda celery_chain: celery_chain.delay().get()),
                ops.map(lambda result: print(result)),
            ).subscribe(
                on_error=lambda _: traceback.print_exc(),  # print stacktrace if error
                on_completed=lambda: print(f"Completed")
            )
            self.source.read()
        finally:
            print("Stopping...")
            #self.source.stop()
            self.status = 1
            print("Stopped")

    
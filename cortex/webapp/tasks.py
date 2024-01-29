from celery import shared_task
from capabilities.processing.base import TrackablePipeline
import logging
from capabilities.pipeline_config import config as kwargs
from diart.sources import FileAudioSource
import diart.operators as dops
import tempfile
from capabilities.models import Entity, PipelineRun
from rx import operators as ops
from capabilities.processing.tasks import process_llm, transcribe
import traceback
from datetime import datetime

logger = logging.getLogger(__name__)



@shared_task
def process_audio_llm_task(pipeline_run_id, entity_id):

    def cleanup(temp_file, pipeline, status):
        pipeline.status=status
        pipeline.completed_at=datetime.now()
        pipeline.save()
        if temp_file is not None:
            temp_file.close()

    logger.debug("executing process_audio_llm_task")
    temp_file = None
    try:
        pipeline = PipelineRun.objects.get(id=pipeline_run_id)
        pipeline.status="running"
        pipeline.save()

        asr_kwargs = {key: kwargs[key] for key in kwargs.keys() if not key.startswith('ollama')}
        context = {"pipeline_run_id": pipeline_run_id}

        # Get the Entity instance with the specific id
        entity = Entity.objects.get(id=entity_id)

        # Create a temporary file
        temp_file = tempfile.NamedTemporaryFile(delete=True)
        # Write the audio file data to the temporary file
        temp_file.write(entity.data)
        
    except:
        pipeline.status="error"
        traceback.print_exc()
        logger.error(f"Error in process_audio_llm_task: {traceback.format_exc()}")
        return

    print("Stopped")
    # Create a FileAudioSource with the temporary file
    source = FileAudioSource(temp_file.name, kwargs["audio_source_sample_rate"])
    chunk_counter = 0
    def update_chunk_counter():
        nonlocal chunk_counter
        chunk_counter += 1
        logger.info(f"### Chunk_counter:{chunk_counter}")

    source.stream.pipe(
        dops.rearrange_audio_stream(
        kwargs["audio_source_chunk_size_in_sec"], 
        kwargs["audio_source_chunk_step_in_sec"], 
        kwargs["audio_source_sample_rate"]
        ),
        #ops.map(lambda sliding_window: asr_llm_pipeline(sliding_window.data)),
        ops.map(lambda sliding_window: transcribe.s(sliding_window, kwargs=asr_kwargs, context={**context,'chunk_num':chunk_counter}) | process_llm.s(kwargs=kwargs, context={**context,'chunk_num':chunk_counter})),  
        ops.map(lambda celery_chain: celery_chain.delay()),
        #ops.map(lambda result: print(result)),
        ops.map(lambda result: update_chunk_counter()),
    ).subscribe(
        on_error=lambda _: traceback.print_exc(), #cleanup(temp_file,pipeline, "error"),  # print stacktrace if error  
        on_completed=lambda: cleanup(temp_file,pipeline, "completed")
    )
    logger.debug("Starting to read audio file")
    source.read()
    logger.info(f"Chuncks sent:{chunk_counter}")

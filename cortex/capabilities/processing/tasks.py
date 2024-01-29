from typing import Any, Dict, Optional
from capabilities.asr.datamodels import TSegment
from capabilities.asr.models import WhisperTranscriber2
from celery import Celery
from capabilities.llm.ollama import ConversationMemory, OllamaThread
from pydantic import BaseModel
from capabilities.services import ArtifactService

#app = Celery('tasks', broker='redis://localhost:6379/0', result_backend='redis://localhost:6379/0')
#app.conf.event_serializer = 'pickle' # this event_serializer is optional. somehow i missed this when writing this solution and it still worked without.
#app.conf.task_serializer = 'pickle'
#app.conf.result_serializer = 'pickle'
#app.conf.accept_content = ['application/json', 'application/x-python-serialize']
#app.conf.task_accept_content = ['application/json', 'application/x-python-serialize']
#app.conf.result_accept_content = ['application/json', 'application/x-python-serialize']

from celery import shared_task, current_task
import logging, time

logger = logging.getLogger(__name__)


from functools import wraps


class TaskResult:
    def __init__(self, return_result, store_result, processor_type):
        self.return_result = return_result
        self.store_result = store_result
        self.processor_type = processor_type

def store_artifact(processor_type, artifact_type):
    def decorator(task_func):
        @wraps(task_func)
        def wrapper(*args, **kwargs):
            start_time = time.time()
            # Extract context and task_kwargs
            context = kwargs.pop('context', {})
            task_kwargs = kwargs.pop('kwargs', {})

            # Call the task function with task_kwargs
            result = task_func(*args, kwargs=task_kwargs, context=context)
            end_time = time.time()
            total_run_time = end_time - start_time

            # Extract pipeline_run_id and determine the data to log
            pipeline_run_id = context.get('pipeline_run_id')
            data_to_log = result.store_result if isinstance(result, TaskResult) else result
            logger.debug(f"Logging data of type {type(data_to_log)}, pipeline_run_id={pipeline_run_id} ")

            if isinstance(data_to_log, BaseModel) \
                and pipeline_run_id is not None:
                # Log the result using ArtifactStoreService
                ArtifactService.store(
                    pipeline_run_id=pipeline_run_id,
                    processor_type=processor_type,
                    artifact_type=artifact_type,
                    data=data_to_log,
                    metadata={
                        'task_id': current_task.request.id,
                        'ts_called': start_time,
                        'total_run_time_ms': total_run_time * 1000,
                        'origin': current_task.request.hostname,
                        'root_task_id': current_task.request.root_id,
                        'context': context
                    }
                )
            else:
                logger.error(f"Cannot log data of type {type(data_to_log)}")

            # Return the result for the next task
            return result.return_result if isinstance(result, TaskResult) else result

        return wrapper
    return decorator

@shared_task
def add(x, y):
    return x + y

@shared_task
def on_raw_message(self,body):
    print("Received raw message: %r" % body)
    self.app.log.info("Received raw message: %r" % body)

@shared_task
def asr_raw_task(kwargs , audio_tensor):
    asr = WhisperTranscriber2(  backend=kwargs['whisper_backend'],
                                    model=kwargs['whisper_model'], 
                                    device=kwargs['whisper_device'])
    return asr.model.transcribe_raw(audio_tensor)

@shared_task
def asr_segment_task(kwargs , segment, audio_tensor, sample_rate, time_shift):
    asr = WhisperTranscriber2(  backend=kwargs['whisper_backend'],
                                    model=kwargs['whisper_model'], 
                                    device=kwargs['whisper_device'])
    return asr.diarize_segment_2(segment, audio_tensor, sample_rate, time_shift=0)

@shared_task
def asr_whole_task(kwargs, audio_tensor, sample_rate, time_shift):
    logger.debug(f"starting raw transcription")
    tsegment = TSegment()
    asr = WhisperTranscriber2(  backend=kwargs['whisper_backend'],
                                    model=kwargs['whisper_model'], 
                                    device=kwargs['whisper_device'])
    logger.debug(f"loaded model")
    transcription = asr.model.transcribe_raw(audio_tensor)
    logger.debug(f"finished raw transcription")

    for segment in transcription['segments']:
        spk_segment = asr.diarize_segment_2(segment, audio_tensor, sample_rate, time_shift=0)
        tsegment.speaker_segments.append(spk_segment)
        logger.debug(f"finished segment diarization")

    logger.debug(f"finished whole transcription")
    return tsegment

@shared_task
@store_artifact(processor_type='llm', artifact_type='RAW')
def process_llm(prompt,kwargs,context):
    llm_evaluator = OllamaThread(model = kwargs['ollama_model'],
                api_url = kwargs['ollama_url'],
                prompt_format = kwargs['ollama_prompt_format'],
                memory=ConversationMemory(),
                continue_on_error=kwargs['ollama_continue_on_error'])
    
    return llm_evaluator.run(prompt, kwargs)

@shared_task
@store_artifact(processor_type='asr', artifact_type='RAW')
def transcribe(audio_sliding_window_feature: Any, kwargs: Dict[str, Any], context: Optional[Any] = None) -> str:
    """
    Transcribes the given audio feature using the WhisperTranscriber2.

    Args:
        audio_sliding_window_feature: The audio feature to transcribe.
        kwargs: A dictionary containing the keyword arguments for the WhisperTranscriber2.
        context: A dictionary containing the context for the task. This argument is ignored by the function.

    Returns:
        A string containing the transcription result. Note that the function actually returns a TaskResult object,
        but due to the log_artifact decorator, the returned value when calling this function will be the next_result
        member of the TaskResult object, which is a string.
    """    
    asr = WhisperTranscriber2(backend=kwargs['whisper_backend'],
                              model=kwargs['whisper_model'],
                              device=kwargs['whisper_device'])
    tsegment = asr.transcribe(audio_sliding_window_feature)
    
    return TaskResult(return_result=str(tsegment), 
                      store_result=tsegment, 
                      processor_type='asr')


if __name__ == '__main__':
    pass #app.start()
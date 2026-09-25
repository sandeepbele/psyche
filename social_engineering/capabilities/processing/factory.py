from capabilities.pipeline_config import config
from capabilities.processing.celery_pipelines import ASRWithLLMOnCelery
from capabilities.processing.rx_pipelines import ASRWithLLMOnRx
from diart.sources import MicrophoneAudioSource, FileAudioSource
from capabilities.pipeline_config import config

def get_audio_file_processing_pipeline(audio_file_path,backend,pipeline_run_id=None):
    source = FileAudioSource(audio_file_path, config['audio_source_sample_rate'])
    pipeline = None
    if backend == 'rx':
        pipeline = ASRWithLLMOnRx(source, config, pipeline_run_id)     
    elif backend == 'celery':
        pipeline = ASRWithLLMOnCelery(source, config, pipeline_run_id)
    else:
        raise Exception(f"Invalid backend:{backend}")

    return pipeline
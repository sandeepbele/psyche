from django.core.management.base import BaseCommand
from capabilities.processing.celery_pipelines import ASRWithLLMOnCelery
from capabilities.processing.rx_pipelines import ASRWithLLMOnRx
from diart.sources import MicrophoneAudioSource, FileAudioSource
from capabilities.pipeline_config import config
from capabilities.processing.factory import get_audio_file_processing_pipeline

class Command(BaseCommand):
    help = 'Runs the ASR LLM pipeline'

    def add_arguments(self, parser):
        parser.add_argument('-f','--audio_file', required=True)
        parser.add_argument('-b','--backend', required=True, choices=['rx','celery'])

    def handle(self, *args, **options):
        audio_file = options['audio_file']
        backend = options['backend']

        """source = FileAudioSource(audio_file, config['audio_source_sample_rate'])
        pipeline = None
        if backend == 'rx':
            pipeline = ASRWithLLMOnRx(source, config)
        elif backend == 'celery':
            pipeline = ASRWithLLMOnCelery(source, config)
        else:
            raise Exception(f"Invalid backend:{backend}")"""
            
        try:
            pipeline = get_audio_file_processing_pipeline(audio_file,backend)
            pipeline.execute()
        except Exception as e:
            print(f"Error: {e}")
            return
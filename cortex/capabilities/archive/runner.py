from voice.prompts import get_prompt_template
from voice.llm.ollama import ConversationMemory, InstructionPromptFactory, OllamaThread
from diart.sources import MicrophoneAudioSource, FileAudioSource

from voice.processing.rx_pipelines import ASRWithLLMOnRx
from voice.processing.celery_pipelines import ASRWithLLMOnCelery
import click
import time


kwargs = {}
kwargs['audio_source_sample_rate'] = 16000
kwargs['audio_source_channels'] = 1

# 30 sec chunks with next chunk starting after 30 sec so no overlap
# if step is 20 then there is 10 sec overlap between chunks
kwargs['audio_source_chunk_size_in_sec'] = 30
kwargs['audio_source_chunk_step_in_sec'] = 30 

kwargs['whisper_backend'] = 'whisper_timestamped'
kwargs['whisper_model'] = 'small'
kwargs['whisper_device'] = 'cpu'
kwargs['ollama_url'] = 'http://localhost:11434/api/generate'
kwargs['ollama_model'] = 'mistral'

prompt_template = get_prompt_template('social_engineering_1')
prompt_format = InstructionPromptFactory(
            system_instruction=prompt_template['system_instruction'], 
            input_guidance=prompt_template['input_guidance'], 
            output_guidance=prompt_template['output_guidance'])

kwargs['ollama_prompt_format'] = prompt_format
#kwargs['ollama_output_parser'] = parse_to_dict
kwargs['ollama_continue_on_error'] = True

kwargs['hf_token'] = 'REDACTED_HUGGINGFACE_TOKEN'


@click.command()
@click.option('-f','--audio_file', required=True, type=click.Path('rb'))
@click.option('-b','--backend', required=True, type=click.Choice(['rx','celery']))
def asr_llm_pipeline(audio_file,backend='rx'):
    
    source = FileAudioSource(audio_file, kwargs['audio_source_sample_rate'])
    pipeline = None
    if backend == 'rx':
        pipeline = ASRWithLLMOnRx(source,kwargs)
    elif backend == 'celery':
        pipeline = ASRWithLLMOnCelery(source,kwargs)
    else:
        raise Exception(f"Invalid backend:{backend}")
    
    pipeline.execute()


if __name__ == '__main__':
    """
    sample command: python -m runner -f "/Users/sandeep/Documents/SB_Sources/anm_dintel/phishnet/scam_call_1.wav" -b "celery"
    """
    start_time = time.time()
    asr_llm_pipeline() #("/Users/sandeep/Documents/SB_Sources/anm_dintel/phishnet/scam_call_1.wav","rx") 
    print(f"Total time in sec:{time.time() - start_time}")

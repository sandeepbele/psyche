import os
from capabilities.llm.ollama import InstructionPromptFactory
from capabilities.prompts import get_prompt_template

config = {}
config['audio_source_sample_rate'] = 16000
config['audio_source_channels'] = 1

# 30 sec chunks with next chunk starting after 30 sec so no overlap
# if step is 20 then there is 10 sec overlap between chunks
config['audio_source_chunk_size_in_sec'] = 30
config['audio_source_chunk_step_in_sec'] = 30 

config['whisper_backend'] = 'whisper_timestamped'
config['whisper_model'] = 'small'
config['whisper_device'] = 'cpu'
config['ollama_url'] = 'http://localhost:11434/api/generate'
config['ollama_model'] = 'mistral'

prompt_template = get_prompt_template('social_engineering_1')
prompt_format = InstructionPromptFactory(
            system_instruction=prompt_template['system_instruction'], 
            input_guidance=prompt_template['input_guidance'], 
            output_guidance=prompt_template['output_guidance'])

config['ollama_prompt_format'] = prompt_format
#kwargs['ollama_output_parser'] = parse_to_dict
config['ollama_continue_on_error'] = True

config['hf_token'] = os.environ.get('HUGGINGFACE_TOKEN', '')

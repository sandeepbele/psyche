import requests
import json
from pprint import pprint
from datetime import datetime
from typing import List
import rich 
import re

from capabilities.llm.datamodels import OllamaRun 

class BaseMemory:
    def __init__(self):
        self.memory = []
    
    def add(self, item):
        self.memory.append(item)
    
    def get(self):
        return self.memory
    
    def clear(self):
        self.memory = []

    def len(self):
        return len(self.memory)
    
class ConversationMemory(BaseMemory):
    def __init__(self,buffer_size=-1):
        super().__init__()
        self.buffer_size = buffer_size
    
    def get(self):
        return super().get()[-self.buffer_size:] if self.buffer_size > 0 else super().get()

class SummarizedConversationMemory(BaseMemory):
    pass

class BasePrompt:
    def get_completed_prompt(self, **kwargs):
        raise NotImplementedError
    
class InstructionPromptFactory(BasePrompt):
               
    def __init__(self, system_instruction, input_guidance=None, output_guidance=None, **kwargs):
        self.system_instruction = system_instruction
        self.input_guidance = input_guidance
        self.output_guidance = output_guidance
        self.kwargs = kwargs
    
    def get_completed_prompt(self, prompt, memory=None, **kwargs):
        
        full_prompt = f"""###Instructions:\n {self.system_instruction}"""

        if memory is not None and memory.len() > 0:
            full_prompt += f"""###Memory:\n {" ".join([str(item) for item in memory.get()])}"""

        if self.input_guidance:
            full_prompt += f"""###Input:\n {self.input_guidance}"""

        full_prompt += f"""\n{prompt}"""
        
        if self.output_guidance:
            full_prompt += f"""###Output:\n {self.output_guidance}"""      
        
        return full_prompt.format(**self.kwargs)
    

# create a class to encapsulate the logic
class Ollma:
    
    def __init__(self, model, system_prompt,stream=False, **kwargs):
        self.model = model
        self.sys_prompt = system_prompt
        self.kwargs = kwargs
        self.url = "http://localhost:11434/api/generate"
        self.headers = {
            'Content-Type': 'application/json'
        }
        self.stream = stream
        self.context = ""
    
    @staticmethod
    def _parse_to_dict(input_string):
        """ format:
        social_engineering >>> boolean
        reasoning >>> str
        conversation_sentiments >>> str
        agent_emotions >>> str
        customer_emotions >>> str
        summary_transcript >>> str
        """
        lines = input_string.strip().split("\n")
        result = {}
        for line in lines:
            if line == "": 
                continue
            key, value = line.split(" >>> ")
            if value == "boolean":
                result[key] = False  # or True, depending on your default value
            else:
                result[key] = value
        return result


    def ask_llm(self, prompt, **kwargs):
        # rewrite for Ollma method
        #prompt = f"{self.sys_prompt} | Prior conversation context: {self.context} | Actual conversation segment: {prompt}"
        #prompt = " ".join( f"[{speaker}]:{transcript}\n" for speaker, transcript in prompt)
        prompt = self.sys_prompt.format(CONVERSATION_SEGMENT = prompt, CONVERSATION_SUMMARY = self.context)
        payload = {
            "model": self.model,
            "prompt":prompt,
            "stream": self.stream,
            **kwargs
        }
        
        pprint(payload)
        
        response = requests.request("POST", self.url, headers=self.headers, data=json.dumps(payload))
        res_json = response.json()
        #pprint(res_json['response'])

        res_dict = self._parse_to_dict(res_json['response'])
        if 'summary_transcript' in res_dict:
            self.context += f" {res_dict['summary_transcript']}"
        if 'social_engineering' in res_dict:
            self.context += f" Social engineering detected so far:{res_dict['social_engineering']}"
        
        return res_dict
    
   
    



    def ask_llm2(prompt,**kwargs):
        """curl http://localhost:11434/api/generate -d '{
        "model": "bakllava",
        "prompt":"What is in this picture?",
        "images": ["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"]
        }'
        """
        url = "http://localhost:11434/api/generate"
        system_propmpt = """This is telephonic conversation between support-agent and customer. The agent is Sarah representing  company called "Anomalytica". 
        Analyse the conversation and identify if there is any social engineering attempt going on. Respond with json in following format:
        {
            "social_engineering": boolean,
            "social_engineering_type": str,
            "social_engineering_subtype": str,
            "reasoning": str,
            "confidence": float,
            "conversation_sentiments: str,
            "agent_emotions": str,
            "customer_emotions": str,
            "summary_transcript": str" // in 80 words or less
        }. Conversation is as follows in the format [speaker]: text >>> """
        captions = [ f"[{speaker}]:{text}\n" for speaker,text in prompt]
        transcript = "".join(captions)
        prompt = f"{system_propmpt} {transcript}"
        payload = {
            "model": "mistral",
            "prompt":prompt,
            "stream": False,
            **kwargs
        }
        headers = {
            'Content-Type': 'application/json'
        }
        print("######payload", payload)
        response = requests.request("POST", url, headers=headers, data=json.dumps(payload))
        return response.text


class OllamaThread():

    def __init__(self, 
                 model:str,
                 api_url:str,
                 prompt_format:BasePrompt,
                 memory:BaseMemory,
                 output_parser:callable=None,
                 continue_on_error:bool=False,
                **kwargs) -> None:
        self.model = model
        self.api_url = api_url
        self.prompt_format = prompt_format
        self.memory = memory
        self.output_parser = output_parser
        self.continue_on_error = continue_on_error
        self.kwargs = kwargs
        self.runs:List[OllamaRun] = []

    def start_ts(self) -> datetime:
        return self.runs[0].req_initiated_ts

    def end_ts(self)-> datetime:
        return self.runs[-1].req_completed_ts
    
    def run_duration(self):
        return (self.end_ts() - self.start_ts()).total_seconds()

    def _parse_to_dict(self,input_string):
        """ format:
        social_engineering >>> boolean
        reasoning >>> str
        conversation_sentiments >>> str
        agent_emotions >>> str
        customer_emotions >>> str
        summary_transcript >>> str
        """
        lines = re.split(r"\n+", input_string.strip()) 
        result = {}
        for line in lines:
            if line == "": 
                continue
            key, value = re.split(r">+", line, maxsplit=1) 
            key = key.strip()
            result[key] = value.strip()

        return result
    
    def run(self, prompt:str, kwargs:dict=None) -> OllamaRun:
        run = OllamaRun(id=len(self.runs), prompt=prompt)
        run.req_initiated_ts = datetime.now()
        try:
            prompt = self.prompt_format.get_completed_prompt(prompt, memory=self.memory, **self.kwargs)
            run.prompt = prompt
            
            payload = {
                "model": self.model,
                "prompt":prompt,
                "stream": False
            }
            headers = {
                'Content-Type': 'application/json'
            }
            #pprint(payload)
            response = requests.request("POST", self.api_url, headers=headers, data=json.dumps(payload))
            if response.status_code != 200:
                raise Exception(f"Error occured while calling API: {response.status_code},{response.text}")
            #pprint(response.text)
            res_json = response.json()
            
            run.raw_response = res_json['response']
            if self.output_parser is not None:
                run.parsed_response = self.output_parser(res_json['response'])
            else:
                run.parsed_response = self._parse_to_dict(res_json['response'])

            self.memory.add(run.parsed_response['summary_transcript']) if 'summary_transcript' in run.parsed_response else None
            
            rich.print(f"Scam:{run.parsed_response['scam']}\nSocial Engineering:{run.parsed_response['social_engineering']}\nReasoning:{run.parsed_response['reasoning']}")
            
        except Exception as e:
            print(f"Error in Ollama Run:" , e)
            e.print_stack()
            run.error = str(e)
        finally:
            run.req_completed_ts = datetime.now()
            run.ttr_model_ms = run.req_completed_ts - run.req_initiated_ts
            run.ttr_rt_ms = run.req_completed_ts - run.req_initiated_ts
            run.input_tokens = len(run.prompt.split(" "))
            run.output_tokens = len(run.raw_response.split(" ")) if run.raw_response else 0
            self.runs.append(run)
            if not self.continue_on_error and run.error:
                raise e
            rich.print(f"\nOllma run completed in {run.ttr_model_ms.total_seconds()} sec")
            rich.print("-----------------------------------")
            return run
        
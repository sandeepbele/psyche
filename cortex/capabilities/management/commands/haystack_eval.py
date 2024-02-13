#new command

from django.core.management.base import BaseCommand

from haystack.document_stores.in_memory import InMemoryDocumentStore
from haystack_integrations.document_stores.elasticsearch import ElasticsearchDocumentStore
from pprint import pprint
from haystack.components.builders import PromptBuilder
from haystack.pipeline import Pipeline
from haystack import Document
import json
from haystack.components.retrievers.in_memory import InMemoryBM25Retriever
from haystack_integrations.components.generators.ollama import OllamaGenerator
import time
from haystack.components.generators import HuggingFaceLocalGenerator
from haystack import component
from transformers import pipeline
from typing import List

import logging, random

from capabilities.models import Artifact, Entity


 

@component
class HuggingFaceSummarizer:
    def __init__(self, model_name="google/pegasus-xsum"):
        # Initialize the summarization model
        self.summarizer = pipeline("summarization", model=model_name)

    @component.output_types(documents=List[Document])
    def run(self, documents: List[Document], merge: bool = True):
        logger = logging.getLogger("haystack")
        if len(documents) == 0:
            return {"documents": []}
        
        # merge all documents into single document
        max_length = 200

        if merge:
            content = ""
            for doc in documents:
                content = f"{content} {doc.content}"
            
            #max_length = 130 * len(documents)
            summary_text = ""
            if len(content) < max_length:
                summary_text = content
            else:
                summary = self.summarizer(content.replace("|","\n"), max_length=max_length, min_length=30, do_sample=False)
                summary_text = summary[0]['summary_text']
            
            #summary = self.summarizer(summary_text.replace("|","\n"), max_length=130, min_length=30, do_sample=False)
            #logger.debug(f"###summary:{summary}")
            return {"documents": [{"content": summary_text, "meta": {"original_doc_id": "merged"}}]}
        else:
            summarized_docs = []
            for doc in documents:
                summary = self.summarizer(doc.content, max_length=130, min_length=30, do_sample=False)
                summarized_docs.append({"content": summary[0]['summary_text'], "meta": {"original_doc_id": doc.id}})
            return {"documents": summarized_docs}

@component
class TranscriptionSegmentPreprocessor:

    @component.output_types(documents=List[Document])
    def run(self, transcriptions: List[Document]):  
        """
        Sample Document:
        {'start': None, 'end': None, 
        'speaker_segments': [
            {'start': 5.9, 'end': 8.06, 'speaker': '1', 'text': ' Thank you for calling IRS, call me out to you.'}, 
            {'start': 8.24, 'end': 14.22, 'speaker': '2', 'text': " Yeah, you called me and I'm just trying to get this squared away with the bill or something that I owe you guys."}, 
            {'start': 16.44, 'end': 18.0, 'speaker': '1', 'text': ' Okay, so when did you got a call, sir?'}, 
            {'start': 18.36, 'end': 19.6, 'speaker': '2', 'text': ' About 20 minutes ago.'}, 
            {'start': 20.36, 'end': 21.17, 'speaker': '3', 'text': ' The same number?'}, 
            {'start': 21.78, 'end': 27.3, 'speaker': '1', 'text': ' Yes. Okay, may I know one speaking to you?'}, 
            {'start': 27.58, 'end': 27.84, 'speaker': '2', 'text': ' Craig?'}], 
            'ttd_model_ms': 39580.19304275513, 'ttd_rt_ms': 47159.247159957886
        }
        """
        processed_docs = []
        for doc in transcriptions:
            content = ""
            for seg in doc.content['speaker_segments']:
                content = f"{content} # [Speaker_{seg['speaker']}] : {seg['text']}"
            processed_docs.append(Document(content=content,meta=doc.meta))
        
        return {"documents": processed_docs}

class ArtifactRetriever:

    @component.output_types(documents=List[Document])
    def run(self,filters:dict, sort:List[str] = None, limit:int = 10, offset:int = 0, **kwargs):
        entities = Artifact.objects.filter(**filters).order_by(*sort)[offset:offset+limit]
        documents = []
        for entity in entities:
            documents.append(Document(content=entity.data, meta=entity.meta))
        return {"documents": documents}
    


class Command(BaseCommand):
    help = 'Dumps the data from the capabilities app'

    def handle(self, *args, **options):

        logging.basicConfig(format="%(levelname)s - %(name)s -  %(message)s", level=logging.WARNING)
        logger = logging.getLogger("haystack")
        logger.setLevel(logging.DEBUG)

        #document_store = InMemoryDocumentStore()
        #document_store = ElasticsearchDocumentStore(hosts = "http://localhost:9200")
        dataset = json.load(open("artifacts.json"))
        pipeline_run_id = random.randint(1,1000)
        for record in dataset:
            start_time = time.time()
            data = json.loads(record['fields']['data'])
            """content = ""
            for seg in data['speaker_segments']:
                #pprint(seg)
                content = f"{content} # [Speaker_{seg['speaker']}] : {seg['text']}"
            print(f"{content}\n")"""
         
            template = """
            Given the following information, answer the question.

            Context:
            {% for document in documents %}
                {{ document.content }}
            {% endfor %}

            Question: {{query}}
            Output format: { 'scam': 'yes', 'social_engineering':'no','reasoning': 'because ...'}
            Answer:
            """
            summarizer =  HuggingFaceSummarizer(model_name="sshleifer/distilbart-cnn-12-6")

            pipe = Pipeline()
            pipe.add_component('preprocessor',TranscriptionSegmentPreprocessor())
            pipe.add_component('summarizer',summarizer)
            pipe.add_component('retriever', ArtifactRetriever())
            #pipe.add_component("retriever", InMemoryBM25Retriever(document_store=document_store))
            pipe.add_component("prompt_builder", PromptBuilder(template=template))
            pipe.add_component("llm", OllamaGenerator(model="mistral", url="http://localhost:11434/api/generate"))
            #pipe.connect("retriever","summarizer")
            #pipe.connect("preprocessor","summarizer")
            #pipe.connect("summarizer","prompt_builder.documents")
            pipe.connect("retriever", "prompt_builder.documents")
            pipe.connect("prompt_builder", "llm")
            #pipe._debug = True
            #pipe.get_component("prompt_builder").debug = True

            query = """This is telephonic conversation between possible customer service agent and a person.Is agent trying to scam the person? \
                Or Do you see any social engineering attempt? If yes then provide short reasoning.If not then don't be verbose. Provide output in json in given format."""

            response = pipe.run({"prompt_builder": {"query": query},
                                "retriever": {"filters":{'pipeline_run_id':pipeline_run_id, 'processor_type':'llm','artifact_type':'RAW'}}
                                })
                                #"preprocessor":{"transcriptions":document_store.filter_documents(filters={
                                #                                                                'meta.pipeline_run_id':pipeline_run_id, 'meta.source':'audio'})
                                #            }
                                #})
                                #"retriever": {"query": "scam social engineering"},})
            
            print(response["llm"]["replies"])

            
            #document_store.write_documents([Document(content=data, meta={'pipeline_run_id':pipeline_run_id, 'source': 'audio', 'processor_type':'asr'})])
    
            logger.debug(f"Time taken for this record:{time.time() - start_time}")
from pydantic import BaseModel, ValidationError
from capabilities.asr.datamodels import TSegment
from capabilities.llm.datamodels import OllamaRun
from capabilities.models import Artifact, PipelineRun, Entity
import logging
from django.core.exceptions import ObjectDoesNotExist
import hashlib
from haystack_integrations.document_stores.elasticsearch import ElasticsearchDocumentStore
from haystack.dataclasses.byte_stream import ByteStream

from haystack import Document
from capabilities.datamodels import EntityModel, PipelineRunModel
from capabilities.phish.datamodels import UrlScreenshot, PhishingAssessment
from datetime import datetime, timedelta
import uuid
from django.conf import settings


logger = logging.getLogger(__name__)

backend = 'postgres'

processor_type_to_model = {
    'asr': TSegment,
    'llm': OllamaRun,
    'phish_scan_url_screenshot_ocr': UrlScreenshot,
    'phish_scan_screenshot_assessment': PhishingAssessment
}

class ArtifactService:
    
    from pydantic import ValidationError

    @staticmethod
    def _validate_data_model(processor_type, data:BaseModel):
        model = processor_type_to_model.get(processor_type)
        if model:
            try:
                # Parse model from JSON
                instance = model.model_validate(data)
                # Convert model back to JSON
                return instance.model_dump_json()
            except ValidationError as e:
                print(f"Validation error for {processor_type}: {e}")
        return None
    
    @staticmethod
    def store(pipeline_run_id, processor_type, artifact_type, data:BaseModel, metadata=None):
        if backend == 'postgres':
            return ArtifactServicePG.store(pipeline_run_id, processor_type, artifact_type, data, metadata)
        elif backend == 'elk':
            return ArtifactServiceELK.store(pipeline_run_id, processor_type, artifact_type, data, metadata)

    @staticmethod
    def increamental_fetch(pipeline_run_id, since_artifact_id, order_by=None, processor_type=None, artifact_type=None, limit=None):
        if backend == 'postgres':
            if order_by is None:
                order_by = 'metadata__context__chunk_num'
            return ArtifactServicePG.increamental_fetch(pipeline_run_id, since_artifact_id, order_by, processor_type, artifact_type, limit)
        elif backend == 'elk':
            return ArtifactServiceELK.increamental_fetch(pipeline_run_id, since_artifact_id, order_by, processor_type, artifact_type, limit)
        

class ArtifactServicePG(object):
    
    @staticmethod
    def store(pipeline_run_id, processor_type, artifact_type, data:BaseModel, metadata=None):
        
        try:
            validated_json = ArtifactService._validate_data_model(processor_type=processor_type, data=data)
        
            pipeline_run = PipelineRun.objects.get(id=pipeline_run_id)
        
            Artifact.objects.create(
                pipeline_run_id=pipeline_run,
                processor_type=processor_type,
                artifact_type=artifact_type,
                data=validated_json,
                metadata=metadata or {}
            )
        except ObjectDoesNotExist:
            raise ValueError(f"ArtifactService model save error: No PipelineRun found with ID {pipeline_run_id}")
        except ValidationError as e:
            logger.error(f"ArtifactService model validation error for {pipeline_run_id} {processor_type}: {e} {data}")
        except Exception as e:
            logger.error(f"ArtifactService model save error: {pipeline_run_id} {processor_type}: {e} {data}")
        
    @staticmethod
    def increamental_fetch(pipeline_run_id, since_artifact_id, order_by='metadata__context__chunk_num', processor_type=None, artifact_type=None, limit=None):
        # Build a dictionary of filter criteria
        filter_criteria = {
            'pipeline_run_id': pipeline_run_id,
            'id__gt': since_artifact_id,
        }

        if processor_type is not None:
            filter_criteria['processor_type'] = processor_type

        if artifact_type is not None:
            filter_criteria['artifact_type'] = artifact_type

        # Filter artifacts that are new since the last fetched artifact
        artifacts = Artifact.objects.filter(**filter_criteria).order_by(order_by)

        if limit is not None:
            artifacts = artifacts[:limit]

        return artifacts
    
class ArtifactServiceELK:
    #document_store = ElasticsearchDocumentStore(hosts = "http://localhost:9200",
    #                                            index="artifact")

    document_store = "" 

    @staticmethod
    def store(pipeline_run_id, processor_type, artifact_type, data:BaseModel, metadata={}):
        
        document_store = ArtifactServiceELK.document_store

        validated_json = ArtifactService._validate_data_model(processor_type=processor_type, data=data)
        document_store.write_documents(
            [ Document(content=validated_json, 
                        meta={'pipeline_run_id':pipeline_run_id, 
                            'processor_type':processor_type, 
                            'artifact_type':artifact_type,
                            **metadata}
                )
            ])
    
    @staticmethod
    def increamental_fetch(pipeline_run_id, since_artifact_id, order_by=None, processor_type=None, artifact_type=None, limit=None):
        
        document_store = ArtifactServiceELK.document_store

        filter_criteria = {
            'meta.pipeline_run_id': pipeline_run_id,
        }
        if processor_type is not None:
            filter_criteria['meta.processor_type'] = processor_type
        if artifact_type is not None:
            filter_criteria['meta.artifact_type'] = artifact_type

        # build elastic search query
        query = {
            'query': {
                'bool': {
                    'filter': [
                        {'term': filter_criteria}
                    ]
                },
                "range": {
                    "_id": {
                            "gt": since_artifact_id,
                        },
                },
            }
        }
        if order_by is not None:
            query['sort'] = {
                "meta.context.chunk_num": {"order_by": 'asc'}
            }
        if limit is not None:
            query['size'] = limit

        return document_store._search_documents(query)
        

class EntityService:

    def get_entity(entity_id):
        if backend == 'postgres':
            return EntityServicePG.get_entity(entity_id)
        elif backend == 'elk':
            return EntityServiceELK.get_entity(entity_id)

    def get_or_create_entity(parent_entity_id, type, data, metadata):
        if backend == 'postgres':
            return EntityServicePG.get_or_create_entity(parent_entity_id, type, data, metadata)
        elif backend == 'elk':
            return EntityServiceELK.get_or_create_entity(parent_entity_id, type, data, metadata)

    def create_pipelinerun(type, name, status='created', metadata={}):
        if backend == 'postgres':
            return EntityServicePG.create_pipelinerun(type, name, status,metadata)
        elif backend == 'elk':
            return EntityServiceELK.create_pipelinerun(type, name, status)
    
    def get_pipelinerun(pipeline_run_id):
        if backend == 'postgres':
            return EntityServicePG.get_pipelinerun(pipeline_run_id)
        elif backend == 'elk':
            return EntityServiceELK.get_pipelinerun(pipeline_run_id)
    
    def search_pipelinerun(entity_id,pipeline_type,recent_cutoff):
        if backend == 'postgres':
            return EntityServicePG.search_pipelinerun(entity_id,pipeline_type,recent_cutoff)
        elif backend == 'elk':
            return EntityServiceELK.search_pipelinerun(entity_id)

    def update_pipelinerun(pipeline_run_id, status):
        if backend == 'postgres':
            return EntityServicePG.update_pipelinerun(pipeline_run_id, status)
        #elif backend == 'elk':
        #    return EntityServiceELK.update_pipelinerun(pipeline_run_id, status)

class EntityServicePG:
   
    @staticmethod
    def get_entity(entity_id):
        entity = Entity.objects.get(id=entity_id)
        return EntityModel(
            id=entity.id,
            uuid=entity.uuid,
            type=entity.type,
            created_ts=entity.created_ts,
            hash=entity.hash,
            data=entity.data,
            metadata=entity.metadata,
            parent=entity.parent.id if entity.parent else None
        )

    @staticmethod
    def get_or_create_entity(parent_entity_id, type, data, metadata):
        parent_entity = None
        if parent_entity_id:
            parent_entity = Entity.objects.get(id=parent_entity_id)
            
        hash = hashlib.sha256(data).hexdigest() if data else None
        entity = None
        try:
            entity = Entity.objects.get(hash=hash) if hash else None
        except Entity.DoesNotExist:
            # Create a new Entity instance with this data
            entity = Entity(
                parent=parent_entity,
                type=type,
                data=data,
                metadata=metadata
            )
            entity.save()

        return EntityModel(
            id=entity.id,
            uuid=entity.uuid,
            type=entity.type,
            created_ts=entity.created_ts,
            hash=entity.hash,
            data=entity.data,
            metadata=entity.metadata,
            parent=entity.parent.id if entity.parent else None
        )
    
    @staticmethod
    def create_pipelinerun(type, name, status='created', metadata={}):
        pipelinerun = PipelineRun.objects.create(type=type, name=name, status=status, metadata=metadata)
        return PipelineRunModel(
            id=pipelinerun.id,
            uuid=pipelinerun.uuid,
            type=pipelinerun.type,
            name=pipelinerun.name,
            created_at=pipelinerun.created_at,
            updated_at=pipelinerun.updated_at,
            completed_at=pipelinerun.completed_at,
            status=pipelinerun.status,
            metadata=pipelinerun.metadata
        )
    
    @staticmethod
    def update_pipelinerun(pipeline_run_id, status):
        pipelinerun = PipelineRun.objects.get(id=pipeline_run_id)
        pipelinerun.status = status
        if status == 'completed':
            pipelinerun.completed_at = datetime.now()
        else:
            pipelinerun.updated_at = datetime.now()
        
        pipelinerun.save()

        return PipelineRunModel(
            id=pipelinerun.id,
            uuid=pipelinerun.uuid,
            type=pipelinerun.type,
            name=pipelinerun.name,
            created_at=pipelinerun.created_at,
            updated_at=pipelinerun.updated_at,
            completed_at=pipelinerun.completed_at,
            status=pipelinerun.status,
            metadata=pipelinerun.metadata
        )

    
    @staticmethod
    def get_pipelinerun(pipeline_run_id):
        pipelinerun = PipelineRun.objects.get(id=pipeline_run_id)
        return PipelineRunModel(
            id=pipelinerun.id,
            uuid=pipelinerun.uuid,
            type=pipelinerun.type,
            name=pipelinerun.name,
            created_at=pipelinerun.created_at,
            updated_at=pipelinerun.updated_at,
            completed_at=pipelinerun.completed_at,
            status=pipelinerun.status,
            metadata=pipelinerun.metadata
        )
    
    @staticmethod
    def search_pipelinerun(entity_id, pipeline_type, recent_cutoff):
        recent_cutoff_date = datetime.now() - timedelta(days=recent_cutoff)
        if 'sqlite' in settings.DATABASES['default']['ENGINE']:
            pipelinerun = PipelineRun.objects.filter(metadata__entity_ids__icontains=entity_id, 
                                                     type=pipeline_type, 
                                                     created_at__gte=recent_cutoff_date, 
                                                     status='completed').all()
        else:
            pipelinerun = PipelineRun.objects.filter(metadata__entity_ids__contains=entity_id, type=pipeline_type, created_at__gte=recent_cutoff_date).all()
        pipelinerun = pipelinerun[0] if pipelinerun else None
        if pipelinerun:
            return PipelineRunModel(
                id=pipelinerun.id,
                uuid=pipelinerun.uuid,
                type=pipelinerun.type,
                name=pipelinerun.name,
                created_at=pipelinerun.created_at,
                updated_at=pipelinerun.updated_at,
                completed_at=pipelinerun.completed_at,
                status=pipelinerun.status,
                metadata=pipelinerun.metadata
            )
        else:
            return None
    

class EntityServiceELK:

    #document_store = ElasticsearchDocumentStore(hosts = "http://localhost:9200",
    #                                            index="entity")
    document_store = ""

    @staticmethod
    def get_entity(entity_id):
        
        document_store = EntityServiceELK.document_store

        entities =  document_store.filter_documents({"_id":entity_id})
        entity = entities[0] if entities else None

        return EntityModel(
            id=entity.id,
            uuid=entity.meta.uuid,
            type=entity.meta.type,
            created_ts=entity.meta.created_ts,
            hash=entity.meta.hash,
            data=entity.blob.data,
            metadata=entity.meta,
            parent=entity.meta.parent_entity_id if 'parent_entity_id' in entity.meta else None
        )

    @staticmethod
    def get_or_create_entity(parent_entity_id, type, data, metadata):
        
        document_store = EntityServiceELK.document_store
        
        hash = hashlib.sha256(data).hexdigest() if data else None
        entity = None
        if hash:
            entity = document_store.filter_documents({"meta.hash":hash})
        
        if not entity:
            # Create a new Entity instance with this data
            entities = document_store.write_documents(
                    
                    [ Document(blob=ByteStream(data=data,mime_type="audio/wav"), 
                            meta={ **metadata,
                                    "uuid":uuid.uuid4(),
                                    "type":type,
                                    "created_ts": datetime.now(),
                                    "hash":hash,
                                    "parent_entity_id":parent_entity_id,
                                    })])
            entity = entities[0] if entities else None
        
        return  EntityModel(
            id=entity.id,
            uuid=entity.meta.uuid,
            type=entity.meta.type,
            created_ts=entity.meta.created_ts,
            hash=entity.meta.hash,
            data=entity.blob.data,
            metadata=entity.meta,
            parent=entity.meta.parent_entity_id if 'parent_entity_id' in entity.meta else None
        )            
    
    @staticmethod
    def create_pipelinerun(type, name, status='created'):
        
        document_store = EntityServiceELK.document_store

        if status == 'created':
            created_at = datetime.now()

        written_docs = document_store.write_documents(
            [ Document(content={"type":type, 
                                "uuid":uuid.uuid4(),
                                "name":name, 
                                "status":status,
                                "created_at":created_at})]) 
        
        if not written_docs:
            return None
        
        return PipelineRunModel(
            id=written_docs[0]._id,
            uuid=written_docs[0].uuid,
            type=written_docs[0].type,
            name=written_docs[0].name,
            created_at=written_docs[0].created_at,
            status=written_docs[0].status
        )
    
    @staticmethod
    def get_pipelinerun(pipeline_run_id):
         
        document_store = EntityServiceELK.document_store

        runs =  document_store.filter_documents({"_id":pipeline_run_id})
        run = runs[0] if runs else None

        return PipelineRunModel(
            id=run.id,
            uuid=run.uuid,
            type=run.type,
            name=run.name,
            created_at=run.created_at,
            updated_at=run.updated_at,
            completed_at=run.completed_at,
            status=run.status,
            metadata=run.metadata
        )
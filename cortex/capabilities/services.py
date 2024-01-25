from pydantic import BaseModel, ValidationError
from capabilities.asr.datamodels import TSegment
from capabilities.llm.datamodels import OllamaRun
from capabilities.models import Artifact, PipelineRun
import logging
from django.core.exceptions import ObjectDoesNotExist

logger = logging.getLogger(__name__)

processor_type_to_model = {
    'asr': TSegment,
    'llm': OllamaRun
}

class ArtifactService(object):

    from pydantic import ValidationError

    @staticmethod
    def validate_data_model(processor_type, data:BaseModel):
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
        
        try:
            validated_json = ArtifactService.validate_data_model(processor_type=processor_type, data=data)
        
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
        
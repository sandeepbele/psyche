# create django model for Entity with fields id,type,data(json)
from django.db import models 
import uuid, hashlib

class Entity (models.Model):   
    ENTITY_TYPE=[
        ('audio_wav', 'audio_wav'),
        ('json','json')]          # possible types can be added here based on your requirement, e.g., VEH , PED etc 
      
    id = models.AutoField(primary_key=True)  
    uuid = models.UUIDField(default=uuid.uuid4, editable=False, unique=True) 
    type =  models.CharField(max_length= 50, choices= ENTITY_TYPE )    #choices for entity or object        
    created_ts =  models.DateTimeField(auto_now_add=True, null=True) # default value for created_at is current time
    hash = models.CharField(max_length=255, null=True) # hash field to store the hash of your Entity's Data
    data  = models.BinaryField(null=True, blank=True)             #json field to store the JSON-like structure of your Entity's Data 
    metadata = models.JSONField(null=True) #json field to store the JSON-like structure of your Entity's Metadata
    parent = models.ForeignKey('self', on_delete=models.CASCADE, related_name='chunks', null=True, blank=True)

    def save(self, *args, **kwargs):
        self.hash = hashlib.sha256(self.data).hexdigest() if self.data else None
        super().save(*args, **kwargs)

            
# create django model for PipelineRun with fields id,pipeline_id,created_at,updated_at,completed_at,status,metadata(json)
class PipelineRun (models.Model):
    id = models.AutoField(primary_key=True) 
    uuid = models.UUIDField(default=uuid.uuid4, editable=False, unique=True)
    type =  models.CharField(max_length=50)
    name = models.CharField(max_length=50) 
    # default value for created_at is current time
    created_at = models.DateTimeField(auto_now_add=True)
    # on update set to current time
    updated_at = models.DateTimeField(auto_now=True)
    # default value for completed_at is null
    completed_at = models.DateTimeField(null=True)
    # default value for status is 'running' with choices 'created','running', 'completed', 'error'
    status = models.CharField(max_length= 50, default='created')
    metadata = models.JSONField(null=True)

# create django model  for Artifacts with fields pipeline_run_id,processor_type,data(blob),metadata(json)
class Artifact (models.Model):
    
    ARTIFACT_TYPE=[
        ('RAW', 'raw'),
        ('SIG','signal'),
    ]
    id = models.AutoField(primary_key=True)
    pipeline_run_id = models.ForeignKey(PipelineRun, on_delete=models.CASCADE)
    processor_type = models.CharField(max_length= 50) 
    artifact_type = models.CharField(max_length= 50, choices= ARTIFACT_TYPE )
    data = models.JSONField()    
    metadata = models.JSONField()


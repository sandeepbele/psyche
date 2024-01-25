# create django model for Entity with fields id,type,data(json)
from django.db import models 
    
class Entity (models.Model):   
    ENTITY_TYPE=[
        ('ENT', 'entity'),
        ('OBJ','object')]          # possible types can be added here based on your requirement, e.g., VEH , PED etc 
      
    id = models.AutoField(primary_key=True)  
    type =  models.CharField(max_length= 50, choices= ENTITY_TYPE )    #choices for entity or object        
    data  = models.JSONField()             #json field to store the JSON-like structure of your Entity's Data 


# create django model for PipelineRun with fields id,pipeline_id,created_at,updated_at,completed_at,status,metadata(json)
class PipelineRun (models.Model):
    id = models.AutoField(primary_key=True) 
    type =  models.CharField(max_length=50)
    name = models.CharField(max_length=50) 
    # default value for created_at is current time
    created_at = models.DateTimeField(auto_now_add=True)
    # default value for created_at is current time
    updated_at = models.DateTimeField(auto_now_add=True)
    # default value for completed_at is null
    completed_at = models.DateTimeField(null=True)
    # default value for status is 'running' with choices 'created','running', 'completed', 'error'
    status = models.CharField(max_length= 50, default='created')
    metadata = models.JSONField(null=True)

# create django model  for Artifacts with fields pipeline_run_id,processor_type,data(blob),metadata(json)
class Artifact (models.Model):
    
    ARTIFACT_TYPE=[
        ('RAW', 'raw'),
        ('OBSRV','observation'),
    ]
    id = models.AutoField(primary_key=True)
    pipeline_run_id = models.ForeignKey(PipelineRun, on_delete=models.CASCADE)
    processor_type = models.CharField(max_length= 50) 
    artifact_type = models.CharField(max_length= 50, choices= ARTIFACT_TYPE )
    data = models.JSONField()    
    metadata = models.JSONField()


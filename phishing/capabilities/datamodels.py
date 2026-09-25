from pydantic import BaseModel
from typing import Optional, List, Dict, Any
from datetime import datetime
import json, uuid

from capabilities.models import Entity


class EntityModel(BaseModel):
    id: int
    uuid: uuid.UUID
    type: str    #choices for entity or object
    created_ts: datetime # default value for created_at is current time
    hash: str # hash field to store the hash of your Entity's Data
    data: bytes            #json field to store the JSON-like structure of your Entity's Data
    metadata: dict = {}#json field to store the JSON-like structure of your Entity's Metadata
    parent: Optional[int] = None

class PipelineRunModel(BaseModel):
    id: int
    uuid: uuid.UUID
    type: str
    name: Optional[str] = None
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    status: str = None
    metadata: Optional[dict] = {}

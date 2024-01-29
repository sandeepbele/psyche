from pydantic import BaseModel
from typing import Optional, List, Dict, Any
from datetime import datetime
import json

from capabilities.models import Entity

class AudioEntity(BaseModel):
    sample_rate: int
    channels: int
    size: int
    start_time: float
    duration: float
    type: str
    data: bytes

    # create constructor to except Entity model
    @classmethod
    def from_entity(cls, entity:Entity) -> 'AudioEntity':
        
        # Deserialize the metadata and data fields
        metadata = json.loads(entity.metadata) if entity.metadata else None
        #data = json.loads(entity.data) if entity.data else None

        # Create the Pydantic Entity instance
        return cls(
            sample_rate=metadata['sample_rate'] if metadata else None,
            channels=metadata['channels'] if metadata else None,
            size=metadata['size'] if metadata else None,
            start_time=metadata['start_time'] if metadata else None,
            duration=metadata['duration'] if metadata else None,
            type=entity.type,
            data=entity.data,
        )
    

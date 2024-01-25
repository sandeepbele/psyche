from pydantic import BaseModel
from datetime import datetime

class OllamaRun(BaseModel):
    prompt: str
    raw_response: str = None
    parsed_response: dict = None
    id : int = 0
    req_initiated_ts: datetime = None
    req_completed_ts: datetime = None
    ttr_model_ms: float = None
    ttr_rt_ms: float = None
    input_tokens: int = None
    output_tokens: int = None
    error: str = None
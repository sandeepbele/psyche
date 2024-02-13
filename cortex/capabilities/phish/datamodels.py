from pydantic import BaseModel, Field, root_validator
from typing import Optional
import base64

class UrlScreenshot(BaseModel):
    url: str
    screenshot_b64: str #base64 encoded screenshot image buffer that can be serialized to json
    ocr_text : Optional[str] = None
    error: Optional[str] = None
    metadata: dict = {} # metadata to identify the run


class PhishingAssessment(BaseModel):
    url: str
    brand: Optional[str] = "Unknown"
    brand_url: Optional[str] = "Unknown"
    business_category: Optional[str] = "Unknown"
    webpage_summary:Optional[str] = "NA"
    is_phishing: bool
    raw_assessment: Optional[dict] = {}
    metadata: dict = {} # metadata to identify the run
import base64
import json
import logging
import re
import time
from functools import wraps

from celery import current_task, shared_task
from pydantic import BaseModel

from capabilities.services import ArtifactService

logger = logging.getLogger(__name__)

class TaskResult:
    def __init__(self, return_result, store_result, processor_type):
        self.return_result = return_result
        self.store_result = store_result
        self.processor_type = processor_type

def store_artifact(processor_type, artifact_type):
    def decorator(task_func):
        @wraps(task_func)
        def wrapper(*args, **kwargs):
            start_time = time.time()
            # Extract context and task_kwargs
            context = kwargs.pop('context', {})
            task_kwargs = kwargs.pop('kwargs', {})

            # Call the task function with task_kwargs
            result = task_func(*args, kwargs=task_kwargs, context=context)
            end_time = time.time()
            total_run_time = end_time - start_time

            # Extract pipeline_run_id and determine the data to log
            pipeline_run_id = context.get('pipeline_run_id')
            data_to_log = result.store_result if isinstance(result, TaskResult) else result
            logger.debug(f"Logging data of type {type(data_to_log)}, pipeline_run_id={pipeline_run_id} ")

            if isinstance(data_to_log, BaseModel) \
                and pipeline_run_id is not None:
                # Log the result using ArtifactStoreService
                ArtifactService.store(
                    pipeline_run_id=pipeline_run_id,
                    processor_type=processor_type,
                    artifact_type=artifact_type,
                    data=data_to_log,
                    metadata={
                        'task_id': current_task.request.id,
                        'ts_called': start_time,
                        'total_run_time_ms': total_run_time * 1000,
                        'origin': current_task.request.hostname,
                        'root_task_id': current_task.request.root_id,
                        'context': context
                    }
                )
            else:
                logger.error(f"Cannot log data of type {type(data_to_log)}")

            # Return the result for the next task
            return result.return_result if isinstance(result, TaskResult) else result

        return wrapper
    return decorator

@shared_task
@store_artifact(processor_type='phish_scan_url_screenshot_ocr', artifact_type='RAW')
def phish_scan_url_to_screenshot(url, kwargs,context):
    # create datamodel for screenshot
    from capabilities.phish.scanner import take_screenshot, tessaract_image_summarize_tostr
    from capabilities.phish.datamodels import UrlScreenshot
    from django.conf import settings
    import os, base64
    screenshot_output_dir = os.path.join(settings.BASE_DIR,'url_screenshots')
    seccomp_path = os.path.join(settings.BASE_DIR,'seccomp_profile.json')

    screenshot_result = take_screenshot(url, screenshot_output_dir, seccomp_path)
    screenshot_file = screenshot_result.get('screenshot_path')
    screenshot_error = screenshot_result.get('error')
    ocr_text = tessaract_image_summarize_tostr(screenshot_file) if screenshot_file else None
    if ocr_text:
        ocr_text = ocr_text.get('text',"")

    screenshot_bytes = "".encode()
    if screenshot_file:
        with open(screenshot_file, 'rb') as f:
            screenshot_bytes = f.read()

    return TaskResult(return_result=ocr_text,
                      store_result= UrlScreenshot(url=url, screenshot_b64=base64.encodebytes(screenshot_bytes), ocr_text=ocr_text, error=screenshot_error, metadata=context),
                      processor_type='phish_scan_url_screenshot_ocr')

@shared_task
@store_artifact(processor_type='phish_scan_screenshot_assessment', artifact_type='SIG')
def phish_scan_screenshot_assessment(ocr_text,url, kwargs,context):
        # create datamodel for phishing assessment
    from capabilities.phish.scanner import ollama_ask_llm, is_phishing_url
    from capabilities.phish.datamodels import PhishingAssessment

    if not ocr_text:
        return PhishingAssessment(url=url, properties={}, is_phishing=False)

    llm_response = ollama_ask_llm(ocr_text)
    llm_response = llm_response.text

    try:
        parsed_resp = json.loads(llm_response.replace("\n","").replace("\\","").strip())
        brand = parsed_resp.get('brand', "")
        brand_url = parsed_resp.get('brand_url', "")
        business_category = parsed_resp.get('business_category', "")
        webpage_summary = parsed_resp.get('webpage_summary', "")
    except json.JSONDecodeError as e:
        brand_match = re.search(r'"brand"\s*:\s*"([^"]+)"', llm_response)
        brand = brand_match.group(1) if brand_match else ""

        brand_url_match = re.search(r'"brand_url"\s*:\s*"([^"]+)"', llm_response)
        brand_url = brand_url_match.group(1) if brand_url_match else ""

        business_category_match = re.search(r'"business_category"\s*:\s*"([^"]+)"', llm_response)
        business_category = business_category_match.group(1) if business_category_match else ""

        webpage_summary_match = re.search(r'"webpage_summary"\s*:\s*"([^"]+)"', llm_response)
        webpage_summary = webpage_summary_match.group(1) if webpage_summary_match else ""

    return PhishingAssessment(
                                url=url,
                                raw_assessment={'ocr_text':ocr_text, 'llm_response':llm_response},
                                is_phishing=is_phishing_url(url, brand_url, brand),
                                brand=brand,
                                brand_url=brand_url,
                                business_category=business_category,
                                webpage_summary=webpage_summary,
                              )

if __name__ == '__main__':
    pass #app.start()
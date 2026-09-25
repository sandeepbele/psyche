import logging
import randomname

from celery import chain
from django.core.serializers import serialize
from django.http import HttpResponse, JsonResponse
from django.shortcuts import render
from django.views.decorators.csrf import csrf_exempt

from capabilities.helpers.utils import check_task_and_children
from capabilities.services import EntityService, ArtifactService
from capabilities.processing.tasks import phish_scan_url_to_screenshot, phish_scan_screenshot_assessment

logger = logging.getLogger(__name__)


def index(request):
    return HttpResponse("Psyche phishing scanner")


def artifacts(request):
    return render(request, 'scan_results2.html')

def artifact_list(request, pipeline_run_id, task_id):
    # Retrieve the PipelineRun instance
    pipeline_run = EntityService.get_pipelinerun(pipeline_run_id)

    # Get the status of the Celery task
    #task = AsyncResult(task_id)
    run_completed = check_task_and_children(task_id)

    # Retrieve the last_artifact_id from the session
    last_artifact_id = request.session.get('last_artifact_id', 0)
    logger.debug(f"last_artifact_id: {last_artifact_id}")

    # Filter artifacts that are new since the last fetched artifact
    artifacts = ArtifactService.increamental_fetch(pipeline_run_id, last_artifact_id)

    # Update the session with the ID of the last artifact in this response, if any
    if artifacts.count() > 0:
        request.session['last_artifact_id'] = artifacts.last().id

    logger.debug("request.sesson.last_artifact_id: " + str(request.session.get('last_artifact_id')))
     # Check if the PipelineRun and the Celery task are completed
    if run_completed and 'last_artifact_id' in request.session:
        del request.session['last_artifact_id']

    # Serialize the new artifacts
    artifacts_json = serialize('json', artifacts)

    logger.info(f"###session_id: {request.session.session_key},passed_last_artifact_id: {last_artifact_id}, artifacts_count: {artifacts.count()},\
                new_last_artifact_id: {artifacts.last().id if artifacts.count() > 0 else last_artifact_id}, run_completed: {run_completed}")

    # Return the list as a JSON response
    return JsonResponse({'artifacts':artifacts_json,
                         'run_completed': run_completed},
                         safe=False)


def url_scan(request):
    return render(request, 'url_scan.html')

#@method_decorator(csrf_exempt, name='dispatch')
@csrf_exempt
def initiate_url_scan(request):
    # fetch url from post request
    url = request.POST.get('url')

    entity = EntityService.get_or_create_entity(None, 'text_url', url.encode(), {})
    #search pipeline with given entity id
    pipeline = EntityService.search_pipelinerun(entity.id, 'url_phish_scan',1)
    if pipeline is not None:
        return JsonResponse({'pipeline_run_id': pipeline.id, 'entity_id': entity.id, 'task_id': None})
    else:
        pipeline = EntityService.create_pipelinerun('url_phish_scan', randomname.get_name(), 'created',
                                                metadata={'entity_ids': [entity.id]})

        from capabilities.processing.tasks import phish_scan_url_to_screenshot, phish_scan_screenshot_assessment
        from celery import chain
        context = {'pipeline_run_id': pipeline.id}
        celery_chain = chain(phish_scan_url_to_screenshot.s(url,context=context), phish_scan_screenshot_assessment.s(url,context=context))
        task = celery_chain.delay()
        #request.session['task'] = task.id
        return JsonResponse({'pipeline_run_id': pipeline.id, 'entity_id': entity.id, 'task_id': task.parent.id})

def scan_results(request):
    return render(request, 'scan_results2.html')
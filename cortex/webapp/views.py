from django.http import HttpResponse, JsonResponse
from django.shortcuts import render
from rest_framework.views import APIView
from rest_framework.response import Response
from capabilities.models import Artifact, PipelineRun, Entity
from .serializers import ArtifactSerializer
from django.core.serializers import serialize
from django.views.decorators.csrf import csrf_exempt
from django.utils.decorators import method_decorator
from django.views import View
from .forms import AudioUploadForm
from capabilities.processing.factory import get_audio_file_processing_pipeline
import traceback, os
from django.conf import settings
import asyncio
from asgiref.sync import sync_to_async
from webapp.tasks import process_audio_llm_task
import wave, io, json, sys
import logging, hashlib
from capabilities.helpers.utils import check_task_and_children

from celery.result import AsyncResult

logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG)

# Create a StreamHandler that sends logging output to stdout
stdout_handler = logging.StreamHandler(sys.stdout)

# Add the StreamHandler to the logger
logger.addHandler(stdout_handler)

# Create your views here.
def index(request):
    return HttpResponse("Hello, World!")

class ArtifactListView(APIView):
    def get(self, request, pipeline_run_id):
        artifacts = Artifact.objects.filter(pipeline_run_id=pipeline_run_id)
        serializer = ArtifactSerializer(artifacts, many=True)
        return Response(serializer.data)

from django.shortcuts import render

def artifacts(request):
    return render(request, 'artifact3.html')


def artifact_list(request, pipeline_run_id, task_id):
    # Retrieve the PipelineRun instance
    pipeline_run = PipelineRun.objects.get(id=pipeline_run_id)

    # Get the status of the Celery task
    #task = AsyncResult(task_id)
    run_completed = check_task_and_children(task_id)

    # Retrieve the last_artifact_id from the session
    last_artifact_id = request.session.get('last_artifact_id', 0)
    logger.debug(f"last_artifact_id: {last_artifact_id}")

    # Filter artifacts that are new since the last fetched artifact
    artifacts = Artifact.objects.filter(
            pipeline_run_id=pipeline_run_id, 
            id__gt=last_artifact_id
        ).order_by('metadata__context__chunk_num')

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


@method_decorator(csrf_exempt, name='dispatch')
class AudioProcessingView(View):
    def post(self, request):
        form = AudioUploadForm(request.POST, request.FILES)
        pipeline_run_id = request.POST.get('pipeline_run_id')
        parent_entity_id = request.POST.get('parent_entity_id')
        if form.is_valid():

            backend = 'celery'
            audio_file = form.cleaned_data['audio_file']

            # Read the file into a bytes object
            data = b''
            for chunk in audio_file.chunks():
                data += chunk

            # Open the file with the wave module
            with wave.open(io.BytesIO(data), 'rb') as wav_file:
                sample_rate = wav_file.getframerate()
                channels = wav_file.getnchannels()
                size = wav_file.getnframes()
                duration = size / float(sample_rate)

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
                    type='audio_wav',
                    data=data,
                    metadata={
                        'sample_rate': sample_rate,
                        'channels': channels,
                        'size': size,
                        'duration': duration
                    }
                )
                entity.save()

            try:
                if pipeline_run_id is None:
                    pipeline = PipelineRun.objects.create(type="asr_llm_celery",status='created')
                else:
                    pipeline = PipelineRun.objects.get(id=pipeline_run_id)

                task = process_audio_llm_task.delay(pipeline.id, entity.id)
                request.session['task'] = task.id

            except Exception as e:
                traceback.print_exc()
                return JsonResponse({'error': str(e)}, status=500)

            return JsonResponse({'pipeline_run_id': pipeline.id, 
                                 'parent_entity_id': parent_entity.id if parent_entity else entity.id,
                                 'entity_id': entity.id, 
                                 'task_id': task.id})
        else:
            return JsonResponse({'error': 'Invalid form'}, status=400)
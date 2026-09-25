#django management command to dump data

from django.core.management.base import BaseCommand
from capabilities.models import  Artifact
from django.core.serializers import serialize

class Command(BaseCommand):
    help = 'Dumps the data from the capabilities app'
    pipeline_run_id = None # add argument to specify pipeline_run_id

    def add_arguments(self, parser):
        parser.add_argument('-p','--pipeline_run_id', type=int, required=True, help='Pipeline Run ID')
        parser.add_argument('-t','--processor_type', type=str, required=False, help='Output file')


    def handle(self, *args, **options):
        pipeline_run_id = options['pipeline_run_id']
        processor_type = options['processor_type']

        # Dump the Artifact data
        artifacts = None
        if processor_type:
            artifacts = Artifact.objects.filter(pipeline_run_id=pipeline_run_id, processor_type=processor_type)
        else:
            artifacts = Artifact.objects.filter(pipeline_run_id=pipeline_run_id)

        artifacts_json = serialize('json', artifacts.order_by('id'))
        with open('artifacts.json', 'w') as f:
            f.write(artifacts_json)
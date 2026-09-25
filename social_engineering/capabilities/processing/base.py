from capabilities.models import PipelineRun
from datetime import datetime
import randomname 

# base class to model pipelines that support different backends
# nothing much planned for this class right now
class AbstractPipeline:
    def execute(self):
        raise NotImplementedError


class TrackablePipeline(AbstractPipeline):
    def __init__(self, type, name=None, pipeline_run_id=None):
        super().__init__()
        if pipeline_run_id is None:
            self.pipeline_run = PipelineRun.objects.create(
                type=type,
                name= name if name else randomname.get_name(),     
            )  # Create a new PipelineRun object
            self.pipeline_run_id = self.pipeline_run.id  # Store the ID of the PipelineRun object
        else:
            self.pipeline_run_id = pipeline_run_id
            try:
                self.pipeline_run = PipelineRun.objects.get(id=pipeline_run_id)
            except PipelineRun.DoesNotExist:
                raise Exception(f"PipelineRun with id {pipeline_run_id} does not exist")

    def execute(self):
        if self.status == 1:
            print("Pipeline already executed")
            return

        try:
            # Execute the pipeline
            self._execute()

            # Update the PipelineRun object when the pipeline finishes
            self.pipeline_run.completed_at = datetime.now()
            self.pipeline_run.status = 'completed'
            self.pipeline_run.save()
        except Exception as e:
            # Update the PipelineRun object if an error occurs
            self.pipeline_run.error_message = str(e)
            self.pipeline_run.status = 'error'
            self.pipeline_run.save()
            raise

    def _execute(self):
        raise NotImplementedError("Subclasses must implement this method")
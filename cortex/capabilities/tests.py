
from django.test import TestCase
from capabilities.datamodels import AudioEntity

from capabilities.models import Artifact, Entity
from capabilities.archive.speaker_helper import extract_stacked_embeddings, extract_combined_embedding, perform_matching

"""
class SpeakerHelperTestCase(TestCase):

    audio_file = "/Users/sandeep/Documents/SB_Sources/anm_dintel/phishnet/sales_call.wav"
    sales_rep_ts = [(0.88,1.5),(8.54,21.4),(26.3,108.22)] # list of tuples of start and end times of sales rep speaking
    sales_rep_ts_2 = [(305.76,309.94)]
    customer_ts = [(2.32,2.84),(22.74,24.76),(108.96,113.76),(232.4,247.2)] # list of tuples of start and end times of customer speaking
    
    def test_extract_stacked_embeddings(self):
       
        embeddings = extract_stacked_embeddings(self.audio_file, self.sales_rep_ts)

        # Perform your assertions or checks on the extracted embeddings
        self.assertIsNotNone(embeddings)
        self.assertEqual(embeddings.shape, (3, 192))  # Assuming embeddings are of shape (num_segments, embedding_dim)

    def test_extract_combined_embedding(self):
        
        embeddings = extract_combined_embedding(self.audio_file, self.sales_rep_ts)

        # Perform your assertions or checks on the extracted embeddings
        self.assertIsNotNone(embeddings)
        self.assertEqual(embeddings.shape, (1, 192))

    def test_embedding_match(self):

        embeddings_ref = extract_stacked_embeddings(self.audio_file, self.sales_rep_ts)
        embeddings_test_match = extract_stacked_embeddings(self.audio_file, self.sales_rep_ts_2)
        embeddings_test_mismatch = extract_stacked_embeddings(self.audio_file, self.customer_ts)
        # Perform your assertions or checks on the extracted embeddings
        self.assertTrue( perform_matching(embeddings_ref, embeddings_test_match) )
        self.assertFalse( perform_matching(embeddings_ref, embeddings_test_mismatch) )
"""

from django.test import TestCase
from capabilities.asr.datamodels import TSegment
from capabilities.services import ArtifactService
from capabilities.asr.datamodels import TSegment, SpeakerSegment
from datetime import datetime
from capabilities.models import PipelineRun

class ArtifactServiceTest(TestCase):
    def setUp(self):
        self.pipeline_run_id = 1
        self.processor_type = 'asr'
        self.artifact_type = 'TSegment'
       
        # Create mock SpeakerSegments
        speaker_segment1 = SpeakerSegment(speaker='Speaker1', start=0.0, end=1.0, text='Hello')
        speaker_segment2 = SpeakerSegment(speaker='Speaker2', start=1.0, end=2.0, text='World')

        # Create mock TSegment
        mock_tsegment = TSegment(
            start=0.0,
            end=2.0,
            speaker_segments=[speaker_segment1, speaker_segment2],
            ttd_model_ms=100.0,
            ttd_rt_ms=200.0
        )
        self.data = mock_tsegment
        self.metadata = {}

    def test_store_tsegment(self):
        
        # Create mock PipelineRun
        mock_pipeline_run = PipelineRun(
            type='TestType',
            name='TestName',
            created_at=datetime.now(),
            updated_at=datetime.now(),
            completed_at=datetime.now(),
            status='TestStatus',
            metadata={
                'key': 'value'
            }
        )
        mock_pipeline_run.save()

        ArtifactService.store(
            pipeline_run_id=mock_pipeline_run.id,
            processor_type=self.processor_type,
            artifact_type=self.artifact_type,
            data=self.data,
            metadata=self.metadata
        )
        artifact = Artifact.objects.get(pipeline_run_id=self.pipeline_run_id)
        self.assertEqual(artifact.processor_type, self.processor_type)
        self.assertEqual(artifact.artifact_type, self.artifact_type)
        self.assertEqual(artifact.data, self.data.model_dump_json())
        self.assertEqual(artifact.metadata, self.metadata)
        self.assertEqual(TSegment.model_validate_json(artifact.data), self.data)


"""
from unittest.mock import patch, Mock
from capabilities.processing.tasks import store_artifact
import pydantic 

class TestLogArtifact(TestCase):
    @patch('capabilities.services.ArtifactService.store', autospec=True)
    def test_log_artifact(self, mock_log):
        # Create a mock function
        @store_artifact('processor_type', 'artifact_type')
        def mock_func(pipeline_run_id,kwargs,context):
            return TSegment()

        # Call the decorated function
        mock_func('pipeline_run_id',kwargs={},context={})
        
        # Check that ArtifactService.log was called with the correct arguments
        mock_log.assert_called_once_with(
            pipeline_run_id='pipeline_run_id',
            processor_type='processor_type',
            artifact_type='artifact_type',
            data=TSegment(),
        )
"""


from django.test import TestCase
import json
from capabilities.datamodels import AudioEntity, Entity

class TestAudioEntity(TestCase):
    def setUp(self):
        self.entity = Entity(
            id=1,
            type='audio',
            created_ts='2022-01-01T00:00:00Z',
            hash='1234567890abcdef',
            data= b'test data',
            metadata=json.dumps({
                'sample_rate': 44100,
                'channels': 2,
                'size': 10000,
                'start_time': 0.0,
                'duration': 3.5
            }),
        )

    def test_from_entity(self):
        audio_entity = AudioEntity.from_entity(self.entity)
        self.assertEqual(audio_entity.sample_rate, 44100)
        self.assertEqual(audio_entity.channels, 2)
        self.assertEqual(audio_entity.size, 10000)
        self.assertEqual(audio_entity.start_time, 0.0)
        self.assertEqual(audio_entity.duration, 3.5)
        self.assertEqual(audio_entity.type, 'audio')
        self.assertEqual(audio_entity.data, b'test data')

from django.test import TestCase
from django.utils import timezone
from .models import Entity

class TestEntityModel(TestCase):
    def setUp(self):
        self.entity = Entity.objects.create(
            type='audio_wav',
            created_ts=timezone.now(),
            #hash='1234567890abcdef',
            data=b'test data',
            metadata={'sample_rate': 44100, 'channels': 2, 'size': 10000, 'duration': 3.5}
        )

    def test_entity_creation(self):
        self.assertIsInstance(self.entity, Entity)
        self.assertEqual(self.entity.type, 'audio_wav')
        self.assertEqual(self.entity.hash, str(hash(self.entity.data)))
        self.assertEqual(self.entity.data, b'test data')
        self.assertEqual(self.entity.metadata, {'sample_rate': 44100, 'channels': 2, 'size': 10000, 'duration': 3.5})

    def test_save_method(self):
        entity_same_hash = Entity(
            type='json',
            created_ts=timezone.now(),
            #hash='1234567890abcdef',
            data= b'test data',
            metadata={'sample_rate': 44100, 'channels': 2, 'size': 10000, 'duration': 3.5}
        )
        saved_entity = entity_same_hash.save()
        self.assertEqual(saved_entity.id, self.entity.id)
        self.assertEqual(saved_entity.type, self.entity.type)
        self.assertEqual(saved_entity.hash, self.entity.hash)
        self.assertEqual(saved_entity.data, self.entity.data)
        self.assertEqual(saved_entity.metadata, self.entity.metadata)
from django.urls import path

from .views import ArtifactListView, artifacts, index, artifact_list, AudioProcessingView

urlpatterns=[
  path('',index),
  #path('api/artifacts/<int:pipeline_run_id>/', ArtifactListView.as_view(), name='artifact-list'),
  path('api/artifacts/<int:pipeline_run_id>/<str:task_id>', artifact_list, name='artifact-list'),
  path('artifacts', artifacts, name='artifacts'),
  path('process_audio/', AudioProcessingView.as_view(), name='process_audio'),
]
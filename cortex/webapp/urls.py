from django.urls import path

from .views import ArtifactListView, artifacts, index, artifact_list, AudioProcessingView, url_scan, initiate_url_scan, scan_results
from sentinel.views import index as sentinel_index, \
                      chat as sentinel_chat, \
                      assistant as sentinel_assistant, \
                      list_threads as sentinel_list_threads, \
                      load_thread as sentinel_get_thread

urlpatterns=[
  path('',index),
  #path('api/artifacts/<int:pipeline_run_id>/', ArtifactListView.as_view(), name='artifact-list'),
  path('api/artifacts/<int:pipeline_run_id>/<str:task_id>', artifact_list, name='artifact-list'),
  path('artifacts', artifacts, name='artifacts'),
  path('process_audio/', AudioProcessingView.as_view(), name='process_audio'),
  path('url_scanner/',url_scan,name='url_scan'),
  path('initiate_url_scan/',initiate_url_scan,name='initiate_url_scan'),
  path('scan_results/',scan_results,name='scan_results'),
  path('sentinel/',sentinel_index),
  path('api/chat/',sentinel_chat,name='chat'),
  path('assistant/',sentinel_assistant,name='assistant'),
  path('api/threads/',sentinel_list_threads,name='list_threads'),
  path('api/threads/<str:thread_uuid>/',sentinel_get_thread,name='get_thread'),
]
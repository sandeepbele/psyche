from django.urls import path

from .views import ArtifactListView, artifacts, index, artifact_list, AudioProcessingView, url_scan, initiate_url_scan, scan_results
from sentinel.views import index as sentinel_index, \
                      chat as sentinel_chat, \
                      assistant as sentinel_assistant, \
                      list_threads as sentinel_list_threads, \
                      load_thread as sentinel_get_thread, \
                      app as sentinel_app, \
                      fetch_app_code as sentinel_fetch_app_code, \
                      get_violations as sentinel_get_violations, \
                      update_guardrails_selection as sentinel_update_guardrails_selection, \
                      get_guardrails_selection as sentinel_get_guardrails_selection, \
                      get_available_guardrails as sentinel_get_available_guardrails, \
                      request_handler as sentinel_evaluate_request, \
                      response_handler as sentinel_store_response, \
                      list_copilotcalls as sentinel_list_copilotcalls, \
                      guard as sentinel_guard \

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
  path('api/threads/',sentinel_list_threads,name='list_threads'),
  path('api/threads/<str:thread_uuid>/',sentinel_get_thread,name='get_thread'),
  path('assistant/',sentinel_assistant,name='assistant'),
  path('app/',sentinel_app,name='app'),
  path('fetch/<str:app_name>/',sentinel_fetch_app_code,name='fetch_app_code'),
  path('api/violations/',sentinel_get_violations,name='get_violations'),
  path('api/guardrails/get/<str:application_name>/', sentinel_get_guardrails_selection, name='get_guardrails_selection'),
  path('api/guardrails/update/<str:application_name>/', sentinel_update_guardrails_selection, name='update_guardrails_selection'),
  path('api/guardrails/list', sentinel_get_available_guardrails, name='get_available_guardrails'),
  path('api/evaluate/<str:app_name>/<str:thread_id>/', sentinel_evaluate_request, name='evaluate_request'),
  path('api/store/<str:app_name>/<str:thread_id>/',sentinel_store_response,name='sentinel_store_response'),
  path('api/gitcopilot/threads/',sentinel_list_copilotcalls,name='list_copilotcalls'),
  path('api/guard/', sentinel_guard, name='guard')


]
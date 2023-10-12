from django.urls import path, include
from . import views

urlpatterns = [

    path('fp-analyse/', views.fp_analyse, name='fp_analyse'),
    path('decode/<a>/', views.decode, name='decode'),
    path('', views.index, name='index'),
    path('chart/', views.get_chart_data, name='chart'),
    path('evaluate_fp/', views.evaluate_fp, name='evaluate_fp'),
    path('get_raw/<request_id>/<r>', views.get_raw, name='get_raw_bot_details'),
    path('get_raw/<request_id>/', views.get_raw, name='get_raw'),
    
]
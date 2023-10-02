from django.urls import path
from . import views

urlpatterns = [
    path('fp-analyse/', views.fp_analyse, name='fp_analyse'),
    path('decode/', views.decode, name='decode'),
    path('', views.index, name='index'),
    path('chart/', views.get_chart_data, name='chart'),
    path('evaluate_fp/', views.evaluate_fp, name='evaluate_fp'),
]
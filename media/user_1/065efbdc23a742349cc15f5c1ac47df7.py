from django.urls import path
from . import views

app_name = 'analysis'

urlpatterns = [
    path('upload/', views.upload_project, name='upload_project'),
    path('analyze/<int:project_id>/', views.analyze_project, name='analyze_project'),
    path('report/<int:project_id>/', views.view_report, name='view_report'),
    path('status/<int:project_id>/', views.get_analysis_status, name='get_analysis_status'),
]
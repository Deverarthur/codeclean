from django.urls import path
from . import views

app_name = 'analysis'

urlpatterns = [
    path('', views.home, name='home'),
    path('upload/', views.upload_project, name='upload_project'),
    path('analyze/<int:project_id>/', views.analyze_project, name='analyze_project'),
    path('view_report/<int:project_id>/', views.view_report, name='view_report'),
    path('get_analysis_status/<int:project_id>/', views.get_analysis_status, name='get_analysis_status'),
    path('generate_tests/<int:project_id>/', views.generate_tests_project, name='generate_tests_project'),
    path('results/<int:project_id>/', views.results, name='results'),  # Ajoute cette ligne si besoin
    path('download_report/<int:project_id>/', views.download_report, name='download_report'),
    path('register/', views.register, name='register'),
]
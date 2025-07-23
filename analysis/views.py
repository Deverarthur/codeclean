import os
import tempfile
import json
import threading
import time
import markdown
from django.shortcuts import render, redirect
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.conf import settings
from django.http import JsonResponse, HttpResponse
from .models import ProjectAnalysis, UploadedFile
from .forms import ProjectUploadForm
from .analyzer import SecurityAnalyzer
from .test_generator import generate_tests_report
from collections import defaultdict
from django.contrib.auth.forms import UserCreationForm
from django.contrib.auth import login
from django.core.paginator import Paginator

@login_required
def upload_project(request):
    if request.method == 'POST':
        form = ProjectUploadForm(request.POST, request.FILES)
        if form.is_valid():
            project = ProjectAnalysis.objects.create(
                user=request.user,
                project_name=form.cleaned_data['project_name']
            )
            for file in request.FILES.getlist('files'):
                UploadedFile.objects.create(
                    analysis=project,
                    file=file,
                    original_name=file.name
                )
            messages.success(request, 'Fichiers uploadés avec succès!')
            action = form.cleaned_data['action']
            if action == 'analysis':
                # Redirige vers la page d'attente
                return redirect('analysis:results', project_id=project.id)
            elif action == 'tests':
                return redirect('analysis:generate_tests_project', project_id=project.id)
    else:
        form = ProjectUploadForm()
    return render(request, 'analysis/upload.html', {'form': form})

@login_required
def analyze_project(request, project_id):
    project = ProjectAnalysis.objects.get(id=project_id, user=request.user)
    
    if not project.analysis_completed:
        with tempfile.TemporaryDirectory() as temp_dir:
            for uploaded_file in project.files.all():
                file_path = os.path.join(temp_dir, uploaded_file.original_name)
                with open(file_path, 'wb+') as dest:
                    for chunk in uploaded_file.file.chunks():
                        dest.write(chunk)
            
            analyzer = SecurityAnalyzer()
            report = analyzer.analyze_project(temp_dir)
            
            project.report_json = report
            project.analysis_completed = True
            project.save()
    
    return redirect('analysis:view_report', project_id=project.id)

@login_required
def generate_tests_project(request, project_id):
    project = ProjectAnalysis.objects.get(id=project_id, user=request.user)
    
    # Supposons que la génération de tests n'a pas encore été réalisée,
    # vous pouvez utiliser un champ tests_generated dans le modèle si besoin.
    if not getattr(project, 'tests_generated', False):
        with tempfile.TemporaryDirectory() as temp_dir:
            for uploaded_file in project.files.all():
                file_path = os.path.join(temp_dir, uploaded_file.original_name)
                with open(file_path, 'wb+') as dest:
                    for chunk in uploaded_file.file.chunks():
                        dest.write(chunk)
            
            tests_report = generate_tests_report(temp_dir)
            project.report_json = {"tests_report": tests_report}
            project.tests_generated = True
            project.save()
    
    context = {
        'project': project,
        'tests_report': project.report_json.get("tests_report", "")
    }
    return render(request, 'analysis/tests_report.html', context)

@login_required
def view_report(request, project_id):
    project = ProjectAnalysis.objects.get(id=project_id, user=request.user)
    
    if not project.analysis_completed:
        return redirect('analysis:analyze_project', project_id=project.id)
    
    report = project.report_json

    
    llm_recommendations_html = None
    if report.get("llm_recommendations"):
        llm_recommendations_html = markdown.markdown(report["llm_recommendations"])

    context = {
        'project': project,
        'report': report,
        'metrics': report.get('summary_metrics', {}),
        'files': report.get('detailed_report', {}).items(),
        'recommendations': report.get('summary_metrics', {}).get('recommendations', []),
        'llm_recommendations_html': llm_recommendations_html,  
    }

    files_by_severity = defaultdict(list)
    for file, issues in report.get('detailed_report', {}).items():
        for issue in issues:
            files_by_severity[issue['severity']].append((file, issue))
    
    context['files_by_severity'] = dict(files_by_severity)
    
    return render(request, 'analysis/report.html', context)

@login_required
def get_analysis_status(request, project_id):
    project = ProjectAnalysis.objects.get(id=project_id, user=request.user)
    return JsonResponse({
        'completed': project.analysis_completed,
        'current_file': project.current_file,
    })

@login_required
def results(request, project_id):
    project = ProjectAnalysis.objects.get(id=project_id, user=request.user)
    if project.analysis_completed:
        return redirect('analysis:view_report', project_id=project.id)

    if not hasattr(project, '_analysis_started'):
        def run_analysis():
            with tempfile.TemporaryDirectory() as temp_dir:
                for uploaded_file in project.files.all():
                    project.current_file = uploaded_file.original_name
                    project.save(update_fields=['current_file'])
                    file_path = os.path.join(temp_dir, uploaded_file.original_name)
                    with open(file_path, 'wb+') as dest:
                        for chunk in uploaded_file.file.chunks():
                            dest.write(chunk)
                    time.sleep(1)  # Ajoute ce délai pour voir défiler les fichiers
                analyzer = SecurityAnalyzer()
                report = analyzer.analyze_project(temp_dir)
                project.report_json = report
                project.analysis_completed = True
                project.current_file = None
                project.save()
        threading.Thread(target=run_analysis).start()
        project._analysis_started = True

    return render(request, 'analysis/results.html', {'project': project})

@login_required
def home(request):
    user = request.user
    projects_list = ProjectAnalysis.objects.filter(user=user).order_by('-id')
    nb_projects = projects_list.count()
    paginator = Paginator(projects_list, 10)  # 5 projets par page (modifie si besoin)
    page_number = request.GET.get('page')
    projects = paginator.get_page(page_number)
    return render(request, 'analysis/home.html', {
        'projects': projects,
        'nb_projects': nb_projects,
    })

@login_required
def download_report(request, project_id):
    project = ProjectAnalysis.objects.get(id=project_id, user=request.user)
    if not project.analysis_completed or not project.report_json:
        return HttpResponse("Rapport non disponible.", status=404)
    response = HttpResponse(
        json.dumps(project.report_json, indent=2, ensure_ascii=False),
        content_type='application/json'
    )
    response['Content-Disposition'] = f'attachment; filename=rapport_{project.project_name}_{project_id}.json'
    return response

def register(request):
    if request.method == 'POST':
        form = UserCreationForm(request.POST)
        if form.is_valid():
            user = form.save()
            login(request, user)
            return redirect('analysis:home')
    else:
        form = UserCreationForm()
    return render(request, 'registration/register.html', {'form': form})
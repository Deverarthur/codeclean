import os
import tempfile
import json
from django.shortcuts import render, redirect
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.conf import settings
from django.http import JsonResponse
from .models import ProjectAnalysis, UploadedFile
from .forms import ProjectUploadForm
from .testgen import generate_pytest_tests_for_project
from .analyzer import SecurityAnalyzer
from collections import defaultdict
import uuid

@login_required
def upload_project(request):
    if request.method == 'POST':
        form = ProjectUploadForm(request.POST, request.FILES)
        if form.is_valid():
            files = request.FILES.getlist('files')
            action = form.cleaned_data['action']

            # Crée un dossier unique pour chaque upload
            upload_id = str(uuid.uuid4())
            user_dir = os.path.join(settings.MEDIA_ROOT, 'uploads', upload_id)
            os.makedirs(user_dir, exist_ok=True)

            for f in files:
                file_path = os.path.join(user_dir, f.name)
                with open(file_path, 'wb+') as destination:
                    for chunk in f.chunks():
                        destination.write(chunk)

            if action == 'analysis':
                analyzer = SecurityAnalyzer(user_dir)
                report = analyzer.analyze_project()  # sans argument
                return render(request, 'analysis/report.html', {'report': report})
            elif action == 'testgen':
                test_results = generate_pytest_tests_for_project(user_dir)
                return render(request, 'analysis/testgen_results.html', {'test_results': test_results})
    else:
        form = ProjectUploadForm()
    
    return render(request, 'analysis/upload.html', {'form': form})

@login_required
def analyze_project(request, project_id):
    project = ProjectAnalysis.objects.get(id=project_id, user=request.user)
    
    if not project.analysis_completed:
        # Créer un répertoire temporaire pour l'analyse
        with tempfile.TemporaryDirectory() as temp_dir:
            # Copier tous les fichiers uploadés dans le répertoire temporaire
            for uploaded_file in project.files.all():
                file_path = os.path.join(temp_dir, uploaded_file.original_name)
                with open(file_path, 'wb+') as dest:
                    for chunk in uploaded_file.file.chunks():
                        dest.write(chunk)
            
            # Analyser le projet
            analyzer = SecurityAnalyzer()
            report = analyzer.analyze_project(temp_dir)
            
            # Sauvegarder les résultats
            project.report_json = report
            project.analysis_completed = True
            project.save()
    
    return redirect('analysis:view_report', project_id=project.id)

@login_required
def view_report(request, project_id):
    project = ProjectAnalysis.objects.get(id=project_id, user=request.user)
    
    if not project.analysis_completed:
        return redirect('analyze_project', project_id=project.id)
    
    # Formater le rapport pour l'affichage
    report = project.report_json

    context = {
        'project': project,
        'report': report,
        'metrics': report.get('summary_metrics', {}),
        'files': report.get('detailed_report', {}).items(),
        'recommendations': report.get('summary_metrics', {}).get('recommendations', [])  # <-- AJOUT
    }

    files_by_severity = defaultdict(list)
    for file, issues in report['detailed_report'].items():
        for issue in issues:
            files_by_severity[issue['severity']].append((file, issue))
    
    context['files_by_severity'] = dict(files_by_severity)
    
    return render(request, 'analysis/report.html', context)

@login_required
def get_analysis_status(request, project_id):
    project = ProjectAnalysis.objects.get(id=project_id, user=request.user)
    return JsonResponse({
        'completed': project.analysis_completed,
        'project_id': project.id
    })
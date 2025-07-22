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
from .analyzer import SecurityAnalyzer
from collections import defaultdict

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
            return redirect('analysis:analyze_project', project_id=project.id)
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
        'files': report.get('detailed_report', {}).items()  # Assure le passage des fichiers
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
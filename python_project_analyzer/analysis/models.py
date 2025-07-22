from django.db import models
from django.contrib.auth.models import User
import os
import uuid

def user_directory_path(instance, filename):
    
    ext = filename.split('.')[-1]
    unique_filename = f"{uuid.uuid4().hex}.{ext}"
    return f"user_{instance.analysis.user.id}/{unique_filename}"

class ProjectAnalysis(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    project_name = models.CharField(max_length=255)
    uploaded_at = models.DateTimeField(auto_now_add=True)
    analysis_completed = models.BooleanField(default=False)
    report_json = models.JSONField(null=True, blank=True)
    current_file = models.CharField(max_length=255, null=True, blank=True)
    
    def __str__(self):
        return f"{self.project_name} - {self.user.username}"

class UploadedFile(models.Model):
    analysis = models.ForeignKey(ProjectAnalysis, related_name='files', on_delete=models.CASCADE)
    file = models.FileField(upload_to=user_directory_path)
    original_name = models.CharField(max_length=255)
    
    def __str__(self):
        return self.original_name
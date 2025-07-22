import json
from django.urls import reverse
from django.test import TestCase, Client
from django.contrib.auth import get_user_model
from ..models import ProjectAnalysis

# tests/test_views.py


User = get_user_model()

class ViewReportTests(TestCase):
    def setUp(self):
        self.client = Client()
        self.user = User.objects.create_user(username='testuser', password='testpass')
        self.client.login(username='testuser', password='testpass')
        self.report_json = {
            "summary_metrics": {
                "recommendations": ["Use virtualenv", "Update dependencies"]
            },
            "detailed_report": {
                "file1.py": [
                    {"severity": "HIGH", "message": "Issue 1"}
                ],
                "file2.py": [
                    {"severity": "LOW", "message": "Issue 2"}
                ]
            }
        }
        self.project = ProjectAnalysis.objects.create(
            user=self.user,
            project_name="Test Project",
            report_json=self.report_json,
            analysis_completed=True
        )

    def test_view_report_success(self):
        url = reverse('analysis:view_report', args=[self.project.id])
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'analysis/report.html')
        self.assertIn('project', response.context)
        self.assertIn('report', response.context)
        self.assertIn('metrics', response.context)
        self.assertIn('files', response.context)
        self.assertIn('recommendations', response.context)
        self.assertIn('files_by_severity', response.context)
        self.assertEqual(response.context['project'], self.project)
        self.assertEqual(response.context['report'], self.report_json)
        self.assertIn('HIGH', response.context['files_by_severity'])
        self.assertIn('LOW', response.context['files_by_severity'])

    def test_view_report_redirect_if_not_completed(self):
        self.project.analysis_completed = False
        self.project.save()
        url = reverse('analysis:view_report', args=[self.project.id])
        response = self.client.get(url)
        self.assertEqual(response.status_code, 302)
        self.assertIn(reverse('analyze_project', args=[self.project.id]), response.url)

    def test_view_report_forbidden_for_other_user(self):
        other_user = User.objects.create_user(username='otheruser', password='otherpass')
        self.client.login(username='otheruser', password='otherpass')
        url = reverse('analysis:view_report', args=[self.project.id])
        response = self.client.get(url)
        self.assertEqual(response.status_code, 404)
import os
import json
import tempfile
from collections import defaultdict
from django.urls import reverse
from django.test import TestCase, Client
from django.contrib.auth import get_user_model
from django.core.files.uploadedfile import SimpleUploadedFile
from analysis.models import ProjectAnalysis, UploadedFile

User = get_user_model()

class ProjectViewsTests(TestCase):
    def setUp(self):
        self.client = Client()
        self.user = User.objects.create_user(username='testuser', password='testpass')
        self.client.login(username='testuser', password='testpass')
        # Dummy file for upload tests
        self.dummy_file = SimpleUploadedFile('dummy.txt', b'Hello, world!')
        
    def test_upload_project_analysis(self):
        """
        Test that uploading a project with action 'analyze' redirects to the analyze_project view.
        """
        form_data = {
            'project_name': 'My Analysis Project',
            # Simulate radio button option: default action is analysis.
            'action': 'analyze'
        }
        response = self.client.post(
            reverse('analysis:upload_project'),
            data={**form_data, 'files': [self.dummy_file]},
            format='multipart'
        )
        # Project should be created and user is redirected to analyze_project view.
        project = ProjectAnalysis.objects.filter(project_name='My Analysis Project', user=self.user).first()
        self.assertIsNotNone(project)
        self.assertEqual(response.status_code, 302)
        self.assertIn(reverse('analysis:analyze_project', args=[project.id]), response.url)

    def test_upload_project_generate_tests(self):
        """
        Test uploading a project with action 'generate_tests' redirects to a test generation view.
        """
        form_data = {
            'project_name': 'My Test Generation Project',
            # New option for generating tests instead of analysis.
            'action': 'generate_tests'
        }
        response = self.client.post(
            reverse('analysis:upload_project'),
            data={**form_data, 'files': [self.dummy_file]},
            format='multipart'
        )
        # Project should be created and user is redirected to the generate_tests view.
        project = ProjectAnalysis.objects.filter(project_name='My Test Generation Project', user=self.user).first()
        self.assertIsNotNone(project)
        self.assertEqual(response.status_code, 302)
        self.assertIn(reverse('analysis:generate_tests', args=[project.id]), response.url)

    def test_analyze_project_process(self):
        """
        Test that the project analysis process works, saving a report and redirecting to view_report.
        """
        # Create a project without a report
        project = ProjectAnalysis.objects.create(
            user=self.user,
            project_name="Analysis Process Project"
        )
        UploadedFile.objects.create(
            analysis=project,
            file=self.dummy_file,
            original_name=self.dummy_file.name
        )
        url = reverse('analysis:analyze_project', args=[project.id])
        response = self.client.get(url)
        # After analysis, the project should be completed and redirect to view_report.
        project.refresh_from_db()
        self.assertTrue(project.analysis_completed)
        self.assertEqual(response.status_code, 302)
        self.assertIn(reverse('analysis:view_report', args=[project.id]), response.url)

    def test_view_report_success(self):
        """
        Test that the view_report displays the analysis report when analysis is completed.
        """
        report = {
            "summary_metrics": {
                "recommendations": ["Consider code refactoring", "Improve tests"]
            },
            "detailed_report": {
                "dummy.txt": [
                    {"severity": "MEDIUM", "message": "Sample issue"}
                ]
            }
        }
        # Create a project with a pre-defined report and mark analysis completed.
        project = ProjectAnalysis.objects.create(
            user=self.user,
            project_name="Report Project",
            report_json=report,
            analysis_completed=True
        )
        url = reverse('analysis:view_report', args=[project.id])
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)
        self.assertIn('project', response.context)
        self.assertIn('report', response.context)
        self.assertIn('metrics', response.context)
        self.assertIn('files', response.context)
        self.assertIn('recommendations', response.context)
        self.assertIn('files_by_severity', response.context)
        self.assertEqual(response.context['project'], project)
        self.assertEqual(response.context['report'], report)
        # Check that issues are grouped by severity correctly.
        self.assertIn('MEDIUM', response.context['files_by_severity'])
        self.assertEqual(response.context['files_by_severity']['MEDIUM'], [('dummy.txt', {'severity': 'MEDIUM', 'message': 'Sample issue'})])

    def test_view_report_redirect_if_not_completed(self):
        """
        Test that view_report redirects to analyze_project if the analysis is not yet completed.
        """
        project = ProjectAnalysis.objects.create(
            user=self.user,
            project_name="Incomplete Analysis Project",
            analysis_completed=False
        )
        url = reverse('analysis:view_report', args=[project.id])
        response = self.client.get(url)
        self.assertEqual(response.status_code, 302)
        self.assertIn(reverse('analysis:analyze_project', args=[project.id]), response.url)

    def test_get_analysis_status(self):
        """
        Test that get_analysis_status returns the correct json response.
        """
        project = ProjectAnalysis.objects.create(
            user=self.user,
            project_name="Status Project",
            analysis_completed=False
        )
        url = reverse('analysis:get_analysis_status', args=[project.id])
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)
        data = json.loads(response.content)
        self.assertFalse(data['completed'])
        self.assertEqual(data['project_id'], project.id)
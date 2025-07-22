from django import forms

class MultipleFileInput(forms.ClearableFileInput):
    allow_multiple_selected = True  # Permettre la sélection multiple

class MultipleFileField(forms.FileField):
    def __init__(self, *args, **kwargs):
        kwargs.setdefault("widget", MultipleFileInput())
        super().__init__(*args, **kwargs)

    def clean(self, data, initial=None):
        single_file_clean = super().clean
        if isinstance(data, (list, tuple)):
            return [single_file_clean(d, initial) for d in data]
        return single_file_clean(data, initial)

class ProjectUploadForm(forms.Form):
    project_name = forms.CharField(label='Nom du projet', max_length=255)
    files = MultipleFileField(
        label='Fichiers Python à analyser',
        help_text='Sélectionnez un ou plusieurs fichiers Python (.py)'
        
    )
    CHOICES = [
        ('analysis', 'Analyse de sécurité'),
        ('testgen', 'Génération de cas de test'),
        ]
    action = forms.ChoiceField(choices=CHOICES, widget=forms.RadioSelect)
    
    def clean_files(self):
        files = self.files.getlist('files')
        if files:
            for file in files:
                if not file.name.endswith('.py'):
                    raise forms.ValidationError('Seuls les fichiers Python (.py) sont acceptés')
        return files
from django import forms
from django.core.exceptions import ValidationError
from .models import Tiroir, Travail, DomaineRecherche, Enseignants

class TravailForm(forms.ModelForm):
    class Meta:
        model = Travail
        fields = ['sujet', 'resume', 'pathFichier', 'domaine_recherche']

        widgets = {
            'sujet': forms.TextInput(attrs={'class': 'form-control'}),
            'resume': forms.Textarea(attrs={'class': 'form-control', 'style': 'height: 100px; resize: none;'}),
            'pathFichier': forms.FileInput(attrs={'class': 'form-control'}),
            'domaine_recherche': forms.Select(attrs={'class': 'form-control'}),
        }

    TYPE_TRAVAIL_CHOICES = [
        ('Projet Ordinaire', 'Projet Ordinaire'),
        ('TFC', 'TFC'),
        ('Mémoire', 'Mémoire'),
    ]
    
    type_travail = forms.ChoiceField(
        choices=TYPE_TRAVAIL_CHOICES,
        widget=forms.Select(attrs={'class': 'form-control'}),
    )
    
    directeur = forms.ModelChoiceField(
        queryset=Enseignants.objects.all(), 
        required=False, 
        widget=forms.Select(attrs={'class': 'form-control'})
    )
    rapporteur = forms.ModelChoiceField(
        queryset=Enseignants.objects.all(), 
        required=True, 
        widget=forms.Select(attrs={'class': 'form-control'})
    )

    def __init__(self, *args, **kwargs):
        super(TravailForm, self).__init__(*args, **kwargs)
        self.fields['domaine_recherche'].queryset = DomaineRecherche.objects.all()

    def clean_pathFichier(self):
        file = self.cleaned_data.get('pathFichier')
        if file:
            if not file.name.endswith('.pdf'):
                raise ValidationError("Le fichier doit être au format PDF.")
            if file.size > 50 * 1024 * 1024:  # 50 MB
                raise ValidationError("Le fichier ne doit pas dépasser 50 Mo.")
        return file

    def clean(self):
        cleaned_data = super().clean()
        type_travail = cleaned_data.get('type_travail')
        directeur = cleaned_data.get('directeur')
        rapporteur = cleaned_data.get('rapporteur')

        if type_travail in ['TFC', 'Mémoire']:
            if not directeur:
                raise ValidationError("Le directeur est requis pour un TFC ou un Mémoire.")
            if directeur == rapporteur:
                raise ValidationError("Le directeur et le rapporteur ne peuvent pas être la même personne pour un TFC ou un Mémoire.")
        return cleaned_data
    

class ModifierTravailForm(forms.ModelForm):
    TYPE_TRAVAIL_CHOICES = [
        ('Projet Ordinaire', 'Projet Ordinaire'),
        ('TFC', 'TFC'),
        ('Mémoire', 'Mémoire'),
    ]
    
    type_travail = forms.ChoiceField(
        choices=TYPE_TRAVAIL_CHOICES,
        widget=forms.Select(attrs={'class': 'form-control'}),
    )
    
    directeur = forms.ModelChoiceField(
        queryset=Enseignants.objects.all(), 
        required=False, 
        widget=forms.Select(attrs={'class': 'form-control'}),
    )
    
    rapporteur = forms.ModelChoiceField(
        queryset=Enseignants.objects.all(), 
        required=False, 
        widget=forms.Select(attrs={'class': 'form-control'}),
    )

    class Meta:
        model = Travail
        fields = ['sujet', 'resume', 'pathFichier', 'domaine_recherche', 'type_travail', 'directeur', 'rapporteur']

        widgets = {
            'sujet': forms.TextInput(attrs={'class': 'form-control'}),
            'resume': forms.Textarea(attrs={'class': 'form-control', 'style': 'height: 100px; resize: none;'}),
            'pathFichier': forms.FileInput(attrs={'class': 'form-control'}),
            'domaine_recherche': forms.Select(attrs={'class': 'form-control'}),
        }

    def __init__(self, *args, **kwargs):
        super(ModifierTravailForm, self).__init__(*args, **kwargs)
        self.fields['domaine_recherche'].queryset = DomaineRecherche.objects.all()

    def clean_pathFichier(self):
        file = self.cleaned_data.get('pathFichier')
        if file:
            if not file.name.endswith('.pdf'):
                raise ValidationError("Le fichier doit être au format PDF.")
            if file.size > 50 * 1024 * 1024:  # 50 MB
                raise ValidationError("Le fichier ne doit pas dépasser 50 Mo.")
        return file

    def clean(self):
        cleaned_data = super().clean()
        type_travail = cleaned_data.get('type_travail')
        directeur = cleaned_data.get('directeur')
        rapporteur = cleaned_data.get('rapporteur')

        if type_travail in ['TFC', 'Mémoire']:
            if not directeur:
                raise ValidationError("Le directeur est requis pour un TFC ou un Mémoire.")
            if directeur == rapporteur:
                raise ValidationError("Le directeur et le rapporteur ne peuvent pas être la même personne pour un TFC ou un Mémoire.")
        elif type_travail == 'Projet Ordinaire' and not rapporteur:
            raise ValidationError("Le rapporteur est requis pour un Projet Ordinaire.")
        
        return cleaned_data

    
class PublierTravailForm(forms.Form):
    tiroir = forms.ModelChoiceField(
        queryset=Tiroir.objects.all(),
        label="Sélectionner un tiroir",
        required=True,
        widget=forms.Select(attrs={'class': 'form-control'})
    )


class TiroirForm(forms.ModelForm):
    class Meta:
        model = Tiroir
        fields = ['nom', 'description']


class ChangerTiroirForm(forms.ModelForm):
    class Meta:
        model = Travail
        fields = ['tiroir']
        widgets = {
            'tiroir': forms.Select(attrs={'class': 'form-control'}),
        }
        labels = {
            'tiroir': 'Sélectionnez le tiroir',
        }

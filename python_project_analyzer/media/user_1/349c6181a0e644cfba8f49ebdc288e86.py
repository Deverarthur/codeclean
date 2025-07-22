from django.forms import ModelForm
from django.contrib.auth.forms import UserCreationForm
from django import forms
from .models import *

from django.contrib.auth.models import User


class CreerUserForm(UserCreationForm):
    class Meta:
        model = User
        fields = ['username', 'email', 'password1', 'password1']


class CreerQuestionForm(ModelForm):
    class Meta:
        model = Question
        fields = ['categorieId', 'questionTexte']


class CreerReponseForm(ModelForm):
    class Meta:
        model = Reponse
        fields = ['reponseTexte']


class RapportQuestionForm(ModelForm):
    class Meta:
        model = RapportQuestion
        fields = ['rapportTexte']


class RapportReponseForm(ModelForm):
    class Meta:
        model = RapportReponse
        fields = ['rapportTexte']

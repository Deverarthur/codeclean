import django_filters
from django_filters import CharFilter
from .models import *


class QuestionFilter(django_filters.FilterSet):
    questionTexte = CharFilter(
        field_name="questionTexte", lookup_expr="icontains")

    class Meta:
        model = Question
        fields = "__all__"
        exclude = ["userId", "dateCreation"]

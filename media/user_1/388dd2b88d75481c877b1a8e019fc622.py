from datetime import datetime
from django.shortcuts import render


def index(request):
    utilisateurs = ["Devernay"]
    return render(request, "appDjango1/index.html", context={"date" : datetime.today(), "utilisateurs" : utilisateurs})
from django.contrib import admin

# Register your models here.
from .models import Travail, DomaineRecherche, TypeTravail, Tiroir, Encadrer, Emprunter, Payer

admin.site.register(Travail)
admin.site.register(DomaineRecherche)
admin.site.register(Tiroir)
admin.site.register(Encadrer)
admin.site.register(Emprunter)
admin.site.register(Payer)
admin.site.register(TypeTravail)


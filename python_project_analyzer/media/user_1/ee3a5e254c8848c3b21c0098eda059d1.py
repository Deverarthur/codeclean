from django.contrib import admin
from .models import *

# Register your models here.
admin.site.register(Categorie)
admin.site.register(Question)
admin.site.register(Reponse)
admin.site.register(Update)
admin.site.register(RapportQuestion)
admin.site.register(RapportReponse)
admin.site.register(SignalerQuestion)
admin.site.register(SignalerReponse)

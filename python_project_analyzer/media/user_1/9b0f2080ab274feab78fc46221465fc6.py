from django.urls import path
from . import views
from django.contrib.auth.views import LogoutView

app_name = 'travaux'

urlpatterns = [
    #Etudiants
    path('etudiants/index_etudiants/', views.index_etudiants, name='index_etudiants'),
    path('etudiants/travaux_soumis/', views.travaux_soumis, name='travaux_soumis'),
    path('soumettre_travail/', views.soumettre_travail, name='soumettre_travail'),
    path('etudiants/details_travail/<int:travail_id>/', views.details_travail, name='details_travail'),
    path('etudiants/telecharger_travail/<int:travail_id>/', views.telecharger_travail, name='telecharger_travail'),
    path('travaux_faculte/', views.travaux_faculte, name='travaux_faculte'),
    path('details_travail_faculte/<int:travail_id>/', views.details_travail_faculte, name='details_travail_faculte'),
    path('achat_travail/<int:travail_id>/', views.achat_travail, name='acheter_travail'),
    path('modifier_travail/<int:travail_id>/', views.modifier_travail, name='modifier_travail'),
    path('deconnexion/', views.deconnexion, name='deconnexion'),


    #Enseignants
    path('enseignants/', views.index_enseignants, name='index_enseignants'),
    path('enseignants/travaux_diriges/', views.travaux_diriges, name='travaux_diriges'),
    path('faculte/publies/', views.travaux_faculte_publies, name='travaux_faculte_publies'),
    path('faculte/details/<int:travail_id>/', views.details_travail_faculte_enseignants, name='details_travail_faculte_enseignants'),
    path('travaux/diriges/details/<int:travail_id>/', views.details_travail_diriges, name='details_travail_diriges'),
    path('travaux/diriges/approuver/<int:travail_id>/', views.approuver_travail, name='approuver_travail'),
    path('travail/rejeter/<int:travail_id>/', views.rejeter_travail, name='rejeter_travail'),

    #Bibliothecaires
    path('bibliothecaire/', views.index_bibliothecaires, name='index_bibliothecaires'),
    path('travaux_facultes_bibliothecaires/', views.travaux_facultes_bibliothecaires, name='travaux_facultes_bibliothecaires'),
    path('emprunter_travail/<int:travail_id>/', views.emprunter_travail, name='emprunter_travail'),
    path('details-travail-faculte/<int:travail_id>/', views.details_travail_faculte_bibliothecaires, name='details_travail_faculte_bibliothecaires'),
    path('travaux-attente/', views.travaux_attente, name='travaux_attente'),
    path('details-travail-attente/<int:travail_id>/', views.details_travail_attente, name='details_travail_attente'),
    path('publier-travail/<int:travail_id>/', views.publier_travail, name='publier_travail'),
    path('tiroirs/', views.list_tiroirs, name='list_tiroirs'),
    path('details-tiroirs/<int:tiroir_id>/', views.details_tiroirs, name='details_tiroirs'),
    path('creer-tiroir/', views.creer_tiroir, name='creer_tiroir'),
    path('details_travaux_tiroirs/<int:travail_id>/', views.details_travaux_tiroirs, name='details_travaux_tiroirs'),
    path('tiroirs/<int:tiroir_id>/travail/<int:travail_id>/changer/', views.changer_tiroir, name='changer_tiroir'),
    path('travaux/empruntes/', views.liste_empruntes, name='liste_empruntes'),
    path('travaux/empruntes/restituer/<int:emprunt_id>/', views.restituer_travail, name='restituer_travail'),
    path('details_travaux_empruntes/<int:travail_id>/', views.details_travaux_empruntes, name='details_travaux_empruntes'),
    path('paiements/', views.liste_paiements, name='liste_paiements'),
    path('paiement/<int:paiement_id>/', views.details_paiement, name='details_paiement'),
    
]


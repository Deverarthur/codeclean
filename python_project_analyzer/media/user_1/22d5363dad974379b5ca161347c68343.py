from django.urls import path
from . import views

urlpatterns = [
    path("enregistrer/", views.PageEnregistrement, name="enregistrer"),
    path("login/", views.loginPage, name="login"),
    path("deconnecter/", views.deconnexion, name="deconnecter"),
    path('', views.pageAccueil, name='pageAccueil'),
    path('home/', views.home, name='home'),

    path('forum/<int:page>/', views.forum, name='forum'),

    path('forum/question/creer', views.creerQuestion, name='creerQuestion'),
    path('forum/question/<int:id>/',
         views.afficherQuestion, name='afficherQuestion'),
    path('forum/question/update/<int:id>/',
         views.updateQuestion, name='updateQuestion'),
    path('forum/question/supprimer/<int:id>/',
         views.supprimerQuestion, name='supprimerQuestion'),

    path('forum/reponse/creer/<int:questionId>',
         views.creerReponse, name='creerReponse'),
    path('forum/reponse/update/<int:reponseId>',
         views.updateReponse, name='updateReponse'),
    path('forum/reponse/supprimer/<int:reponseId>',
         views.supprimerReponse, name='supprimerReponse'),

    path('updates/', views.updates, name="updates"),

    path('forum/question/report/<int:id>/',
         views.rapportQuestion, name="rapportQuestion"),
    path('forum/reponse/report/<int:id>/',
         views.rapportReponse, name="rapportReponse"),

    path('profil/', views.profil, name="profil"),

     path("autosuggest/", views.autosuggestion, name="autosuggestion"),
]


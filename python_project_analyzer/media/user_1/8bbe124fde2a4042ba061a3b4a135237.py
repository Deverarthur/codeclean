from datetime import date
from django.db import models
from users.models import Etudiants, Enseignants
from django.utils.text import slugify
import os

def get_upload_path(instance, filename):
    # Obtenir les 30 premières lettres du sujet
    sujet_slug = slugify(instance.sujet[:30])
    # Obtenir la date de soumission
    date_soumission = instance.dateSoumission.strftime('%Y%m%d')
    # Obtenir le nom de l'étudiant
    etudiant_nom = slugify(f"{instance.etudiant.prenom}_{instance.etudiant.nom}")
    # Obtenir l'extension du fichier
    ext = filename.split('.')[-1]
    # Générer le nouveau nom de fichier
    new_filename = f"{etudiant_nom}_{date_soumission}_{sujet_slug}.{ext}"
    # Retourner le chemin complet
    return os.path.join('Documents', new_filename)

class DomaineRecherche(models.Model):
    intitule = models.CharField(max_length=200)
    description = models.TextField()

    def __str__(self):
        return self.intitule

class TypeTravail(models.Model):
    nom = models.CharField(max_length=100)

    def __str__(self):
        return self.nom

class Tiroir(models.Model):
    nom = models.CharField(max_length=200)
    description = models.TextField()

    def __str__(self):
        return self.nom

class Travail(models.Model):
    sujet = models.CharField(max_length=200)
    resume = models.TextField()
    anneePublication = models.CharField(max_length=25, null=True)
    pathFichier = models.FileField(upload_to=get_upload_path)
    statut = models.CharField(max_length=100)
    etudiant = models.ForeignKey(Etudiants, on_delete=models.CASCADE, related_name='travaux')
    tiroir = models.ForeignKey(Tiroir, on_delete=models.SET_NULL, null=True, related_name='travaux')
    domaine_recherche = models.ForeignKey(DomaineRecherche, on_delete=models.SET_NULL, null=True, related_name='travaux')
    typeTravail = models.CharField(max_length=100, default='Projet Ordinaire')
    dateSoumission = models.DateField(default=date.today)
    imprime = models.BooleanField(null=True)
    emprunte = models.BooleanField(null=True)
    promotion = models.CharField(max_length=100, null=True)
    option = models.CharField(max_length=100, null=True)

    def __str__(self):
        return self.sujet

class Encadrer(models.Model):
    travail = models.ForeignKey(Travail, on_delete=models.CASCADE, related_name='encadrements')
    enseignant = models.ForeignKey(Enseignants, on_delete=models.CASCADE, related_name='encadrements')
    role = models.CharField(max_length=100)
    decision = models.BooleanField(null=True)
    motif = models.TextField(blank=True, null=True)

    def __str__(self):
        return f"{self.travail.sujet} - {self.enseignant.prenom} {self.enseignant.nom}"

class Payer(models.Model):
    etudiant = models.ForeignKey(Etudiants, on_delete=models.CASCADE, related_name='paiements')
    travail = models.ForeignKey(Travail, on_delete=models.CASCADE, related_name='paiements')
    statutPaiement = models.CharField(max_length=100)
    date = models.DateField()
    montant = models.DecimalField(max_digits=10, decimal_places=2)

    def __str__(self):
        return f"{self.etudiant.prenom} {self.etudiant.nom} - {self.travail.sujet}"

class Emprunter(models.Model):
    etudiant = models.ForeignKey(Etudiants, on_delete=models.CASCADE, related_name='emprunts')
    travail = models.ForeignKey(Travail, on_delete=models.CASCADE, related_name='emprunts')
    dateEmprunt = models.DateField()
    etat = models.CharField(max_length=100)

    def __str__(self):
        return f"{self.etudiant.prenom} {self.etudiant.nom} - {self.travail.sujet}"

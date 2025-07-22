from django.db import models
from django.conf import settings


class Categorie(models.Model):
    nomCategorie = models.CharField(max_length=100)
    dateCreation = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return '%s' % (self.nomCategorie)


class Question(models.Model):
    userId = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
    )
    categorieId = models.ForeignKey(Categorie, on_delete=models.CASCADE)
    questionTexte = models.TextField()
    datecreation = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return '%s' % (self.questionTexte)


class Reponse(models.Model):
    userId = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
    )
    questionId = models.ForeignKey(Question, on_delete=models.CASCADE)
    reponseTexte = models.TextField()
    dateCreation = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return '%s' % (self.reponseTexte)


class Update(models.Model):
    categorieId = models.ForeignKey(Categorie, on_delete=models.CASCADE)
    updateTexte = models.TextField()
    dateCreation = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return '%s' % (self.updateTexte)


class RapportQuestion(models.Model):
    userId = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
    )
    questionId = models.ForeignKey(Question, on_delete=models.CASCADE)
    rapportTexte = models.TextField()
    dateCreation = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return '%s' % (self.rapportTexte)


class RapportReponse(models.Model):
    userId = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
    )
    reponseId = models.ForeignKey(Reponse, on_delete=models.CASCADE)
    rapportTexte = models.TextField()
    dateCreation = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return '%s' % (self.rapportTexte)


class SignalerQuestion(models.Model):
    questionId = models.ForeignKey(Question, on_delete=models.CASCADE)
    dateCreation = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return '%s' % (self.questionId.questionTexte)


class SignalerReponse(models.Model):
    reponseId = models.ForeignKey(Reponse, on_delete=models.CASCADE)
    dateCreation = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return '%s' % (self.reponseId.reponseTexte)

from django.contrib.auth.decorators import login_required
from django.shortcuts import render, redirect
from django.http import HttpResponse, Http404, JsonResponse
from django.contrib.auth.forms import UserCreationForm
from django.contrib.auth import authenticate, login, logout
from django.core.mail import send_mail
from django.contrib import messages  
from .models import *
from .filters import *


from .forms import *
import logging
custom_db_logger = logging.getLogger("forum.custom.db")

# Create your views here.

def PageEnregistrement(request):
    if request.user.is_authenticated:
        return redirect('home')
    else:
        form = CreerUserForm()
        if request.method == 'POST':
            form = CreerUserForm(request.POST)
            if form.is_valid():
                user = form.save()
                userMessage = form.cleaned_data.get('username')
                email = form.cleaned_data.get('email')  # Récupérer l'email de l'utilisateur
                messages.success(request, 'Compte créé avec succès pour ' + userMessage)

                # Envoyer un email de confirmation
                subject = 'Bienvenue sur Forum'
                message = f'Bonjour {userMessage},\n\nVotre compte a été créé avec succès.\n\nCordialement,\nL\'équipe Forum'
                from_email = settings.EMAIL_HOST_USER
                recipient_list = [email]
                
                send_mail(subject, message, from_email, recipient_list, fail_silently=False)

                return redirect('login')

        context = {'form': form}
        return render(request, 'forum/enregistrer.html', context)


def loginPage(request):
    if request.user.is_authenticated:
        return redirect('home')

    else:
        if request.method == 'POST':
            username = request.POST.get('username')
            password = request.POST.get('password')

            user = authenticate(request, username=username, password=password)

            if user is not None:
                login(request, user)
                return redirect('home')

            else:
                messages.info(request, 'Nom d utilisateur ou mot de passe incorrect !')

        context = {}
        return render(request, 'forum/login.html', context)


def deconnexion(request):
    logout(request)
    return redirect('pageAccueil')


def pageAccueil(request):
    if request.user.is_authenticated:
        return redirect("forum", page=1)
    return render(request, 'forum/index.html', {})


@login_required(login_url='login')
def home(request):

    return redirect("forum", page=1)


@login_required(login_url='login')
def forum(request, page):
    questions = Question.objects.all().order_by('-dateCreation')
    filtrerQuestion = QuestionFilter(request.GET, queryset=questions)
    questions = filtrerQuestion.qs

    min_index = (page-1)*10
    max_index = min((page*10)-1, len(questions)-1)
    if len(questions) % 10 == 0:
        max_page = len(questions)//10
    else:
        max_page = len(questions)//10 + 1

    if len(questions) == 0:
        min_index = 0
        max_index = 0
        max_page = 1
    context = {'questions': questions[min_index:max_index+1],
               'pageSuivante': min(page+1, max_page),
               'pagePrecedente': max(page-1, 1),
               'filtrerQuestion': filtrerQuestion,
               }
    return render(request, 'forum/forum.html', context)


@login_required(login_url='login')
def creerQuestion(request):
    form = CreerQuestionForm()
    if request.method == 'POST':
        form = CreerQuestionForm(request.POST)
        if form.is_valid():
            question = form.save(commit=False)
            question.userId = request.user
            question.save()

            return redirect("forum", page=1)
        else:
            print("Formulaire non valide")

    context = {'form': form}
    return render(request, 'forum/creerQuestion.html', context)


@login_required(login_url='login')
def afficherQuestion(request, id):
    question = Question.objects.get(id=id)
    auteur = question.userId
    userCourant = request.user
    reponses = question.reponse_set.all().order_by('-dateCreation')

    context = {
        'question': question,
        'reponses': reponses,
        'auteur': auteur,
        'userCourant': userCourant
    }
    return render(request, 'forum/afficherQuestion.html', context)


@login_required(login_url='login')
def updateQuestion(request, id):
    question = Question.objects.get(id=id)
    if(request.user != question.userId):
        return redirect("afficherQuestion", id=id)
    
    form = CreerQuestionForm(instance=question)
    if request.method == 'POST':
        form = CreerQuestionForm(request.POST, instance=question)
        if form.is_valid():
            form.save()

            return redirect("afficherQuestion", id=id)
    context = {'form': form}
    return render(request, 'forum/creerQuestion.html', context)


@login_required(login_url='login')
def supprimerQuestion(request, id):
    if request.method == 'POST':
        question = Question.objects.get(id=id)
        if(request.user != question.userId):
            return redirect("afficherQuestion", id=id)
        custom_db_logger.debug("%s Question supprimée \"%s\""%(request.user, question))
        question.delete()
        return redirect('forum', page=1)
    else:
        raise Http404("Page non trouvée")


@login_required(login_url='login')
def creerReponse(request, questionId):
    question = Question.objects.get(id=questionId)
    form = CreerReponseForm()
    if request.method == 'POST':
        form = CreerReponseForm(request.POST)
        if form.is_valid():
            reponse = form.save(commit=False)
            reponse.userId = request.user
            reponse.questionId = question
            reponse.save()

            send_mail(
                subject='Nouvelle réponse à votre question',
                message=f'Bonjour {question.userId.username},\n\nVotre question a reçu une nouvelle réponse de {request.user.username}.\n\nVisitez Forum pour voir la réponse.\n\nCordialement,\nVotre équipe Forum',
                from_email=settings.EMAIL_HOST_USER,
                recipient_list=[question.userId.email],
                fail_silently=False,
            )

            return redirect("afficherQuestion", id=questionId)
        else:
            print("Formulaire non valide")

    context = {'form': form}
    return render(request, 'forum/creerReponse.html', context)


@login_required(login_url='login')
def updateReponse(request, reponseId):
    reponse = Reponse.objects.get(id=reponseId)
    if(request.user != reponse.userId):
        return redirect("afficherQuestion", reponseId=reponse.questionId)
    form = CreerReponseForm(instance=reponse)
    if request.method == 'POST':
        form = CreerReponseForm(request.POST, instance=reponse)
        if form.is_valid():
            form.save()

            return redirect("afficherQuestion", id=reponse.questionId.id)
    context = {'form': form}
    return render(request, 'forum/creerReponse.html', context)


@login_required(login_url='login')
def supprimerReponse(request, reponseId):
    if request.method == 'POST':
        reponse = Reponse.objects.get(id=reponseId)
        questionId_courant = reponse.questionId.id
        if(request.user != reponse.userId):
            return redirect("afficherQuestion", id=questionId_courant)
        custom_db_logger.debug("%s Réponse supprimée \"%s\""%(request.user, reponse))
        reponse.delete()
        return redirect('afficherQuestion', id=questionId_courant)
    else:
        print("Accès Invalide")
        raise Http404("Page non trouvée")


@login_required(login_url='login')
def updates(request):
    updates = Update.objects.all().order_by('-dateCreation')
    context = {'updates': updates}
    return render(request, 'forum/updates.html', context)


@login_required(login_url='login')
def rapportQuestion(request, id):
    question = Question.objects.get(id=id)
    form = RapportQuestionForm()
    errors = list()
    threshold = 1

    prev_rapport = RapportQuestion.objects.filter(
        questionId=question.id, userId=request.user.id)
    
    if len(prev_rapport) >= 1:
        errors.append("Question déjà rappportée")
        return redirect("afficherQuestion", id=question.id)

    elif request.method == "POST":

        form = RapportQuestionForm(request.POST)
        if form.is_valid():
            report = form.save(commit=False)
            report.userId = request.user
            report.questionId= question
            report.save()

        total_reports = RapportQuestion.objects.filter(questionId=question.id)
        if len(total_reports) == threshold:
            questionSignalee = SignalerQuestion()
            questionSignalee.questionId = question
            questionSignalee.save()
            return redirect("afficherQuestion", id=question.id)
    context = {'form': form, 'errors': errors}
    return render(request, "forum/rapporterQuestion.html", context)


@login_required(login_url='login')
def rapportReponse(request, id):
    reponse = Reponse.objects.get(id=id)
    form = RapportReponseForm()
    errors = list()
    threshold = 1

    prev_rapport = RapportReponse.objects.filter(
        reponseId=reponse.id, userId=request.user.id)

    if len(prev_rapport) >= 1:
        errors.append("Question déjà rapportée")
        return redirect("afficherQuestion", id=reponse.question_id.id)

    elif request.method == "POST":

        form = RapportReponseForm(request.POST)
        if form.is_valid():
            rapport = form.save(commit=False)
            rapport.userId = request.user
            rapport.reponseId = reponse
            rapport.save()

        total_reports = RapportReponse.objects.filter(reponseId=reponse.id)
        if len(total_reports) == threshold:
            reponseSignalee= SignalerReponse()
            reponseSignalee.reponseId= reponse
            reponseSignalee.save()
            return redirect("afficherQuestion", id=reponse.questionId.id)
    context = {'form': form, 'errors': errors}
    return render(request, "forum/rapporterReponse.html", context)



@login_required(login_url='login')
def profil(request):
    questions = Question.objects.filter(
        userId=request.user.id).order_by('-dateCreation')
    reponses = Reponse.objects.filter(
        userId=request.user.id).order_by('-dateCreation')
    context = {'questions': questions, 'reponses': reponses}
    return render(request, "forum/profil.html", context)


def autosuggestion(request):
    requete = request.GET.get('term')
    queryset = Question.objects.filter(question_text__icontains=requete)
    list = []
    list += [x.questionTexte for x in queryset]
    return JsonResponse(list, safe=False)

from datetime import datetime
import locale
from django.shortcuts import render, redirect
from django.contrib.auth import authenticate, login, logout
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.contrib.auth.models import User

from .decorators import etudiant_required, enseignant_required, bibliothecaire_required
from .forms import ChangerTiroirForm, ModifierTravailForm, PublierTravailForm, TiroirForm, TravailForm
from .models import Emprunter, Tiroir, Travail, Encadrer, Payer, Enseignants, Etudiants
from django.shortcuts import render, get_object_or_404
from django.http import HttpResponse
from django.db.models import Q, Prefetch
from users.models import Etudiants
from django.utils import timezone
from django.db.models import Count
from django.db import models

@login_required
@etudiant_required
def index_etudiants(request):
    
    user = request.user

    
    total_travaux_publies = Travail.objects.filter(statut='Publié').count()

    
    travaux_achetes = Payer.objects.filter(etudiant=user.etudiants).count()

   
    recents_travaux = Travail.objects.filter(statut='Publié').order_by('-dateSoumission')[:10]

    
    context = {
        'user': user,
        'total_travaux_publies': total_travaux_publies,
        'travaux_achetes': travaux_achetes,
        'recents_travaux': recents_travaux,
    }

    return render(request, 'travaux/etudiants/index_etudiants.html', context)

@login_required
@etudiant_required
def travaux_soumis(request):
    etudiant = request.user.etudiants
    travaux = Travail.objects.filter(etudiant=etudiant)

    travaux_data = []
    for travail in travaux:
        encadrements = travail.encadrements.all()
        directeur = encadrements.filter(role="Directeur").first()
        rapporteur = encadrements.filter(role="Rapporteur").first()
        travaux_data.append({
            'travail': travail,
            'directeur': directeur.enseignant if directeur else None,
            'rapporteur': rapporteur.enseignant if rapporteur else None,
        })

    
    achats = Payer.objects.filter(etudiant=etudiant)
    travaux_achetes = [achat.travail for achat in achats]

    context = {
        'travaux_data': travaux_data,
        'travaux_achetes': travaux_achetes,
    }
    return render(request, 'travaux/etudiants/travaux_soumis.html', context)

@login_required
@etudiant_required
def soumettre_travail(request):
    if request.method == 'POST':
        form = TravailForm(request.POST, request.FILES)
        if form.is_valid():
            travail = form.save(commit=False)
            travail.statut = 'En attente'
            travail.etudiant = request.user.etudiants
            travail.typeTravail = form.cleaned_data.get('type_travail')
            
            
            etudiant = request.user.etudiants
            travail.promotion = etudiant.promotion
            travail.option = etudiant.option
            
            travail.save()

           
            type_travail = form.cleaned_data.get('type_travail')
            directeur = form.cleaned_data.get('directeur')
            rapporteur = form.cleaned_data.get('rapporteur')

            if type_travail in ['TFC', 'Mémoire']:
                if directeur:
                    Encadrer.objects.create(travail=travail, enseignant=directeur, role='Directeur')
                if rapporteur:
                    Encadrer.objects.create(travail=travail, enseignant=rapporteur, role='Rapporteur')
            elif type_travail == 'Projet Ordinaire':
                if rapporteur:
                    Encadrer.objects.create(travail=travail, enseignant=rapporteur, role='Rapporteur')

            messages.success(request, "Le travail a été soumis avec succès.")
            return redirect('travaux:travaux_soumis')
    else:
        form = TravailForm()
    
    return render(request, 'travaux/etudiants/soumettre_travail.html', {'form': form})


@login_required
@etudiant_required
def details_travail(request, travail_id):
    travail = get_object_or_404(Travail, pk=travail_id)
    encadrements = travail.encadrements.all()

    directeur = encadrements.filter(role="Directeur").first()
    rapporteur = encadrements.filter(role="Rapporteur").first()
    
    motif_rejet = None
    enseignant_rejet = None

    if travail.statut == 'Rejeté':
        for encadrement in encadrements:
            if encadrement.decision == 0:
                motif_rejet = encadrement.motif
                enseignant_rejet = encadrement.enseignant
                break
    
    context = {
        'travail': travail,
        'directeur': directeur.enseignant if directeur else None,
        'rapporteur': rapporteur.enseignant if rapporteur else None,
        'motif_rejet': motif_rejet,
        'enseignant_rejet': enseignant_rejet,
    }
    return render(request, 'travaux/etudiants/details_travaux.html', context)


def telecharger_travail(request, travail_id):
    travail = get_object_or_404(Travail, pk=travail_id)
    file_path = travail.pathFichier.path
    

    with open(file_path, 'rb') as f:
        response = HttpResponse(f.read(), content_type='application/octet-stream')
        response['Content-Disposition'] = f'attachment; filename={travail.pathFichier.name}'
        return response
    
@login_required
@etudiant_required
def travaux_faculte(request):
    etudiant = request.user.etudiants
    travaux = Travail.objects.filter(statut='Publié').select_related('domaine_recherche', 'etudiant')

    travaux_data = []
    for travail in travaux:
        achete = Payer.objects.filter(etudiant=etudiant, travail=travail).exists()

        travaux_data.append({
            'travail': travail,
            'achete': achete
        })

    return render(request, 'travaux/etudiants/travaux_faculte.html', {'travaux_data': travaux_data})

@login_required
@etudiant_required
def details_travail_faculte(request, travail_id):
    travail = get_object_or_404(Travail, id=travail_id)
    directeur = Encadrer.objects.filter(travail=travail, role='Directeur').first()
    rapporteur = Encadrer.objects.filter(travail=travail, role='Rapporteur').first()

    return render(request, 'travaux/etudiants/details_travaux_faculte.html', {
        'travail': travail,
        'directeur': directeur,
        'rapporteur': rapporteur
    })

@login_required
@etudiant_required
def achat_travail(request, travail_id):
    travail = get_object_or_404(Travail, pk=travail_id)
    etudiant = get_object_or_404(Etudiants, id=request.user.id) 

    if request.method == "POST":
        montant = request.POST.get("montant")
        Payer.objects.create(
            etudiant=etudiant,
            travail=travail,
            statutPaiement="Payé",
            date=timezone.now(),
            montant=montant
        )
        messages.success(request, "Paiement effectué avec succès")
        return redirect('travaux:travaux_faculte')

    return render(request, 'travaux/etudiants/achat_travail.html', {'travail': travail})

@login_required
@etudiant_required
def modifier_travail(request, travail_id):
    travail = get_object_or_404(Travail, id=travail_id)
    
    if request.method == 'POST':
        form = ModifierTravailForm(request.POST, request.FILES, instance=travail)
        if form.is_valid():
            travail = form.save(commit=False)
            travail.statut = 'En attente'
            travail.save()

            # Mise à jour des encadrements
            type_travail = form.cleaned_data.get('type_travail')
            directeur = form.cleaned_data.get('directeur')
            rapporteur = form.cleaned_data.get('rapporteur')

            # Supprimer les encadrements existants
            Encadrer.objects.filter(travail=travail).delete()

            # Ajouter le directeur et le rapporteur en fonction du type de travail
            if type_travail in ['TFC', 'Mémoire']:
                Encadrer.objects.create(travail=travail, enseignant=directeur, role='Directeur')
                Encadrer.objects.create(travail=travail, enseignant=rapporteur, role='Rapporteur')
            elif type_travail == 'Projet Ordinaire':
                Encadrer.objects.create(travail=travail, enseignant=rapporteur, role='Rapporteur')

            messages.success(request, "Le travail a été modifié et soumis avec succès.")
            return redirect('travaux:travaux_soumis')
    else:
        form = ModifierTravailForm(instance=travail)
        
    return render(request, 'travaux/etudiants/modifier_travail.html', {'form': form, 'travail': travail})




def deconnexion(request):
    logout(request)

    request.session.flush()
    return redirect('users:connexion')


#Enseignants
@login_required
@enseignant_required
def index_enseignants(request):
    enseignant = Enseignants.objects.get(pk=request.user.id)

    
    travaux_diriges_publies = Travail.objects.filter(
        encadrements__enseignant=enseignant,
        statut='Publié'
    ).distinct()

    # Travaux en attente pour cet enseignant
    travaux_en_attente = Travail.objects.filter(
        encadrements__enseignant=enseignant,
        encadrements__role='Rapporteur',
        encadrements__decision__isnull=True,
        typeTravail__in=['Projet ordinaire', 'TFC', 'Mémoire']
    ).distinct() | Travail.objects.filter(
        encadrements__enseignant=enseignant,
        encadrements__role='Directeur',
        encadrements__travail__encadrements__role='Rapporteur',
        encadrements__travail__encadrements__decision=1,
        encadrements__decision__isnull=True,
        typeTravail__in=['TFC', 'Mémoire']
    ).distinct()

    
    total_travaux_publies = Travail.objects.filter(
        statut='Publié'
    ).count()

    context = {
        'travaux_diriges_publies': travaux_diriges_publies.count(),
        'travaux_en_attente': travaux_en_attente.count(),
        'total_travaux_publies': total_travaux_publies,
        'travaux_diriges': travaux_diriges_publies.order_by('-dateSoumission')[:10],
    }
    return render(request, 'travaux/enseignants/index_enseignants.html', context)

@login_required
@enseignant_required
def travaux_diriges(request):
    enseignant = request.user.enseignants

    # Travaux où l'enseignant est rapporteur
    travaux_rapporteur = Travail.objects.filter(
        encadrements__enseignant=enseignant,
        encadrements__role='Rapporteur',
        typeTravail__in=['Projet ordinaire', 'TFC', 'Mémoire']
    ).distinct()

    # Travaux où l'enseignant est directeur et le rapporteur a approuvé
    travaux_directeur = Travail.objects.filter(
        encadrements__enseignant=enseignant,
        encadrements__role='Directeur',
        encadrements__travail__encadrements__role='Rapporteur',
        encadrements__travail__encadrements__decision=1
    ).distinct()

    # Combiner les deux QuerySets
    travaux_combines = travaux_rapporteur | travaux_directeur

    
    travaux_statut = []
    for travail in travaux_combines:
        encadrements = travail.encadrements.all()
        rapporteur_decision = None
        directeur_decision = None
        for encadrement in encadrements:
            if encadrement.role == 'Rapporteur':
                rapporteur_decision = encadrement.decision
            elif encadrement.role == 'Directeur':
                directeur_decision = encadrement.decision

        
        if travail.typeTravail == 'Projet Ordinaire':
            if rapporteur_decision is None:
                statut = 'En attente'
            elif rapporteur_decision == 0:
                statut = 'Rejeté'
            elif rapporteur_decision == 1:
                if travail.statut == 'Publié' and travail.tiroir_id is not None and travail.imprime == 1:
                    statut = 'Publié'
                else:
                    statut = 'Approuvé'
            else:
                statut = 'En attente'
        else:  
            if rapporteur_decision is None:
                statut = 'En attente'
            elif rapporteur_decision == 0:
                statut = 'Rejeté'
            elif rapporteur_decision == 1 and directeur_decision is None:
                statut = 'En attente'
            elif rapporteur_decision == 1 and directeur_decision == 0:
                statut = 'Rejeté'
            elif rapporteur_decision == 1 and directeur_decision == 1:
                if travail.statut == 'Publié' and travail.tiroir_id is not None and travail.imprime == 1:
                    statut = 'Publié'
                else:
                    statut = 'Approuvé'
            else:
                statut = 'En attente'

        
        show_buttons = True
        if statut == 'En attente' and travail.typeTravail in ['TFC', 'Mémoire']:
            if travail.encadrements.filter(role='Rapporteur', decision=1, enseignant=enseignant).exists() and travail.encadrements.filter(role='Directeur', decision__isnull=True).exists():
                show_buttons = False

        travaux_statut.append({
            'travail': travail,
            'statut': statut,
            'show_buttons': show_buttons,
        })

    context = {
        'travaux_statut': travaux_statut,
    }
    return render(request, 'travaux/enseignants/travaux_diriges.html', context)


@login_required
@enseignant_required
def travaux_faculte_publies(request):
    travaux_publies = Travail.objects.filter(statut='Publié')
    context = {
        'travaux_publies': travaux_publies,
    }
    return render(request, 'travaux/enseignants/travaux_facultes_enseignants.html', context)

@login_required
@enseignant_required
def details_travail_faculte_enseignants(request, travail_id):
    travail = get_object_or_404(Travail, id=travail_id)
    directeur = Encadrer.objects.filter(travail=travail, role='Directeur').first()
    rapporteur = Encadrer.objects.filter(travail=travail, role='Rapporteur').first()
    context = {
        'travail': travail,
        'directeur': directeur,
        'rapporteur': rapporteur
    }
    return render(request, 'travaux/enseignants/details_travaux_faculte_enseignants.html', context)

@login_required
@enseignant_required
def details_travail_diriges(request, travail_id):
    travail = get_object_or_404(Travail, id=travail_id)
    directeur = Encadrer.objects.filter(travail=travail, role='Directeur').first()
    rapporteur = Encadrer.objects.filter(travail=travail, role='Rapporteur').first()
    encadrement_rejet = Encadrer.objects.filter(travail=travail, decision=False).first()

    context = {
        'travail': travail,
        'directeur': directeur,
        'rapporteur': rapporteur,
        'motif_rejet': encadrement_rejet.motif if encadrement_rejet else None,
        'enseignant_rejet': encadrement_rejet.enseignant if encadrement_rejet else None,
    }
    return render(request, 'travaux/enseignants/details_travaux_diriges.html', context)


@login_required
@enseignant_required
def approuver_travail(request, travail_id):
    enseignant = request.user.enseignants
    travail = get_object_or_404(Travail, id=travail_id)

    try:
        encadrement = Encadrer.objects.get(travail=travail, enseignant=enseignant)
        encadrement.decision = 1
        encadrement.save()

       
        if travail.typeTravail == 'Projet Ordinaire' and encadrement.role == 'Rapporteur':
            travail.statut = 'Approuvé'
        elif encadrement.role == 'Directeur':
            travail.statut = 'Approuvé'
        else:
            travail.statut = 'En attente'
        travail.save()

        messages.success(request, 'Le travail a été approuvé avec succès.')
    except Encadrer.DoesNotExist:
        messages.error(request, "Erreur : L'enseignant n'est pas assigné à ce travail.")
    
    return redirect('travaux:travaux_diriges')

@login_required
@enseignant_required
def rejeter_travail(request, travail_id):
    travail = get_object_or_404(Travail, id=travail_id)
    enseignant = request.user.enseignants

    if request.method == 'POST':
        motif = request.POST.get('motif')
        encadrement = get_object_or_404(Encadrer, travail=travail, enseignant=enseignant)
        encadrement.decision = False
        encadrement.motif = motif
        encadrement.save()

        travail.statut = 'Rejeté'
        travail.save()

        messages.success(request, 'Le travail a été rejeté avec succès.')
        return redirect('travaux:travaux_diriges')

    context = {
        'travail': travail,
    }
    return render(request, 'travaux/enseignants/rejeter_travail.html', context)


#Bibliothécaire
@login_required
@bibliothecaire_required
def index_bibliothecaires(request):
    travaux_publies_count = Travail.objects.filter(statut='Publié').count()
    travaux_approuves_count = Travail.objects.filter(statut='Approuvé').count()
    travaux_empruntes_count = Emprunter.objects.filter(etat='Emprunté').count()

    current_year = datetime.now().year
    current_month = datetime.now().month

    if current_month < 11:
        academic_year_start = datetime(current_year - 1, 11, 1)
    else:
        academic_year_start = datetime(current_year, 11, 1)

    academic_year_end = datetime(current_year + 1, 8, 31)

    total_paiements = Payer.objects.filter(
        date__range=(academic_year_start, academic_year_end)
    ).aggregate(total=models.Sum('montant'))['total']

    recent_travaux = Travail.objects.filter(statut='Publié').order_by('-anneePublication')[:10]

    context = {
        'travaux_publies_count': travaux_publies_count,
        'travaux_approuves_count': travaux_approuves_count,
        'travaux_empruntes_count': travaux_empruntes_count,
        'total_paiements': total_paiements,
        'recent_travaux': recent_travaux,
    }
    return render(request, 'travaux/bibliothecaires/index_bibliothecaires.html', context)



@login_required
@bibliothecaire_required
def travaux_facultes_bibliothecaires(request):
    travaux_publies = Travail.objects.filter(statut='Publié')
    context = {
        'travaux_publies': travaux_publies,
    }
    return render(request, 'travaux/bibliothecaires/travaux_facultes_bibliothecaires.html', context)

@login_required
@bibliothecaire_required
def emprunter_travail(request, travail_id):
    travail = get_object_or_404(Travail, id=travail_id)
    etudiants = Etudiants.objects.all()

    if travail.emprunte:
        messages.error(request, "Ce travail est déjà emprunté.")
        return redirect('travaux:travaux_facultes_bibliothecaires')

    if request.method == 'POST':
        etudiant_id = request.POST.get('etudiant')
        etudiant = get_object_or_404(Etudiants, id=etudiant_id)
        
        
        travail.emprunte = True
        travail.save()

       
        Emprunter.objects.create(
            etudiant=etudiant,
            travail=travail,
            dateEmprunt=timezone.now().date(),
            etat='Emprunté'
        )

      
        Payer.objects.create(
            etudiant=etudiant,
            travail=travail,
            statutPaiement='Payé',
            date=timezone.now().date(),
            montant=5000
        )

        messages.success(request, 'Le travail a été emprunté et le paiement enregistré avec succès.')
        return redirect('travaux:travaux_facultes_bibliothecaires')

    context = {
        'travail': travail,
        'etudiants': etudiants,
    }
    return render(request, 'travaux/bibliothecaires/emprunter.html', context)

@login_required
@bibliothecaire_required
def details_travail_faculte_bibliothecaires(request, travail_id):
    travail = get_object_or_404(Travail, id=travail_id)
    emprunt = Emprunter.objects.filter(travail=travail, etat="Emprunté").first() 
    directeur = Encadrer.objects.filter(travail=travail, role='Directeur').first()
    rapporteur = Encadrer.objects.filter(travail=travail, role='Rapporteur').first()
    tiroir = travail.tiroir

    context = {
        'travail': travail,
        'emprunt': emprunt,
        'directeur': directeur,
        'rapporteur': rapporteur,
        'tiroir': tiroir,
    }
    return render(request, 'travaux/bibliothecaires/details_travaux_faculte_bibliothecaires.html', context)

@login_required
@bibliothecaire_required
def travaux_attente(request):
    travaux_approuves = Travail.objects.filter(statut='Approuvé')
    context = {
        'travaux_approuves': travaux_approuves
    }
    return render(request, 'travaux/bibliothecaires/travaux_attente.html', context)

@login_required
@bibliothecaire_required
def details_travail_attente(request, travail_id):
    travail = get_object_or_404(Travail, id=travail_id)
    directeur = Encadrer.objects.filter(travail=travail, role='Directeur').first()
    rapporteur = Encadrer.objects.filter(travail=travail, role='Rapporteur').first()

    context = {
        'travail': travail,
        'directeur': directeur,
        'rapporteur': rapporteur,
    }
    return render(request, 'travaux/bibliothecaires/details_travaux_attente.html', context)

@login_required
@bibliothecaire_required
def publier_travail(request, travail_id):
    travail = get_object_or_404(Travail, id=travail_id)
    if request.method == 'POST':
        form = PublierTravailForm(request.POST)
        if form.is_valid():
            tiroir = form.cleaned_data['tiroir']
            imprime = form.cleaned_data['imprime']
            
            travail.statut = 'Publié'
            travail.tiroir = tiroir
            travail.imprime = imprime
            travail.save()
            messages.success(request, 'Le travail a été publié avec succès.')
            return redirect('travaux:travaux_attente')
    else:
        form = PublierTravailForm()
    
    context = {
        'form': form,
        'travail': travail,
    }
    return render(request, 'travaux/bibliothecaires/publier_travail.html', context)


locale.setlocale(locale.LC_TIME, 'fr_FR.UTF-8')

def capitalize_first_letter(text):
    return text.capitalize()

@login_required
@bibliothecaire_required
def publier_travail(request, travail_id):
    travail = get_object_or_404(Travail, pk=travail_id)

    if request.method == 'POST':
        form = PublierTravailForm(request.POST)
        if form.is_valid():
            tiroir = form.cleaned_data['tiroir']
            
            mois_annee_publication = capitalize_first_letter(timezone.now().strftime('%B %Y'))

            travail.anneePublication = mois_annee_publication
            travail.statut = 'Publié'
            travail.tiroir = tiroir
            travail.imprime = True
            travail.save()

            
            messages.success(request, 'Le travail a été publié avec succès.')

            
            return redirect('travaux:travaux_attente')
    else:
        form = PublierTravailForm()

    return render(request, 'travaux/bibliothecaires/publier_travail.html', {
        'form': form,
        'travail': travail,
    })

@login_required
@bibliothecaire_required
def list_tiroirs(request):
    tiroirs = Tiroir.objects.annotate(num_travaux=Count('travaux'))
    return render(request, 'travaux/bibliothecaires/tiroirs.html', {'tiroirs': tiroirs})

@login_required
@bibliothecaire_required
def details_tiroirs(request, tiroir_id):
    tiroir = get_object_or_404(Tiroir, id=tiroir_id)
    travaux = Travail.objects.filter(tiroir=tiroir)
    return render(request, 'travaux/bibliothecaires/details_tiroirs.html', {'tiroir': tiroir, 'travaux': travaux})

@login_required
@bibliothecaire_required
def creer_tiroir(request):
    if request.method == 'POST':
        form = TiroirForm(request.POST)
        if form.is_valid():
            form.save()
            messages.success(request, 'Le tiroir a été créé avec succès.')
            return redirect('travaux:list_tiroirs')
    else:
        form = TiroirForm()
    return render(request, 'travaux/bibliothecaires/creer_tiroir.html', {'form': form})


@login_required
@bibliothecaire_required
def details_travaux_tiroirs(request, travail_id):
    travail = get_object_or_404(Travail, id=travail_id)
    emprunt = Emprunter.objects.filter(travail=travail, etat="Emprunté").first()
    directeur = Encadrer.objects.filter(travail=travail, role='Directeur').first()
    rapporteur = Encadrer.objects.filter(travail=travail, role='Rapporteur').first()
    tiroir = travail.tiroir

    context = {
        'travail': travail,
        'emprunt': emprunt,
        'directeur': directeur,
        'rapporteur': rapporteur,
        'tiroir': tiroir,
    }
    return render(request, 'travaux/bibliothecaires/details_travaux_tiroirs.html', context)

@login_required
@bibliothecaire_required
def changer_tiroir(request, travail_id, tiroir_id):
    travail = get_object_or_404(Travail, id=travail_id)
    tiroir_courant = get_object_or_404(Tiroir, id=tiroir_id)
    if request.method == 'POST':
        form = ChangerTiroirForm(request.POST, instance=travail)
        if form.is_valid():
            form.save()
            messages.success(request, 'Tiroir changé avec succès.')
            return redirect('travaux:details_tiroirs', tiroir_id=tiroir_courant.id)
    else:
        form = ChangerTiroirForm(instance=travail)

    context = {
        'travail': travail,
        'form': form,
        'tiroir_courant': tiroir_courant,
    }
    return render(request, 'travaux/bibliothecaires/changer_tiroir.html', context)

@login_required
@bibliothecaire_required
def liste_empruntes(request):
    emprunts = Emprunter.objects.filter(etat='Emprunté')
    context = {
        'emprunts': emprunts,
    }
    return render(request, 'travaux/bibliothecaires/liste_empruntes.html', context)


@login_required
@bibliothecaire_required
def restituer_travail(request, emprunt_id):
    emprunt = get_object_or_404(Emprunter, id=emprunt_id)
    emprunt.etat = 'Restitué'
    emprunt.save()

    travail = emprunt.travail
    travail.emprunte = 0
    travail.save()

    messages.success(request, 'Travail restitué avec succès.')
    return redirect('travaux:liste_empruntes')


@login_required
@bibliothecaire_required
def details_travaux_empruntes(request, travail_id):
    travail = get_object_or_404(Travail, id=travail_id)
    emprunt = Emprunter.objects.filter(travail=travail, etat="Emprunté").first()
    directeur = Encadrer.objects.filter(travail=travail, role='Directeur').first()
    rapporteur = Encadrer.objects.filter(travail=travail, role='Rapporteur').first()
    tiroir = travail.tiroir

    context = {
        'travail': travail,
        'emprunt': emprunt,
        'directeur': directeur,
        'rapporteur': rapporteur,
        'tiroir': tiroir,
    }
    return render(request, 'travaux/bibliothecaires/details_travaux_empruntes.html', context)

@login_required
@bibliothecaire_required
def liste_paiements(request):
    paiements = Payer.objects.all()
    return render(request, 'travaux/bibliothecaires/paiements.html', {'paiements': paiements})


@login_required
@bibliothecaire_required
def details_paiement(request, paiement_id):
    paiement = get_object_or_404(Payer, id=paiement_id)
    
    
    directeur = Encadrer.objects.filter(travail=paiement.travail, role='Directeur').first()
    rapporteur = Encadrer.objects.filter(travail=paiement.travail, role='Rapporteur').first()

    context = {
        'paiement': paiement,
        'directeur': directeur,
        'rapporteur': rapporteur,
    }
    
    return render(request, 'travaux/bibliothecaires/details_paiement.html', context)







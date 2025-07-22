from django.shortcuts import render
from functools import wraps

def etudiant_required(view_func):
    @wraps(view_func)
    def _wrapped_view(request, *args, **kwargs):
        if request.user.is_authenticated and request.user.role == 'Etudiant':
            return view_func(request, *args, **kwargs)
        else:
            return render(request, 'users/403.html', status=403)
    return _wrapped_view

def enseignant_required(view_func):
    @wraps(view_func)
    def _wrapped_view(request, *args, **kwargs):
        if request.user.is_authenticated and request.user.role == 'Enseignant':
            return view_func(request, *args, **kwargs)
        else:
            return render(request, 'users/403.html', status=403)
    return _wrapped_view

def bibliothecaire_required(view_func):
    @wraps(view_func)
    def _wrapped_view(request, *args, **kwargs):
        if request.user.is_authenticated and request.user.role == 'Bibliothecaire':
            return view_func(request, *args, **kwargs)
        else:
            return render(request, 'users/403.html', status=403)
    return _wrapped_view


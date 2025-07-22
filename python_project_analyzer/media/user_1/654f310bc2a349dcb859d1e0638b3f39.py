import hashlib
from django.http import HttpResponse
from django.views.decorators.csrf import csrf_exempt
from django.db import connection

# Variable sensible exposée
SECRET_KEY = "hardcoded_secret"
api_key = "1234567890abcdef"
password = "supersecret"

class Base:
    pass

class A(Base):
    pass

class B(A):
    pass

class C(B):
    pass

class D(C):
    pass

class E(D):
    pass

class UserManager:
    def get_user(self, username, password):
        # Injection SQL potentielle
        query = f"SELECT * FROM users WHERE username='{username}' AND password='{password}'"
        with connection.cursor() as cursor:
            cursor.execute(query)
            return cursor.fetchone()

def long_function(a, b, c, d, e, f, g, h, i, j):
    # Fonction trop longue et complexe
    if a > 0:
        if b > 0:
            if c > 0:
                if d > 0:
                    if e > 0:
                        if f > 0:
                            if g > 0:
                                if h > 0:
                                    if i > 0:
                                        if j > 0:
                                            print("Très complexe")
    for x in range(100):
        for y in range(100):
            for z in range(100):
                print(x, y, z)
    return a + b + c + d + e + f + g + h + i + j

def encrypt_data(data):
    # Utilisation de chiffrement faible
    return hashlib.md5(data.encode()).hexdigest()

@csrf_exempt  # Pas de protection CSRF
def unsafe_view(request):
    # XSS potentiel
    name = request.GET.get("name")
    return HttpResponse("Bonjour " + name)

def no_auth_check(request):
    # Pas de contrôle d'autorisation
    return HttpResponse("Données sensibles: " + str(request.user.email))

def endpoint_no_validation(request):
    # Endpoint sans validation d'entrée
    param = request.GET.get("param")
    return HttpResponse(param)

def duplicate_code():
    # Code dupliqué
    print("duplicate")
    print("duplicate")
    print("duplicate")

def function_with_many_params(a, b, c, d, e, f, g, h, i, j, k, l):
    return a + b + c + d + e + f + g + h + i + j + k + l

# Mauvaise gestion des dépendances (exemple fictif)
import requests  # Supposons que cette version est vulnérable

# Décorateur inutile
def useless_decorator(func):
    def wrapper(*args, **kwargs):
        return func(*args, **kwargs)
    return wrapper

@useless_decorator
def decorated_func():
    pass

# Endpoint HTTP sans validation
def http_endpoint(request):
    return HttpResponse(request.GET.get("input"))

# Mauvaise annotation de type
def bad_types(a, b) -> int:
    return str(a) + str(b)

# Utilisation d'une clé API dans le code
def call_api():
    key = "api_key_123"
    return key

# Pas de docstring, pas de commentaires, style non PEP8

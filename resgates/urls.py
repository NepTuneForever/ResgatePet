from django.contrib.auth import views as auth_views
from django.urls import path
from .views import CreatePetView, ViewAnimais, LoginView, RegisterView, LogoutView, DetalheAnimalView
from rest_framework.authtoken.views import obtain_auth_token

urlpatterns = [
    path('animais/', ViewAnimais.as_view(), name='animais'),
    path('cadastrar/', CreatePetView.as_view(), name='cadastrar-animal'),
    path("login/", LoginView.as_view(), name="login"),
    path("register/", RegisterView.as_view(), name="register"),
    path("logout/", LogoutView.as_view(), name="logout"),
    path('animal/<int:pk>/', DetalheAnimalView.as_view(), name='detalhe-animal'),
]
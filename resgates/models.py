from django.db import models
from django.contrib.auth.models import User

class Profile(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE)
    empresa = models.BooleanField(default=False)

class Animal(models.Model):
    nome = models.CharField(max_length=20)
    tipo = models.CharField(max_length=10)
    idade = models.IntegerField()
    caracteristicas = models.CharField(max_length=100)
    localizacao = models.CharField(max_length=30)
    contato = models.CharField(max_length=20)
    foto = models.CharField(max_length=250)

    def __str__(self):
        return self.nome

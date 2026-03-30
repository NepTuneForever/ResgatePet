from django.contrib import admin

from .models import AlertaResgate, Animal, Favorito, Profile, SolicitacaoAdocao


@admin.register(Profile)
class ProfileAdmin(admin.ModelAdmin):
    list_display = ("user", "empresa", "nome_completo", "telefone")
    search_fields = ("user__username", "nome_completo", "telefone")
    list_filter = ("empresa",)


@admin.register(Animal)
class AnimalAdmin(admin.ModelAdmin):
    list_display = ("nome", "tipo", "status", "porte", "localizacao", "abrigo", "destaque")
    search_fields = ("nome", "localizacao", "caracteristicas")
    list_filter = ("tipo", "status", "porte", "sexo", "destaque")


@admin.register(SolicitacaoAdocao)
class SolicitacaoAdocaoAdmin(admin.ModelAdmin):
    list_display = ("animal", "nome_contato", "status", "criado_em")
    search_fields = ("animal__nome", "nome_contato", "email_contato")
    list_filter = ("status",)


@admin.register(Favorito)
class FavoritoAdmin(admin.ModelAdmin):
    list_display = ("adotante", "animal", "criado_em")
    search_fields = ("adotante__username", "animal__nome")


@admin.register(AlertaResgate)
class AlertaResgateAdmin(admin.ModelAdmin):
    list_display = ("titulo", "localizacao", "status", "criado_por", "criado_em")
    search_fields = ("titulo", "localizacao", "descricao")
    list_filter = ("status",)

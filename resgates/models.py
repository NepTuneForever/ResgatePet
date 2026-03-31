from django.contrib.auth.models import User
from django.core.validators import MaxValueValidator
from django.db import models
from django.urls import reverse
from django.utils import timezone


class Profile(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name="profile")
    empresa = models.BooleanField(default=False)
    nome_completo = models.CharField(max_length=100, blank=True)
    endereco = models.CharField(max_length=200, blank=True)
    cep = models.CharField(max_length=10, blank=True)
    responsavel = models.CharField(max_length=100, blank=True)
    telefone = models.CharField(max_length=20, blank=True)

    class Meta:
        ordering = ["user__username"]

    def __str__(self):
        return self.nome_exibicao

    @property
    def nome_exibicao(self):
        if self.empresa and self.nome_completo:
            return self.nome_completo
        if not self.empresa and self.nome_completo:
            return self.nome_completo
        return self.user.username


class Animal(models.Model):
    TIPO_CHOICES = [
        ("Cachorro", "Cachorro"),
        ("Gato", "Gato"),
        ("Outro", "Outro"),
    ]
    SEXO_CHOICES = [
        ("Macho", "Macho"),
        ("Fêmea", "Fêmea"),
    ]
    PORTE_CHOICES = [
        ("Pequeno", "Pequeno"),
        ("Médio", "Médio"),
        ("Grande", "Grande"),
    ]
    STATUS_CHOICES = [
        ("disponivel", "Disponível"),
        ("em_analise", "Em análise"),
        ("adotado", "Adotado"),
    ]

    nome = models.CharField(max_length=50)
    tipo = models.CharField(max_length=20, choices=TIPO_CHOICES)
    idade = models.PositiveIntegerField(validators=[MaxValueValidator(40)])
    sexo = models.CharField(max_length=10, choices=SEXO_CHOICES, default="Macho")
    porte = models.CharField(max_length=10, choices=PORTE_CHOICES, default="Médio")
    pelagem = models.CharField(max_length=50, blank=True)
    data_resgate = models.DateField(null=True, blank=True)
    v8_v10 = models.BooleanField(default=False)
    antirrabica = models.BooleanField(default=False)
    giardia = models.BooleanField(default=False)
    leucemia = models.BooleanField(default=False)
    castrado = models.BooleanField(default=False)
    vermifugado = models.BooleanField(default=False)
    status_saude = models.TextField(blank=True)
    caracteristicas = models.TextField()
    localizacao = models.CharField(max_length=100)
    contato = models.CharField(max_length=20)
    foto = models.URLField(max_length=500, blank=True, default="")
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default="disponivel")
    destaque = models.BooleanField(default=False)
    criado_em = models.DateTimeField(auto_now_add=True, null=True)
    atualizado_em = models.DateTimeField(auto_now=True)
    abrigo = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name="animais_cadastrados",
        null=True,
        blank=True,
    )

    class Meta:
        ordering = ["-destaque", "-criado_em", "nome"]

    def __str__(self):
        return self.nome

    @property
    def disponivel_para_adocao(self):
        return self.status == "disponivel"

    @property
    def nome_abrigo(self):
        if not self.abrigo_id:
            return "Abrigo não informado"
        profile = getattr(self.abrigo, "profile", None)
        if profile and profile.nome_exibicao:
            return profile.nome_exibicao
        return self.abrigo.username

    @property
    def foto_principal(self):
        if not self.pk:
            return None
        imagens = getattr(self, "_prefetched_objects_cache", {}).get("imagens")
        if imagens is not None:
            principal = next((imagem for imagem in imagens if imagem.principal), None)
            return principal or (imagens[0] if imagens else None)
        principal = self.imagens.filter(principal=True).first()
        return principal or self.imagens.first()

    @property
    def foto_url(self):
        foto_principal = self.foto_principal
        if foto_principal and foto_principal.url:
            return foto_principal.url
        return self.foto

    @property
    def fotos_extras(self):
        if not self.pk:
            return []
        imagens = getattr(self, "_prefetched_objects_cache", {}).get("imagens")
        if imagens is not None:
            return [imagem for imagem in imagens if not imagem.principal]
        return self.imagens.filter(principal=False)


class AnimalImagem(models.Model):
    animal = models.ForeignKey(Animal, on_delete=models.CASCADE, related_name="imagens")
    imagem = models.ImageField(upload_to="animais/", blank=True)
    imagem_arquivo = models.BinaryField(blank=True, null=True)
    imagem_content_type = models.CharField(max_length=100, blank=True, default="")
    imagem_nome = models.CharField(max_length=255, blank=True, default="")
    principal = models.BooleanField(default=False)
    ordem = models.PositiveIntegerField(default=0)
    criado_em = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-principal", "ordem", "id"]

    def __str__(self):
        return f"Imagem de {self.animal.nome}"

    @property
    def url(self):
        if self.imagem_arquivo:
            return reverse("animal-imagem", args=[self.pk])
        if self.imagem:
            return self.imagem.url
        return ""


class Favorito(models.Model):
    adotante = models.ForeignKey(User, on_delete=models.CASCADE, related_name="favoritos")
    animal = models.ForeignKey(Animal, on_delete=models.CASCADE, related_name="favoritado_por")
    criado_em = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-criado_em"]
        constraints = [
            models.UniqueConstraint(fields=["adotante", "animal"], name="favorito_unico_por_usuario")
        ]

    def __str__(self):
        return f"{self.adotante.username} favoritou {self.animal.nome}"


class SolicitacaoAdocao(models.Model):
    STATUS_CHOICES = [
        ("novo", "Novo"),
        ("em_analise", "Em análise"),
        ("aprovado", "Aprovado"),
        ("recusado", "Recusado"),
    ]

    animal = models.ForeignKey(Animal, on_delete=models.CASCADE, related_name="solicitacoes")
    adotante = models.ForeignKey(User, on_delete=models.CASCADE, related_name="solicitacoes_adocao")
    nome_contato = models.CharField(max_length=120)
    email_contato = models.EmailField()
    telefone_contato = models.CharField(max_length=20)
    mensagem = models.TextField(blank=True)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default="novo")
    criado_em = models.DateTimeField(auto_now_add=True)
    atualizado_em = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-criado_em"]
        constraints = [
            models.UniqueConstraint(
                fields=["animal", "adotante"],
                name="uma_solicitacao_por_animal_e_adotante",
            )
        ]

    def __str__(self):
        return f"{self.nome_contato} -> {self.animal.nome}"

    def save(self, *args, **kwargs):
        super().save(*args, **kwargs)
        if self.status == "aprovado" and self.animal.status != "adotado":
            self.animal.status = "adotado"
            self.animal.save(update_fields=["status", "atualizado_em"])
        elif self.status == "em_analise" and self.animal.status == "disponivel":
            self.animal.status = "em_analise"
            self.animal.save(update_fields=["status", "atualizado_em"])


class AlertaResgate(models.Model):
    STATUS_CHOICES = [
        ("aberto", "Aberto"),
        ("em_atendimento", "Em atendimento"),
        ("concluido", "Concluído"),
    ]

    titulo = models.CharField(max_length=120)
    descricao = models.TextField()
    localizacao = models.CharField(max_length=120)
    contato = models.CharField(max_length=20)
    criado_por = models.ForeignKey(User, on_delete=models.CASCADE, related_name="alertas_criados")
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default="aberto")
    criado_em = models.DateTimeField(default=timezone.now)

    class Meta:
        ordering = ["status", "-criado_em"]

    def __str__(self):
        return self.titulo

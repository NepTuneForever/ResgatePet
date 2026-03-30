from django.contrib import messages
from django.contrib.auth import login, logout
from django.contrib.auth.mixins import LoginRequiredMixin, UserPassesTestMixin
from django.db import IntegrityError
from django.db.models import Count, Prefetch, Q
from django.http import HttpResponseRedirect
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse, reverse_lazy
from django.views.generic import CreateView, DetailView, ListView, TemplateView, UpdateView, View
from rest_framework import generics, permissions

from .forms import AnimalFilterForm, AnimalForm, LoginForm, RegisterForm, SolicitacaoAdocaoForm
from .models import Animal, Favorito, Profile, SolicitacaoAdocao
from .serializers import AnimalSerializer, SolicitacaoAdocaoSerializer


def ensure_profile(user):
    profile, _ = Profile.objects.get_or_create(user=user)
    return profile


def apply_animal_filters(queryset, params):
    q = params.get("q", "").strip()
    tipo = params.get("tipo", "").strip()
    porte = params.get("porte", "").strip()
    sexo = params.get("sexo", "").strip()
    status = params.get("status", "").strip()
    localizacao = params.get("localizacao", "").strip()

    if q:
        queryset = queryset.filter(
            Q(nome__icontains=q)
            | Q(caracteristicas__icontains=q)
            | Q(localizacao__icontains=q)
            | Q(pelagem__icontains=q)
        )
    if tipo:
        queryset = queryset.filter(tipo=tipo)
    if porte:
        queryset = queryset.filter(porte=porte)
    if sexo:
        queryset = queryset.filter(sexo=sexo)
    if status:
        queryset = queryset.filter(status=status)
    if localizacao:
        queryset = queryset.filter(localizacao__icontains=localizacao)

    return queryset


class HomeRedirectView(View):
    def get(self, request):
        return redirect("animais")


class LogoutView(View):
    def post(self, request):
        logout(request)
        return redirect("login")


class RegisterView(View):
    template_name = "register.html"

    def get(self, request):
        if request.user.is_authenticated:
            return redirect("painel")
        return render(request, self.template_name, {"form": RegisterForm()})

    def post(self, request):
        if request.user.is_authenticated:
            return redirect("painel")

        form = RegisterForm(request.POST)
        if not form.is_valid():
            return render(request, self.template_name, {"form": form})

        user = form.save()
        login(request, user)
        messages.success(request, "Conta criada com sucesso.")
        return redirect("painel")


class LoginView(View):
    template_name = "login.html"

    def get(self, request):
        if request.user.is_authenticated:
            return redirect("painel")
        return render(request, self.template_name, {"form": LoginForm()})

    def post(self, request):
        if request.user.is_authenticated:
            return redirect("painel")

        form = LoginForm(request, request.POST)
        if not form.is_valid():
            return render(request, self.template_name, {"form": form})

        login(request, form.get_user())
        return redirect("painel")


class PasswordRecoveryView(View):
    template_name = "recuperar.html"

    def get(self, request):
        return render(request, self.template_name)


class EmpresaRequiredMixin(LoginRequiredMixin, UserPassesTestMixin):
    def test_func(self):
        return ensure_profile(self.request.user).empresa

    def handle_no_permission(self):
        messages.error(self.request, "Esta área é exclusiva para abrigos.")
        return redirect("painel")


class AdotanteRequiredMixin(LoginRequiredMixin, UserPassesTestMixin):
    def test_func(self):
        return not ensure_profile(self.request.user).empresa

    def handle_no_permission(self):
        messages.error(self.request, "Esta ação é exclusiva para adotantes.")
        return redirect("painel")


class ViewAnimais(ListView):
    model = Animal
    template_name = "animais.html"
    context_object_name = "animais"

    def get_queryset(self):
        queryset = (
            Animal.objects.select_related("abrigo", "abrigo__profile")
            .prefetch_related("solicitacoes", "imagens")
            .annotate(total_solicitacoes=Count("solicitacoes"))
        )
        return apply_animal_filters(queryset, self.request.GET)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["filter_form"] = AnimalFilterForm(self.request.GET or None)
        context["tipos"] = Animal.TIPO_CHOICES
        context["destaques"] = Animal.objects.filter(destaque=True).prefetch_related("imagens")[:3]
        context["total_animais"] = self.object_list.count()

        favoritos_ids = []
        if self.request.user.is_authenticated:
            ensure_profile(self.request.user)
            favoritos_ids = list(
                Favorito.objects.filter(adotante=self.request.user).values_list("animal_id", flat=True)
            )
        context["favoritos_ids"] = favoritos_ids
        return context


class DetalheAnimalView(DetailView):
    model = Animal
    template_name = "detalhe.html"
    context_object_name = "animal"

    def get_queryset(self):
        return Animal.objects.select_related("abrigo", "abrigo__profile").prefetch_related("imagens")

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        user = self.request.user
        context["interesse_existente"] = None
        context["is_favorito"] = False
        context["can_show_interest_form"] = False
        context["interest_form"] = None

        if user.is_authenticated:
            profile = ensure_profile(user)
            context["is_favorito"] = Favorito.objects.filter(adotante=user, animal=self.object).exists()
            if not profile.empresa:
                context["interesse_existente"] = SolicitacaoAdocao.objects.filter(
                    animal=self.object,
                    adotante=user,
                ).first()
                if self.object.disponivel_para_adocao and context["interesse_existente"] is None:
                    context["can_show_interest_form"] = True
                    context["interest_form"] = SolicitacaoAdocaoForm(user=user, animal=self.object)
        context["galeria_imagens"] = list(self.object.imagens.all())
        return context


class CreatePetView(EmpresaRequiredMixin, CreateView):
    model = Animal
    form_class = AnimalForm
    template_name = "criar.html"
    success_url = reverse_lazy("painel-abrigo")

    def form_valid(self, form):
        form.instance.abrigo = self.request.user
        messages.success(self.request, "Animal cadastrado com sucesso.")
        return super().form_valid(form)


class UpdatePetView(EmpresaRequiredMixin, UpdateView):
    model = Animal
    form_class = AnimalForm
    template_name = "criar.html"
    success_url = reverse_lazy("painel-abrigo")

    def get_queryset(self):
        return Animal.objects.filter(abrigo=self.request.user)

    def form_valid(self, form):
        messages.success(self.request, "Cadastro do animal atualizado.")
        return super().form_valid(form)


class DashboardRedirectView(LoginRequiredMixin, View):
    def get(self, request):
        profile = ensure_profile(request.user)
        if profile.empresa:
            return redirect("painel-abrigo")
        return redirect("painel-adotante")


class AbrigoDashboardView(EmpresaRequiredMixin, TemplateView):
    template_name = "painel_abrigo.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        animais = Animal.objects.filter(abrigo=self.request.user).prefetch_related(
            "imagens",
            Prefetch(
                "solicitacoes",
                queryset=SolicitacaoAdocao.objects.select_related("adotante").order_by("-criado_em"),
            )
        )
        solicitacoes = SolicitacaoAdocao.objects.filter(animal__abrigo=self.request.user).select_related(
            "animal",
            "adotante",
        )
        context["animais"] = animais
        context["solicitacoes"] = solicitacoes
        context["stats"] = {
            "animais": animais.count(),
            "disponiveis": animais.filter(status="disponivel").count(),
            "em_analise": animais.filter(status="em_analise").count(),
            "adotados": animais.filter(status="adotado").count(),
            "solicitacoes": solicitacoes.count(),
        }
        return context


class AdotanteDashboardView(AdotanteRequiredMixin, TemplateView):
    template_name = "painel_adotante.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        favoritos = Favorito.objects.filter(adotante=self.request.user).select_related("animal").prefetch_related("animal__imagens")
        solicitacoes = SolicitacaoAdocao.objects.filter(adotante=self.request.user).select_related("animal").prefetch_related("animal__imagens")
        recomendados = Animal.objects.filter(status="disponivel").prefetch_related("imagens").exclude(
            id__in=favoritos.values_list("animal_id", flat=True)
        )[:4]
        context["favoritos"] = favoritos
        context["solicitacoes"] = solicitacoes
        context["recomendados"] = recomendados
        return context


class FavoriteToggleView(AdotanteRequiredMixin, View):
    def post(self, request, pk):
        animal = get_object_or_404(Animal, pk=pk)
        favorito, created = Favorito.objects.get_or_create(adotante=request.user, animal=animal)
        if created:
            messages.success(request, f"{animal.nome} foi adicionado aos favoritos.")
        else:
            favorito.delete()
            messages.info(request, f"{animal.nome} foi removido dos favoritos.")
        return HttpResponseRedirect(request.POST.get("next") or reverse("detalhe-animal", args=[animal.pk]))


class SolicitarAdocaoView(AdotanteRequiredMixin, View):
    def post(self, request, pk):
        animal = get_object_or_404(Animal, pk=pk)
        form = SolicitacaoAdocaoForm(request.POST, user=request.user, animal=animal)

        if not animal.disponivel_para_adocao:
            messages.error(request, "Este animal não está disponível para novas solicitações.")
            return redirect("detalhe-animal", pk=pk)

        if form.is_valid():
            try:
                form.save()
            except IntegrityError:
                messages.error(request, "Você já enviou interesse para este animal.")
            else:
                animal.status = "em_analise"
                animal.save(update_fields=["status", "atualizado_em"])
                messages.success(request, "Seu interesse foi enviado ao abrigo.")
            return redirect("detalhe-animal", pk=pk)

        return render(
            request,
            "detalhe.html",
            {
                "animal": animal,
                "interest_form": form,
                "can_show_interest_form": True,
                "is_favorito": Favorito.objects.filter(adotante=request.user, animal=animal).exists(),
                "interesse_existente": None,
            },
        )


class AtualizarSolicitacaoView(EmpresaRequiredMixin, View):
    def post(self, request, pk):
        solicitacao = get_object_or_404(
            SolicitacaoAdocao.objects.select_related("animal"),
            pk=pk,
            animal__abrigo=request.user,
        )
        novo_status = request.POST.get("status")
        valid_status = {choice[0] for choice in SolicitacaoAdocao.STATUS_CHOICES}
        if novo_status not in valid_status:
            messages.error(request, "Status inválido.")
            return redirect("painel-abrigo")

        solicitacao.status = novo_status
        solicitacao.save()

        if novo_status == "recusado":
            animal = solicitacao.animal
            if not animal.solicitacoes.exclude(status="recusado").exists():
                animal.status = "disponivel"
                animal.save(update_fields=["status", "atualizado_em"])

        messages.success(request, "Solicitação atualizada.")
        return redirect("painel-abrigo")


class AnimalListAPIView(generics.ListAPIView):
    serializer_class = AnimalSerializer
    permission_classes = [permissions.AllowAny]

    def get_queryset(self):
        queryset = Animal.objects.select_related("abrigo", "abrigo__profile").prefetch_related("imagens")
        return apply_animal_filters(queryset, self.request.query_params)


class AnimalDetailAPIView(generics.RetrieveAPIView):
    queryset = Animal.objects.select_related("abrigo", "abrigo__profile").prefetch_related("imagens")
    serializer_class = AnimalSerializer
    permission_classes = [permissions.AllowAny]


class SolicitationListAPIView(generics.ListAPIView):
    serializer_class = SolicitacaoAdocaoSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        profile = ensure_profile(self.request.user)
        queryset = SolicitacaoAdocao.objects.select_related("animal", "adotante")
        if profile.empresa:
            return queryset.filter(animal__abrigo=self.request.user)
        return queryset.filter(adotante=self.request.user)

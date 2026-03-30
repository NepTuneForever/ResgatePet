from django import forms
from django.contrib.auth import authenticate
from django.contrib.auth.models import User

from .models import Animal, Profile, SolicitacaoAdocao


class RegisterForm(forms.Form):
    username = forms.CharField(max_length=150, label="Usuário")
    email = forms.EmailField(label="E-mail")
    password1 = forms.CharField(widget=forms.PasswordInput, label="Senha")
    password2 = forms.CharField(widget=forms.PasswordInput, label="Confirmar senha")
    empresa = forms.BooleanField(required=False, label="Conta de abrigo")
    nome_completo = forms.CharField(max_length=100, label="Nome ou nome do abrigo")
    endereco = forms.CharField(max_length=200, required=False)
    cep = forms.CharField(max_length=10, required=False)
    responsavel = forms.CharField(max_length=100, required=False)
    telefone = forms.CharField(max_length=20, required=False)

    def clean_username(self):
        username = self.cleaned_data["username"].strip()
        if User.objects.filter(username=username).exists():
            raise forms.ValidationError("Usuário já existe.")
        return username

    def clean(self):
        cleaned_data = super().clean()
        password1 = cleaned_data.get("password1")
        password2 = cleaned_data.get("password2")
        empresa = cleaned_data.get("empresa")

        if password1 and password2 and password1 != password2:
            self.add_error("password2", "As senhas não conferem.")

        if empresa:
            if not cleaned_data.get("responsavel"):
                self.add_error("responsavel", "Informe o responsável pelo abrigo.")
            if not cleaned_data.get("endereco"):
                self.add_error("endereco", "Informe o endereço do abrigo.")

        return cleaned_data

    def save(self):
        data = self.cleaned_data
        user = User.objects.create_user(
            username=data["username"],
            email=data["email"],
            password=data["password1"],
        )
        Profile.objects.update_or_create(
            user=user,
            defaults={
                "empresa": data["empresa"],
                "nome_completo": data["nome_completo"],
                "endereco": data["endereco"],
                "cep": data["cep"],
                "responsavel": data["responsavel"],
                "telefone": data["telefone"],
            },
        )
        return user


class LoginForm(forms.Form):
    username = forms.CharField(max_length=150, label="Usuário")
    password = forms.CharField(widget=forms.PasswordInput, label="Senha")

    def __init__(self, request=None, *args, **kwargs):
        self.request = request
        self.user = None
        super().__init__(*args, **kwargs)

    def clean(self):
        cleaned_data = super().clean()
        username = cleaned_data.get("username")
        password = cleaned_data.get("password")

        if username and password:
            self.user = authenticate(self.request, username=username, password=password)
            if self.user is None:
                raise forms.ValidationError("Credenciais inválidas.")

        return cleaned_data

    def get_user(self):
        return self.user


class AnimalForm(forms.ModelForm):
    class Meta:
        model = Animal
        fields = [
            "nome",
            "tipo",
            "idade",
            "sexo",
            "porte",
            "pelagem",
            "data_resgate",
            "v8_v10",
            "antirrabica",
            "giardia",
            "leucemia",
            "castrado",
            "vermifugado",
            "status_saude",
            "caracteristicas",
            "localizacao",
            "contato",
            "foto",
            "status",
            "destaque",
        ]
        widgets = {
            "data_resgate": forms.DateInput(attrs={"type": "date"}),
            "status_saude": forms.Textarea(attrs={"rows": 3}),
            "caracteristicas": forms.Textarea(attrs={"rows": 4}),
        }

    def clean_idade(self):
        idade = self.cleaned_data["idade"]
        if idade < 0:
            raise forms.ValidationError("Idade não pode ser negativa.")
        return idade


class AnimalFilterForm(forms.Form):
    q = forms.CharField(required=False, label="Busca")
    tipo = forms.ChoiceField(
        required=False,
        choices=[("", "Todos os tipos"), *Animal.TIPO_CHOICES],
    )
    porte = forms.ChoiceField(
        required=False,
        choices=[("", "Qualquer porte"), *Animal.PORTE_CHOICES],
    )
    sexo = forms.ChoiceField(
        required=False,
        choices=[("", "Qualquer sexo"), *Animal.SEXO_CHOICES],
    )
    status = forms.ChoiceField(
        required=False,
        choices=[("", "Todos os status"), *Animal.STATUS_CHOICES],
    )
    localizacao = forms.CharField(required=False)


class SolicitacaoAdocaoForm(forms.ModelForm):
    class Meta:
        model = SolicitacaoAdocao
        fields = ["nome_contato", "email_contato", "telefone_contato", "mensagem"]
        widgets = {"mensagem": forms.Textarea(attrs={"rows": 4})}

    def __init__(self, *args, **kwargs):
        self.user = kwargs.pop("user", None)
        self.animal = kwargs.pop("animal", None)
        super().__init__(*args, **kwargs)

        if self.user and hasattr(self.user, "profile"):
            profile = self.user.profile
            self.fields["nome_contato"].initial = profile.nome_exibicao
            self.fields["email_contato"].initial = self.user.email
            self.fields["telefone_contato"].initial = profile.telefone

    def clean(self):
        cleaned_data = super().clean()
        if self.user and self.animal and self.animal.abrigo_id == self.user.id:
            raise forms.ValidationError("O abrigo responsável não pode solicitar adoção do próprio animal.")
        return cleaned_data

    def save(self, commit=True):
        instance = super().save(commit=False)
        instance.adotante = self.user
        instance.animal = self.animal
        if commit:
            instance.save()
        return instance

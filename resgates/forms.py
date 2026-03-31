from django import forms
from django.contrib.auth import authenticate
from django.contrib.auth.models import User
from django.db import transaction
from PIL import Image, UnidentifiedImageError

from .models import Animal, AnimalImagem, Profile, SolicitacaoAdocao


class MultipleFileInput(forms.ClearableFileInput):
    allow_multiple_selected = True


class MultipleFileField(forms.FileField):
    widget = MultipleFileInput

    def clean(self, data, initial=None):
        single_file_clean = super().clean
        if not data:
            return []
        if isinstance(data, (list, tuple)):
            return [single_file_clean(file, initial) for file in data]
        return [single_file_clean(data, initial)]


class RegisterForm(forms.Form):
    ACCOUNT_TYPE_CHOICES = [
        ("pessoa", "Quero adotar"),
        ("empresa", "Sou empresa"),
    ]

    account_type = forms.ChoiceField(
        label="Tipo de conta",
        choices=ACCOUNT_TYPE_CHOICES,
        initial="pessoa",
        widget=forms.RadioSelect,
    )
    username = forms.CharField(max_length=150, label="Usuário")
    email = forms.EmailField(label="E-mail")
    password1 = forms.CharField(widget=forms.PasswordInput, label="Senha")
    password2 = forms.CharField(widget=forms.PasswordInput, label="Confirmar senha")
    nome_completo = forms.CharField(max_length=100, label="Nome ou nome do abrigo")
    endereco = forms.CharField(max_length=200, required=False)
    cep = forms.CharField(max_length=10, required=False)
    responsavel = forms.CharField(max_length=100, required=False)
    telefone = forms.CharField(max_length=20, required=False)

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["nome_completo"].widget.attrs.update({"placeholder": "Seu nome completo"})
        self.fields["telefone"].widget.attrs.update({"placeholder": "(11) 99999-9999"})
        self.fields["endereco"].widget.attrs.update({"placeholder": "Rua, número e bairro"})
        self.fields["cep"].widget.attrs.update({"placeholder": "00000-000"})
        self.fields["responsavel"].widget.attrs.update({"placeholder": "Nome do responsável"})

    def clean_username(self):
        username = self.cleaned_data["username"].strip()
        if User.objects.filter(username=username).exists():
            raise forms.ValidationError("Usuário já existe.")
        return username

    def clean(self):
        cleaned_data = super().clean()
        password1 = cleaned_data.get("password1")
        password2 = cleaned_data.get("password2")
        account_type = cleaned_data.get("account_type") or "pessoa"
        empresa = account_type == "empresa"
        cleaned_data["empresa"] = empresa

        if password1 and password2 and password1 != password2:
            self.add_error("password2", "As senhas não conferem.")

        if empresa:
            if not cleaned_data.get("nome_completo"):
                self.add_error("nome_completo", "Informe o nome da empresa ou abrigo.")
            if not cleaned_data.get("responsavel"):
                self.add_error("responsavel", "Informe o responsável pelo abrigo.")
            if not cleaned_data.get("endereco"):
                self.add_error("endereco", "Informe o endereço do abrigo.")
            if not cleaned_data.get("cep"):
                self.add_error("cep", "Informe o CEP do abrigo.")

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
    foto_principal_upload = forms.ImageField(
        required=False,
        label="Foto principal",
        widget=forms.ClearableFileInput(attrs={"accept": "image/*"}),
    )
    fotos_extras = MultipleFileField(
        required=False,
        label="Mais fotos",
        widget=MultipleFileInput(attrs={"accept": "image/*"}),
    )

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

    def clean(self):
        cleaned_data = super().clean()
        foto_principal = cleaned_data.get("foto_principal_upload")
        fotos_extras = self._get_uploaded_files("fotos_extras")

        if foto_principal:
            self._validate_image_file(foto_principal, "foto_principal_upload")

        for foto_extra in fotos_extras:
            self._validate_image_file(foto_extra, "fotos_extras")

        possui_imagem_existente = bool(getattr(self.instance, "foto_url", ""))
        if not foto_principal and not fotos_extras and not possui_imagem_existente:
            raise forms.ValidationError("Envie ao menos uma imagem do animal.")

        self.cleaned_data["fotos_extras"] = fotos_extras
        return cleaned_data

    def save(self, commit=True):
        animal = super().save(commit=False)
        if not animal.foto:
            animal.foto = ""

        if commit:
            with transaction.atomic():
                animal.save()
                self._save_uploaded_images(animal)

        return animal

    def _save_uploaded_images(self, animal):
        foto_principal = self.cleaned_data.get("foto_principal_upload")
        fotos_extras = list(self.cleaned_data.get("fotos_extras", []))

        if foto_principal is None and fotos_extras and not animal.imagens.filter(principal=True).exists():
            foto_principal = fotos_extras.pop(0)

        if foto_principal is not None:
            self._delete_existing_principal(animal)
            self._create_uploaded_image(
                animal=animal,
                uploaded_file=foto_principal,
                principal=True,
                ordem=0,
            )

        ordem_inicial = animal.imagens.filter(principal=False).count()
        for indice, foto_extra in enumerate(fotos_extras, start=ordem_inicial + 1):
            self._create_uploaded_image(
                animal=animal,
                uploaded_file=foto_extra,
                principal=False,
                ordem=indice,
            )

    def _delete_existing_principal(self, animal):
        imagem_principal = animal.imagens.filter(principal=True).first()
        if imagem_principal:
            if imagem_principal.imagem:
                imagem_principal.imagem.delete(save=False)
            imagem_principal.delete()

    def _create_uploaded_image(self, animal, uploaded_file, principal, ordem):
        AnimalImagem.objects.create(
            animal=animal,
            principal=principal,
            ordem=ordem,
            imagem_arquivo=uploaded_file.read(),
            imagem_content_type=getattr(uploaded_file, "content_type", "") or "image/jpeg",
            imagem_nome=getattr(uploaded_file, "name", "")[:255],
        )
        uploaded_file.seek(0)

    def _get_uploaded_files(self, field_name):
        if hasattr(self.files, "getlist"):
            return self.files.getlist(field_name)
        uploaded_files = self.files.get(field_name, [])
        if not uploaded_files:
            return []
        if isinstance(uploaded_files, (list, tuple)):
            return list(uploaded_files)
        return [uploaded_files]

    def _validate_image_file(self, image_file, field_name):
        try:
            with Image.open(image_file) as image:
                image.verify()
        except (UnidentifiedImageError, OSError):
            raise forms.ValidationError("Envie apenas arquivos de imagem válidos.") from None
        finally:
            image_file.seek(0)


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

import io
import tempfile

from django.contrib.auth.models import User
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import TestCase, override_settings
from django.urls import reverse
from django.utils.datastructures import MultiValueDict

from .forms import AnimalForm, RegisterForm
from .models import Animal, AnimalImagem, Profile


def build_test_image(name="foto.jpg", color=(240, 180, 80)):
    from PIL import Image

    file_obj = io.BytesIO()
    image = Image.new("RGB", (32, 32), color)
    image.save(file_obj, format="JPEG")
    file_obj.seek(0)
    return SimpleUploadedFile(name, file_obj.read(), content_type="image/jpeg")


TEMP_MEDIA_ROOT = tempfile.mkdtemp()


@override_settings(MEDIA_ROOT=TEMP_MEDIA_ROOT)
class AnimalFormTests(TestCase):
    def get_valid_data(self):
        return {
            "nome": "Luna",
            "tipo": "Gato",
            "idade": 2,
            "sexo": "Fêmea",
            "porte": "Pequeno",
            "pelagem": "Branca",
            "data_resgate": "2026-03-20",
            "v8_v10": "on",
            "antirrabica": "on",
            "giardia": "",
            "leucemia": "",
            "castrado": "on",
            "vermifugado": "on",
            "status_saude": "Saudável.",
            "caracteristicas": "Dócil e acostumada com apartamento.",
            "localizacao": "São Paulo",
            "contato": "11999999999",
            "status": "disponivel",
            "destaque": "on",
        }

    def test_save_creates_principal_and_extra_images(self):
        form = AnimalForm(
            data=self.get_valid_data(),
            files=MultiValueDict(
                {
                    "foto_principal_upload": [build_test_image("principal.jpg")],
                    "fotos_extras": [build_test_image("extra-1.jpg"), build_test_image("extra-2.jpg")],
                }
            ),
        )

        self.assertTrue(form.is_valid(), form.errors)
        animal = form.save()

        self.assertEqual(Animal.objects.count(), 1)
        self.assertEqual(AnimalImagem.objects.filter(animal=animal).count(), 3)
        self.assertTrue(AnimalImagem.objects.filter(animal=animal, principal=True).exists())
        self.assertEqual(AnimalImagem.objects.filter(animal=animal, principal=False).count(), 2)
        imagem_principal = AnimalImagem.objects.get(animal=animal, principal=True)
        self.assertTrue(imagem_principal.imagem_arquivo)
        self.assertEqual(imagem_principal.imagem_content_type, "image/jpeg")
        self.assertTrue(animal.foto_url.startswith("/animal-imagem/"))

    def test_first_extra_becomes_principal_when_main_image_is_missing(self):
        form = AnimalForm(
            data=self.get_valid_data(),
            files=MultiValueDict({"fotos_extras": [build_test_image("extra-unica.jpg")]}),
        )

        self.assertTrue(form.is_valid(), form.errors)
        animal = form.save()

        imagem_principal = AnimalImagem.objects.get(animal=animal, principal=True)
        self.assertEqual(imagem_principal.imagem_nome, "extra-unica.jpg")
        self.assertTrue(imagem_principal.url.startswith("/animal-imagem/"))

    def test_uploaded_image_is_served_by_internal_route(self):
        form = AnimalForm(
            data=self.get_valid_data(),
            files=MultiValueDict({"foto_principal_upload": [build_test_image("principal.jpg")]}),
        )

        self.assertTrue(form.is_valid(), form.errors)
        animal = form.save()
        imagem_principal = AnimalImagem.objects.get(animal=animal, principal=True)

        response = self.client.get(reverse("animal-imagem", args=[imagem_principal.pk]))

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response["Content-Type"], "image/jpeg")
        self.assertGreater(len(response.content), 0)


class RegisterFormTests(TestCase):
    def test_regular_account_does_not_require_company_fields(self):
        form = RegisterForm(
            data={
                "account_type": "pessoa",
                "username": "adotante",
                "email": "adotante@example.com",
                "password1": "senha-forte-123",
                "password2": "senha-forte-123",
                "nome_completo": "Pessoa Comum",
                "telefone": "11999999999",
                "endereco": "",
                "cep": "",
                "responsavel": "",
            }
        )

        self.assertTrue(form.is_valid(), form.errors)
        user = form.save()

        profile = Profile.objects.get(user=user)
        self.assertFalse(profile.empresa)
        self.assertEqual(profile.nome_completo, "Pessoa Comum")

    def test_company_account_requires_company_fields(self):
        form = RegisterForm(
            data={
                "account_type": "empresa",
                "username": "abrigo",
                "email": "abrigo@example.com",
                "password1": "senha-forte-123",
                "password2": "senha-forte-123",
                "nome_completo": "Abrigo Esperanca",
                "telefone": "11999999999",
                "endereco": "",
                "cep": "",
                "responsavel": "",
            }
        )

        self.assertFalse(form.is_valid())
        self.assertIn("endereco", form.errors)
        self.assertIn("cep", form.errors)
        self.assertIn("responsavel", form.errors)

    def test_company_account_is_persisted_as_empresa(self):
        form = RegisterForm(
            data={
                "account_type": "empresa",
                "username": "ong-centro",
                "email": "ong@example.com",
                "password1": "senha-forte-123",
                "password2": "senha-forte-123",
                "nome_completo": "ONG Centro",
                "telefone": "11999999999",
                "endereco": "Rua Principal, 100",
                "cep": "01000-000",
                "responsavel": "Maria Silva",
            }
        )

        self.assertTrue(form.is_valid(), form.errors)
        user = form.save()

        self.assertTrue(User.objects.filter(username="ong-centro").exists())
        profile = Profile.objects.get(user=user)
        self.assertTrue(profile.empresa)
        self.assertEqual(profile.responsavel, "Maria Silva")

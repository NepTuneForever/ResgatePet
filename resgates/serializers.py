from rest_framework import serializers

from .models import Animal, AnimalImagem, SolicitacaoAdocao


class AnimalImagemSerializer(serializers.ModelSerializer):
    imagem = serializers.ImageField(read_only=True)

    class Meta:
        model = AnimalImagem
        fields = ["id", "imagem", "principal", "ordem"]


class AnimalSerializer(serializers.ModelSerializer):
    abrigo = serializers.SerializerMethodField()
    disponivel_para_adocao = serializers.BooleanField(read_only=True)
    foto = serializers.SerializerMethodField()
    imagens = AnimalImagemSerializer(many=True, read_only=True)

    class Meta:
        model = Animal
        fields = [
            "id",
            "nome",
            "tipo",
            "idade",
            "sexo",
            "porte",
            "pelagem",
            "data_resgate",
            "status_saude",
            "caracteristicas",
            "localizacao",
            "contato",
            "foto",
            "imagens",
            "status",
            "destaque",
            "criado_em",
            "abrigo",
            "disponivel_para_adocao",
        ]

    def get_abrigo(self, obj):
        return obj.nome_abrigo

    def get_foto(self, obj):
        return obj.foto_url


class SolicitacaoAdocaoSerializer(serializers.ModelSerializer):
    animal = serializers.CharField(source="animal.nome", read_only=True)
    adotante = serializers.CharField(source="adotante.username", read_only=True)

    class Meta:
        model = SolicitacaoAdocao
        fields = [
            "id",
            "animal",
            "adotante",
            "nome_contato",
            "email_contato",
            "telefone_contato",
            "mensagem",
            "status",
            "criado_em",
            "atualizado_em",
        ]

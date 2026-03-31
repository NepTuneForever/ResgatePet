from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("resgates", "0006_alter_animal_foto_animalimagem"),
    ]

    operations = [
        migrations.AlterField(
            model_name="animalimagem",
            name="imagem",
            field=models.ImageField(blank=True, upload_to="animais/"),
        ),
        migrations.AddField(
            model_name="animalimagem",
            name="imagem_arquivo",
            field=models.BinaryField(blank=True, null=True),
        ),
        migrations.AddField(
            model_name="animalimagem",
            name="imagem_content_type",
            field=models.CharField(blank=True, default="", max_length=100),
        ),
        migrations.AddField(
            model_name="animalimagem",
            name="imagem_nome",
            field=models.CharField(blank=True, default="", max_length=255),
        ),
    ]

from django.apps import AppConfig


class ResgatesConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = 'resgates'

    def ready(self):
        import resgates.signals  # noqa: F401

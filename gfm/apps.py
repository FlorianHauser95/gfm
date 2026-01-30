from django.apps import AppConfig


class GfmConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'gfm'

    def ready(self):
        from . import signals  # noqa
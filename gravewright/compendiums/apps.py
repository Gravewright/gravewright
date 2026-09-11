from django.apps import AppConfig


class CompendiumsConfig(AppConfig):
    name = "gravewright.compendiums"
    label = "gravewright_compendiums"

    def ready(self):
        from . import signals

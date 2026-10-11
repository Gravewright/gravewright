from django.apps import AppConfig


class PdfSystemConfig(AppConfig):
    name = "gravewright.pdf_system"
    label = "gravewright_pdf_system"

    def ready(self):
        from .system import register
        register()

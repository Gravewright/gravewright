"""Build a verified activation plan without importing the new packages."""
from django.core.management.base import BaseCommand
from gravewright.modules.server_apps import plan
from scripts.update_supervisor import write


class Command(BaseCommand):
    def add_arguments(self, parser):
        parser.add_argument('module_id')
        parser.add_argument('version')
        parser.add_argument('enabled', choices=['true', 'false'])
        parser.add_argument('destination')

    def handle(self, **options):
        write(options['destination'], plan(options['module_id'], options['version'], options['enabled'] == 'true'))

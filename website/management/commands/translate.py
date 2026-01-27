"""
    translate.py
    Management script for Django to easily run the "makemessages"-command and "compilemessages"-command for all files in your Django application.
    Add LANGUAGE_IGNORE_PATTERNS = [] to you settings file for custom ignore patterns
"""
from django.core.management.base import BaseCommand
from django.core import management
from django.utils.translation import to_locale


class Command(BaseCommand):
    help = "Runs command makemessages for all domains"
    language_names = None

    def add_arguments(self, parser):
        parser.add_argument(
            "--compile-all",
            action="store_true",
            dest="compile-all",
            default=False,
            help="Compiles .po files to .mo files (compilemessages only)"
        )

    def handle(self, *args, **options):
        ignore_patterns = self.SETTINGS.LANGUAGE_IGNORE_PATTERNS
        self.language_names = [to_locale(language_tuple[0]) for language_tuple in self.SETTINGS.LANGUAGES]

        if options["compile-all"]:
            self.stdout.write("Compiling All Translation Files")
            management.call_command("compilemessages", locale=self.language_names)
            return
        else:
            self.stdout.write("Translating Python and template files")
            management.call_command("makemessages", locale=self.language_names, domain="django", ignore=ignore_patterns)


"""
    translate.py
    Management script for Django to easily run the
    'makemessages'-command and 'compilemessages'-command for all
    files in your Django application.

    Put in any registered django app in the location
    <app>/management/commands/translate.py
    and then use python manage.py translate
    to run makemessages on all files in your project

    Made by Johan Niklasson
    https://github.com/vonNiklasson
    https://gist.github.com/vonNiklasson/5fec59ad635ff3083f914188cb6736cf

    Modified by Charles Williams
    https://github.com/charlwillia6
    https://gist.github.com/charlwillia6/9b1e311dd6747c867631e6cde1c527aa

    Add LANGUAGE_IGNORE_PATTERNS = [] to you settings file for custom ignore
    patterns
"""
import os
from django.conf import settings as django_settings
from django.core.management.base import BaseCommand
from django.core import management


class Command(BaseCommand):
    settings = django_settings
    full_locale_path = ""
    ignore_patterns = ['node_modules/*']
    help = "Runs command makemessages for all domains"
    languages = None
    is_shared = False

    def add_arguments(self, parser):
        parser.add_argument(
            '--no-django',
            action='store_true',
            dest='no-django',
            default=False,
            help='Makes the translation for python and template files only (excludes JavaScript translation unless stated)'
        )

        parser.add_argument(
            '--no-djangojs',
            action='store_true',
            dest='no-djangojs',
            default=False,
            help='Makes the translation for javascript files only (excludes regular translation unless stated)'
        )

        parser.add_argument(
            '--compile-all',
            action='store_true',
            dest='compile-all',
            default=False,
            help='Compiles .po files to .mo files (compilemessages only)'
        )

    def handle(self, *args, **options):
        if self.settings is None:
            raise Exception("settings is None")

        if hasattr(self.settings, 'LANGUAGE_IGNORE_PATTERNS'):
            ignore_patterns = self.settings.LANGUAGE_IGNORE_PATTERNS
        else:
            ignore_patterns = Command.ignore_patterns

        self.languages = [seq[0] for seq in self.settings.LANGUAGES]
        self.full_locale_path = os.path.join(self.settings.BASE_DIR, "search_filter_sort", "locale")

        po_list = []
        should_make_django = True
        should_make_djangojs = True
        should_compile = False

        self.rename_locale_folders("_", "-")

        if options['no-django']:
            should_make_django = False

        if options['no-djangojs']:
            should_make_djangojs = False

        if options['compile-all']:
            should_make_django = False
            should_make_djangojs = False
            should_compile = True

        print(self.languages)

        if should_make_django:
            self.stdout.write("Translating Python and template files")
            management.call_command('makemessages', locale=self.languages, domain='django', ignore=ignore_patterns)
            po_list.append("django.po")

        if should_make_djangojs:
            self.stdout.write("Translating JavaScript files")
            management.call_command('makemessages', locale=self.languages, domain='djangojs', ignore=ignore_patterns)
            po_list.append("djangojs.po")

        if should_compile:
            self.stdout.write("Compiling All Translation Files")
            management.call_command('compilemessages', local=self.languages)

        self.rename_locale_folders("-", "_")

    def rename_locale_folders(self, old_folder_splitter, new_folder_splitter):
        for language in self.languages:
            old_language_folder_name = language.replace(new_folder_splitter, old_folder_splitter)
            new_language_folder_name = language.replace(old_folder_splitter, new_folder_splitter)

            old_full_locale_file_path = os.path.join(self.full_locale_path, old_language_folder_name)
            new_full_locale_file_path = os.path.join(self.full_locale_path, new_language_folder_name)
            os.rename(old_full_locale_file_path, new_full_locale_file_path)

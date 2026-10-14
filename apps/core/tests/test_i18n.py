from django.core.management.base import BaseCommand, CommandError

from apps.core import i18n_tools


class Command(BaseCommand):
    help = "Compile locale/*/LC_MESSAGES/django.po to .mo (no GNU gettext needed)."

    def add_arguments(self, parser):
        parser.add_argument(
            "--check",
            action="store_true",
            help="Write nothing; fail if a .mo is stale or a source string has no translation.",
        )

    def handle(self, *args, check=False, **options):
        if not check:
            for path in i18n_tools.compile_all():
                self.stdout.write(f"compiled {path}")
            return
        problems = [f"stale catalog: {path}" for path in i18n_tools.stale_catalogs()]
        problems += [f"untranslated ({lang}): {text!r}" for lang, text in i18n_tools.untranslated()]
        if problems:
            raise CommandError("\n".join(problems))
        self.stdout.write("Translations are complete and compiled.")

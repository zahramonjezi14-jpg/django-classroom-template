"""Create one learning page in an app while keeping filenames student-chosen."""

from django.core.management.base import BaseCommand, CommandError

from classroom_tools.scaffolding import ClassroomError, create_page


class Command(BaseCommand):
    help = "Create a template, a view and a URL for a student-chosen page name."

    def add_arguments(self, parser):
        parser.add_argument("app_name", help="نام اپلیکیشن")
        parser.add_argument("page_name", help="نام صفحه، مثلاً about")

    def handle(self, *args, **options):
        try:
            changes = create_page(options["app_name"], options["page_name"])
        except ClassroomError as exc:
            raise CommandError(str(exc)) from exc
        self.stdout.write("\n📄 صفحه جدید ساخته شد. ببین چه اتفاقی افتاد:\n")
        for step in changes:
            self.stdout.write("  ✅ " + step)
        self.stdout.write("\nحالا فایل HTML را به سلیقه خودت تغییر بده.\n")

"""The ordinary Django startapp command, with visible educational scaffolding."""

from django.core.management.commands.startapp import Command as DjangoStartApp
from django.core.management.base import CommandError

from classroom_tools.scaffolding import ClassroomError, ROOT, complete_app, project_files


class Command(DjangoStartApp):
    help = "Create a standard Django app and explain the classroom setup steps."

    def handle(self, **options):
        name = options.get("name")
        if options.get("directory"):
            raise CommandError(
                "در محیط آموزشی، startapp را بدون مسیر اضافی اجرا کن."
            )
        try:
            project_files()
        except ClassroomError as exc:
            raise CommandError(str(exc)) from exc
        if name and (ROOT / name).exists():
            raise CommandError("پوشه‌ای با همین نام وجود دارد؛ نام تازه‌ای انتخاب کن.")
        super().handle(**options)
        try:
            changes = complete_app(name)
        except ClassroomError as exc:
            raise CommandError(str(exc)) from exc
        self.stdout.write("\n🎉 اپلیکیشن ساخته شد! این تغییرات را یاد بگیر:\n")
        for step in changes:
            self.stdout.write("  ✅ " + step)
        self.stdout.write(
            "\nحالا فایل HTML خودت را ویرایش کن یا صفحه تازه بساز:\n"
            + f"  python manage.py newpage {name} about\n"
            + "برای نمایش سایت: python manage.py runserver 0.0.0.0:8000\n"
        )

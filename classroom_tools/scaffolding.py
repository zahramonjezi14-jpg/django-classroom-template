"""Safe, predictable scaffolding for an introductory Django classroom.

The learner still executes real Django commands. We only create starter files,
register URLs/apps, and describe each change. Existing student files are never
overwritten by the app/page generator.
"""

from __future__ import annotations

import keyword
import re
from pathlib import Path


ROOT = Path(__file__).resolve().parent.parent


class ClassroomError(Exception):
    """A helpful error that can be shown directly to students."""


def project_files() -> tuple[Path, Path]:
    manage_path = ROOT / "manage.py"
    if not manage_path.exists():
        raise ClassroomError(
            "ابتدا پروژه را بساز: django-admin startproject mysite ."
        )
    source = manage_path.read_text(encoding="utf-8")
    match = re.search(
        r"setdefault\(\s*['\"]DJANGO_SETTINGS_MODULE['\"]\s*,\s*['\"]([\w.]+)['\"]",
        source,
    )
    if not match:
        raise ClassroomError("نام پروژه در manage.py پیدا نشد.")
    package_name = match.group(1).removesuffix(".settings")
    if match.group(1) != f"{package_name}.settings":
        raise ClassroomError("ساختار settings.py این پروژه استاندارد نیست.")
    package = ROOT.joinpath(*package_name.split("."))
    settings_path = package / "settings.py"
    urls_path = package / "urls.py"
    if not settings_path.is_file() or not urls_path.is_file():
        raise ClassroomError("فایل‌های settings.py و urls.py پیدا نشدند.")
    return settings_path, urls_path


def configure_project() -> list[str]:
    """Idempotently adjust the project created by django-admin startproject."""
    settings_path, _ = project_files()
    source = settings_path.read_text(encoding="utf-8")
    changes: list[str] = []

    if not re.search(r"['\"]classroom_tools['\"]\s*,", source):
        anchor = re.search(r"(?m)^INSTALLED_APPS\s*=\s*\[\s*\n", source)
        if not anchor:
            raise ClassroomError("فهرست INSTALLED_APPS در settings.py پیدا نشد.")
        source = (
            source[: anchor.end()]
            + '    "classroom_tools",\n'
            + source[anchor.end() :]
        )
        changes.append('settings.py ← "classroom_tools" به INSTALLED_APPS اضافه شد')

    if "BASE_DIR / \"templates\"" not in source:
        match = re.search(r"['\"]DIRS['\"]\s*:\s*\[\s*\]", source)
        if not match:
            raise ClassroomError("گزینه DIRS در TEMPLATES پیدا نشد.")
        source = source[: match.start()] + "'DIRS': [BASE_DIR / \"templates\"]" + source[match.end() :]
        changes.append("settings.py ← پوشه templates به تنظیمات قالب‌ها اضافه شد")

    allowed_line = 'ALLOWED_HOSTS = ["localhost", "127.0.0.1", ".app.github.dev"]'
    if ".app.github.dev" not in source:
        match = re.search(r"(?m)^ALLOWED_HOSTS\s*=.*$", source)
        if not match:
            raise ClassroomError("گزینه ALLOWED_HOSTS در settings.py پیدا نشد.")
        source = source[: match.start()] + allowed_line + source[match.end() :]
        changes.append("settings.py ← پیش‌نمایش Codespaces مجاز شد")

    if "CSRF_TRUSTED_ORIGINS" not in source:
        source += '\nCSRF_TRUSTED_ORIGINS = ["https://*.app.github.dev"]\n'
        changes.append("settings.py ← تنظیم فرم‌های پیش‌نمایش انجام شد")

    # A generated SECRET_KEY must not be checked into a public student repo.
    if "DJANGO_SECRET_KEY" not in source:
        match = re.search(r"(?m)^SECRET_KEY\s*=.*$", source)
        if not match:
            raise ClassroomError("گزینه SECRET_KEY در settings.py پیدا نشد.")
        source = (
            source[: match.start()]
            + 'SECRET_KEY = os.environ.get("DJANGO_SECRET_KEY", "django-insecure-classroom-only-change-before-deployment")'
            + source[match.end() :]
        )
        source = "import os\n\n" + source
        changes.append("settings.py ← کلید توسعه جایگزین شد؛ هنگام انتشار کلید محرمانه لازم است")

    if changes:
        settings_path.write_text(source, encoding="utf-8")
    templates = ROOT / "templates"
    templates.mkdir(exist_ok=True)
    (templates / ".gitkeep").touch(exist_ok=True)
    return changes


def valid_name(name: str) -> bool:
    return name.isidentifier() and not keyword.iskeyword(name)


def _add_to_installed_apps(app_name: str, settings_path: Path) -> None:
    content = settings_path.read_text(encoding="utf-8")
    if re.search(r"['\"]" + re.escape(app_name) + r"['\"]\s*,", content):
        return
    match = re.search(r"(?m)^INSTALLED_APPS\s*=\s*\[\s*\n", content)
    if not match:
        raise ClassroomError("INSTALLED_APPS قابل ویرایش نیست.")
    content = content[: match.end()] + f'    "{app_name}",\n' + content[match.end() :]
    settings_path.write_text(content, encoding="utf-8")


def _include_app_url(app_name: str, project_urls: Path) -> str:
    content = project_urls.read_text(encoding="utf-8")
    patterns = re.search(r"(?m)^urlpatterns\s*=\s*\[\s*\n", content)
    if not patterns:
        raise ClassroomError("فهرست urlpatterns در urls.py پیدا نشد.")
    # Django's generated module docstring includes a sample include('blog.urls').
    # Only inspect the actual urlpatterns, not instructional comments/docstrings.
    routes = content[patterns.end() :]
    if f'include("{app_name}.urls")' in routes or f"include('{app_name}.urls')" in routes:
        return f"/{app_name}/"

    import_line = re.search(r"(?m)^from django\.urls import ([^\n#]+)$", content)
    if not import_line:
        raise ClassroomError("خط import مربوط به django.urls پیدا نشد.")
    imports = [part.strip() for part in import_line.group(1).split(",")]
    if "include" not in imports:
        imports.append("include")
        content = (
            content[: import_line.start()]
            + "from django.urls import " + ", ".join(imports)
            + content[import_line.end() :]
        )

    # The first app becomes the home page; subsequent apps use their own path.
    patterns = re.search(r"(?m)^urlpatterns\s*=\s*\[\s*\n", content)
    if not patterns:
        raise ClassroomError("فهرست urlpatterns در urls.py پیدا نشد.")
    first_app = not re.search(
        r"\binclude\s*\(\s*['\"][\w.]+\.urls['\"]\s*\)",
        content[patterns.end() :],
    )
    route = "" if first_app else f"{app_name}/"
    match = patterns
    content = (
        content[: match.end()]
        + f'    path("{route}", include("{app_name}.urls")),\n'
        + content[match.end() :]
    )
    project_urls.write_text(content, encoding="utf-8")
    return "/" + route


def _html_template(app_name: str, page_name: str) -> str:
    title = f"صفحه {page_name} از اپ {app_name}"
    return f'''<!DOCTYPE html>
<html lang="fa" dir="rtl">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>{title}</title>
  <style>
    * {{ box-sizing: border-box; }}
    body {{ margin: 0; min-height: 100vh; padding: 24px; display: grid;
           place-items: center; font-family: Tahoma, sans-serif;
           background: linear-gradient(135deg, #e0f2fe, #f5f3ff); color: #172554; }}
    main {{ width: min(100%, 620px); padding: 32px; border-radius: 24px;
            background: white; box-shadow: 0 12px 40px #1e3a8a1c; }}
    h1 {{ font-size: clamp(1.5rem, 5vw, 2.2rem); }}
    p {{ line-height: 2; }}
  </style>
</head>
<body>
  <main>
    <h1>🎉 {title}</h1>
    <p>آفرین! این صفحه با جنگوی واقعی اجرا شده است.</p>
    <p>حالا نوبت توست که متن، رنگ‌ها و ظاهر صفحه را تغییر بدهی.</p>
  </main>
</body>
</html>
'''


def complete_app(app_name: str) -> list[str]:
    """Called only after Django successfully created the app folder."""
    settings_path, project_urls = project_files()
    app_dir = ROOT / app_name
    if not (app_dir / "apps.py").exists():
        raise ClassroomError("ابتدا باید Django پوشه اپلیکیشن را بسازد.")

    app_urls = app_dir / "urls.py"
    if app_urls.exists():
        raise ClassroomError("فایل urls.py از قبل وجود دارد؛ چیزی بازنویسی نشد.")
    views_path = app_dir / "views.py"
    views_before = views_path.read_text(encoding="utf-8")
    if re.search(r"(?m)^def index\s*\(", views_before):
        raise ClassroomError("تابع index از قبل وجود دارد؛ چیزی بازنویسی نشد.")

    # The custom command is only used immediately after startapp created a new app.
    app_urls.write_text(
        "from django.urls import path\nfrom . import views\n\n"
        + f'app_name = "{app_name}"\n\n'
        + 'urlpatterns = [\n    path("", views.index, name="index"),\n]\n',
        encoding="utf-8",
    )
    views_path.write_text(
        "from django.shortcuts import render\n\n\n"
        + "def index(request):\n"
        + f'    return render(request, "{app_name}/index.html")\n',
        encoding="utf-8",
    )
    template_dir = app_dir / "templates" / app_name
    template_dir.mkdir(parents=True, exist_ok=False)
    (template_dir / "index.html").write_text(
        _html_template(app_name, "index"), encoding="utf-8"
    )
    _add_to_installed_apps(app_name, settings_path)
    route = _include_app_url(app_name, project_urls)
    return [
        f"Django ← پوشه {app_name}/ را با فایل‌های استاندارد ساخت",
        f"settings.py ← نام اپ {app_name} در INSTALLED_APPS ثبت شد",
        f"{app_name}/templates/{app_name}/index.html ← صفحه اولیه ساخته شد",
        f"{app_name}/views.py ← تابع index برای نمایش قالب اضافه شد",
        f"{app_name}/urls.py ← آدرس صفحه به تابع index متصل شد",
        f"urls.py اصلی ← آدرس {route} به اپ {app_name} متصل شد",
    ]


def create_page(app_name: str, page_name: str) -> list[str]:
    if not valid_name(app_name) or not valid_name(page_name):
        raise ClassroomError("نام اپ و صفحه باید انگلیسی و معتبر برای پایتون باشند.")
    if page_name == "index":
        raise ClassroomError("صفحه index از قبل ساخته شده؛ نام دیگری انتخاب کن.")
    app_dir = ROOT / app_name
    views = app_dir / "views.py"
    urls = app_dir / "urls.py"
    target = app_dir / "templates" / app_name / f"{page_name}.html"
    if not views.exists() or not urls.exists():
        raise ClassroomError("ابتدا اپ را با python manage.py startapp بساز.")
    if target.exists():
        raise ClassroomError("این فایل صفحه از قبل وجود دارد؛ چیزی بازنویسی نشد.")
    views_text = views.read_text(encoding="utf-8")
    urls_text = urls.read_text(encoding="utf-8")
    if re.search(rf"(?m)^def\s+{re.escape(page_name)}\s*\(", views_text):
        raise ClassroomError("تابعی با این نام از قبل وجود دارد.")
    if re.search(rf"name\s*=\s*['\"]{re.escape(page_name)}['\"]", urls_text):
        raise ClassroomError("آدرسی با این نام از قبل وجود دارد.")
    pattern = re.search(r"(?m)^urlpatterns\s*=\s*\[\s*\n", urls_text)
    if not pattern:
        raise ClassroomError("فهرست urlpatterns در فایل اپ قابل ویرایش نیست.")
    urls_text = (
        urls_text[: pattern.end()]
        + f'    path("{page_name}/", views.{page_name}, name="{page_name}"),\n'
        + urls_text[pattern.end() :]
    )
    target.write_text(_html_template(app_name, page_name), encoding="utf-8")
    views.write_text(
        views_text.rstrip()
        + f'\n\n\ndef {page_name}(request):\n    return render(request, "{app_name}/{page_name}.html")\n',
        encoding="utf-8",
    )
    urls.write_text(urls_text, encoding="utf-8")
    return [
        f"{app_name}/templates/{app_name}/{page_name}.html ← صفحه ساخته شد",
        f"{app_name}/views.py ← تابع {page_name} اضافه شد",
        f"{app_name}/urls.py ← مسیر {page_name}/ ثبت شد",
    ]

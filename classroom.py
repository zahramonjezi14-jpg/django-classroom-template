"""Run once after django-admin startproject to prepare the teaching environment."""

from __future__ import annotations

import argparse

from classroom_tools.scaffolding import ClassroomError, configure_project


def main() -> None:
    parser = argparse.ArgumentParser(description="ابزار آماده‌سازی کلاس جنگو")
    parser.add_argument("action", choices=["prepare"], help="آماده کردن پروژه پس از startproject")
    args = parser.parse_args()
    try:
        changes = configure_project()
    except ClassroomError as exc:
        parser.error(str(exc))
    print("\n🎓 محیط آموزشی جنگو آماده است!")
    if changes:
        for step in changes:
            print("  ✅", step)
    else:
        print("  ✅ قبلاً آماده شده بود؛ تغییری لازم نیست.")
    print("\nقدم بعد: python manage.py startapp blog")
    print("(به جای blog نام اپ دلخواه خودت را بنویس.)\n")


if __name__ == "__main__":
    main()

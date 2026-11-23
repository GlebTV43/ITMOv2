from pathlib import Path

from django.conf import settings
from django.contrib.auth import get_user_model
from django.core.files import File
from django.core.management.base import BaseCommand, CommandError

from books.models import Book

DEMO_PASSWORD = "demo-books-only-8"
LISTINGS = (
    ("reader", "Марсианин", "Энди Вейер", "martian.jpg",
     "Мягкая обложка, страницы чистые, на корешке небольшой залом.",
     "Классика приключений или современная фантастика."),
    ("owner", "Граф Монте-Кристо", "Александр Дюма", "monte.jpg",
     "Твёрдый переплёт, на уголках видны следы чтения.",
     "Исторический роман, современная проза."),
    ("owner", "Sapiens. Краткая история человечества", "Юваль Ной Харари", "sapiens.jpg",
     "Аккуратно прочитана, обложка целая.",
     "Научпоп о космосе или о природе."),
    ("owner", "Дюна", "Фрэнк Герберт", "dune.jpg",
     "Твёрдый переплёт, есть небольшие потёртости на обложке. Страницы чистые.",
     "Научная фантастика, особенно «Марсианин»."),
)


class Command(BaseCommand):
    help = "Create two local demo accounts and four sample listings."

    def handle(self, *args, **options):
        if not settings.DEBUG:
            raise CommandError("Demo data can only be created with DEBUG enabled.")

        users = {}
        for key, name in (("reader", "Маша"), ("owner", "Илья")):
            email = f"{key}@example.invalid"
            user, created = get_user_model().objects.get_or_create(
                username=email, defaults={"email": email, "first_name": name},
            )
            if created:
                user.set_password(DEMO_PASSWORD)
                user.save(update_fields=["password"])
            users[key] = user

        demo_photos = Path(__file__).resolve().parents[2] / "static" / "books" / "demo"
        for key, title, author, filename, description, wanted in LISTINGS:
            owner = users[key]
            if Book.objects.filter(owner=owner, title=title).exists():
                continue
            with (demo_photos / filename).open("rb") as photo:
                Book.objects.create(
                    owner=owner, title=title, author=author, photo=File(photo, name=filename),
                    description=description, wanted=wanted,
                )
        self.stdout.write(self.style.SUCCESS("Demo accounts and listings are ready."))

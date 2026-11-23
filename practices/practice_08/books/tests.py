import re
from io import BytesIO
from tempfile import TemporaryDirectory

from django.core import mail
from django.contrib.auth import get_user_model
from django.core import signing
from django.core.cache import cache
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import Client, TestCase, override_settings
from django.urls import reverse
from PIL import Image

from . import accounts, exchanges
from .models import Book, Exchange

User = get_user_model()


class AccountsTest(TestCase):
    def setUp(self):
        cache.clear()

    def test_registration_requires_email_link_and_password_is_hashed(self):
        self.client.post(reverse("register"), {"email": "READER@example.com"})
        user = User.objects.get(username="reader@example.com")
        self.assertFalse(user.is_active)
        self.assertFalse(user.has_usable_password())
        path = re.search(r"/activate/[^\s]+/", mail.outbox[0].body).group()
        self.assertEqual(self.client.get(path).status_code, 200)
        user.refresh_from_db()
        self.assertFalse(user.is_active)

        password = "a-passphrase-for-my-bookcase-17"
        self.assertRedirects(self.client.post(path, {
            "name": "Читатель", "new_password1": password, "new_password2": password,
        }), reverse("login"))
        user.refresh_from_db()
        self.assertTrue(user.is_active)
        self.assertNotEqual(user.password, password)
        self.assertTrue(user.check_password(password))
        self.assertEqual(self.client.get(path).status_code, 400)
        self.assertRedirects(self.client.post(reverse("login"), {
            "username": "READER@example.com", "password": password,
        }), reverse("catalog"))
        self.assertNotContains(self.client.get(reverse("profile", args=[user.pk])), user.email)

    def test_expired_and_invalid_links(self):
        user = User.objects.create(username="pending@example.com", is_active=False)
        token = signing.dumps(user.pk, salt=accounts.TOKEN_SALT)
        with override_settings():
            from unittest.mock import patch
            import time

            with patch("django.core.signing.time.time", return_value=time.time() + 86401):
                self.assertEqual(self.client.get(reverse("activate", args=[token])).status_code, 400)
        self.assertEqual(self.client.get(reverse("activate", args=["wrong"])).status_code, 400)


class BookFlowTest(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.anna = User.objects.create(username="anna@example.com", first_name="Анна")
        cls.boris = User.objects.create(username="boris@example.com", first_name="Борис")
        cls.third = User.objects.create(username="third@example.com", first_name="Третий")
        cls.offered = cls.book(cls.anna, "Дюна", "Фрэнк Герберт", "Солярис")
        cls.requested = cls.book(cls.boris, "Солярис", "Станислав Лем", "Дюна")
        cls.other = cls.book(cls.third, "Пикник на обочине", "Стругацкие", "Дюна")

    @staticmethod
    def book(owner, title, author, wanted):
        return Book.objects.create(owner=owner, title=title, author=author, wanted=wanted,
                                   description="Есть потёртости", photo="covers/test.jpg")

    def test_cyrillic_search_and_detail_alternatives(self):
        response = self.client.get(reverse("catalog"), {"q": "СОЛЯРИС ЛЕМ", "offer": "ДЮНА"})
        self.assertContains(response, "Солярис")
        self.assertNotContains(response, "Пикник на обочине")
        response = self.client.get(reverse("book", args=[self.requested.pk]))
        self.assertContains(response, "Другие варианты")
        self.assertContains(response, "Пикник на обочине")

    def test_real_photo_upload_and_invalid_content(self):
        self.client.force_login(self.anna)
        data = {"title": "Книга", "author": "Автор", "description": "Целая", "wanted": "Другую"}
        with TemporaryDirectory() as media, override_settings(MEDIA_ROOT=media):
            bad = SimpleUploadedFile("fake.png", b"text", content_type="image/png")
            self.assertContains(self.client.post(reverse("add_book"), data | {"photo": bad}),
                                "Загрузите корректное фото")
            buffer = BytesIO()
            Image.new("RGB", (80, 60)).save(buffer, format="PNG")
            photo = SimpleUploadedFile("book.png", buffer.getvalue(), content_type="image/png")
            response = self.client.post(reverse("add_book"), data | {"photo": photo})
            item = Book.objects.get(title="Книга")
            self.assertRedirects(response, reverse("book", args=[item.pk]))
            with Image.open(item.photo.path) as output:
                self.assertEqual(output.format, "JPEG")

    def test_exchange_and_public_history(self):
        self.client.force_login(self.anna)
        self.client.post(reverse("propose", args=[self.requested.pk]), {
            "offered": self.offered.pk, "text": "Привет, предлагаю Дюну!",
        })
        item = Exchange.objects.get()
        detail = reverse("exchange", args=[item.pk])
        competing = exchanges.propose(self.third, self.other.pk, self.offered.pk, "Ещё предложение")

        self.client.force_login(self.boris)
        self.assertContains(self.client.get(detail), "Привет, предлагаю Дюну!")
        self.assertRedirects(self.client.post(detail, {"text": "Договорились!"}), detail)
        self.assertContains(self.client.get(detail), "Договорились!")
        self.assertRedirects(self.client.post(self.action(item, "accept")), detail)
        competing.refresh_from_db()
        self.assertEqual(competing.status, Exchange.Status.CANCELLED)
        self.offered.refresh_from_db()
        self.assertEqual(self.offered.status, Book.Status.RESERVED)
        self.client.post(self.action(item, "received"))
        self.client.post(self.action(item, "received"))
        item.refresh_from_db()
        self.assertEqual(item.status, Exchange.Status.ACCEPTED)

        self.client.force_login(self.anna)
        self.client.post(self.action(item, "received"))
        item.refresh_from_db()
        self.requested.refresh_from_db()
        self.assertEqual(item.status, Exchange.Status.COMPLETED)
        self.assertEqual(self.requested.status, Book.Status.EXCHANGED)
        self.client.post(reverse("add_read_book"), {"title": "Солярис", "author": "Станислав Лем"})
        profile = self.client.get(reverse("profile", args=[self.anna.pk]))
        self.assertContains(profile, "Дюна ↔ Солярис")
        self.assertContains(profile, "Солярис · Станислав Лем")

    def test_only_participants_and_csrf_for_actions(self):
        item = exchanges.propose(self.anna, self.offered.pk, self.requested.pk, "Привет!")
        self.client.force_login(self.third)
        self.assertEqual(self.client.get(reverse("exchange", args=[item.pk])).status_code, 404)
        self.assertEqual(self.client.post(self.action(item, "accept")).status_code, 404)

        protected = Client(enforce_csrf_checks=True)
        protected.force_login(self.boris)
        self.assertEqual(protected.post(self.action(item, "accept")).status_code, 403)
        self.assertEqual(protected.get(self.action(item, "accept")).status_code, 405)

    def test_dispute_and_mutual_cancellation_keep_books_consistent(self):
        item = exchanges.propose(self.anna, self.offered.pk, self.requested.pk, "Привет!")
        exchanges.change_status(item.pk, self.boris, "accept")
        exchanges.change_status(item.pk, self.anna, "dispute")
        exchanges.change_status(item.pk, self.anna, "cancel")
        self.offered.refresh_from_db()
        self.assertEqual(self.offered.status, Book.Status.RESERVED)
        with self.assertRaises(exchanges.ExchangeError):
            exchanges.change_status(item.pk, self.anna, "cancel")
        exchanges.change_status(item.pk, self.boris, "cancel")
        item.refresh_from_db()
        self.offered.refresh_from_db()
        self.requested.refresh_from_db()
        self.assertEqual(item.status, Exchange.Status.CANCELLED)
        self.assertEqual(self.offered.status, Book.Status.AVAILABLE)
        self.assertEqual(self.requested.status, Book.Status.AVAILABLE)

    @staticmethod
    def action(item, action):
        return reverse("exchange_action", args=[item.pk, action])
